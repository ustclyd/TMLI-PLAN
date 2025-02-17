import numpy as np
import torch
from PIL import Image,ImageOps
import random
from skimage import exposure
from skimage.util import random_noise

import cv2
from scipy.ndimage.interpolation import map_coordinates
from scipy.ndimage.filters import gaussian_filter


class RandomErase2D(object):
    '''
    Data augmentation method.
    Args:

    '''
    def __init__(self, window_size=(64,64), scale_flag=True, prob=0.5):
        self.window_size = window_size
        self.scale_flag = scale_flag
        self.prob = prob
    
    def __call__(self, sample):
        if self.scale_flag:
            h_factor = np.random.uniform(0.5, 1)
            w_factor = np.random.uniform(0.5, 1)
            max_h, max_w = np.uint8(self.window_size[0]*h_factor),np.uint8(self.window_size[1]*w_factor)
        else:
            max_h, max_w = self.window_size
        image = sample['image']
        mask = sample['mask']

        h,w = image.shape
        roi_window = []
        
        if np.sum(mask) !=0:
            roi_nz = np.nonzero(mask)
            roi_window.append((
                np.maximum((np.amin(roi_nz[0]) - max_h//2), 0),
                np.minimum((np.amax(roi_nz[0]) + max_h//2), h)
            ))

            roi_window.append((
                np.maximum((np.amin(roi_nz[1]) - max_w//2), 0),
                np.minimum((np.amax(roi_nz[1]) + max_w//2), w)
            ))

        else:
            roi_window.append((random.randint(0,64),random.randint(-64,0)))
            roi_window.append((random.randint(0,64),random.randint(-64,0)))
        
        if np.random.uniform(0, 1) > self.prob:
            direction = random.choice(['t','d','l','r'])
            # print(direction)
            if direction == 't':
                image[:roi_window[0][0],:] = 0
            elif direction == 'd':
                image[roi_window[0][1]:,:] = 0
            elif direction == 'l':
                image[:,:roi_window[1][0]] = 0
            elif direction == 'r':
                image[:,roi_window[1][1]:] = 0

        new_sample = {'image': image, 'mask': mask}

        return new_sample





class RandomFlip2D(object):
    '''
    Data augmentation method.
    Flipping the image, including horizontal and vertical flipping.
    Args:
    - mode: string, consisting of 'h' and 'v'. Optional methods and 'hv' is default.
            'h'-> horizontal flipping,
            'v'-> vertical flipping,
            'hv'-> random flipping.

    '''
    def __init__(self, mode='hv'):
        self.mode = mode

    def __call__(self, sample):
        # image: numpy array
        # mask: numpy array
        image = sample['image']
        mask = sample['mask']

        image = Image.fromarray(image)
        mask = Image.fromarray(np.uint8(mask))

        if 'h' in self.mode and 'v' in self.mode:
            random_factor = np.random.uniform(0, 1)
            if random_factor < 0.3:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
                mask = mask.transpose(Image.FLIP_LEFT_RIGHT)
            elif random_factor < 0.6:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                mask = mask.transpose(Image.FLIP_TOP_BOTTOM)

        elif 'h' in self.mode:
            if np.random.uniform(0, 1) > 0.5:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
                mask = mask.transpose(Image.FLIP_LEFT_RIGHT)

        elif 'v' in self.mode:
            if np.random.uniform(0, 1) > 0.5:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                mask = mask.transpose(Image.FLIP_TOP_BOTTOM)
            
        image = np.array(image).astype(np.float32)
        mask = np.array(mask).astype(np.float32)
        new_sample = {'image': image, 'mask': mask}

        return new_sample


class RandomRotate2D(object):
    """
    Data augmentation method.
    Rotating the image with random degree.
    Args:
    - degree: the rotate degree from (-degree , degree)
    Returns:
    - rotated image and mask
    """

    def __init__(self, degree=[-15,-10,-5,0,5,10,15]):
        self.degree = degree

    def __call__(self, sample):
        image = sample['image']
        mask = sample['mask']

        image = Image.fromarray(image)
        mask = Image.fromarray(np.uint8(mask))

        rotate_degree = random.choice(self.degree)
        image = image.rotate(rotate_degree, Image.BILINEAR)
        mask = mask.rotate(rotate_degree, Image.NEAREST)

        image = np.array(image).astype(np.float32)
        mask = np.array(mask).astype(np.float32)
        return {'image': image, 'mask': mask}


class RandomZoom2D(object):
    """
    Data augmentation method.
    Zooming the image with random scale.
    Args:
    - scale: the scale factor from the scale
    Returns:
    - zoomed image and mask, keep original size
    """

    def __init__(self, scale=(0.8,1.2)):
        assert isinstance(scale,tuple)
        self.scale = scale

    def __call__(self, sample):
        image = sample['image']
        mask = sample['mask']

        image = Image.fromarray(image)
        mask = Image.fromarray(np.uint8(mask))

        scale_factor = random.uniform(self.scale[0],self.scale[1])
        # print(scale_factor)
        h, w = image.size[0], image.size[1]  # source image width and height
        tw, th = int(h * scale_factor), int(w * scale_factor)  #croped width and height

        if scale_factor < 1.:
            left_shift = []
            mask_np = sample['mask']
            select_index = np.concatenate([np.where(mask_np != 0)], axis=1)
            if select_index.shape[1] == 0:
                left_shift.append([0, (w - tw)])
                left_shift.append([0, (h - th)])
            else:
                x_left = max(0, min(select_index[0]))
                x_right = min(w, max(select_index[0]))
                y_left = max(0, min(select_index[1]))
                y_right = min(h, max(select_index[1]))
                left_shift.append(
                    [max(0, min(x_left, x_right - tw)),
                     min(x_left, w - tw)])
                left_shift.append(
                    [max(0, min(y_left, y_right - th)),
                     min(y_left, h - th)])
            x1 = random.randint(left_shift[1][0], left_shift[1][1])
            y1 = random.randint(left_shift[0][0], left_shift[0][1])
            image = image.crop((x1, y1, x1 + tw, y1 + th))
            mask = mask.crop((x1, y1, x1 + tw, y1 + th))
        else:
            pw, ph = tw - w, th - h
            pad_value = [
                int(random.uniform(0, pw / 2)),
                int(random.uniform(0, ph / 2))
            ]
            image = ImageOps.expand(image,
                                    border=(pad_value[0], pad_value[1],
                                            tw - w,
                                            th - h),
                                    fill=0)
            mask = ImageOps.expand(mask,
                                   border=(pad_value[0], pad_value[1],
                                           tw - w,
                                           th - h),
                                   fill=0)
        tw, th = h, w
        image, mask = image.resize((tw, th), Image.BILINEAR), mask.resize((tw, th), Image.NEAREST)

        image = np.array(image).astype(np.float32)
        mask = np.array(mask).astype(np.float32)
        return {'image': image, 'mask': mask}



class RandomAdjust2D(object):
    """
    Data augmentation method.
    Adjust the brightness of the image with random gamma.
    Args:
    - scale: the gamma from the scale
    Returns:
    - adjusted image
    """

    def __init__(self, scale=(0.2,1.8)):
        assert isinstance(scale,tuple)
        self.scale = scale

    def __call__(self, sample):
        image = sample['image']
        gamma = random.uniform(self.scale[0],self.scale[1])
        image = exposure.adjust_gamma(image, gamma) 
        sample['image'] = image
        return sample


class RandomNoise2D(object):
    """
    Data augmentation method.
    Add random salt-and-pepper noise to the image with a probability.
    Returns:
    - adjusted image
    """
    def __call__(self, sample):
        image = sample['image']
        prob = random.uniform(0,1)
        if prob > 0.9:
            image = random_noise(image,mode='s&p') 
        sample['image'] = image
        return sample


class RandomGaussionNoise2D(object):
    """
    Data augmentation method.
    Add random Gaussion noise to the image with a probability.
    Returns:
    - adjusted image
    """
    def __call__(self, sample):
        prob = random.uniform(0,1)
        if prob > 0.9:
            image = sample['image']
            gaussion_noise = np.random.normal(size=image.shape)*0.002
            image += gaussion_noise
            sample['image'] = image
        return sample


class RandomDistort2D(object):
    """
    Data augmentation method.
    Add random salt-and-pepper noise to the image with a probability.
    Returns:
    - adjusted image
    """
    def __init__(self,random_state=None,alpha=200,sigma=20,grid_scale=4,prob=0.5):
        self.random_state = random_state
        self.alpha = alpha
        self.sigma = sigma
        self.grid_scale = grid_scale
        self.prob = prob

    def __call__(self, sample):
        if np.random.uniform(0, 1) > self.prob:
            image = sample['image']
            mask = sample['mask']

            if self.random_state is None:
                random_state = np.random.RandomState(None)

            im_merge = np.concatenate((image[...,None], mask[...,None]), axis=2)
            shape = im_merge.shape
            shape_size = shape[:2]

            self.alpha //= self.grid_scale  # Does scaling these make sense? seems to provide
            self.sigma //= self.grid_scale  # more similar end result when scaling grid used.
            grid_shape = (shape_size[0]//self.grid_scale, shape_size[1]//self.grid_scale)

            blur_size = int(4 * self.sigma) | 1
            rand_x = cv2.GaussianBlur(
                (random_state.rand(*grid_shape) * 2 - 1).astype(np.float32),
                ksize=(blur_size, blur_size), sigmaX=self.sigma) * self.alpha
            rand_y = cv2.GaussianBlur(
                (random_state.rand(*grid_shape) * 2 - 1).astype(np.float32),
                ksize=(blur_size, blur_size), sigmaX=self.sigma) * self.alpha
            if self.grid_scale > 1:
                rand_x = cv2.resize(rand_x, shape_size[::-1])
                rand_y = cv2.resize(rand_y, shape_size[::-1])

            grid_x, grid_y = np.meshgrid(np.arange(shape_size[1]), np.arange(shape_size[0]))
            grid_x = (grid_x + rand_x).astype(np.float32)
            grid_y = (grid_y + rand_y).astype(np.float32)

            distorted_img = cv2.remap(im_merge, grid_x, grid_y, borderMode=cv2.BORDER_REFLECT_101, interpolation=cv2.INTER_LINEAR)
            '''
            alpha, sigma, alpha_affine = im_merge.shape[1] * 2, im_merge.shape[1] * 0.08, im_merge.shape[1] * 0.08

            # Random affine
            center_square = np.float32(shape_size) // 2
            square_size = min(shape_size) // 3

            pts1 = np.float32([center_square + square_size, [center_square[0]+square_size, center_square[1]-square_size], center_square - square_size])
            pts2 = pts1 + random_state.uniform(-alpha_affine, alpha_affine, size=pts1.shape).astype(np.float32)
            M = cv2.getAffineTransform(pts1, pts2)
            im_merge = cv2.warpAffine(im_merge, M, shape_size[::-1], borderMode=cv2.BORDER_REFLECT_101)

            dx = gaussian_filter((random_state.rand(*shape) * 2 - 1), sigma) * alpha
            dy = gaussian_filter((random_state.rand(*shape) * 2 - 1), sigma) * alpha
            dz = np.zeros_like(dx)

            x, y, z = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]), np.arange(shape[2]))
            indices = np.reshape(y+dy, (-1, 1)), np.reshape(x+dx, (-1, 1)), np.reshape(z, (-1, 1))

            distorted_img = map_coordinates(im_merge, indices, order=1, mode='reflect').reshape(shape)
            '''
            sample['image'] = distorted_img[...,0]
            sample['mask']  = distorted_img[...,1]

        return sample
