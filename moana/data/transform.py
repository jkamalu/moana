import random

import torchvision.transforms.functional as TF


class RandomCrop:

    def __init__(self, size):
        self.size = size
        
    def get_params(self, image):
        w, h = image.size
        th, tw = self.size
        if w == tw and h == th:
            return 0, 0, h, w
        i = random.randint(0, h - th)
        j = random.randint(0, w - tw)
        return i, j, th, tw

    def __call__(self, sample):
        x, y = sample
        i, j, h, w = self.get_params(x)
        return TF.crop(x, i, j, h, w), TF.crop(y, i, j, h, w)


class ToTensor:

    def __call__(self, sample):
        """
        PIL image to tensor
        """
        x, y = sample
        return TF.to_tensor(x), (TF.to_tensor(y) * 255).int()
    

class ToPILImage:

    def __call__(self, sample):
        """
        Tensor to PIL image
        """
        x, y = sample
        return TF.to_pil_image(x), TF.to_pil_image(y)


class RandomDiscreteRotation:

    def __init__(self, angles):
        self.angles = angles

    def __call__(self, sample):
        x, y = sample
        angle = random.choice(self.angles)
        if angle:
            return TF.rotate(x, angle), TF.rotate(y, angle, fill=(0,))
        return x, y

    
class RandomHorizontalFlip:
    
    def __init__(self, p=0.5):
        self.p = p

    def __call__(self, sample):
        x, y = sample
        if random.random() < self.p:
            return TF.hflip(x), TF.hflip(y)
        return x, y

    
class RandomVerticalFlip:
    
    def __init__(self, p=0.5):
        self.p = p

    def __call__(self, sample):
        x, y = sample
        if random.random() < self.p:
            return TF.vflip(x), TF.vflip(y)
        return x, y
