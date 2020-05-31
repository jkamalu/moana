import os
import random

import numpy as np

from skimage import io

import torch
from torch.utils.data import Dataset


class MoanaDataset(Dataset):

    def __init__(self, root_dir, pixel_dim, N=None, transform=None, empty=False):
        if not empty:
            self.init_from_args(root_dir, pixel_dim, N=N, transform=transform)
        
    
    def init_from_args(self, root_dir, pixel_dim, N=None, transform=None):
        self.root_dir = root_dir
        self.pixel_dim = pixel_dim
        self.transform = transform
        
        self.images_dir = os.path.join(root_dir, "images")
        self.labels_dir = os.path.join(root_dir, "masks")
        
        self.all_file_names = list(filter(lambda f: f.endswith("png"), os.listdir(self.images_dir)))
        random.shuffle(self.all_file_names)
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

    
    @classmethod
    def split(cls, dataset, split):
        dataset_0 = MoanaDataset(None, None, empty=True)
        dataset_1 = MoanaDataset(None, None, empty=True)
        
        dataset_0.root_dir = dataset.root_dir
        dataset_0.pixel_dim = dataset.pixel_dim
        dataset_0.transform = dataset.transform
        dataset_0.images_dir = os.path.join(dataset_0.root_dir, "images")
        dataset_0.labels_dir = os.path.join(dataset_0.root_dir, "masks")
        
        dataset_1.root_dir = dataset.root_dir
        dataset_1.pixel_dim = dataset.pixel_dim
        dataset_1.transform = dataset.transform
        dataset_1.images_dir = os.path.join(dataset_1.root_dir, "images")
        dataset_1.labels_dir = os.path.join(dataset_1.root_dir, "masks")
        
        N = int(len(dataset.file_names) * split)
        dataset_0.file_names = random.sample(dataset.file_names, N)
        dataset_1.file_names = list(set(dataset.file_names) - set(dataset_0.file_names))
        
        return dataset_0, dataset_1
        
        
        