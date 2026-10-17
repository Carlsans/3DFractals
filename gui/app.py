"""3DFractals GUI. Run from the repository root:  python -m gui.app"""
import random
import sys
import tempfile
import threading
import traceback
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QPlainTextEdit,
                               QPushButton, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from gui import bridge  # noqa: E402


_JOBS = []


class Job(QThread):
    log = Signal(str)
    item = Signal(object)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        _JOBS.append(self)
        self.fn, self._stop = fn, threading.Event()

    def should_stop(self):
        return self._stop.is_set()

    def stop(self):
        self._stop.set()

    def run(self):
        try:
            self.finished_ok.emit(self.fn(self))
        except Exception:
            self.failed.emit(traceback.format_exc())


class LogBox(QPlainTextEdit):
    def __init__(self, height=90):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(300)
        self.setMaximumHeight(height)

    def add(self, text):
        self.appendPlainText(text)


class Runner:
    def __init__(self, log, buttons=()):
        self.log, self.buttons, self.job = log, buttons, None

    def start(self, fn, on_done=None, on_item=None):
        if self.job is not None and self.job.isRunning():
            return
        self.job = Job(fn)
        self.job.log.connect(self.log.add)
        self.job.failed.connect(lambda tb: self.log.add(tb.strip().splitlines()[-1]))
        if on_done:
            self.job.finished_ok.connect(on_done)
        if on_item:
            self.job.item.connect(on_item)
        self.job.finished.connect(lambda: [b.setEnabled(True) for b in self.buttons])
        for b in self.buttons:
            b.setEnabled(False)
        self.job.start()

    def stop(self):
        if self.job is not None:
            self.job.stop()


class View(QLabel):
    def __init__(self, size=520):
        super().__init__("no volume")
        self.setMinimumSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background:#111;color:#888")
        self.rgb = None

    def show_rgb(self, rgb):
        self.rgb = np.ascontiguousarray(rgb)
        h, w, _ = self.rgb.shape
        self.setPixmap(QPixmap.fromImage(QImage(self.rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()))


class State:
    def __init__(self):
        self.volume, self.ids, self.params = None, [0, 0, 0, 0], {}


def spin(lo, hi, v):
    w = QSpinBox(); w.setRange(lo, hi); w.setValue(v); return w


def dspin(lo, hi, v, step=0.1, dec=2):
    w = QDoubleSpinBox(); w.setRange(lo, hi); w.setSingleStep(step); w.setDecimals(dec); w.setValue(v); return w


class VolumeTab(QWidget):
    volume_ready = Signal()

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.index = spin(0, bridge.FORMULA_COUNT - 1, 16994)
        self.fn = [QComboBox() for _ in range(4)]
        for box in self.fn:
            box.addItems(bridge.FUNCTION_NAMES)
        self.index.valueChanged.connect(self.from_index)
        for box in self.fn:
            box.currentIndexChanged.connect(self.from_boxes)
        self.formula = QLabel("")
        self.res = spin(8, 400, 80)
        self.maxiter = spin(5, 1000, 100)
        self.rx0, self.rx1 = dspin(-10, 10, -2.0), dspin(-10, 10, 2.0)
        self.ry0, self.ry1 = dspin(-10, 10, -1.5), dspin(-10, 10, 1.5)
        self.zre0, self.zim0, self.zre1, self.zim1 = dspin(-10, 10, -2.0), dspin(-10, 10, 2.0), dspin(-10, 10, 2.0), dspin(-10, 10, -2.0)
        self.b_run = QPushButton("Compute volume"); self.b_run.clicked.connect(self.compute)
        b_stop = QPushButton("Stop"); b_stop.clicked.connect(lambda: self.runner.stop())
        b_log = QPushButton("Load formula from an old log (fractalNNNlog.txt)..."); b_log.clicked.connect(self.open_log)
        self.selection = QComboBox()
        for key, label in bridge.SELECTIONS:
            self.selection.addItem(label, key)
        self.selection.currentIndexChanged.connect(self.redraw)
        self.vector = QLineEdit(", ".join(map(str, bridge.DEFAULT_VECTOR)))
        self.step = spin(0, 1000, 5); self.step.valueChanged.connect(self.redraw)
        self.cmap = QComboBox(); self.cmap.addItems(["gist_earth", "viridis", "magma", "turbo", "twilight", "bone"])
        self.cmap.currentTextChanged.connect(self.redraw)
        self.az = QSlider(Qt.Horizontal); self.az.setRange(0, 360); self.az.setValue(35); self.az.valueChanged.connect(self.redraw)
        self.el = QSlider(Qt.Horizontal); self.el.setRange(-90, 90); self.el.setValue(25); self.el.valueChanged.connect(self.redraw)
        self.view = View(); self.info = QLabel(""); self.log = LogBox(70)
        self.runner = Runner(self.log, (self.b_run,))
        form = QFormLayout()
        form.addRow("Formula number (0 - 104975)", self.index)
        for k, box in enumerate(self.fn):
            form.addRow(f"fn{k + 1}", box)
        form.addRow(self.formula)
        form.addRow("Voxels per side", self.res); form.addRow("Iterations", self.maxiter)
        form.addRow("x range", self._pair(self.rx0, self.rx1)); form.addRow("y range", self._pair(self.ry0, self.ry1))
        form.addRow("z start (re, im)", self._pair(self.zre0, self.zim0)); form.addRow("z end (re, im)", self._pair(self.zre1, self.zim1))
        left = QVBoxLayout(); left.addLayout(form); left.addWidget(self._row(self.b_run, b_stop)); left.addWidget(b_log)
        right = QVBoxLayout(); right.addWidget(self.view, 1)
        sel = QFormLayout()
        sel.addRow("Voxels shown", self.selection); sel.addRow("Iteration list", self.vector); sel.addRow("Shell iteration", self.step)
        sel.addRow("Colormap", self.cmap); sel.addRow("Azimuth", self.az); sel.addRow("Elevation", self.el)
        right.addLayout(sel); right.addWidget(self.info)
        top = QHBoxLayout(); top.addLayout(left, 1); top.addLayout(right, 2)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.log)
        self.from_index()

    @staticmethod
    def _pair(a, b):
        return VolumeTab._row(a, b)

    @staticmethod
    def _row(*widgets):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0, 0, 0, 0)
        for x in widgets:
            l.addWidget(x)
        return w

    def from_index(self):
        ids = bridge.formula_ids(self.index.value())
        for box, i in zip(self.fn, ids):
            box.blockSignals(True); box.setCurrentIndex(i); box.blockSignals(False)
        self.state.ids = ids
        self.formula.setText(bridge.formula_text(ids))

    def from_boxes(self):
        ids = [b.currentIndex() for b in self.fn]
        self.index.blockSignals(True); self.index.setValue(bridge.formula_index(ids)); self.index.blockSignals(False)
        self.state.ids = ids
        self.formula.setText(bridge.formula_text(ids))

    def set_formula(self, index):
        self.index.setValue(index)

    def open_log(self):
        path, _ = QFileDialog.getOpenFileName(self, "Log", "", "Text (*.txt)")
        if path:
            ids = bridge.parse_log(path)
            if ids is None:
                self.log.add("no formula found in that file")
            else:
                self.set_formula(bridge.formula_index(ids))

    def settings(self):
        return dict(resolution=(self.res.value(),) * 3, maxiter=self.maxiter.value(),
                    rangex=(self.rx0.value(), self.rx1.value()), rangey=(self.ry0.value(), self.ry1.value()),
                    rangez=(complex(self.zre0.value(), self.zim0.value()), complex(self.zre1.value(), self.zim1.value())))

    def compute(self):
        ids, params = list(self.state.ids), self.settings()
        self.log.add(f"computing {params['resolution']} on {bridge.DEVICE} ...")

        def done(volume):
            self.state.volume, self.state.params = volume, params
            self.volume_ready.emit()
            self.redraw()
        self.runner.start(lambda job: bridge.compute_volume(ids, job=job, **params), done)

    def mask(self):
        v = self.state.volume
        sel = self.selection.currentData()
        try:
            vector = [int(x) for x in self.vector.text().replace(";", ",").split(",") if x.strip()]
        except ValueError:
            vector = None
        return bridge.select(v, sel, vector, self.step.value())

    def redraw(self):
        v = self.state.volume
        if v is None:
            return
        pts, vals = bridge.surface_points(v, self.mask())
        self.view.show_rgb(bridge.render_points(pts, vals, self.az.value(), self.el.value(), 520, self.cmap.currentText()))
        self.info.setText(f"{v.shape}, {int((v != 0).sum())} escaped voxels, highest iteration {int(v.max())}, {len(pts)} surface voxels shown")


class MeshTab(QWidget):
    def __init__(self, state, volume_tab):
        super().__init__()
        self.state, self.vt = state, volume_tab
        self.out = QLineEdit(str(Path(tempfile.gettempdir()) / "fractal3d_output"))
        b_out = QPushButton("Output folder..."); b_out.clicked.connect(self.pick)
        self.mode = QComboBox()
        for key, label in bridge.MODES:
            self.mode.addItem(label, key)
        self.water = dspin(0, 1, 0.15, 0.05, 2)
        self.decim = dspin(0, 1, 0.0, 0.05, 2)
        self.slice = QCheckBox("Cut with a diagonal plane (sliceMesh)")
        self.thick = dspin(0, 50, 0.0, 0.5, 2)
        self.scale = QCheckBox("Scale to millimetres (voxel size = extrusion width x layer height)")
        self.ext = dspin(0.05, 5, 0.2, 0.05, 2); self.layer = dspin(0.02, 2, 0.1, 0.02, 2)
        self.name = QLineEdit("fractal")
        self.b_mesh = QPushButton("Build STL"); self.b_mesh.clicked.connect(self.build)
        self.b_steps = QPushButton("Build one STL per iteration shell"); self.b_steps.clicked.connect(self.build_steps)
        legacy = QGroupBox("Legacy / experimental")
        self.b_scad = QPushButton("Export OpenSCAD array (Openscad.py)"); self.b_scad.clicked.connect(self.scad)
        self.b_cubes = QPushButton("One box per voxel (generateStlCubic, low resolutions only)"); self.b_cubes.clicked.connect(self.cubes)
        ll = QVBoxLayout(legacy); ll.addWidget(self.b_scad); ll.addWidget(self.b_cubes)
        self.view = View(420); self.info = QLabel(""); self.info.setWordWrap(True); self.log = LogBox(110)
        self.runner = Runner(self.log, (self.b_mesh, self.b_steps))
        form = QFormLayout()
        form.addRow(b_out, self.out); form.addRow("File name", self.name); form.addRow("Method", self.mode)
        form.addRow("Reject below this watertight ratio", self.water); form.addRow("Decimation (fraction of faces kept, 0 = off)", self.decim)
        form.addRow(self.slice); form.addRow("Added thickness (mm, 0 = off)", self.thick)
        form.addRow(self.scale); form.addRow("Extrusion width / layer height (mm)", self.vt._row(self.ext, self.layer))
        left = QVBoxLayout(); left.addLayout(form); left.addWidget(self.b_mesh); left.addWidget(self.b_steps); left.addWidget(legacy)
        right = QVBoxLayout(); right.addWidget(self.view, 1); right.addWidget(self.info)
        top = QHBoxLayout(); top.addLayout(left, 1); top.addLayout(right, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.log)

    def pick(self):
        p = QFileDialog.getExistingDirectory(self, "Output folder")
        if p:
            self.out.setText(p)

    def generator(self):
        scale = (self.ext.value(), self.layer.value()) if self.scale.isChecked() else None
        return bridge.make_generator(self.out.text(), self.mode.currentData(), self.water.value(),
                                     self.decim.value() or None, self.slice.isChecked(), self.thick.value(), scale)

    def build(self):
        if self.state.volume is None:
            self.log.add("compute a volume first"); return
        mask, name = self.vt.mask(), self.name.text() + ".stl"
        gen = self.generator()

        def work(job):
            mesh = bridge.build_mesh(gen, mask, name)
            if mesh is None:
                return None
            return mesh, bridge.watertight_ratio(gen, mesh)

        def done(result):
            if result is None:
                self.info.setText("rejected (empty, or below the watertight ratio)"); return
            mesh, ratio = result
            self.info.setText(f"{len(mesh.faces)} faces, watertight faces {ratio * 100:.1f} %, saved to {gen.parameters.basedirectory}{name}")
            pts, vals = bridge.mesh_points(mesh, 150_000)
            self.view.show_rgb(bridge.render_points(pts, vals, self.vt.az.value(), self.vt.el.value(), 420, self.vt.cmap.currentText()))
        self.runner.start(work, done)

    def build_steps(self):
        if self.state.volume is None:
            return
        volume, gen, base = self.state.volume, self.generator(), self.name.text()
        values = [int(v) for v in np.unique(volume) if v > 0]

        def work(job):
            made = 0
            for v in values:
                if job.should_stop():
                    break
                if bridge.build_mesh(gen, bridge.select(volume, "steps", None, v), f"{base}_step{v}.stl") is not None:
                    made += 1
                job.log.emit(f"shell {v}")
            return made
        self.runner.start(work, lambda n: self.log.add(f"{n} shells written"))

    def scad(self):
        if self.state.volume is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "OpenSCAD", "fractalarray.scad", "OpenSCAD (*.scad)")
        if path:
            bridge.export_scad(self.state.volume, path); self.log.add(f"wrote {path}")

    def cubes(self):
        if self.state.volume is None:
            return
        try:
            mesh = bridge.cubes_mesh(self.vt.mask())
        except Exception as exc:
            self.log.add(str(exc)); return
        path = Path(self.out.text()); path.mkdir(parents=True, exist_ok=True)
        mesh.export(str(path / (self.name.text() + "_boxes.stl")))
        self.log.add(f"{len(mesh.faces)} faces written")


class SearchTab(QWidget):
    open_formula = Signal(int)

    def __init__(self):
        super().__init__()
        self.mode = QComboBox(); self.mode.addItems(["a range of formula numbers", "random formula numbers"])
        self.start = spin(0, bridge.FORMULA_COUNT - 1, 15600); self.count = spin(1, 100000, 200)
        self.res = spin(16, 150, 50); self.water = dspin(0, 1, 0.15, 0.05, 2)
        self.b_run = QPushButton("Search"); b_stop = QPushButton("Stop")
        self.b_run.clicked.connect(self.run); b_stop.clicked.connect(lambda: self.runner.stop())
        b_save = QPushButton("Save kept numbers..."); b_save.clicked.connect(self.save)
        self.list = QListWidget(); self.list.itemDoubleClicked.connect(lambda i: self.open_formula.emit(i.data(Qt.UserRole)))
        self.view = View(360)
        self.list.currentItemChanged.connect(self.preview)
        self.log = LogBox(80)
        self.runner = Runner(self.log, (self.b_run,))
        self.kept = {}
        form = QFormLayout()
        form.addRow("Method", self.mode); form.addRow("First number", self.start); form.addRow("How many", self.count)
        form.addRow("Voxels per side", self.res); form.addRow("Keep if watertight faces >=", self.water)
        left = QVBoxLayout(); left.addLayout(form)
        row = QHBoxLayout(); [row.addWidget(w) for w in (self.b_run, b_stop, b_save)]; left.addLayout(row)
        left.addWidget(QLabel("Kept formulas (double-click to open in the first tab)")); left.addWidget(self.list, 1)
        top = QHBoxLayout(); top.addLayout(left, 1); top.addWidget(self.view, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.log)

    def run(self):
        mode, start, count, res, water = self.mode.currentIndex(), self.start.value(), self.count.value(), self.res.value(), self.water.value()
        self.list.clear(); self.kept = {}
        tmp = tempfile.mkdtemp(prefix="fractal3d_search_")

        def work(job):
            gen = bridge.make_generator(tmp, "smooth", 0.0)
            ids_to_try = ([random.randrange(bridge.FORMULA_COUNT) for _ in range(count)] if mode == 1
                          else list(range(start, min(start + count, bridge.FORMULA_COUNT))))
            kept = 0
            for n, fid in enumerate(ids_to_try):
                if job.should_stop():
                    break
                volume = bridge.compute_volume(bridge.formula_ids(fid), (res,) * 3, 100)
                mask = bridge.select(volume)
                if mask.sum() < 50:
                    continue
                mesh = bridge.build_mesh(gen, mask, "candidate.stl")
                if mesh is None:
                    continue
                ratio = bridge.watertight_ratio(gen, mesh)
                if ratio >= water:
                    kept += 1
                    job.item.emit((fid, ratio, volume))
                job.log.emit(f"{n + 1}/{len(ids_to_try)} formula {fid}: ratio {ratio:.2f}") if (n + 1) % 20 == 0 else None
            return kept

        def on_item(item):
            fid, ratio, volume = item
            self.kept[fid] = volume
            it = QListWidgetItem(f"{fid}   {bridge.formula_text(bridge.formula_ids(fid))}   ({ratio * 100:.0f} % watertight)")
            it.setData(Qt.UserRole, fid)
            self.list.addItem(it)
        self.runner.start(work, lambda k: self.log.add(f"{k} formulas kept"), on_item)

    def preview(self, item, _=None):
        if item is None:
            return
        volume = self.kept.get(item.data(Qt.UserRole))
        if volume is not None:
            pts, vals = bridge.surface_points(volume)
            self.view.show_rgb(bridge.render_points(pts, vals, 35, 25, 360))

    def save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Kept numbers", "kept_formulas.txt", "Text (*.txt)")
        if path:
            Path(path).write_text("\n".join(str(k) for k in self.kept) + "\n")


class PrintTab(QWidget):
    def __init__(self, state, volume_tab, mesh_tab):
        super().__init__()
        self.state, self.vt, self.mt = state, volume_tab, mesh_tab
        self.size = spin(10, 400, 100)
        self.nozzle = dspin(0.1, 2, 0.4, 0.05, 2); self.layer = dspin(0.05, 0.6, 0.2, 0.05, 2)
        self.scaling = dspin(0.1, 4, 0.5, 0.1, 2)
        self.maxvox = spin(1, 4000, 100)
        self.info = QLabel(""); self.info.setWordWrap(True)
        self.b_calc = QPushButton("Compute resolution"); self.b_calc.clicked.connect(self.calc)
        self.b_run = QPushButton("Render and build a print-sized STL"); self.b_run.clicked.connect(self.run)
        self.log = LogBox(160)
        self.runner = Runner(self.log, (self.b_run,))
        form = QFormLayout()
        form.addRow("Model size (mm, cube)", self.size); form.addRow("Nozzle diameter (mm)", self.nozzle); form.addRow("Layer height (mm)", self.layer)
        form.addRow("Scaling (below 1 = finer voxels = heavier)", self.scaling)
        form.addRow("Refuse if more than (million voxels)", self.maxvox)
        lay = QVBoxLayout(self); lay.addLayout(form); lay.addWidget(self.b_calc); lay.addWidget(self.info); lay.addWidget(self.b_run); lay.addWidget(self.log)
        self.calc()

    def calc(self):
        res, (width, layer) = bridge.print_resolution((self.size.value(),) * 3, self.nozzle.value(), self.layer.value(), self.scaling.value())
        total = res[0] * res[1] * res[2]
        self.info.setText(f"Resolution {res} = {total / 1e6:.0f} million voxels, voxel {width:.3f} x {width:.3f} x {layer:.3f} mm. "
                          f"The volume alone needs {total * 2 / 1e9:.1f} GB of memory (int16).")
        return res, (width, layer), total

    def run(self):
        res, (width, layer), total = self.calc()
        if total > self.maxvox.value() * 1e6:
            self.log.add("too many voxels for the limit set above"); return
        ids = list(self.state.ids)
        params = dict(self.vt.settings(), resolution=tuple(res))
        gen = bridge.make_generator(self.mt.out.text(), "cubes", 0.0, 0.2, False, 0.0, (width, layer))
        name = self.mt.name.text() + "_print.stl"

        def work(job):
            job.log.emit("computing the volume in slabs ...")
            volume = bridge.compute_volume(ids, job=job, **params)
            job.log.emit("meshing (this can take a long time and a lot of memory) ...")
            try:
                mesh = bridge.build_mesh(gen, bridge.select(volume), name)
            except Exception as exc:
                job.log.emit(f"decimation or meshing failed: {exc}")
                gen.parameters.decimationratio = None
                mesh = bridge.build_mesh(gen, bridge.select(volume), name)
            return mesh
        self.runner.start(work, lambda m: self.log.add("rejected" if m is None else f"{len(m.faces)} faces written to {gen.parameters.basedirectory}{name}"))


class ToolsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.files = QListWidget()
        b_add = QPushButton("Add STL files..."); b_add.clicked.connect(self.add)
        b_clear = QPushButton("Clear"); b_clear.clicked.connect(self.files.clear)
        self.cut = QCheckBox("Subtract them from a cube instead of fusing (difference_meshes_from_cube)")
        self.slice = QCheckBox("Then cut with a diagonal plane (sliceMesh), as fusemeshs.py did")
        b_run = QPushButton("Fuse..."); b_run.clicked.connect(self.run)
        self.view = View(360); self.log = LogBox(100)
        b_open = QPushButton("View an STL file..."); b_open.clicked.connect(self.open_stl)
        left = QVBoxLayout()
        left.addWidget(QLabel("Fuse several STL files (fusemeshs.py)")); left.addWidget(self.files, 1)
        row = QHBoxLayout(); row.addWidget(b_add); row.addWidget(b_clear); left.addLayout(row)
        left.addWidget(self.cut); left.addWidget(self.slice); left.addWidget(b_run); left.addWidget(b_open)
        top = QHBoxLayout(); top.addLayout(left, 1); top.addWidget(self.view, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.log)

    def add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "STL", "", "STL (*.stl)")
        self.files.addItems(paths)

    def run(self):
        paths = [self.files.item(i).text() for i in range(self.files.count())]
        if not paths:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Output", "fused.stl", "STL (*.stl)")
        if out:
            try:
                mesh = bridge.fuse(paths, out, self.cut.isChecked(), self.slice.isChecked())
                self.log.add(f"{len(mesh.faces)} faces written to {out}")
            except Exception as exc:
                self.log.add(f"{type(exc).__name__}: {exc} (boolean operations need a trimesh boolean engine such as manifold3d)")

    def open_stl(self):
        path, _ = QFileDialog.getOpenFileName(self, "STL", "", "STL (*.stl)")
        if path:
            import trimesh
            mesh = trimesh.load(path)
            pts, vals = bridge.mesh_points(mesh, 200_000)
            self.view.show_rgb(bridge.render_points(pts, vals, 35, 25, 360))
            self.log.add(f"{len(mesh.faces)} faces, watertight: {mesh.is_watertight}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3DFractals")
        state = State()
        self.vt = VolumeTab(state)
        self.mt = MeshTab(state, self.vt)
        self.st = SearchTab()
        self.pt = PrintTab(state, self.vt, self.mt)
        self.tt = ToolsTab()
        tabs = QTabWidget()
        for w, name in ((self.vt, "Formula and volume"), (self.mt, "Mesh and export"), (self.st, "Search"), (self.pt, "Print size"),
                        (self.tt, "Legacy tools")):
            tabs.addTab(w, name)
        self.setCentralWidget(tabs)
        self.st.open_formula.connect(lambda n: (self.vt.set_formula(n), tabs.setCurrentWidget(self.vt)))
        self.resize(1200, 820)

    def closeEvent(self, event):
        running = [job for job in _JOBS if job.isRunning()]
        for job in running:
            job.stop()
        # a QThread destroyed while running aborts the process, and terminating one inside CUDA does too
        if not all(job.wait(15000) for job in running):
            import os
            os._exit(0)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
