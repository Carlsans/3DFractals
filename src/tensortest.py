import numpy as np
import trimesh
from trimesh.voxel import creation

def create_voxel_mesh(voxel_grid):
    # Convert the voxel grid to a trimesh Voxel object
    voxels = trimesh.voxel.VoxelGrid(voxel_grid)

    # Convert voxels to a mesh
    mesh = voxels.as_boxes()

    # Merge vertices
    mesh.merge_vertices()

    # Remove duplicate faces
    mesh.update_faces(mesh.unique_faces())

    # Simplify the mesh
    #target_faces = int(mesh.faces.shape[0] * 0.5)  # Reduce to 50%


    # Ensure the mesh is still valid
    #simplified_mesh.fix_normals()
    #simplified_mesh.fill_holes()

    return mesh

# Example usage
# Create a sample 3D tensor (10x10x10)
voxel_grid = np.zeros((10, 10, 10), dtype=bool)
voxel_grid[2:3, 2:6, 2:8] = True  # Create a 6x6x6 cube in the center

# Generate the mesh
mesh = create_voxel_mesh(voxel_grid)

# Export to STL
mesh.export('voxel_mesh.stl')

print(f"Faces: {len(mesh.faces)}")
print(f"Vertices: {len(mesh.vertices)}")


exit()
import math
import time

import numpy as np
from stl import mesh

# Define the 8 vertices of the cube
vertices = np.array([
    [-1, -1, -1],
    [+1, -1, -1],
    [+1, +1, -1],
    [-1, +1, -1],
    [-1, -1, +1],
    [+1, -1, +1],
    [+1, +1, +1],
    [-1, +1, +1]
])

# Define the 12 triangles composing the cube
faces = np.array([
    [0, 3, 1],
    [1, 3, 2],
    [0, 4, 7],
    [0, 7, 3],
    [4, 5, 6],
    [4, 6, 7],
    [5, 1, 2],
    [5, 2, 6],
    [2, 3, 7],
    [2, 7, 6],
    [0, 1, 5],
    [0, 5, 4]
])

# Create the mesh
cube = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))

for i, f in enumerate(faces):
    for j in range(3):
        cube.vectors[i][j] = vertices[f[j], :]
# Generate 4 different meshes so we can rotate them later
print("cube.data",cube.data)
timebefore = time.time()
cubescount = int(math.pow(2,3))
meshes = [mesh.Mesh(cube.data.copy()) for _ in range(cubescount)]
for i in meshes:

    i.x += .5
    continue
    i.y += 2
    i.z += 3
    #i.x += (cubescount / 1000) * np.random.rand(1)
    #i.y += (cubescount / 1000) * np.random.rand(1)
    #i.z += (cubescount / 1000) * np.random.rand(1)

meshesdata = [obj.data for obj in meshes]

cubesdata = np.concatenate(meshesdata)
#print("cubesdata",cubesdata)
for i in cubesdata:
    #print(i)
    for j in i:
        print(j.shape)
print("cubesdata.shape",cubesdata.shape)
# Write the mesh to file "cube.stl"
cubes = mesh.Mesh(cubesdata)
cubes.save('cubes.stl')
print("time elapsed in sec",time.time()-timebefore)
exit()
import torch
x = torch.tensor([-2,-1,0,1,2])
x = x.view(x.shape[0],1,1)
y = torch.tensor([-2,-1,0,1,2])
y = y.view(1,y.shape[0],1)
z = torch.tensor([-2,-1,0,1,2])
z = z.view(1,1,z.shape[0])
print(x.shape)
print(y.shape)
print(z.shape)
xy = x + y
print(xy.view(x.shape[0],y.shape[1]))
print(xy.shape)
xyz = xy + z
print(xyz)
print(xyz.shape)
def getzlinear(A=1,B=0):
    limits = [-2,2]
    zdimension = 5
    # y = Ax + B
    x = torch.linspace(limits[0], limits[1],steps=zdimension)
    y = x * A + B
    print(x)
    print(y)
    z = x + y * 1j
    print(z)
getzlinear()