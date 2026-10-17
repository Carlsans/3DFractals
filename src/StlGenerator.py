import math
import os
from pathlib import Path

import pythoncom
from mayavi import mlab
# Set the backend to offscreen rendering
os.environ['ETS_TOOLKIT'] = 'qt4'
os.environ['QT_API'] = 'pyqt5'
mlab.options.offscreen = True
import torch
import numpy as np
import mcubes
from sklearn.neighbors._kd_tree import KDTree
from stl import mesh
import trimesh
from trimesh.voxel import creation
from trimesh.boolean import union
from scipy.spatial import Delaunay
from scipy.ndimage import gaussian_filter
from skimage import measure
from PIL import Image
from src.FractalParameters import FractalParameters
import moderngl

class StlGenerator:
    def __init__(self):
        self.parameters = FractalParameters()

    def generateStlCubic2(self,tensor,filename = "fractal.stl"):
        filepath = self.parameters.basedirectory + filename
        if self.parameters.mode == "issearching":
            method = "point_cloud"
        if self.parameters.mode == "isdrawing" or self.parameters.mode == "isrendering":
            method = "voxelmarchingcube"

        if torch.is_tensor(tensor):
            tensor = tensor.cpu().numpy()
        if method == "cubes":
            voxels = trimesh.voxel.VoxelGrid(tensor)
            # Convert voxels to a mesh
            mesh = voxels.as_boxes()
        if method == "point_cloud":
            print("Generating mesh with point cloud marching cube method")
            print("tensor.shape",tensor.shape)
            # Needed shape (x*x*x,3) current shape (x,x,x)
            points = np.argwhere((tensor >= 0))
            print("points.shape",points.shape)
            #tri = Delaunay(points)
            #mesh = trimesh.Trimesh(vertices=points, faces=tri.simplices)
            #mesh = self.point_cloud_to_mesh(points)
            mesh = self.create_smooth_fractal_mesh(tensor,points,tensor.shape)
        if method == "voxelmarchingcube":
            print("Generating mesh with voxel marching cube method")
            try:
                mesh = trimesh.voxel.ops.matrix_to_marching_cubes(tensor)
            except ValueError as e:
                print('error type: ', type(e))
                return None
            # Step 2: Ensure the mesh is watertight
            mesh.fill_holes()
            # Remove duplicate and degenerate faces
            mesh.remove_degenerate_faces()
            mesh.remove_duplicate_faces()
            #mesh = mesh.repair()
            # Step 3: Simplify the mesh (optional)
            if not (self.parameters.decimationratio is None ):
                targetfaces = len(mesh.faces)*self.parameters.decimationratio
                mesh = mesh.simplify_quadratic_decimation(targetfaces)
            # Step 4: Orient the mesh correctly
            mesh.fix_normals()
            # Ensure the mesh is centered and aligned with the XY plane
            mesh.rezero()
            if self.parameters.mode == "isrendering":
                mesh.apply_scale((self.parameters.extrusionwidth,self.parameters.extrusionwidth,self.parameters.layerheight))
            #mesh.vertices -= mesh.center_mass
            #mesh.vertices[:, 2] -= mesh.bounds[0][2]
        if mesh is None:
            if os.path.exists(filepath):
                os.remove(filepath)
            return
        # Merge vertices
        mesh.merge_vertices()
        # Remove duplicate faces
        mesh.update_faces(mesh.unique_faces())
        if self.parameters.stlslice:
            mesh = self.sliceMesh(mesh)
        if self.parameters.stladdvolume > 0:
            mesh = self.add_thickness_to_mesh(mesh)
        if self.parameters.minimumwatertightratio > 0 :
            watertightratio = self.meshWatertightComponentsRatio(mesh)
            #print(watertightratio)
            if watertightratio < self.parameters.minimumwatertightratio:
                return None
        mesh.export(filepath)
        return mesh
    def generateObjectPhoto(self,mesh,filename,takephoto = 3,samedir = False):
        if mesh is None:
            print("Cant generate images on None mesh...")
            return
        if samedir:
            filepath = self.parameters.basedirectory + filename
        else:
            filepath = self.parameters.basedirectory + "images/" + filename



        # get a scene object containing the mesh, this is equivalent to:
        # scene = trimesh.scene.Scene(mesh)
        scene = mesh.scene()

        # a 45 degree homogeneous rotation matrix around
        # the Y axis at the scene centroid
        rotate = trimesh.transformations.rotation_matrix(
            angle=np.radians(55.0), direction=[1, 1, 0], point=scene.centroid
        )
        roolangle = 360 / takephoto
        for i in range(takephoto):
            #trimesh.constants.log.info(f"Saving image {i}")

            # rotate the camera view transform
            #camera_old, _geometry = scene.graph[scene.camera.name]
            #camera_new = np.dot(rotate, camera_old)

            # apply the new transform
            #scene.graph[scene.camera.name] = camera_new
            # Create a mayavi figure
            mlab.figure(size=(300, 200))

            # Visualize the mesh
            mlab.triangular_mesh(*mesh.vertices.T, mesh.faces)
            mlab.view(azimuth=45, elevation=30, distance=self.parameters.resolution[0]*2.5, roll=i*roolangle)
            # Save the figure as an image
            mlab.savefig(filepath+"f"+str(i)+ ".png")
            mlab.close()
            # try:
            #     # increment the file name
            #     #file_name = "render_" + str(i) + ".png"
            #     # save a render of the object as a png
            #     png = scene.save_image(resolution=[300, 200], visible=True)
            #     with open(filepath+"f"+str(i)+ ".png", "wb") as f:
            #         f.write(png)
            #         f.close()
            #
            # except BaseException as E:
            #     print("unable to save image", str(E))
       #  # Create a scene and add the mesh to it
       #  scene = trimesh.Scene(mesh)
       #
       #  # Define the camera parameters
       #  resolution = (400, 300)  # Width and height of the image
       #  fov = (60, 45)  # Field of view in degrees (horizontal, vertical)
       #  angle_degrees = 67
       #  distance = 10
       #  angle_radians = math.radians(angle_degrees)
       #  x = distance * math.sin(angle_radians)
       #  z = distance * math.cos(angle_radians)
       #
       #  camera_position = [x, 0, z]
       #  camera_target = [0, 0, 0]
       #  up_vector = [0, 1, 0]
       #  # Get the bounds of the mesh
       #  bounds = mesh.bounds
       #
       #  # Calculate the width on each axis
       #  width_x = bounds[1][0] - bounds[0][0]
       #  width_y = bounds[1][1] - bounds[0][1]
       #  width_z = bounds[1][2] - bounds[0][2]
       #  # Define the camera position and orientation
       # # camera_position = [bounds[1][0]-width_x/2, bounds[1][1]-width_y/2, bounds[1][2]]  # XYZ coordinates
       #  #camera_target = [bounds[0][0]+width_x/2, bounds[0][1]+width_y/2, bounds[0][2]+width_z/2]  # Look at point
       #
       #
       #  # Calculate camera transform
       #  z_axis = np.array(camera_target) - np.array(camera_position)
       #  z_axis = z_axis.astype('float64') /np.linalg.norm(z_axis)
       #  x_axis = np.cross(np.array(up_vector), z_axis)
       #  x_axis = x_axis.astype('float64') / np.linalg.norm(x_axis)
       #  y_axis = np.cross(z_axis, x_axis)
       #
       #  rotation = np.column_stack((x_axis, y_axis, z_axis))
       #  translation = np.array(camera_position)
       #
       #  camera_transform = np.eye(4)
       #  camera_transform[:3, :3] = rotation
       #  camera_transform[:3, 3] = translation
       #  print("rotation",rotation)
       #  print("translation",translation)
       #  # Invert the camera transform
       #  camera_transform = np.linalg.inv(camera_transform)
       #
       #  # Render the scene
       #  png = scene.save_image(resolution=resolution,
       #                         fov=fov,
       #                         camera_transform=camera_transform)
       #
       #  # Convert the PNG data to an image and save it
       #  img = Image.open(trimesh.util.wrap_as_stream(png))
       #  img.save(filepath)
    def meshWatertightComponentsRatio(self,mesh):
        if not( self.parameters.selectedfew == []):
            print("Skipping watertight components ratio to speed up")
            return 1
        # Split the mesh into connected components
        components = mesh.split()
        # Initialize counters
        total_faces = len(mesh.faces)
        watertight_faces = 0
        # Check each component
        for component in components:
            if component.is_watertight:
                watertight_faces += len(component.faces)
        # Calculate the percentage of watertight faces
        percent_watertight_faces = watertight_faces / total_faces
        print(f"Percentage of watertight faces: {percent_watertight_faces*100:.2f}%")
        return percent_watertight_faces
    def sliceMesh(self,mesh):
        # Define the normal of the cutting plane
        normal = np.array([-1, 0, -1])
        # Define a point on the cutting plane (e.g., the origin)
        point = np.array([0, 0, 0])
        # Calculate the centroid of the mesh
        centroid = mesh.centroid
        # Translate the mesh to center it at the origin
        mesh.apply_translation(-centroid)
        mesh.fix_normals()
        mesh.remove_degenerate_faces()

        # Slice the mesh along the plane
        sliced_mesh = mesh.slice_plane(plane_origin=point, plane_normal=normal)
        # print(sliced_mesh)
        # # Cap the sliced mesh to ensure it is watertight
        #sliced_mesh = sliced_mesh.convex_hull
        # # Check if the capped mesh is watertight
        # if capped_mesh.is_watertight:
        #     print("The mesh is watertight.")
        # else:
        #     print("The mesh is not watertight.")
        return sliced_mesh

    def coordinates_to_volume(self,coordinates, shape):
        volume = np.zeros(shape, dtype=float)
        coords = coordinates.astype(int)
        volume[coords[:, 0], coords[:, 1], coords[:, 2]] = 1.0
        return volume



    def smooth_volume(self,volume, sigma=1.0):
        return gaussian_filter(volume.astype(float), sigma=sigma)

    def add_thickness_to_mesh(self,mesh):
        thickness = self.parameters.stladdvolume
        # Create a copy of the mesh for positive and negative offset
        positive_offset = mesh.copy()
        negative_offset = mesh.copy()

        # Compute the offset along vertex normals
        positive_offset.vertices += mesh.vertex_normals * (thickness / 2)
        negative_offset.vertices -= mesh.vertex_normals * (thickness / 2)

        # Optionally: Recalculate normals for the new meshes
        positive_offset.rezero()
        negative_offset.rezero()

        # Invert the negative offset mesh to align face normals correctly
        negative_offset.invert()

        # Optionally: Perform boolean operations to combine the meshes
        # Use `trimesh.boolean.union` to combine meshes if you have an external library for this

        thickened_mesh = union([positive_offset, negative_offset])

        # Optionally: Fill holes or cleanup if needed
        thickened_mesh = thickened_mesh.fill_holes()
        # Perform cleanup to close the mesh
        #thickened_mesh = thickened_mesh.convex_hull
        # Ensure the resulting mesh is clean and manifold
        thickened_mesh.remove_duplicate_faces()
        thickened_mesh.remove_degenerate_faces()
        thickened_mesh.fill_holes()

        return thickened_mesh
    def create_smooth_fractal_mesh(self,tensor,coordinates, shape, iso_level=0.5, sigma=1.0):
        # Convert coordinates to volume
        volume = tensor

        # Smooth the volume
        smooth_vol = self.smooth_volume(volume, sigma)
        #print("smooth_vol",smooth_vol)
        # Use Marching Cubes to create a mesh
        try:
            vertices, faces, normals, _ = measure.marching_cubes(smooth_vol, iso_level)
        except ValueError as e:
            print('error type: ', type(e))
            return None
        # Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, normals=normals)

        # Smooth the mesh further
        mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=5)

        return mesh
    def point_cloud_to_mesh(self,points, k_neighbors=20, distance_upper_bound=None):
        # Compute normals
        tree = KDTree(points)
        distances, indices = tree.query(points, k=k_neighbors)

        normals = []
        for i, neighbors in enumerate(indices):
            neighbors = neighbors[1:]  # Exclude the point itself
            centered = points[neighbors] - points[i]
            cov = np.cov(centered, rowvar=False)
            eigenvalues, eigenvectors = np.linalg.eig(cov)
            normal = eigenvectors[:, np.argmin(eigenvalues)]
            normals.append(normal)

        normals = np.array(normals)

        # Create initial mesh
        tri = Delaunay(points)
        mesh = trimesh.Trimesh(vertices=points, faces=tri.simplices, vertex_normals=normals)

        # Remove long edges
        if distance_upper_bound is not None:
            mesh.remove_edges_by_length(distance_upper_bound)

        # Smooth the mesh
        mesh = trimesh.smoothing.filter_laplacian(mesh, iterations=5)

        # Fix mesh issues
        mesh.fill_holes()
        mesh.remove_degenerate_faces()
        mesh.remove_duplicate_faces()
        mesh.remove_unreferenced_vertices()

        return mesh

    def remove_non_manifold_elements(self,mesh):
        # Remove non-manifold edges
        mesh.remove_degenerate_faces()

        # Get non-manifold edges

        mesh = trimesh.util.concatenate(mesh.split(only_watertight=True))
        # Remove faces attached to non-manifold edges
        # face_mask = np.ones(len(mesh.faces), dtype=bool)
        #     for edge in non_manifold_edges:
        #         face_mask[mesh.edges_face[mesh.edges[edge]]] = False
        # mesh.update_faces(face_mask)

        # Remove non-manifold vertices
        mesh.remove_unreferenced_vertices()

        return mesh
    def difference_meshes_from_cube(self,file_paths,exportpath):
        # Load all meshes
        subtract_meshes = [trimesh.load(file_path) for file_path in file_paths]
        cube = trimesh.creation.box(extents=self.parameters.modeldimensions)
        subtract_meshes = trimesh.util.concatenate(subtract_meshes)
        subtract_meshes.merge_vertices()
        subtract_meshes.fill_holes()
        # Get dimensions (bounding box)
        bounding_box = subtract_meshes.bounding_box
        dimensions = bounding_box.extents
        # Get position (center of mass)
        center_mass = subtract_meshes.center_mass
        dimensions = [dimensions[0] * 1.1,dimensions[1] * 1.1,dimensions[2] * 1.1 ]
        center_mass = [dimensions[0]/2 - dimensions[0] *.05,dimensions[1]/2 - dimensions[1] *.05,dimensions[2]/2 - dimensions[2] *.05]
        #center_mass = [center_mass[0]-center_mass[0]*.05, center_mass[1]+center_mass[1]*.05,center_mass[2] - center_mass[2]*.05]
        print("dimensions",dimensions)
        print("center_mass",center_mass)

        # Create a cube with the same dimensions
        cube = trimesh.creation.box(extents=dimensions,
                                    transform=trimesh.transformations.translation_matrix(center_mass))

        result = cube
        result = result.difference(self.remove_non_manifold_elements(subtract_meshes))
        # for mesh in subtract_meshes:
        #     if not mesh.is_volume:
        #         continue
        #     print(mesh)
        #     result = result.difference(self.remove_non_manifold_elements(mesh))
        #     result = self.remove_non_manifold_elements(result)
        # Merge vertices that are close together
        result.merge_vertices()
        # Remove duplicate faces
        result.remove_duplicate_faces()
        result.export(exportpath)
        return result
    def fuse_meshes(self,file_paths,exportpath):
        # Load all meshes
        meshes = [trimesh.load(file_path) for file_path in file_paths]

        # Combine all meshes into one
        combined_mesh = trimesh.util.concatenate(meshes)

        # Merge vertices that are close together
        combined_mesh.merge_vertices()

        # Remove duplicate faces
        combined_mesh.remove_duplicate_faces()

        combined_mesh.export(exportpath)
    def generateStlsbyRules(self,tensor,filename=""):


        # Select in a defined vector
        vector = [1,2,3,6,7,8,12,13,14,18,19,20,24,25,26,43,44,45,45,77,78,79,80,81,99,100]
        mask = np.isin(tensor, vector)
        self.generateStlCubic2(np.where(mask,tensor, False).astype(bool), filename+"Vector.stl")
        print("Generated stl for defined vector values")

    def generateStlCubicbySteps(self,tensor,overlap = 0,dirname = "fractalstep/",takephoto = 0):
        print(tensor.shape)
        tensor = tensor.cpu().numpy()
        print(tensor.shape)
        values = np.unique(tensor)
        print(values)
        filepath = self.parameters.basedirectory + dirname
        Path(filepath).mkdir(parents=True, exist_ok=True) # Create dir if not exist
        for i in values :
            print("Generating",i)
            condition = (tensor>=i) & (tensor<=i+overlap)
            #print(condition)
            mesh = self.generateStlCubic2(np.where(condition, tensor, False),filename=dirname +"stepno"+ str(i)+ ".stl")
            if takephoto > 0 :
                self.generateObjectPhoto(mesh,filename = dirname +"stepno"+ str(i),takephoto=takephoto,samedir=True)


    def generateStlCubic(self,tensor):
        tensor = tensor.cpu().numpy()
        coordinates = np.argwhere((tensor >= 0))
        #print(coordinates.shape)
        cube = self.generatecube()
        meshes = [mesh.Mesh(cube.data.copy()) for _ in range(coordinates.shape[0])]
        print("Cubes count :",coordinates.shape[0])
        index = 0
        for i in meshes:
            i.x += coordinates[index,0]
            i.y += coordinates[index,1]
            i.z += coordinates[index,2]
            index += 1
        meshesdata = [obj.data for obj in meshes]
        cubesdata = np.concatenate(meshesdata)
        #print(cubesdata)
        cubes = mesh.Mesh(cubesdata)
        cubes.save('fractal.stl')
    def generatecube(self):
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
        return cube
    def generateStlFromTensor2(self,tensor):

        tensor -= tensor.min(1, keepdim=True)[0]
        tensor = tensor.to(dtype=torch.float) / tensor.max(1, keepdim=True)[0]
        tensor = tensor.cpu().numpy()
        # Use marching cubes to create a mesh
        vertices, triangles = mcubes.marching_cubes(tensor, 0)

        # Create the mesh
        cube = mesh.Mesh(np.zeros(triangles.shape[0], dtype=mesh.Mesh.dtype))
        for i, f in enumerate(triangles):
            for j in range(3):
                cube.vectors[i][j] = vertices[f[j], :]

        # Save the mesh
        cube.save('binary_tensor_mesh.stl')

        print("Mesh saved as 'binary_tensor_mesh.stl'")
    def generateStlFromTensor(self,tensor):
        tensor -= tensor.min(1, keepdim=True)[0]
        tensor = tensor.to(dtype=torch.float) / tensor.max(1, keepdim=True)[0]
        tensor = tensor.cpu().numpy()
        # Use marching cubes to create a mesh
        vertices, triangles = mcubes.marching_cubes(tensor, 0.5)

        # Create the mesh
        cube = mesh.Mesh(np.zeros(triangles.shape[0], dtype=mesh.Mesh.dtype))
        for i, f in enumerate(triangles):
            for j in range(3):
                cube.vectors[i][j] = vertices[f[j], :]

        # Save the mesh
        cube.save('cubic_mesh.stl')

        print("Mesh saved as 'cubic_mesh.stl'")
