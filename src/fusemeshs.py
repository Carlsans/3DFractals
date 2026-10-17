import os

from src.FractalParameters import FractalParameters
from src.StlGenerator import StlGenerator

stlgenerator = StlGenerator()
file_list = []
folderpath = os.path.dirname(os.path.realpath(__file__)) + "/stlfuse/"
for root, dirs, files in os.walk(folderpath):
    for file in files:
        file_list.append(os.path.join(root, file))
if folderpath+"fused.stl" in file_list:
    file_list.remove(folderpath+"fused.stl")
if folderpath+"fusedandcutted.stl" in file_list:
    file_list.remove(folderpath+"fusedandcutted.stl")
print(file_list)
mesh = stlgenerator.difference_meshes_from_cube(file_list,folderpath+"fused.stl")
mesh = stlgenerator.sliceMesh(mesh)
mesh.export(folderpath+"fusedandcutted.stl")

