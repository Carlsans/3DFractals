"""Glue between the PySide6 GUI and the 3DFractals engine.

``FractalGenerator3D.py`` starts an endless generation loop when it is imported, and ``StlGenerator.py`` imports Windows-only
(``pythoncom``) and GUI (``mayavi``, ``moderngl``) modules at the top even though only ``generateObjectPhoto`` uses them.
The GUI therefore takes the formula (``FractalFormula``), the parameters and the mesh code (``StlGenerator``) from the engine -
with the unused imports stubbed - and re-implements the generation loop with explicit settings and chunked computation.
"""
import sys
import types
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _shims():
    for path in (str(REPO), str(SRC)):          # FractalFormula imports 'diyfunctions' as a top-level module
        if path not in sys.path:
            sys.path.insert(0, path)
    for name in ("pythoncom", "mcubes", "stl", "moderngl", "mayavi", "mayavi.mlab"):
        try:
            __import__(name)
        except Exception:
            module = types.ModuleType(name)
            if name == "mayavi.mlab":
                module.options = types.SimpleNamespace(offscreen=True)
            if name == "mayavi":
                module.mlab = types.ModuleType("mayavi.mlab")
                module.mlab.options = types.SimpleNamespace(offscreen=True)
                sys.modules["mayavi.mlab"] = module.mlab
            if name == "stl":
                module.mesh = types.ModuleType("stl.mesh")
                module.mesh.Mesh = type("Mesh", (), {"dtype": None})
                sys.modules["stl.mesh"] = module.mesh
            sys.modules[name] = module


_shims()

import trimesh  # noqa: E402

# The engine was written for an older trimesh that still had these two methods.
if not hasattr(trimesh.Trimesh, "remove_degenerate_faces"):
    trimesh.Trimesh.remove_degenerate_faces = lambda self: self.update_faces(self.nondegenerate_faces())
if not hasattr(trimesh.Trimesh, "remove_duplicate_faces"):
    trimesh.Trimesh.remove_duplicate_faces = lambda self: self.update_faces(self.unique_faces())

from src.FractalFormula import FractalFormula  # noqa: E402
from src.FractalParameters import FractalParameters  # noqa: E402
from src.StlGenerator import StlGenerator  # noqa: E402

_probe = FractalFormula((torch.zeros(1), torch.zeros(1), torch.zeros(1)))
FUNCTIONS = _probe.fnlist
FUNCTION_NAMES = [getattr(f, "__name__", str(f)) for f in FUNCTIONS]
FUNCTION_COUNT = len(FUNCTIONS)
FORMULA_COUNT = FUNCTION_COUNT ** 4

MODES = [("cubes", "Voxel marching cubes (drawing and rendering modes)"),
         ("smooth", "Smoothed marching cubes (searching mode)")]
SELECTIONS = [("escaped", "Every voxel that escaped (default)"),
              ("even", "Only even iteration numbers ('Odd.stl' in the original)"),
              ("vector", "A list of iteration numbers ('Vector.stl' in the original)"),
              ("steps", "One shell per iteration number ('fractalbysteps')")]
DEFAULT_VECTOR = [1, 2, 3, 6, 7, 8, 12, 13, 14, 18, 19, 20, 24, 25, 26, 43, 44, 45, 77, 78, 79, 80, 81, 99, 100]


def formula_ids(index):
    """Formula number -> indices of fn1..fn4 (fn1 changes fastest, as in FractalFormula.incrementformula)."""
    return [(index // FUNCTION_COUNT ** k) % FUNCTION_COUNT for k in range(4)]


def formula_index(ids):
    return sum(i * FUNCTION_COUNT ** k for k, i in enumerate(ids))


def formula_text(ids):
    f = [FUNCTION_NAMES[i] for i in ids]
    return f"z = {f[3]}({f[0]}(c) * {f[1]}(c) + {f[2]}(z))"


def parse_log(path):
    """Read a 'fractalNNNlog.txt' of the original and return the formula indices (or None)."""
    ids = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith("fn") and " = " in line:
            key, value = line.split(" = ", 1)
            for idx, f in enumerate(FUNCTIONS):
                nm = getattr(f, "__name__", "")
                if nm and (f"method {nm} " in value or f"function {nm} " in value):
                    ids[key.strip()] = idx
    if len(ids) == 4:
        return [ids["fn1"], ids["fn2"], ids["fn3"], ids["fn4"]]
    return None


def coordinates(resolution, rangex, rangey, rangez, x0=0, x1=None):
    nx, ny, nz = resolution
    x1 = nx if x1 is None else x1
    xs = torch.linspace(rangex[0], rangex[1], steps=nx, device=DEVICE)[x0:x1].view(-1, 1, 1)
    ys = torch.linspace(rangey[0], rangey[1], steps=ny, device=DEVICE).view(1, -1, 1) * 1j
    zr = torch.linspace(rangez[0].real, rangez[1].real, steps=nz, device=DEVICE)
    zi = torch.linspace(rangez[0].imag, rangez[1].imag, steps=nz, device=DEVICE)
    return xs, ys, (zr + zi * 1j).view(1, 1, nz)


def compute_volume(ids, resolution=(50, 50, 50), maxiter=100, rangex=(-2.0, 2.0), rangey=(-1.5, 1.5),
                   rangez=(-2 + 2j, 2 - 2j), max_chunk_voxels=24_000_000, job=None):
    """Escape iteration of every voxel (int16), z <- fn4(fn1(c) * fn2(c) + fn3(z)), z = x + iy, c along the third axis.

    The volume is computed in slabs along x, which gives exactly the same result because voxels are independent.
    """
    nx, ny, nz = resolution
    fns = [FUNCTIONS[i] for i in ids]
    slab = max(1, min(nx, max_chunk_voxels // (ny * nz)))
    out = np.zeros((nx, ny, nz), dtype=np.int16)
    with torch.no_grad():
        for x0 in range(0, nx, slab):
            if job is not None and job.should_stop():
                break
            x1 = min(nx, x0 + slab)
            xs, ys, c = coordinates(resolution, rangex, rangey, rangez, x0, x1)
            z = xs + ys
            result = torch.zeros((x1 - x0, ny, nz), dtype=torch.int16, device=DEVICE)
            for i in range(maxiter):
                z = fns[3](fns[0](c) * fns[1](c) + fns[2](z))
                escaped = (z.real + z.imag) > 4
                result[escaped] = i
                z = torch.where(escaped, torch.full_like(z, float("nan")), z)
            out[x0:x1] = result.cpu().numpy()
            del z, result
    return out


def select(volume, selection="escaped", vector=None, step_value=None, overlap=0):
    """Boolean mask the original passes to the mesher."""
    if selection == "even":
        return np.where(volume % 2 == 0, volume, False).astype(bool)
    if selection == "vector":
        return np.where(np.isin(volume, vector or DEFAULT_VECTOR), volume, False).astype(bool)
    if selection == "steps" and step_value is not None:
        return np.where((volume >= step_value) & (volume <= step_value + overlap), volume, False).astype(bool)
    return volume != 0


def make_generator(basedir, mode="cubes", watertight_min=0.0, decimation=None, slice_mesh=False, thickness=0.0,
                   scale_to_mm=None):
    """A StlGenerator from the engine configured like FractalParameters in its three modes."""
    generator = StlGenerator()
    p = generator.parameters
    p.basedirectory = str(basedir).rstrip("/") + "/"
    p.mode = "isdrawing" if mode == "cubes" else "issearching"
    p.selectedfew = []
    p.minimumwatertightratio = watertight_min
    p.decimationratio = decimation
    p.stlslice = slice_mesh
    p.stladdvolume = thickness
    if scale_to_mm:
        p.mode = "isrendering"
        p.extrusionwidth, p.layerheight = scale_to_mm
    Path(p.basedirectory).mkdir(parents=True, exist_ok=True)
    return generator


def build_mesh(generator, mask, name):
    """StlGenerator.generateStlCubic2: marching cubes, clean-up, optional decimation / slice / thickness,
    watertight check, STL export. Returns the trimesh (or None when rejected)."""
    return generator.generateStlCubic2(mask, filename=name)


def watertight_ratio(generator, mesh):
    saved = generator.parameters.selectedfew
    generator.parameters.selectedfew = []
    try:
        return generator.meshWatertightComponentsRatio(mesh)
    finally:
        generator.parameters.selectedfew = saved


def print_resolution(model_mm=(100, 100, 100), nozzle=0.4, layer=0.2, scaling=0.5):
    """FractalParameters.renderforprint: one voxel per extrusion width and per layer."""
    layer, width = layer * scaling, nozzle * scaling
    return [int(model_mm[0] // width), int(model_mm[1] // width), int(model_mm[2] // layer)], (width, layer)


def render_points(points, values, azimuth=35, elevation=25, size=520, cmap="gist_earth", dot=2):
    """Orthographic z-buffer splat of 3-D points coloured by value, brightest = nearest."""
    from matplotlib import colormaps
    img = np.full((size, size, 3), 17, np.uint8)
    if len(points) == 0:
        return img
    p = points.astype(np.float32) - points.mean(axis=0)
    a, e = np.radians(azimuth), np.radians(elevation)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]], np.float32)
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]], np.float32)
    q = p @ (rx @ rz).T
    scale = 0.46 * size / max(np.abs(q[:, :2]).max(), 1e-6)
    px = (q[:, 0] * scale + size / 2).astype(int)
    py = (size / 2 - q[:, 1] * scale).astype(int)
    depth = q[:, 2]
    order = np.argsort(depth)                    # far first, near drawn last
    v = np.asarray(values, np.float32)
    v = (v - v.min()) / (v.max() - v.min() + 1e-9)
    shade = 0.45 + 0.55 * (depth - depth.min()) / (depth.max() - depth.min() + 1e-9)
    colors = (colormaps.get_cmap(cmap)(v)[:, :3] * shade[:, None] * 255).astype(np.uint8)
    for dx in range(dot):
        for dy in range(dot):
            ix, iy = np.clip(px[order] + dx, 0, size - 1), np.clip(py[order] + dy, 0, size - 1)
            img[iy, ix] = colors[order]
    return img


def surface_points(volume, mask=None, max_points=400_000):
    """Occupied voxels that touch an empty one, with their iteration value."""
    occ = (volume != 0) if mask is None else mask
    padded = np.pad(occ, 1)
    inner = padded[1:-1, 1:-1, 1:-1]
    core = (padded[:-2, 1:-1, 1:-1] & padded[2:, 1:-1, 1:-1] & padded[1:-1, :-2, 1:-1] & padded[1:-1, 2:, 1:-1]
            & padded[1:-1, 1:-1, :-2] & padded[1:-1, 1:-1, 2:])
    surface = inner & ~core
    idx = np.argwhere(surface)
    if len(idx) > max_points:
        idx = idx[np.random.default_rng(0).choice(len(idx), max_points, replace=False)]
    return idx, volume[tuple(idx.T)] if len(idx) else np.zeros(0)


def mesh_points(mesh, count=300_000):
    pts, faces = trimesh.sample.sample_surface(mesh, count)
    return pts, mesh.vertices[mesh.faces[faces][:, 0]][:, 2]


def export_scad(volume, path):
    """Openscad.saveFractaltoFile: the volume as an OpenSCAD array (legacy; loads slowly above ~50^3)."""
    with open(path, "w") as f:
        f.write("fractalarray = " + np.array2string(volume, threshold=volume.size, separator=",") + ";\n")
        f.write(f"xsize = {volume.shape[0]};\nysize = {volume.shape[1]};\nzsize = {volume.shape[2]};\n")


def fuse(paths, out_path, cut_from_cube=False, slice_after=False):
    """StlGenerator.fuse_meshes / difference_meshes_from_cube / sliceMesh (the 'fusemeshs.py' script)."""
    generator = StlGenerator()
    if cut_from_cube:
        mesh = generator.difference_meshes_from_cube(paths, out_path)
        if slice_after:
            mesh = generator.sliceMesh(mesh)
            mesh.export(out_path)
        return mesh
    generator.fuse_meshes(paths, out_path)
    return trimesh.load(out_path)


def cubes_mesh(mask, max_voxels=40_000):
    """StlGenerator.generateStlCubic: one box per voxel (only practical at low resolutions)."""
    if int(mask.sum()) > max_voxels:
        raise ValueError(f"{int(mask.sum())} voxels: too many boxes, lower the resolution")
    return trimesh.voxel.VoxelGrid(mask).as_boxes()
