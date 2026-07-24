"""
STEP Surface Selector & STL Exporter
=====================================
Requirements:
    pip install pythonocc-core PySide6

Usage:
    python step_surface_selector.py [path/to/file.step]
    or run with no arguments and use File > Import STEP.

Session files (.sss) are JSON and store:
  - absolute path to the STEP file
  - all group definitions (name -> list of face indices)
  - hidden face indices
  - display mode
  - group color index counter
"""

import sys
import os
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
import json
from collections import defaultdict

# ── OCC imports ───────────────────────────────────────────────────────────────
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepClass3d import BRepClass3d_SolidClassifier
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.TopoDS import TopoDS_Compound, TopoDS_Shape
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.AIS import AIS_Shape, AIS_InteractiveObject, AIS_DisplayMode
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.Aspect import Aspect_TOL_SOLID
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.gp import gp_Pnt, gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.TopAbs import TopAbs_SOLID
from OCC.Core.BRep import BRep_Tool
from OCC.Core.V3d import V3d_DirectionalLight
import math
import subprocess
import random
import struct
from OCC.Display.backend import load_backend

load_backend("pyside6")
from OCC.Display.qtDisplay import qtViewer3d

# ── Qt imports ────────────────────────────────────────────────────────────────
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QLineEdit,
    QFileDialog, QMessageBox, QSplitter, QGroupBox, QToolBar, QInputDialog, QScrollArea, QFrame, QTreeWidget,
    QTreeWidgetItem, QAbstractItemView, QStatusBar, QColorDialog,
    QMenuBar, QMenu, QDoubleSpinBox, QDialog, QDialogButtonBox,
    QSlider, QSpinBox, QSizePolicy, QRubberBand,
)
from PySide6.QtCore import Qt, QSize, QRect, QPoint, QTimer, Signal
from PySide6.QtWidgets import QRubberBand
from PySide6.QtGui import QAction, QColor, QIcon, QFont, QPainter, QPen, QBrush, QPolygon


# Pointer file: a tiny text file next to the scripts that holds the path
# to the current stl_bridge.json. Since the STEP tool and XML GUI run as
# separate processes, env vars don't cross — the pointer file does.
_BRIDGE_PTR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'stl_bridge.ptr')

def _write_stl_bridge(out_dir: str, stl_paths: list, vtk_path: str | None = None):
    """Write stl_bridge.json into out_dir and record its path in stl_bridge.ptr."""
    bridge_path = os.path.join(out_dir, 'stl_bridge.json')
    payload = {'stl_files': stl_paths}
    if vtk_path:
        payload['vtk_files'] = [vtk_path]
    try:
        with open(bridge_path, 'w', encoding='utf-8') as _f:
            json.dump(payload, _f, indent=2)
        # Write pointer so the XML GUI subprocess can locate the bridge
        with open(_BRIDGE_PTR, 'w', encoding='utf-8') as _pf:
            _pf.write(bridge_path)
    except Exception as _e:
        print(f'Bridge write failed: {_e}')


# ctypes helper used for OCC view unprojection
import ctypes
def ctypes_float(v=0.0):
    return ctypes.c_double(v)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_step(path: str):
    reader = STEPControl_Reader()
    status = reader.ReadFile(path)
    if status != 1:
        raise RuntimeError(f"Cannot read STEP file: {path}")
    reader.TransferRoots()
    root = reader.OneShape()
    faces = []
    explorer = TopExp_Explorer(root, TopAbs_FACE)
    while explorer.More():
        faces.append(explorer.Current())
        explorer.Next()
    return root, faces


def shapes_to_stl(shapes, output_path: str, linear_deflection=0.1, angular_deflection=0.5):
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for s in shapes:
        builder.Add(compound, s)
    mesh = BRepMesh_IncrementalMesh(compound, linear_deflection, False, angular_deflection)
    mesh.Perform()
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    writer.Write(compound, output_path)


def _write_probe_vtk(point, output_path: str):
    """Write a single point as a VTK legacy ASCII PolyData file."""
    x, y, z = point
    content = (
        "# vtk DataFile Version 3.0\n"
        "Probe Point\n"
        "ASCII\n"
        "DATASET POLYDATA\n"
        "POINTS 1 float\n"
        f"{x:.8g} {y:.8g} {z:.8g}\n"
        "VERTICES 1 2\n"
        "1 0\n"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def occ_color(r, g, b):
    return Quantity_Color(r, g, b, Quantity_TOC_RGB)



# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

HIGHLIGHT_COLOR = occ_color(1.0, 0.6, 0.0)
NORMAL_COLOR    = occ_color(0.7, 0.8, 0.9)
GROUP_COLORS = [
    (0.2, 0.8, 0.4),
    (0.9, 0.3, 0.3),
    (0.3, 0.5, 1.0),
    (0.9, 0.7, 0.1),
    (0.7, 0.2, 0.9),
    (0.1, 0.8, 0.8),
]


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class SurfaceSelectorWidget(QWidget):
    """Embeddable STEP management widget — works inside a tab OR standalone."""
    # Signal emitted after a successful Export to CAE
    exported = Signal(list)   # list of STL paths
    groups_changed = Signal()  # emitted when groups are added/renamed/deleted

    def __init__(self, step_path=None, parent=None):
        super().__init__(parent)
        self._is_embedded = parent is not None

        # ── State ─────────────────────────────────────────────────────────────
        self.step_path = None
        self.root_shape = None
        self.faces: list[TopoDS_Shape] = []
        self.ais_faces: list[AIS_Shape] = []
        self.selected_indices: set[int] = set()
        self.groups: dict[str, list[int]] = {}
        self.hidden_indices: set[int] = set()
        self._display_mode = "shaded"
        self._group_color_idx = 0
        # map group_name -> (r,g,b) so colours survive save/load
        self._group_colors: dict[str, tuple] = {}
        # map group_name -> transparency 0.0–1.0 (0=opaque, 1=fully transparent)
        self._group_transparency: dict[str, float] = {}
        # probe point
        self._probe_point: list = [0.0, 0.0, 0.0]   # [x, y, z]
        self._probe_ais = None                        # AIS_Shape for sphere
        self._probe_active = False
        self._probe_dragging = False
        # bounding box cache
        self._bbox = None   # (xmin,ymin,zmin,xmax,ymax,zmax)
        # overlay label
        self._info_label = None
        # axis overlay widget
        self._axis_widget = None
        # panel toggle actions (only created in standalone/menubar mode)
        self._act_show_surfaces = None
        self._act_show_groups = None
        # OCC display — initialised lazily on first show
        self._display = None
        # STL export refinement settings, configurable via "Output STL
        # refinement" toolbar button. linear_deflection: max chord error
        # between the mesh and the true surface (smaller = finer, more
        # triangles, better curvature following). angular_deflection: max
        # angle (degrees) between adjacent triangle normals (smaller = finer
        # on curved regions specifically).
        self._stl_linear_deflection = 0.1
        self._stl_angular_deflection_deg = 10.0
        # GEO-tab requirements (optional, declared in GUIsetup.xml).
        # Both default to "no requirement" so setups that don't mention
        # them behave exactly as before.
        self._probe_required = False
        self._mandatory_groups = []

        if not self._is_embedded:
            self._build_menubar_standalone()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._finalise_layout()
        # Expand to fill whatever container we're placed in
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Surface list hidden by default
        self._surface_panel.setVisible(False)
        if self._act_show_surfaces:
            self._act_show_surfaces.setChecked(False)

        if step_path:
            self._open_file(step_path)

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _build_menubar_standalone(self):
        """Build a QMenuBar and insert it at the top of this widget's layout."""
        mb = QMenuBar(self)
        self._menubar = mb
        # Will be prepended to the layout by _build_toolbar

        # File menu
        file_menu = mb.addMenu("File")
        self._add_action(file_menu, "Import STEP...",  self._on_open,          "Ctrl+O")
        file_menu.addSeparator()
        self._add_action(file_menu, "Quit",            self.close,             "Ctrl+Q")

        # Selection menu
        sel_menu = mb.addMenu("Selection")
        self._add_action(sel_menu, "Clear Selection",            self._clear_selection)
        sel_menu.addSeparator()
        self._add_action(sel_menu, "Select Unassigned",          self._select_unassigned)
        sel_menu.addSeparator()
        self._add_action(sel_menu, "Select Area Below Threshold...", self._select_area_below)
        self._add_action(sel_menu, "Select Area Above Threshold...", self._select_area_above)

        # View menu
        view_menu = mb.addMenu("View")
        self._add_action(view_menu, "Shaded",         self._set_shaded)
        self._add_action(view_menu, "Wireframe",      self._set_wireframe)
        view_menu.addSeparator()
        self._add_action(view_menu, "Hide Selected",  self._hide_selected)
        self._add_action(view_menu, "Show All",       self._show_all)
        view_menu.addSeparator()
        self._add_action(view_menu, "Fit All",        self._fit_all,          "F")

        # Panels menu
        panels_menu = mb.addMenu("Panels")
        self._act_show_surfaces = QAction("Show Surface List", self, checkable=True, checked=True)
        self._act_show_surfaces.triggered.connect(self._toggle_surface_panel)
        panels_menu.addAction(self._act_show_surfaces)
        self._act_show_groups = QAction("Show Group List", self, checkable=True, checked=True)
        self._act_show_groups.triggered.connect(self._toggle_group_panel)
        panels_menu.addAction(self._act_show_groups)

        # Tools menu
        tools_menu = mb.addMenu("Tools")
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Place Probe Point",        self._place_probe_point)
        self._add_action(tools_menu, "Remove Probe Point",       self._remove_probe_point)
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Toggle Model Info Overlay",self._toggle_info_overlay)

    def _add_action(self, menu_or_tb, label, slot, shortcut=None):
        a = QAction(label, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(shortcut)
        menu_or_tb.addAction(a)
        return a

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setIconSize(QSize(24, 24))
        # QWidget has no addToolBar — add it to the top of our layout
        # Layout is built in _build_central, so we store tb and insert later
        self._toolbar = tb

        for label, tip, slot, shortcut in [
            ("Import STEP",  "Import STEP file",          self._on_open,      "Ctrl+O"),
            (None, None, None, None),
            ("Shaded",     "Shaded display mode",       self._set_shaded,   None),
            ("Wireframe",  "Wireframe display mode",    self._set_wireframe,None),
            (None, None, None, None),
            ("Hide Sel.",  "Hide selected surfaces",    self._hide_selected,None),
            ("Show All",   "Show all surfaces",         self._show_all,     None),
            (None, None, None, None),
            ("Fit All",    "Fit view to all shapes",    self._fit_all,      "F"),
            ("Output STL refinement", "Set STL export mesh resolution", self._open_stl_refinement_dialog, None),
        ]:
            if label is None:
                tb.addSeparator()
            else:
                a = QAction(label, self)
                a.setToolTip(tip)
                a.triggered.connect(slot)
                if shortcut:
                    a.setShortcut(shortcut)
                tb.addAction(a)

    def _finalise_layout(self):
        """Insert menubar and toolbar above the splitter in the VBox layout."""
        lay = self.layout()
        if lay is None:
            return
        insert_idx = 0
        if hasattr(self, '_menubar'):
            lay.insertWidget(insert_idx, self._menubar)
            insert_idx += 1
        lay.insertWidget(insert_idx, self._toolbar)

    # ── Central widget ────────────────────────────────────────────────────────

    def _build_central(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._splitter = splitter
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(splitter, stretch=1)

        self.canvas = qtViewer3d(self)
        self.canvas.setMinimumWidth(200)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(self.canvas)

        right = QWidget()
        right.setMinimumWidth(320)
        right.setMaximumWidth(420)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 6, 6, 6)
        rl.setSpacing(8)
        splitter.addWidget(right)

        # Surface list
        self._surface_panel = QGroupBox("Surfaces  (click to select / deselect)")
        fl = QVBoxLayout(self._surface_panel)
        self.face_list = QListWidget()
        self.face_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.face_list.itemSelectionChanged.connect(self._on_face_selection_changed)
        fl.addWidget(self.face_list)
        rl.addWidget(self._surface_panel, 3)

        # Groups panel
        self._group_panel = QGroupBox("Groups")
        gg = self._group_panel
        gl = QVBoxLayout(gg)

        row = QHBoxLayout()
        self.group_name_edit = QLineEdit()
        self.group_name_edit.setPlaceholderText("Group name…")
        row.addWidget(self.group_name_edit)
        btn_add = QPushButton("Add Group")
        btn_add.clicked.connect(self._add_group)
        row.addWidget(btn_add)
        gl.addLayout(row)

        self.group_tree = QTreeWidget()
        self.group_tree.setHeaderLabels(["Group / Surface", "# Faces"])
        self.group_tree.setColumnWidth(0, 200)
        self.group_tree.itemClicked.connect(self._on_group_item_clicked)
        self.group_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.group_tree.customContextMenuRequested.connect(self._on_group_tree_context_menu)
        gl.addWidget(self.group_tree)

        btn_row = QHBoxLayout()
        btn_del = QPushButton("Delete Group")
        btn_del.clicked.connect(self._delete_group)
        btn_row.addWidget(btn_del)
        btn_clr = QPushButton("Clear Selection")
        btn_clr.clicked.connect(self._clear_selection)
        btn_row.addWidget(btn_clr)
        gl.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        btn_unassigned = QPushButton("Select Unassigned")
        btn_unassigned.setToolTip("Select all surfaces not yet in any group")
        btn_unassigned.clicked.connect(self._select_unassigned)
        btn_row2.addWidget(btn_unassigned)
        btn_check = QPushButton("Check Overlaps")
        btn_check.setToolTip("Find surfaces assigned to more than one group")
        btn_check.clicked.connect(self._check_overlaps)
        btn_row2.addWidget(btn_check)
        gl.addLayout(btn_row2)

        # ── Area selection ────────────────────────────────────────────
        btn_row3 = QHBoxLayout()
        btn_below = QPushButton("Area Below...")
        btn_below.setToolTip("Select surfaces with area below a threshold")
        btn_below.clicked.connect(self._select_area_below)
        btn_row3.addWidget(btn_below)
        btn_above = QPushButton("Area Above...")
        btn_above.setToolTip("Select surfaces with area above a threshold")
        btn_above.clicked.connect(self._select_area_above)
        btn_row3.addWidget(btn_above)
        gl.addLayout(btn_row3)

        # ── Probe point ───────────────────────────────────────────────
        btn_row4 = QHBoxLayout()
        btn_probe = QPushButton("Place Probe Point")
        btn_probe.setToolTip("Place a red sphere probe point inside the model")
        btn_probe.clicked.connect(self._place_probe_point)
        btn_row4.addWidget(btn_probe)
        btn_rm_probe = QPushButton("Remove Probe")
        btn_rm_probe.setToolTip("Remove the probe point from the view")
        btn_rm_probe.clicked.connect(self._remove_probe_point)
        btn_row4.addWidget(btn_rm_probe)
        gl.addLayout(btn_row4)

        rl.addWidget(self._group_panel, 2)
        rl.addStretch()

    def _build_statusbar(self):
        # QWidget has no native status bar; use a label at the bottom
        self.status = _StatusBarProxy(self)
        self.status.showMessage("Open a STEP file or session to begin.")

    def showEvent(self, event):
        """Initialise the OCC driver lazily on first show (safe for embedded use).

        showEvent fires as the widget *starts* becoming visible, but the
        underlying X11 window may not be fully mapped by the X server yet —
        especially for a widget nested inside a QScrollArea/QTabWidget that
        itself was just realised for the first time. Calling InitDriver()
        (which has OCC attach its OpenGL/X11 rendering context directly to
        this widget's native window) too early can hit a window that exists
        as a Qt object but doesn't yet have a valid X11 id from the server's
        point of view, producing a fatal 'BadWindow' X protocol error.

        Qt's own isVisible() is not a reliable signal here — it can return
        True before the X server has actually mapped/exposed the window.
        The reliable signal is the top-level QWindow's isExposed() (true
        only after the platform has confirmed the window is mapped and
        ready to be drawn into) combined with pumping the event loop so any
        pending X11 map/configure events are actually processed before we
        proceed.
        """
        super().showEvent(event)
        if hasattr(self, 'canvas') and not hasattr(self, '_display'):
            self._display = None
            QTimer.singleShot(0, self._init_occ_driver_deferred)

    def _is_truly_exposed(self) -> bool:
        """Return True only once the top-level native window is confirmed
        mapped/exposed by the windowing system — more reliable than
        QWidget.isVisible() for timing X11/OpenGL attachment."""
        if not self.isVisible():
            return False
        top = self.window()
        win_handle = top.windowHandle() if top is not None else None
        if win_handle is not None:
            try:
                return bool(win_handle.isExposed())
            except Exception:
                pass
        # Fallback: no QWindow handle available yet — not safe to proceed.
        return False

    def _init_occ_driver_deferred(self):
        """Deferred driver init for the very first show. Re-defers itself
        (with the event loop pumped each time) until the top-level window
        is confirmed exposed by the platform, then runs the real init."""
        if getattr(self, '_display', None) is not None:
            return  # already initialised
        QApplication.processEvents()  # let any pending map/configure events land
        if not self._is_truly_exposed():
            QTimer.singleShot(30, self._init_occ_driver_deferred)
            return
        self._init_occ_driver_now()

    def _init_occ_driver_now(self):
        """Actually initialise the OCC driver, synchronously. Safe to call
        any time the widget is already known to be visible/mapped (e.g. from
        a user-triggered action like opening a STEP file)."""
        if getattr(self, '_display', None) is not None:
            return
        try:
            self.canvas.InitDriver()
            self._display = self.canvas._display
            self.canvas.mouseReleaseEvent = self._on_canvas_click
            self._apply_display_mode_to_all()
        except Exception as e:
            print(f'OCC InitDriver failed: {e}')

    def closeEvent(self, event=None):
        """Tear down the OCC context/view before Qt destroys the native window.

        Without this, closing a tab/window that hosts the OCC viewport can
        race with X11 window destruction, producing BadWindow errors when
        OCC's view/context still holds a reference to the now-gone window.

        Can also be called directly with event=None (e.g. from
        StepEmbedWidget.cleanup_occ()) for widgets that never receive a
        real Qt closeEvent because they're embedded children, not top-level
        windows.
        """
        try:
            if getattr(self, '_display', None) is not None:
                ctx = self._display.Context
                # Erase all displayed objects and remove them from the context
                ctx.RemoveAll(True)
                # Release the view before the widget's window handle disappears
                if hasattr(self._display, 'View') and self._display.View is not None:
                    self._display.View.Remove()
        except Exception as e:
            print(f'OCC cleanup on close failed (non-fatal): {e}')
        finally:
            self._display = None
        if event is not None:
            super().closeEvent(event)


    def __del__(self):
        # Defensive: ensure cleanup runs even if closeEvent was never called
        # (e.g. widget destroyed programmatically without going through close()).
        try:
            if getattr(self, '_display', None) is not None:
                self._display.Context.RemoveAll(True)
        except Exception:
            pass

    # ── File open ─────────────────────────────────────────────────────────────

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open STEP File", "",
            "STEP Files (*.step *.stp *.STEP *.STP)"
        )
        if path:
            self._open_file(path)

    def _open_file(self, path: str):
        self.status.showMessage(f"Loading {path} …")
        QApplication.processEvents()
        try:
            root, faces = load_step(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status.showMessage("Load failed.")
            return

        self.step_path = path
        self.root_shape = root
        self.faces = faces
        self.selected_indices.clear()
        self.hidden_indices.clear()
        self.groups.clear()
        self._group_colors.clear()
        self._group_color_idx = 0
        # Mandatory groups (declared in GUIsetup.xml) survive a re-open:
        # re-create them empty so they're always visible in the panel.
        for _g in self._mandatory_groups:
            self.groups[_g] = []

        if not hasattr(self, '_display') or self._display is None:
            self._init_occ_driver_now()
        if self._display is None:
            QMessageBox.critical(self, "Error",
                                 "Failed to initialise the 3D viewer.")
            return
        self.canvas.mouseReleaseEvent = self._on_canvas_click

        self._display.EraseAll()
        self.ais_faces.clear()
        for face in self.faces:
            ais = AIS_Shape(face)
            ais.SetColor(NORMAL_COLOR)
            self._display.Context.Display(ais, True)
            self.ais_faces.append(ais)

        self._apply_display_mode_to_all()
        self._display.FitAll()

        # Compute bounding box
        box = Bnd_Box()
        brepbndlib.Add(self.root_shape, box)
        xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
        self._bbox = (xmin, ymin, zmin, xmax, ymax, zmax)
        self._update_info_overlay()

        self.face_list.blockSignals(True)
        self.face_list.clear()
        for i in range(len(self.faces)):
            item = QListWidgetItem(f"Surface {i+1:03d}")
            item.setData(Qt.UserRole, i)
            self.face_list.addItem(item)
        self.face_list.blockSignals(False)

        # Repaint the group tree — self.groups may still contain the
        # mandatory groups (re-created above), so don't just clear the view.
        self._refresh_group_tree()
        if self.isWindow():
            # Only meaningful (and warning-free) for the standalone window;
            # embedded in a tab, this widget is not a top-level window.
            self.setWindowTitle(
                f"STEP Surface Selector — {os.path.basename(path)}"
            )
        self.status.showMessage(
            f"Loaded {len(self.faces)} surfaces from {os.path.basename(path)}"
        )

    # ── Viewport interaction ──────────────────────────────────────────────────

    def _on_canvas_click(self, event):
        qtViewer3d.mouseReleaseEvent(self.canvas, event)
        ctx = self._display.Context
        ctx.InitSelected()
        if not ctx.MoreSelected():
            return
        sel = ctx.SelectedInteractive()
        face_idx = None
        for i, ais in enumerate(self.ais_faces):
            if ais == sel:
                face_idx = i
                break
        if face_idx is None:
            return
        if event.button() == Qt.RightButton:
            self._show_surface_context_menu(face_idx, event.globalPos())
        else:
            self._toggle_face(face_idx, sync_list=True)

    def _show_surface_context_menu(self, face_idx: int, global_pos):
        """Rich context menu shown when right-clicking a surface in the 3-D view."""
        from PySide6.QtWidgets import QMenu, QWidgetAction
        from PySide6.QtGui import QFont as QF

        # ── Gather info ───────────────────────────────────────────────────
        props = GProp_GProps()
        brepgprop.SurfaceProperties(self.faces[face_idx], props)
        area = props.Mass()
        belonging = [name for name, idxs in self.groups.items() if face_idx in idxs]

        # ── Build menu ────────────────────────────────────────────────────
        menu = QMenu(self)

        # Title label (non-interactive)
        title_action = QWidgetAction(menu)
        title_lbl = QLabel(f"  Surface {face_idx+1:03d}  ")
        f = title_lbl.font(); f.setBold(True); f.setPointSize(f.pointSize() + 1)
        title_lbl.setFont(f)
        title_lbl.setStyleSheet("padding: 4px 8px; background: palette(midlight);")
        title_action.setDefaultWidget(title_lbl)
        menu.addAction(title_action)

        # Area info
        area_action = QWidgetAction(menu)
        area_lbl = QLabel(f"  Area: {area:.6g} units²  ")
        area_lbl.setStyleSheet("padding: 2px 8px; color: grey;")
        area_action.setDefaultWidget(area_lbl)
        menu.addAction(area_action)

        # Groups info
        if belonging:
            grp_action = QWidgetAction(menu)
            grp_lbl = QLabel(f"  Groups: {', '.join(belonging)}  ")
            grp_lbl.setStyleSheet("padding: 2px 8px; color: grey;")
            grp_action.setDefaultWidget(grp_lbl)
            menu.addAction(grp_action)
        else:
            grp_action = QWidgetAction(menu)
            grp_lbl = QLabel("  Groups: (unassigned)  ")
            grp_lbl.setStyleSheet("padding: 2px 8px; color: grey;")
            grp_action.setDefaultWidget(grp_lbl)
            menu.addAction(grp_action)

        menu.addSeparator()

        # Hide this surface
        act_hide_surf = menu.addAction(f"Hide Surface {face_idx+1:03d}")

        menu.addSeparator()

        # Remove from group sub-menu (one entry per group this face belongs to)
        remove_actions = {}
        if belonging:
            remove_menu = menu.addMenu("Remove from group")
            for gname in belonging:
                act = remove_menu.addAction(gname)
                remove_actions[act] = gname
        else:
            no_remove = menu.addAction("Remove from group")
            no_remove.setEnabled(False)

        menu.addSeparator()

        # Add to existing group sub-menu
        other_groups = [g for g in self.groups if g not in belonging]
        add_existing_actions = {}
        if other_groups:
            add_menu = menu.addMenu("Add to existing group")
            for gname in other_groups:
                act = add_menu.addAction(gname)
                add_existing_actions[act] = gname
        else:
            no_add = menu.addAction("Add to existing group")
            no_add.setEnabled(False)

        # Add to new group
        act_new_group = menu.addAction("Add to new group...")

        # ── Execute ───────────────────────────────────────────────────────
        chosen = menu.exec_(global_pos)

        if chosen == act_hide_surf:
            ctx2 = self._display.Context
            ctx2.Erase(self.ais_faces[face_idx], True)
            self.hidden_indices.add(face_idx)
            item = self.face_list.item(face_idx)
            item.setForeground(QColor(160, 160, 160))
            item.setText(f"Surface {face_idx+1:03d}  [hidden]")
            self.status.showMessage(f"Surface {face_idx+1:03d} hidden.")

        elif chosen in remove_actions:
            self._remove_face_from_group(face_idx, remove_actions[chosen])

        elif chosen in add_existing_actions:
            gname = add_existing_actions[chosen]
            existing = set(self.groups[gname])
            existing.add(face_idx)
            self.groups[gname] = sorted(existing)
            r, g, b = self._ensure_group_color(gname)
            self._set_face_color(face_idx, occ_color(r, g, b))
            t = self._group_transparency.get(gname, 0.0)
            self._display.Context.SetTransparency(self.ais_faces[face_idx], t, True)
            self._refresh_group_tree()
            self.status.showMessage(
                f"Surface {face_idx+1:03d} added to group '{gname}'."
            )

        elif chosen == act_new_group:
            name, ok = QInputDialog.getText(
                self, "New group", "Enter group name:"
            )
            name = name.strip()
            if not ok or not name:
                return
            if name in self.groups:
                existing = set(self.groups[name])
                existing.add(face_idx)
                self.groups[name] = sorted(existing)
            else:
                self.groups[name] = [face_idx]
                r, g, b = GROUP_COLORS[self._group_color_idx % len(GROUP_COLORS)]
                self._group_colors[name] = (r, g, b)
                self._group_transparency[name] = 0.0
                self._group_color_idx += 1
            r, g, b = self._ensure_group_color(name)
            self._set_face_color(face_idx, occ_color(r, g, b))
            self._refresh_group_tree()
            self.status.showMessage(
                f"Surface {face_idx+1:03d} added to group '{name}'."
            )

    def _toggle_face(self, idx: int, sync_list=False):
        if idx in self.selected_indices:
            self.selected_indices.discard(idx)
            self._restore_face_color(idx)
        else:
            self.selected_indices.add(idx)
            self._set_face_color(idx, HIGHLIGHT_COLOR)

        if sync_list:
            self.face_list.blockSignals(True)
            self.face_list.item(idx).setSelected(idx in self.selected_indices)
            self.face_list.blockSignals(False)

        self.status.showMessage(f"{len(self.selected_indices)} surface(s) selected.")

    def _set_face_color(self, idx: int, color: Quantity_Color):
        ctx = self._display.Context
        ctx.SetColor(self.ais_faces[idx], color, True)

    def _restore_face_color(self, idx: int):
        """Restore a face to its group colour, or NORMAL if unassigned."""
        for name, indices in self.groups.items():
            if idx in indices:
                color_tuple = self._group_colors.get(name)
                if color_tuple:
                    self._set_face_color(idx, occ_color(*color_tuple))
                    return
        self._set_face_color(idx, NORMAL_COLOR)

    def _on_face_selection_changed(self):
        selected_now = {
            self.face_list.item(r).data(Qt.UserRole)
            for r in range(self.face_list.count())
            if self.face_list.item(r).isSelected()
        }
        for i in self.selected_indices - selected_now:
            self._restore_face_color(i)
        for i in selected_now - self.selected_indices:
            self._set_face_color(i, HIGHLIGHT_COLOR)
        self.selected_indices = selected_now
        self.status.showMessage(f"{len(self.selected_indices)} surface(s) selected.")

    # ── Display modes ─────────────────────────────────────────────────────────

    def _set_shaded(self):
        self._display_mode = "shaded"
        self._apply_display_mode_to_all()

    def _set_wireframe(self):
        self._display_mode = "wireframe"
        self._apply_display_mode_to_all()

    def _apply_display_mode_to_all(self):
        if not hasattr(self, "_display"):
            return
        ctx = self._display.Context
        mode = 1 if self._display_mode == "shaded" else 0
        for ais in self.ais_faces:
            ctx.SetDisplayMode(ais, mode, True)
        self.status.showMessage(f"Display mode: {self._display_mode.capitalize()}")

    # ── Hide / show ───────────────────────────────────────────────────────────

    def _hide_selected(self):
        if not self.selected_indices:
            return
        ctx = self._display.Context
        for i in list(self.selected_indices):
            ctx.Erase(self.ais_faces[i], True)
            self.hidden_indices.add(i)
            item = self.face_list.item(i)
            item.setForeground(QColor(160, 160, 160))
            item.setText(f"Surface {i+1:03d}  [hidden]")
        self.selected_indices.clear()
        self.face_list.clearSelection()
        self.status.showMessage(f"{len(self.hidden_indices)} surface(s) hidden.")

    def _show_all(self):
        if not hasattr(self, "_display"):
            return
        ctx = self._display.Context
        for i in self.hidden_indices:
            ctx.Display(self.ais_faces[i], True)
            item = self.face_list.item(i)
            item.setForeground(QColor(0, 0, 0))
            item.setText(f"Surface {i+1:03d}")
        self.hidden_indices.clear()
        self.status.showMessage("All surfaces visible.")

    def _fit_all(self):
        if hasattr(self, "_display"):
            self._display.FitAll()

    # ── Groups ────────────────────────────────────────────────────────────────

    def _add_group(self):
        name = self.group_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "No name", "Please enter a group name.")
            return
        if not self.selected_indices:
            QMessageBox.warning(self, "No selection",
                                "Select at least one surface first.")
            return

        indices = sorted(self.selected_indices)
        is_new = name not in self.groups

        if is_new:
            self.groups[name] = indices
            # Assign and remember a colour for this group
            r, g, b = GROUP_COLORS[self._group_color_idx % len(GROUP_COLORS)]
            self._group_colors[name] = (r, g, b)
            self._group_color_idx += 1
        else:
            existing = set(self.groups[name])
            existing.update(indices)
            self.groups[name] = sorted(existing)

        r, g, b = self._ensure_group_color(name)
        gc = occ_color(r, g, b)
        for i in indices:
            self._set_face_color(i, gc)

        self._refresh_group_tree()
        self._clear_selection()
        self.group_name_edit.clear()
        self.status.showMessage(
            f"Group '{name}' has {len(self.groups[name])} surface(s)."
        )

    def _delete_group(self):
        item = self.group_tree.currentItem()
        if item is None:
            return
        name = item.text(0) if item.parent() is None else item.parent().text(0)
        if name not in self.groups:
            return
        if QMessageBox.question(
            self, "Delete group", f"Delete group '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        for i in self.groups[name]:
            self._set_face_color(i, NORMAL_COLOR)
        del self.groups[name]
        self._group_colors.pop(name, None)
        self._refresh_group_tree()
        self.status.showMessage(f"Group '{name}' deleted.")

    def _ensure_group_color(self, name):
        """Return the (r, g, b) colour for a group, assigning the next
        palette colour first if the group doesn't have one yet. Mandatory
        groups pre-created empty from GUIsetup.xml reach their first face
        assignment without ever passing through 'Add Group', so they have
        no colour until this runs."""
        if name not in self._group_colors:
            r, g, b = GROUP_COLORS[self._group_color_idx % len(GROUP_COLORS)]
            self._group_colors[name] = (r, g, b)
            self._group_transparency.setdefault(name, 0.0)
            self._group_color_idx += 1
        return self._group_colors[name]

    def _refresh_group_tree(self):
        self.groups_changed.emit()
        self.group_tree.clear()
        for name, indices in self.groups.items():
            # NOTE: column 0 text must stay exactly the group name — several
            # handlers read item.text(0) to identify the group. Mandatory
            # status is signalled by colour only.
            top = QTreeWidgetItem([name, str(len(indices))])
            f = top.font(0); f.setBold(True); top.setFont(0, f)
            if name in self._mandatory_groups and len(indices) == 0:
                # Mandatory but still empty → red until at least one face
                # is assigned. Overrides the group colour.
                top.setForeground(0, QColor(200, 30, 30))
                top.setToolTip(0, "Mandatory group — assign at least one face")
            else:
                color_tuple = self._group_colors.get(name)
                if color_tuple:
                    r, g, b = color_tuple
                    top.setForeground(
                        0, QColor(int(r*255), int(g*255), int(b*255))
                    )
            for i in indices:
                child = QTreeWidgetItem([f"  Surface {i+1:03d}", ""])
                child.setData(0, Qt.UserRole, i)
                top.addChild(child)
            self.group_tree.addTopLevelItem(top)
        self.group_tree.expandAll()

    def _on_group_item_clicked(self, item, col):
        if item.parent() is None:
            name = item.text(0)
            indices = self.groups.get(name, [])
        else:
            idx = item.data(0, Qt.UserRole)
            indices = [idx] if idx is not None else []
        self._clear_selection(silent=True)
        self.face_list.blockSignals(True)
        for i in indices:
            self.selected_indices.add(i)
            self._set_face_color(i, HIGHLIGHT_COLOR)
            self.face_list.item(i).setSelected(True)
        self.face_list.blockSignals(False)
        self.status.showMessage(f"{len(indices)} surface(s) highlighted.")

    def _on_group_tree_context_menu(self, pos):
        """Context menu for the group tree.
        - Right-click on a group header  -> Hide / Show group faces
        - Right-click on a surface child -> Remove surface from group
        """
        item = self.group_tree.itemAt(pos)
        if item is None:
            return

        menu = QMenu(self)
        global_pos = self.group_tree.viewport().mapToGlobal(pos)

        if item.parent() is None:
            # ── Group header ──────────────────────────────────────────────
            group_name = item.text(0)
            act_hide  = menu.addAction(f"Hide '{group_name}'")
            act_show  = menu.addAction(f"Show '{group_name}'")
            menu.addSeparator()
            act_color = menu.addAction(f"Change color of '{group_name}'...")
            act_trans = menu.addAction(f"Set transparency of '{group_name}'...")
            chosen = menu.exec_(global_pos)
            if chosen == act_hide:
                self._hide_group(group_name)
            elif chosen == act_show:
                self._show_group(group_name)
            elif chosen == act_color:
                self._change_group_color(group_name)
            elif chosen == act_trans:
                self._change_group_transparency(group_name)
        else:
            # ── Surface child ─────────────────────────────────────────────
            group_name = item.parent().text(0)
            face_idx = item.data(0, Qt.UserRole)
            if face_idx is None:
                return
            act_remove = menu.addAction(
                f"Remove Surface {face_idx+1:03d} from '{group_name}'"
            )
            chosen = menu.exec_(global_pos)
            if chosen == act_remove:
                self._remove_face_from_group(face_idx, group_name)

    def _hide_group(self, group_name: str):
        """Hide all faces that belong to group_name."""
        indices = self.groups.get(group_name, [])
        ctx = self._display.Context
        for i in indices:
            if i not in self.hidden_indices:
                ctx.Erase(self.ais_faces[i], True)
                self.hidden_indices.add(i)
                item = self.face_list.item(i)
                item.setForeground(QColor(160, 160, 160))
                item.setText(f"Surface {i+1:03d}  [hidden]")
        self.status.showMessage(
            f"Group '{group_name}': {len(indices)} surface(s) hidden."
        )

    def _show_group(self, group_name: str):
        """Show all faces that belong to group_name."""
        indices = self.groups.get(group_name, [])
        ctx = self._display.Context
        shown = 0
        for i in indices:
            if i in self.hidden_indices:
                ctx.Display(self.ais_faces[i], True)
                self.hidden_indices.discard(i)
                item = self.face_list.item(i)
                item.setForeground(QColor(0, 0, 0))
                item.setText(f"Surface {i+1:03d}")
                self._restore_face_color(i)
                shown += 1
        self.status.showMessage(
            f"Group '{group_name}': {shown} surface(s) made visible."
        )

    def _change_group_color(self, group_name: str):
        """Open a colour picker and apply the chosen colour to the group."""
        current = self._group_colors.get(group_name, (0.7, 0.8, 0.9))
        initial = QColor(int(current[0]*255), int(current[1]*255), int(current[2]*255))
        color = QColorDialog.getColor(initial, self, f"Choose color for '{group_name}'")
        if not color.isValid():
            return
        r, g, b = color.redF(), color.greenF(), color.blueF()
        self._group_colors[group_name] = (r, g, b)
        gc = occ_color(r, g, b)
        ctx = self._display.Context
        transp = self._group_transparency.get(group_name, 0.0)
        for i in self.groups.get(group_name, []):
            ctx.SetColor(self.ais_faces[i], gc, True)
            ctx.SetTransparency(self.ais_faces[i], transp, True)
        self._refresh_group_tree()
        self.status.showMessage(f"Group '{group_name}' colour updated.")

    def _change_group_transparency(self, group_name: str):
        """Open a dialog with a 0-100 slider to set group transparency."""
        current_t = self._group_transparency.get(group_name, 0.0)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Transparency — '{group_name}'")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("0 = fully opaque          100 = fully transparent"))

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(current_t * 100))
        slider.setTickInterval(10)
        slider.setTickPosition(QSlider.TicksBelow)
        layout.addWidget(slider)

        value_label = QLabel(f"{slider.value()}")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return

        transp = slider.value() / 100.0
        self._group_transparency[group_name] = transp
        ctx = self._display.Context
        for i in self.groups.get(group_name, []):
            ctx.SetTransparency(self.ais_faces[i], transp, True)
        self.status.showMessage(
            f"Group '{group_name}' transparency set to {slider.value()}%."
        )

    def _remove_face_from_group(self, face_idx: int, group_name: str):
        """Remove a single face from a group; delete the group if it becomes empty."""
        if group_name not in self.groups:
            return
        indices = self.groups[group_name]
        if face_idx not in indices:
            return
        indices.remove(face_idx)
        if not indices:
            # Group is now empty — remove it entirely
            del self.groups[group_name]
            self._group_colors.pop(group_name, None)
            self.status.showMessage(
                f"Surface {face_idx+1:03d} removed; group '{group_name}' is now empty and was deleted."
            )
        else:
            self.groups[group_name] = indices
            self.status.showMessage(
                f"Surface {face_idx+1:03d} removed from group '{group_name}'."
            )
        # Restore the face colour (may still belong to another group)
        self._restore_face_color(face_idx)
        self._refresh_group_tree()

    def _clear_selection(self, silent=False):
        for i in list(self.selected_indices):
            self._restore_face_color(i)
        self.selected_indices.clear()
        self.face_list.blockSignals(True)
        self.face_list.clearSelection()
        self.face_list.blockSignals(False)
        if not silent:
            self.status.showMessage("Selection cleared.")

    # ── Unassigned selection & overlap check ──────────────────────────────────

    def _select_unassigned(self):
        if not self.faces:
            return
        assigned = {i for indices in self.groups.values() for i in indices}
        unassigned = [i for i in range(len(self.faces)) if i not in assigned]
        if not unassigned:
            QMessageBox.information(
                self, "No unassigned surfaces",
                "Every surface is already assigned to at least one group."
            )
            return
        self._clear_selection(silent=True)
        self.face_list.blockSignals(True)
        for i in unassigned:
            self.selected_indices.add(i)
            self._set_face_color(i, HIGHLIGHT_COLOR)
            self.face_list.item(i).setSelected(True)
        self.face_list.blockSignals(False)
        self.status.showMessage(
            f"{len(unassigned)} unassigned surface(s) selected "
            f"out of {len(self.faces)} total."
        )

    # ── Area-based selection ──────────────────────────────────────────────────

    def _compute_face_areas(self):
        """Return list of areas (float) for every loaded face, in model units²."""
        areas = []
        for face in self.faces:
            props = GProp_GProps()
            brepgprop.SurfaceProperties(face, props)
            areas.append(props.Mass())
        return areas

    def _ask_threshold(self, title: str, label: str) -> float | None:
        """Pop up a dialog asking for a numeric threshold. Returns None on cancel."""
        if not self.faces:
            QMessageBox.warning(self, "No model", "Import a STEP file first.")
            return None
        areas = self._compute_face_areas()
        min_a, max_a = min(areas), max(areas)

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(
            f"{label}\n\nFace area range in this model:\n"
            f"  min = {min_a:.6g}\n  max = {max_a:.6g}"
        ))
        spin = QDoubleSpinBox()
        spin.setDecimals(6)
        spin.setRange(0.0, max_a * 10)
        spin.setValue((min_a + max_a) / 2.0)
        spin.setSingleStep((max_a - min_a) / 100.0 if max_a != min_a else 1.0)
        layout.addWidget(spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec_() != QDialog.Accepted:
            return None
        return spin.value()

    def _select_by_area(self, below: bool):
        threshold = self._ask_threshold(
            "Select by Area",
            f"Enter area threshold (select surfaces {'below' if below else 'above'}):"
        )
        if threshold is None:
            return
        areas = self._compute_face_areas()
        hits = [i for i, a in enumerate(areas)
                if (a < threshold if below else a > threshold)]
        if not hits:
            QMessageBox.information(
                self, "No matches",
                f"No surfaces found with area {'below' if below else 'above'} {threshold:.6g}."
            )
            return
        self._clear_selection(silent=True)
        self.face_list.blockSignals(True)
        for i in hits:
            self.selected_indices.add(i)
            self._set_face_color(i, HIGHLIGHT_COLOR)
            self.face_list.item(i).setSelected(True)
        self.face_list.blockSignals(False)
        self.status.showMessage(
            f"{len(hits)} surface(s) with area {'<' if below else '>'} {threshold:.6g} selected."
        )

    def _select_area_below(self):
        self._select_by_area(below=True)

    def _select_area_above(self):
        self._select_by_area(below=False)

    def _check_overlaps(self):
        if not self.groups:
            QMessageBox.information(self, "No groups", "No groups defined yet.")
            return
        face_to_groups = defaultdict(list)
        for name, indices in self.groups.items():
            for i in indices:
                face_to_groups[i].append(name)
        overlapping = {i: g for i, g in face_to_groups.items() if len(g) > 1}
        if not overlapping:
            QMessageBox.information(
                self, "No overlaps ✔",
                "All surfaces belong to at most one group — no overlaps found."
            )
            self.status.showMessage("Overlap check: no overlaps found.")
            return
        RED = occ_color(1.0, 0.1, 0.1)
        self._clear_selection(silent=True)
        self.face_list.blockSignals(True)
        for i in overlapping:
            self._set_face_color(i, RED)
            self.selected_indices.add(i)
            self.face_list.item(i).setSelected(True)
        self.face_list.blockSignals(False)
        lines = [f"Found {len(overlapping)} surface(s) in multiple groups:\n"]
        for i, grps in sorted(overlapping.items()):
            lines.append(f"  Surface {i+1:03d}  →  {', '.join(grps)}")
        QMessageBox.warning(self, "Overlapping surfaces", "\n".join(lines))
        self.status.showMessage(
            f"Overlap check: {len(overlapping)} surface(s) highlighted in red."
        )

    # ── STL Export ────────────────────────────────────────────────────────────

    # ── Panel visibility ──────────────────────────────────────────────────────

    def _toggle_surface_panel(self, checked: bool):
        self._surface_panel.setVisible(checked)

    def _toggle_group_panel(self, checked: bool):
        self._group_panel.setVisible(checked)

    # ── Info overlay ──────────────────────────────────────────────────────────

    def _update_info_overlay(self):
        """Create / update the text overlay shown on the bottom-right of the viewport."""
        if not hasattr(self, '_display') or self._bbox is None:
            return
        xmin, ymin, zmin, xmax, ymax, zmax = self._bbox
        # Total volume via bounding box * face count (approximate; real vol needs solid)
        # Try to compute real volume from root shape
        vol_str = "n/a"
        try:
            vprops = GProp_GProps()
            from OCC.Core.BRepGProp import brepgprop as _bg
            _bg.VolumeProperties(self.root_shape, vprops)
            vol = abs(vprops.Mass())
            vol_str = f"{vol:.6g}"
        except Exception:
            pass

        # Coarse mesh estimates from bounding box volume
        bbox_vol = (xmax-xmin)*(ymax-ymin)*(zmax-zmin)
        if bbox_vol > 0:
            m100k = (bbox_vol/1e5)**(1/3)
            m1M   = (bbox_vol/1e6)**(1/3)
            m10M  = (bbox_vol/1e7)**(1/3)
            mesh_lines = [
                f"Mesh 100k : {m100k:.4g}",
                f"Mesh 1M   : {m1M:.4g}",
                f"Mesh 10M  : {m10M:.4g}",
            ]
        else:
            mesh_lines = []

        lines = [
            f"Volume : {vol_str} units\u00b3",
            f"X : [{xmin:.4g} , {xmax:.4g}]",
            f"Y : [{ymin:.4g} , {ymax:.4g}]",
            f"Z : [{zmin:.4g} , {zmax:.4g}]",
            "─" * 22,
        ] + mesh_lines

        if self._info_label is None:
            self._info_label = QLabel(self.canvas)
            self._info_label.setStyleSheet(
                "background: rgba(0,0,0,140); color: #e0e0e0;"
                "padding: 6px 10px; border-radius: 4px;"
                "font-family: monospace; font-size: 11px;"
            )
            self._info_label.setAttribute(Qt.WA_TransparentForMouseEvents)
            self._info_label.show()

        self._info_label.setText("\n".join(lines))
        self._info_label.adjustSize()
        self._reposition_info_label()

    def _reposition_info_label(self):
        if self._info_label is None:
            return
        cw = self.canvas.width()
        ch = self.canvas.height()
        lw = self._info_label.width()
        lh = self._info_label.height()
        margin = 8
        self._info_label.move(cw - lw - margin, ch - lh - margin)

    def _toggle_info_overlay(self):
        if self._info_label is not None:
            self._info_label.setVisible(not self._info_label.isVisible())

    # ── Tools (coarse mesh + bounding box) ──────────────────────────────────

    def _estimate_coarse_mesh(self):
        if self._bbox is None:
            QMessageBox.warning(self, 'No model', 'Import a STEP file first.'); return
        xmin, ymin, zmin, xmax, ymax, zmax = self._bbox
        vol = (xmax-xmin)*(ymax-ymin)*(zmax-zmin)
        if vol <= 0:
            QMessageBox.warning(self, 'Error', 'Bounding box volume is zero.'); return
        QMessageBox.information(self, 'Estimate coarse mesh',
            f'Bounding box volume: {vol:.4g} units\u00b3\n\n'
            f'  100k cells  \u2192  cell size \u2248 {(vol/1e5)**(1/3):.5g}\n'
            f'  1M cells    \u2192  cell size \u2248 {(vol/1e6)**(1/3):.5g}\n'
            f'  10M cells   \u2192  cell size \u2248 {(vol/1e7)**(1/3):.5g}')

    def _show_bounding_box(self):
        if self._bbox is None:
            QMessageBox.warning(self, 'No model', 'Import a STEP file first.'); return
        xmin, ymin, zmin, xmax, ymax, zmax = self._bbox
        QMessageBox.information(self, 'Bounding Box',
            f'X : {xmin:.6g}  \u2192  {xmax:.6g}   (\u0394 = {xmax-xmin:.6g})\n'
            f'Y : {ymin:.6g}  \u2192  {ymax:.6g}   (\u0394 = {ymax-ymin:.6g})\n'
            f'Z : {zmin:.6g}  \u2192  {zmax:.6g}   (\u0394 = {zmax-zmin:.6g})')

    # ── Rescale ───────────────────────────────────────────────────────────────

    def _rescale_model(self):
        if not self.faces:
            QMessageBox.warning(self, "No model", "Import a STEP file first.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Rescale Model")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel(
            "Scale factor (e.g. 1000 converts metres to millimetres):"
        ))
        spin = QDoubleSpinBox()
        spin.setDecimals(6)
        spin.setRange(1e-9, 1e9)
        spin.setValue(1.0)
        lay.addWidget(spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)
        if dlg.exec_() != QDialog.Accepted:
            return
        factor = spin.value()
        if factor == 1.0:
            return
        trsf = gp_Trsf()
        trsf.SetScaleFactor(factor)
        ctx = self._display.Context
        new_faces = []
        for i, face in enumerate(self.faces):
            new_shape = BRepBuilderAPI_Transform(face, trsf, True).Shape()
            new_faces.append(new_shape)
            self.ais_faces[i].Set(new_shape)
            ctx.Redisplay(self.ais_faces[i], True)
        self.faces = new_faces
        # Recompute bbox
        from OCC.Core.BRep import BRep_Builder as _BB
        builder = _BB()
        compound = TopoDS_Compound()
        builder.MakeCompound(compound)
        for f in self.faces:
            builder.Add(compound, f)
        box = Bnd_Box()
        brepbndlib.Add(compound, box)
        self._bbox = box.Get()
        self._update_info_overlay()
        self._display.FitAll()
        self.status.showMessage(f"Model rescaled by factor {factor}.")

    # ── Probe point ───────────────────────────────────────────────────────────

    def _random_point_in_shape(self, max_attempts=300):
        """Return a random point that lies on or very near the model geometry.

        Strategy:
          1. Try BRepClass3d_SolidClassifier (works when root_shape is a solid).
          2. Fall back to picking a random face and returning its centre of mass
             — this is guaranteed to be ON the model surface, which is the best
             we can do for open shells / surface models with no closed solid.
        """
        from OCC.Core.TopAbs import TopAbs_IN
        xmin, ymin, zmin, xmax, ymax, zmax = self._bbox
        tol = 1e-6

        # ── Attempt 1: solid classifier (closed solid STEP files) ────────
        try:
            for _ in range(max_attempts):
                px = random.uniform(xmin, xmax)
                py = random.uniform(ymin, ymax)
                pz = random.uniform(zmin, zmax)
                clf = BRepClass3d_SolidClassifier(self.root_shape,
                                                  gp_Pnt(px, py, pz), tol)
                if clf.State() == TopAbs_IN:
                    return px, py, pz
        except Exception:
            pass

        # ── Attempt 2: centroid of a randomly chosen face ─────────────
        # This always succeeds for surface models (shells, open bodies).
        if self.faces:
            face = random.choice(self.faces)
            props = GProp_GProps()
            brepgprop.SurfaceProperties(face, props)
            cog = props.CentreOfMass()
            return cog.X(), cog.Y(), cog.Z()

        # ── Fallback: bbox centroid ────────────────────────────────────
        return (xmin+xmax)/2, (ymin+ymax)/2, (zmin+zmax)/2

    def _place_probe_point(self):
        """Place a red sphere at a random point inside the solid volume."""
        if not self.faces:
            QMessageBox.warning(self, "No model", "Import a STEP file first.")
            return
        self._remove_probe_point()
        self.status.showMessage("Finding point inside solid...")
        QApplication.processEvents()
        px, py, pz = self._random_point_in_shape()
        self._probe_point = [px, py, pz]
        xmin, ymin, zmin, xmax, ymax, zmax = self._bbox
        radius = max(xmax - xmin, ymax - ymin, zmax - zmin) * 0.015
        sphere = BRepPrimAPI_MakeSphere(gp_Pnt(px, py, pz), radius).Shape()
        self._probe_ais = AIS_Shape(sphere)
        self._probe_ais.SetColor(occ_color(1.0, 0.0, 0.0))
        ctx = self._display.Context
        ctx.Display(self._probe_ais, True)
        ctx.SetDisplayMode(self._probe_ais, 1, True)
        self._probe_active = True
        self.status.showMessage(
            f"Probe placed at ({px:.4g}, {py:.4g}, {pz:.4g})"
        )
        # Connect mouse for dragging
        self.canvas.mousePressEvent   = self._probe_mouse_press
        self.canvas.mouseMoveEvent    = self._probe_mouse_move
        self.canvas.mouseReleaseEvent = self._probe_mouse_release

    def _remove_probe_point(self):
        if self._probe_ais is not None and hasattr(self, '_display'):
            self._display.Context.Erase(self._probe_ais, True)
            self._probe_ais = None
        self._probe_active = False
        self._probe_dragging = False
        # Restore normal click handlers
        self.canvas.mousePressEvent   = lambda e: qtViewer3d.mousePressEvent(self.canvas, e)
        self.canvas.mouseMoveEvent    = lambda e: qtViewer3d.mouseMoveEvent(self.canvas, e)
        self.canvas.mouseReleaseEvent = self._on_canvas_click
        self.status.showMessage("Probe point removed.")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_info_label()

    def _probe_mouse_press(self, event):

        qtViewer3d.mousePressEvent(self.canvas, event)
        if event.button() == Qt.LeftButton and self._probe_active:
            ctx = self._display.Context
            ctx.InitSelected()
            if ctx.MoreSelected() and ctx.SelectedInteractive() == self._probe_ais:
                self._probe_dragging = True
                event.accept()

    def _probe_mouse_move(self, event):
        if self._probe_dragging:
            # Unproject mouse to a point on the plane z = probe_z
            v = self._display.View
            x, y = event.x(), event.y()
            px, py, pz = self._probe_point
            from OCC.Core.gp import gp_Pnt
            wx = ctypes_float(); wy = ctypes_float(); wz = ctypes_float()
            try:
                v.Convert(x, y, wx, wy, wz)
                self._move_probe(wx.value, wy.value, pz)
            except Exception:
                pass
        else:
            qtViewer3d.mouseMoveEvent(self.canvas, event)

    def _probe_mouse_release(self, event):
        if self._probe_dragging and event.button() == Qt.LeftButton:
            self._probe_dragging = False
        else:
            self._on_canvas_click(event)

    def _move_probe(self, x: float, y: float, z: float):
        self._probe_point = [x, y, z]
        self._remove_probe_ais_only()
        xmin, ymin, zmin, xmax, ymax, zmax = self._bbox
        radius = max(xmax - xmin, ymax - ymin, zmax - zmin) * 0.015
        sphere = BRepPrimAPI_MakeSphere(gp_Pnt(x, y, z), radius).Shape()
        self._probe_ais = AIS_Shape(sphere)
        self._probe_ais.SetColor(occ_color(1.0, 0.0, 0.0))
        ctx = self._display.Context
        ctx.Display(self._probe_ais, True)
        ctx.SetDisplayMode(self._probe_ais, 1, True)
        self.status.showMessage(f"Probe at ({x:.4g}, {y:.4g}, {z:.4g})")

    def _remove_probe_ais_only(self):
        if self._probe_ais is not None:
            self._display.Context.Erase(self._probe_ais, True)
            self._probe_ais = None

    # ── STL export refinement settings ──────────────────────────────────────

    def _open_stl_refinement_dialog(self):
        """Popup to configure STL export mesh resolution ahead of time.
        Values are stored on the instance and used silently by every
        subsequent export — no dialog interrupts the actual export anymore.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Output STL refinement")
        lay = QVBoxLayout(dlg)

        lay.addWidget(QLabel(
            "<b>STL export mesh refinement</b><br>"
            "Smaller values produce smaller triangles that follow the "
            "surface curvature more closely, at the cost of larger files."
        ))

        from PySide6.QtWidgets import QFormLayout
        form = QFormLayout()

        spin_lin = QDoubleSpinBox()
        spin_lin.setDecimals(4)
        spin_lin.setRange(0.0001, 10.0)
        spin_lin.setValue(self._stl_linear_deflection)
        spin_lin.setToolTip(
            "Linear deflection: maximum distance between the mesh chord\n"
            "and the true surface, in model units. Smaller = finer mesh."
        )
        form.addRow("Linear deflection:", spin_lin)

        spin_ang = QDoubleSpinBox()
        spin_ang.setDecimals(2)
        spin_ang.setRange(0.1, 45.0)
        spin_ang.setValue(self._stl_angular_deflection_deg)
        spin_ang.setSuffix(" °")
        spin_ang.setToolTip(
            "Angular deflection: maximum angle between adjacent triangle\n"
            "normals. Smaller = finer mesh, especially on curved surfaces."
        )
        form.addRow("Angular deflection:", spin_ang)

        lay.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return

        self._stl_linear_deflection = spin_lin.value()
        self._stl_angular_deflection_deg = spin_ang.value()
        self.status.showMessage(
            f"STL refinement set: linear={self._stl_linear_deflection:.4g}, "
            f"angular={self._stl_angular_deflection_deg:.2g}°"
        )

    def _export_stl(self):
        if not self.groups:
            QMessageBox.warning(self, "No groups", "Create at least one group first.")
            return

        import math
        lin = self._stl_linear_deflection
        ang_rad = math.radians(self._stl_angular_deflection_deg)

        # ── Output folder ─────────────────────────────────────────────────
        out_dir = QFileDialog.getExistingDirectory(self, "Select output folder")
        if not out_dir:
            return

        exported, errors = [], []
        for name, indices in self.groups.items():
            shapes = [self.faces[i] for i in indices]
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
            out_path = os.path.join(out_dir, f"{safe}.stl")
            try:
                shapes_to_stl(shapes, out_path, lin, ang_rad)
                exported.append(out_path)
            except Exception as e:
                errors.append(f"{name}: {e}")

        # ── Export probe point as VTK ─────────────────────────────────
        vtk_msg = ""
        exported_vtk = None
        if self._probe_active and self._probe_point:
            exported_vtk = os.path.join(out_dir, "probe_point.vtk")
            try:
                _write_probe_vtk(self._probe_point, exported_vtk)
                vtk_msg = f"\nProbe point exported to probe_point.vtk"
            except Exception as e:
                vtk_msg = f"\nProbe VTK export failed: {e}"
                exported_vtk = None

        # Write bridge file (same folder as STLs)
        _write_stl_bridge(out_dir, exported, exported_vtk)
        self._last_export_paths = exported

        if errors:
            err_msg = "Some groups failed to export:\n" + "\n".join(errors)
            QMessageBox.warning(self, "Export warnings", err_msg)

        if not exported:
            QMessageBox.warning(self, "Nothing exported",
                                "No STL files were produced. Check your groups.")
            return

        # ── Notify / launch XML GUI ───────────────────────────────────
        self.exported.emit(exported)
        if self._is_embedded:
            # Embedded: signal is enough — XML GUI is already open
            QMessageBox.information(self, 'Exported',
                f'Exported {len(exported)} group(s) to:\n{out_dir}\n\n'
                'File fields in other tabs have been updated.')
        else:
            _launch_xml_gui()
            self.window().close()


# ─────────────────────────────────────────────────────────────────────────────
# XML GUI launcher
# ─────────────────────────────────────────────────────────────────────────────

def _launch_xml_gui():
    """Spawn xmlreader.py as a subprocess. The bridge pointer file tells it
    where to find the exported files, which are auto-loaded on startup."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'xmlreader.py')
    env = os.environ.copy()
    # Pass the bridge pointer path so xmlreader finds the right bridge file
    env['BRIDGE_PTR_FILE'] = _BRIDGE_PTR
    subprocess.Popen([sys.executable, script], env=env)


# ─────────────────────────────────────────────────────────────────────────────
# Axis triad overlay widget
# ─────────────────────────────────────────────────────────────────────────────

class _StatusBarProxy:
    """Status bar for QWidget context: shows a QLabel + optionally mirrors to a real QStatusBar."""
    def __init__(self, parent):
        self._lbl = QLabel()
        self._lbl.setStyleSheet('color: #555; font-size: 11px; padding: 2px;')
        self._real_sb = None   # set by SurfaceSelectorApp to mirror messages
        parent.layout().addWidget(self._lbl)
    def showMessage(self, msg, *a):
        self._lbl.setText(msg)
        if self._real_sb:
            self._real_sb.showMessage(msg)


class SurfaceSelectorApp(QMainWindow):
    """Standalone window: embeds SurfaceSelectorWidget as central widget."""
    def __init__(self, step_path=None):
        super().__init__()
        self.setWindowTitle('STEP Surface Selector & STL Exporter')
        self.resize(1280, 800)
        self._widget = SurfaceSelectorWidget(step_path, parent=None)
        self.setCentralWidget(self._widget)
        # Mirror the widget's menubar actions onto the QMainWindow menubar
        if hasattr(self._widget, '_menubar'):
            for action in self._widget._menubar.actions():
                self.menuBar().addAction(action)
        # Add toolbar to QMainWindow
        if hasattr(self._widget, '_toolbar'):
            self.addToolBar(self._widget._toolbar)
        # Status bar
        sb = QStatusBar()
        self.setStatusBar(sb)
        # Proxy the widget's status messages to the real statusbar
        self._widget.status._real_sb = sb

    def closeEvent(self, event):
        """Ensure the embedded widget's OCC context is torn down cleanly
        before this top-level window's native handle is destroyed."""
        try:
            self._widget.closeEvent(None)
        except Exception as e:
            print(f'OCC cleanup before close failed (non-fatal): {e}')
        super().closeEvent(event)


class StepEmbedWidget(QWidget):
    """Embeds SurfaceSelectorWidget inside a QTabWidget tab.
    Emits files_exported(list) after a successful 'Export to CAE'.
    """
    files_exported = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._step = SurfaceSelectorWidget(parent=self)
        self._step.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self._step, stretch=1)
        # Forward the inner widget's signal outward
        self._step.exported.connect(self.files_exported)

    def cleanup_occ(self):
        """Explicitly tear down the OCC context. Call this from the hosting
        window's closeEvent (e.g. the XML GUI's QMainWindow), since a child
        widget embedded in a tab never receives its own closeEvent when the
        application quits — only top-level windows do.
        """
        try:
            self._step.closeEvent(None)
        except Exception as e:
            print(f'StepEmbedWidget cleanup failed (non-fatal): {e}')


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    step_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = SurfaceSelectorApp(step_path)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
