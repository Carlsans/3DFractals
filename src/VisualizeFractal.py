import numpy as np
#import ConfigObj
from mayavi import mlab

from src.FractalParameters import FractalParameters


class VisualizeFractal:
    def __init__(self):
        self.parameters = FractalParameters()

    def drawVoxelTorchTensor(self,tensor):
        tensor = tensor.cpu().numpy()
        # Threshold to create a binary mask
        threshold = 1

        # Plot the voxels
        #mlab.contour3d(voxels.astype(float), contours=[0.5], opacity=0.5)
        print(tensor.shape)
        #xx, yy, zz = tensor
        #print(xx.size)
        #exit()
        mlab.points3d(tensor,
                             mode="sphere",
                             scale_factor=.1)

        mlab.show()