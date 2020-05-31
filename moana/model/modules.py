import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .utils import pad_fn


class RDUNet(nn.Module):
    
    def __init__(self, dimension, classes, channels=64, depth=4, **kwargs):
        """
        The RDU-Net as proposed by Sahmsolmoali et al.
        (See https://arxiv.org/abs/2003.07784)
        """
        super().__init__(**kwargs)
        
        self.dimension = dimension
        self.channels = channels
        self.depth = depth
        
        down_blocks = []
        up_blocks = []
        
        # the down-sampling layers
        for level in range(depth):
            is_head = level == 0
            if is_head:
                in_channels = self.dimension[0]
            else:
                in_channels = channels * 2 ** (level - 1)
            out_channels = channels * 2 ** level
            down_blocks.append(DownBlock(in_channels, out_channels, is_head=is_head))

        # the bridge layer
        in_channels = channels * 2 ** (depth - 1)
        out_channels = channels * 2 ** depth
        self.bridge = Bridge(in_channels, out_channels)
            
        # the up-sampling layers
        for level in range(self.depth - 1, -1, -1):
            in_channels = channels * 2 ** (level + 1)
            out_channels = channels * 2 ** level
            up_blocks.insert(0, UpBlock(in_channels, out_channels))
            
        # the output layer
        self.output = nn.Conv2d(channels, classes, (1, 1))
        
        self.down_blocks = nn.ModuleList(down_blocks)
        self.up_blocks = nn.ModuleList(up_blocks)
        
    def forward(self, x):
        out = x
        residuals = []
        for level in range(self.depth):
            out, residual = self.down_blocks[level](out)
            residuals.append(residual)
        out = self.bridge(out)
        for level in range(self.depth - 1, -1, -1):
            out = self.up_blocks[level](out, residuals[level])
        out = self.output(out)
        return out


class DenseNet(nn.Module):
    
    def __init__(self, channels, n_layers=6, **kwargs):
        """
        The modified DenseNet as proposed in Sahmsolmoali
        et al. (See https://arxiv.org/abs/2003.07784)
        """
        super().__init__(**kwargs)
        
        blocks = []
        self.residuals = []
        
        factors = math.ceil(math.log2(n_layers))
        for i in range(n_layers):
            i = i + 1
            
            # layer connectivity
            residual = [i - 2 ** k for k in range(factors) if i - 2 ** k > 0]    
            
            # kernel and in_channels
            kernel = 3
            in_channels = channels * max(1, len(residual))
            if i == 1 or i == n_layers:
                kernel = 1
            
            # build layers and store connectivity
            block = nn.ModuleList([
                nn.BatchNorm2d(in_channels),
                nn.PReLU(), 
                nn.Conv2d(in_channels, channels, kernel, padding=pad_fn(kernel, 1))
            ])
            
            blocks.append(block)                        
            self.residuals.append(residual)
            
        self.blocks = nn.ModuleList(blocks)
            
    def forward(self, x):
        outputs = []
        for i, (norm, func, conv) in enumerate(self.blocks):
            i = i + 1
            if i == 1:
                features = x
            else:
                features = outputs[-1]
                for j in self.residuals[i - 1][1:]:
                    features = torch.cat([features, outputs[j - 1]], dim=1)
            outputs.append(conv(func(norm(features))))
        return outputs[-1]
    

class DownBlock(nn.Module):
    
    def __init__(self, in_channels, out_channels, is_head=False, **kwargs):
        """
        The down-sampling block.
        
        Note: The original implementation is built in TensorFlow 
              and uses implicit "SAME" padding to enable a (2, 2)
              kernel for the final convolutional layer. To do this
              in PyTorch, we use assymetric padding.
        """
        super().__init__(**kwargs)
                
        if is_head:
            self.norm1 = nn.Identity()
            self.func1 = nn.Identity()
        else:
            self.norm1 = nn.BatchNorm2d(in_channels)
            self.func1 = nn.PReLU()
        self.conv1 = nn.Conv2d(in_channels, out_channels, (3, 3), padding=pad_fn(3, 1))
            
        self.dense = DenseNet(out_channels)
        
        self.norm2 = nn.BatchNorm2d(out_channels)
        self.func2 = nn.PReLU()
        self.conv2 = nn.Conv2d(out_channels, out_channels, (2, 2))

        self.conv3 = nn.Conv2d(out_channels, out_channels, (2, 2), stride=2, padding=pad_fn(2, 2))

    def forward(self, x, return_residual=True):
        out = self.conv1(self.func1(self.norm1(x)))
        out = self.dense(out)
        residual = self.conv2(F.pad(self.func2(self.norm2(out)), (0, 1, 0, 1)))
        out = self.conv3(residual)
        if return_residual:
            return out, residual
        else:
            return out

        
class UpBlock(nn.Module):
    
    def __init__(self, in_channels, out_channels, **kwargs):
        """
        The up-sampling block.
        
        Note: The original implementation is built in TensorFlow 
              and uses implicit "SAME" padding to enable a (2, 2)
              kernel for the final convolutional layer. To do this
              in PyTorch, we use assymetric padding.
        """
        super().__init__(**kwargs)
        
        self.upsample = nn.Upsample(scale_factor=(2, 2))
        
        self.norm1 = nn.BatchNorm2d(in_channels)
        self.func1 = nn.PReLU()
        self.conv1 = nn.Conv2d(in_channels, out_channels, (3, 3), padding=pad_fn(3, 1))
            
        self.dense = DenseNet(out_channels)
        
        self.norm2 = nn.BatchNorm2d(out_channels)
        self.func2 = nn.PReLU()
        self.conv2 = nn.Conv2d(out_channels, out_channels, (2, 2))
        
    def forward(self, x, residual):
        """
        The upsampling forward pass.
        
        Note: The original implementation adds the residual
              immediately after upsampling, but we find this 
              is impossible, given the paper schematic, due to
              a channel dimension mismatch.
              
        TODO: Account for the above with strided convolution.
        """
        out = self.upsample(x)
        out = self.conv1(self.func1(self.norm1(out)))
        out = out + residual
        out = self.dense(out)
        out = self.conv2(F.pad(self.func2(self.norm2(out)), (0, 1, 0, 1)))
        return out


class Bridge(nn.Module):
        
    def __init__(self, in_channels, out_channels, **kwargs):
        """
        The bridge betwen down-sampling and up-sampling
        layers.
        
        Note: The original implementation is built in TensorFlow 
              and uses implicit "SAME" padding to enable a (2, 2)
              kernel for the final convolutional layer. To do this
              in PyTorch, we use assymetric padding.
        """
        super().__init__(**kwargs)
                
        self.norm1 = nn.BatchNorm2d(in_channels)
        self.func1 = nn.PReLU()
        self.conv1 = nn.Conv2d(in_channels, out_channels, (2, 2))
            
        self.dense = DenseNet(out_channels)
        
        self.norm2 = nn.BatchNorm2d(out_channels)
        self.func2 = nn.PReLU()
        self.conv2 = nn.Conv2d(out_channels, out_channels, (2, 2))
        
    def forward(self, x):
        out = self.conv1(F.pad(self.func1(self.norm1(x)), (0, 1, 0, 1)))
        out = self.dense(out)
        out = self.conv2(F.pad(self.func2(self.norm2(out)), (0, 1, 0, 1)))
        return out
