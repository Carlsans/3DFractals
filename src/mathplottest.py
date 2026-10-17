import numpy as np
import matplotlib.pyplot as plt

# Example 3D tensor
tensor = np.random.rand(50, 50, 50)  # A 4x4x4 tensor
print(tensor)
# Threshold the tensor to create a binary mask (True where you want to plot a voxel)
threshold = 0.8
voxels = tensor > threshold
print(voxels.shape)
# Set colors based on the value in the tensor

colors = plt.cm.viridis(tensor)
# Create a figure and 3D axes
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot the voxels
ax.voxels(voxels, facecolors=colors, edgecolor='k')

# Set labels
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')

plt.show()