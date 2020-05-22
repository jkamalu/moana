import torch
import torchvision
from matplotlib import pyplot as plt


def imshow_image(tensor, nrow):
    if len(tensor.shape) < 4:
        tensor = tensor.unsqueeze(0)
    temp = torch.nn.functional.pad(tensor, [20, 20, 20, 20])
    fig = plt.imshow(torchvision.utils.make_grid(temp, nrow=nrow).permute(1, 2, 0))
    fig.axes.xaxis.set_visible(False)
    fig.axes.yaxis.set_visible(False)
    plt.show()


def imshow_label(tensor, nrow):
    if len(tensor.shape) < 4:
        tensor = tensor.unsqueeze(0)
    temp = torch.nn.functional.pad(tensor, [20, 20, 20, 20])
    grid = torchvision.utils.make_grid(temp, nrow=nrow).permute(1, 2, 0).double()
    fig = plt.imshow(grid / 3, cmap=plt.cm.gray)
    fig.axes.xaxis.set_visible(False)
    fig.axes.yaxis.set_visible(False)
    plt.show()
