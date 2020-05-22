import os

import numpy as np

from skimage import io

from torch.utils.data import Dataset


class MoanaDataset(Dataset):

    def __init__(self, root_dir, pixel_dim, N=None, transform=None):
        
        self.root_dir = root_dir
        self.pixel_dim = pixel_dim
        self.transform = transform
        
        self.images_dir = os.path.join(root_dir, "images")
        self.labels_dir = os.path.join(root_dir, "masks")
        
        self.all_file_names = list(filter(lambda f: f.endswith("png"), os.listdir(self.images_dir)))
        if N is None:
            self.file_names = self.all_file_names
        else:
            self.file_names = random.sample(self.all_file_names, N)

        
    def __len__(self):
        return len(self.file_names)

    
    def __getitem__(self, idx):
        image_name = os.path.join(self.images_dir, self.file_names[idx])
        label_name = os.path.join(self.labels_dir, self.file_names[idx])
        
        image = self._crop(io.imread(image_name)[:, :, :3])
        label = self._aggregate_label(self._crop(io.imread(label_name)))

        sample = (image, label)

        if self.transform:
            sample = self.transform(sample)

        return sample
    

    def _crop(self, image):
        image = image[:self.pixel_dim[0], :self.pixel_dim[1]]
        return image


    def _aggregate_label(self, label):
        """
        Map noisy labels to aggreate classes.
            - land, 1  -> 1
            - sand, 2  -> 2
            - ????, 3  -> 0
            - reef, 4  -> 3
            - none, 15 -> 0
        """
        label[label == 3] = 0
        label[label == 15] = 0
        label[label == 4] = 3
        return label
        
