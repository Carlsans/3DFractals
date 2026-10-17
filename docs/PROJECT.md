# 3DFractals: how it works, what worked, what did not

Written from the code and from the folder it left behind: 9,066 formula logs, 1,811 + 1,543 + 1,505 STL files and a hand-picked `choix` folder in `src/output/` (159 GB), all dated August 2024.
Statements marked *(inferred)* are conclusions from that evidence, not recorded results.

## The idea

Take an escape-time fractal, add a **third axis**, and 3D print the solid. The set is a volume of `x * y * t` voxels and a surface mesh is extracted from it.

For each voxel the engine iterates

```
z0 = x + i*y          c = a point on a complex line that moves with the third axis  (z-start -> z-end)
z  <-  fn4( fn1(c) * fn2(c) + fn3(z) )
```

and stores the number of the iteration at which `real(z) + imag(z)` exceeds 4 (0 = never). Each of fn1..fn4 is one of **18 functions** (`real`, `imag`, `conj`, `abs`, `angle`, `sin`, `cos`, `tan`, `sinh`, `cosh`, `tanh`, `exp`, `log`, `log10`, `sqrt`, `square`, `cubic`, `parallel`),
so there are 18^4 = **104,976 formulas**, numbered in counting order with `fn1` changing fastest. The number is the file name: `fractal16994.stl`. (The GUI's number-to-formula mapping reproduces the formula written in the old log files.)

## Pipeline

| Stage | File | Notes |
|---|---|---|
| Formula | `FractalFormula.py` | The 18 functions, the odometer-style `incrementformula`, and `applyformula`. Several functions add `0j` so complex tensors stay complex. |
| Volume | `FractalGenerator3D.computeFractal` | Torch tensors; 50^3 for the search, 120^3 for "drawing", up to ~500 x 500 x 1000 for printing; 100 iterations. |
| Mesh | `StlGenerator.generateStlCubic2` | Marching cubes on the voxel mask (trimesh), fill holes, drop degenerate and duplicate faces, optional quadratic decimation, `fix_normals`, `rezero`, scale to millimetres in render mode. |
| Filter | `meshWatertightComponentsRatio` | Split into components and keep the formula only if at least **15 %** of the faces belong to watertight components. |
| Variants | `generateStlCubic2` ×3 | Besides the full mask, a second STL with only the even iteration numbers (`...Odd.stl`), and a third with a hand-written list of 26 iteration numbers (`...Vector.stl`). |
| Photos | `generateObjectPhoto` | Mayavi renderings of the mesh, Windows only. |
| Post | `fusemeshs.py`, `difference_meshes_from_cube`, `sliceMesh` | Fuse several STL files, subtract them from a cube, cut with a diagonal plane. |

Three modes in `FractalParameters`: `issearching` (smoothed marching cubes, small), `isdrawing` (the formulas still present in the output folder, re-rendered at 120^3 with photos) and `isrendering` (a chosen list of numbers at print resolution: 100 mm cube, 0.2 mm layers x 0.4 mm nozzle, with a "scaling" factor that halves the voxel size).

## What worked

- **Brute force over a small formula space.** 18^4 formulas at 50^3 were fast enough to look at 90,000 of them. The surviving logs span numbers from 2,279 to 96,624.
- **The watertight-face ratio as a filter.** A cheap, objective test for "this will not fall apart in the slicer".
- **Curating by deleting.** `FileManager.getFractalIndex` lists the STL files that are still in the folder and re-renders only those: the author threw away uninteresting meshes and the next stage followed.
  That is why there are 9,066 logs for 1,811 kept meshes.
- **Selecting iteration shells.** Using only some iteration numbers (even ones, or a list) turns one solid into a second, more open shape from the same data.
- **Marching cubes on voxels rather than one box per voxel.** The first approach (`generateStlCubic`, one cube per voxel through numpy-stl) was abandoned: millions of boxes.

## What did not work

- **Print resolution is heavy.** The "scaling" comment in `renderforprint` says "Augment if the model is too heavy!": at 0.1 mm voxels a 100 mm cube is about 250 million voxels. The GUI computes the volume in slabs to bound memory.
- **OpenSCAD route.** `Openscad.saveFractaltoFile` writes the volume as a text array (`fractalarray.scad`, 585 KB at 10^3) for a `cutfractal.scad` that imports an STL. It is the first approach (Aug 12) and was dropped.
- **Mayavi photos** need a display and `pythoncom` (Windows). They are imported at the top of `StlGenerator`, so the whole module fails to import elsewhere.
- **Boolean operations** (`add_thickness_to_mesh`, `difference_meshes_from_cube`) need an external boolean engine in trimesh, and their results are often not manifold (`remove_non_manifold_elements` is a patch for this).
- **Point-cloud / Delaunay meshing** (`point_cloud_to_mesh`) is written but not used.
- **The script cannot be imported.** `FractalGenerator3D.py` ends with `fractalgenerator.computeFractal()`, which loops until `exit()` after the last formula.
- **Device mix.** `result` is a CPU tensor indexed by a mask computed on the GPU, which fails on a CUDA machine *(inferred: the script ran on a Windows CPU)*.
- **Newer trimesh** removed `remove_degenerate_faces` / `remove_duplicate_faces`; the GUI adds them back.

## Lessons

1. A tiny, enumerable family of formulas plus a cheap automatic filter beats hand design: generate everything, filter, then look.
2. Keep the formula number in the file name; it is the whole genome.
3. Check printability (watertight ratio) at search resolution, before spending hours on a print-sized render.
4. Voxel masks + marching cubes scales; per-voxel geometry does not.
5. Compute volumes in slabs; voxels are independent, so slabs are exact.

## Running the original code

`src/FractalGenerator3D.py` from the repository root (modules import `src.X`, and `FractalFormula` imports `diyfunctions` directly, so `src/` must also be on `PYTHONPATH`). Needs the Windows-only packages above. Set the mode in `FractalParameters.py`.
