# Features that exist in the code but are not part of the final workflow

| # | Feature | Where in the code | Why unused | In the GUI |
|---|---|---|---|---|
| 1 | Smoothed marching cubes | `StlGenerator.create_smooth_fractal_mesh` (searching mode) | Replaced by plain voxel marching cubes for drawing and rendering | Mesh and export > Method "Smoothed marching cubes"; the Search tab uses it |
| 2 | One box per voxel | `StlGenerator.generateStlCubic` | Millions of boxes | Mesh and export > "One box per voxel" (refuses above 40,000 voxels) |
| 3 | OpenSCAD array export | `Openscad.py`, `*.scad` | First approach, replaced by STL | Mesh and export > "Export OpenSCAD array" |
| 4 | Even-numbered shells | `generateStlCubic2(... % 2 == 0)` | Produced a second STL per formula | Formula and volume > "Voxels shown" |
| 5 | Iteration list | `generateStlsbyRules` | Hard-coded list of 26 numbers | Same, with an editable list |
| 6 | One STL per iteration shell | `generateStlCubicbySteps` | Only in rendering mode | Mesh and export > "Build one STL per iteration shell" |
| 7 | Cut by a diagonal plane | `sliceMesh`, `stlslice` | Off | Mesh and export checkbox, and in Legacy tools |
| 8 | Added thickness | `add_thickness_to_mesh`, `stladdvolume` | Off; needs a boolean engine | Mesh and export field |
| 9 | Mesh decimation | `decimationratio` | Used only when printing | Mesh and export field (needs `fast_simplification`; the print tab retries without it) |
| 10 | Fuse STLs, subtract from a cube | `fuse_meshes`, `difference_meshes_from_cube`, `fusemeshs.py` | Manual post-processing | Legacy tools |
| 11 | Reading old logs | `FileManager`, `fractalNNNlog.txt` | The log lists the four functions | Formula and volume > "Load formula from an old log" |
| 12 | Curate by deleting | `FileManager.getFractalIndex` | A workflow rather than a feature | Search tab keeps a list; "Save kept numbers" |
| 13 | Voxel plot with Mayavi | `VisualizeFractal.py`, `generateObjectPhoto` | Windows/display only | Replaced by the built-in rotating preview |
| 14 | Delaunay point-cloud mesh | `point_cloud_to_mesh` | Never called | Not integrated: it is a prototype that needs a KD-tree normal estimate per point and produces no usable surface |
| 15 | Gaussian-smoothed volume, `moderngl` | imports in `StlGenerator` | Never used | Not integrated |
