# 3DFractals

3D-printable fractals. A third axis is added to an escape-time fractal, `z <- fn4( fn1(c) * fn2(c) + fn3(z) )`, with 18 functions at each of four places (**104,976 formulas**). The voxel
volume is turned into a mesh with marching cubes, filtered by the fraction of watertight faces, and exported as STL.

- How it works, what worked and what did not: [docs/PROJECT.md](docs/PROJECT.md)
- Features that were tried and dropped: [docs/UNUSED_FEATURES.md](docs/UNUSED_FEATURES.md)

## GUI

```
pip install -r requirements-gui.txt
python -m gui.app
```

- **Formula and volume**: pick a formula by number or by its four functions, compute on the GPU, rotate the preview, choose which iteration shells to show.
- **Mesh and export**: marching cubes, watertight check, decimation, cutting, thickness, millimetre scaling, one STL per shell, OpenSCAD export.
- **Search**: test a range or random formula numbers at low resolution and keep those with enough watertight faces.
- **Print size**: resolution of a print-sized render from the nozzle and layer height, computed in slabs.
- **Legacy tools**: fuse STL files, subtract them from a cube, view an STL.

Outputs go to the folder you choose (default: a temporary folder). The original scripts write into `src/output/`.

## Original scripts

`src/FractalGenerator3D.py` (starts an endless search when run). They need Windows-only packages (`pythoncom`, `mayavi`) for the photo step.

## License

[PolyForm Noncommercial 1.0.0](LICENSE). Personal, research and hobby use are allowed; commercial use is not.

## Launch the GUI

Linux: `./run.sh`  
Windows: `run_win.bat`

The first run creates a `.venv` and installs `requirements-gui.txt`; later runs start immediately.
