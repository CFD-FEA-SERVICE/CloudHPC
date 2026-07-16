"""
GUI_drawer.py  —  Qt version
Replaces Tkinter with PySide6 throughout, while keeping all data_singleton,
IO_service, and utils logic unchanged.
"""

import copy, subprocess, os, sys, json, math

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QScrollArea,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog,
    QMessageBox, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QPixmap

from GUI_logic import (
    QtStringVar, on_change_update, show_multiple_fields,
    update_maps, update_multiple_visual_data, is_multiple_visible,
)
from IO_service import export_to_xml, load_xml
from utils import BASIC_SETTINGS_TAB_NAME, change_key, print_debug_util, rm_buttons_map
from data_singleton import DataSingleton
from CADvista import openpyvista

try:
    import stl, numpy
    from stl import mesh
except ImportError:
    stl = None; numpy = None; mesh = None

data_instance = DataSingleton.get_instance()

# ── STL bridge ────────────────────────────────────────────────────────────────
_BRIDGE_PTR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stl_bridge.ptr')

def _read_stl_bridge() -> dict:
    """Return {'stl_files': [...], 'vtk_files': [...]} from the bridge JSON.
    Location is read from stl_bridge.ptr (written by the STEP tool).
    Falls back to stl_bridge.json next to this file if the pointer is absent.
    """
    bridge = None
    try:
        with open(_BRIDGE_PTR, 'r', encoding='utf-8') as f:
            bridge = f.read().strip()
    except Exception:
        pass
    if not bridge or not os.path.isfile(bridge):
        bridge = os.environ.get(
            'STL_BRIDGE_FILE',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stl_bridge.json')
        )
    try:
        with open(bridge, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {'stl_files': data.get('stl_files', []), 'vtk_files': data.get('vtk_files', [])}
    except Exception:
        return {'stl_files': [], 'vtk_files': []}

# ── _FrameProxy ───────────────────────────────────────────────────────────────
class _FrameProxy(QWidget):
    """QWidget with .frame_name and a QGridLayout helper."""
    def __init__(self, frame_name, parent=None):
        super().__init__(parent)
        self.frame_name = frame_name
        self._gl = QGridLayout(self)
        self._gl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._row = 0

    def grid_layout(self):
        return self._gl

    def next_row(self):
        r = self._row; self._row += 1; return r

    def set_row(self, r):
        self._row = max(self._row, r + 1)


# ── _notify_attachment_dropdowns (stub — kept for compatibility) ──────────────
_attachment_refresh_callbacks = []

def _notify_attachment_dropdowns():
    for cb in _attachment_refresh_callbacks:
        try: cb()
        except Exception: pass


# ── handle_image ──────────────────────────────────────────────────────────────
def handle_image(XML_representation, qt_string_map, frame, sub_frame,
                 element, row_num, index, multiple_name):
    active = sub_frame if sub_frame else frame
    try:
        px = QPixmap(element["default"]).scaledToWidth(100, Qt.SmoothTransformation)
        lbl = QLabel(); lbl.setPixmap(px)
        active.grid_layout().addWidget(lbl, row_num, 0)
    except Exception as e:
        print(f"Image error: {e}")


# ── handle_dropdown ───────────────────────────────────────────────────────────
def handle_dropdown(XML_representation, qt_string_map, frame, sub_frame,
                    element, row_num, index, multiple_name):
    is_layer = multiple_name is not None
    options = []
    j = index + 1
    while j < len(XML_representation) and XML_representation[j]["name"] == "option":
        options.append(str(XML_representation[j]["default"])); j += 1

    active = sub_frame if sub_frame else frame
    lbl = QLabel(element["name"])
    active.grid_layout().addWidget(lbl, row_num, 0)

    sv = QtStringVar()
    trace_id = on_change_update(frame, sub_frame, sv, element, multiple_name)
    element["trace_id"] = trace_id

    combo = QComboBox(); combo.addItems(options)
    if is_layer:
        multi_obj = data_instance.multiple_struct_blueprint[multiple_name]
        multi_obj[element["name"]] = element["default"]
        if element["default"] in options: combo.setCurrentText(element["default"])
        sv.set(combo.currentText()); element["tkString"] = sv
    else:
        update_maps(frame, sub_frame, element, sv, qt_string_map)
        if element["default"] in options: combo.setCurrentText(element["default"])

    combo.currentTextChanged.connect(sv.set)
    active.grid_layout().addWidget(combo, row_num, 1)
    element["widget"] = {"field": combo, "label": lbl}
    if is_layer:
        data_instance.multiple_struct_blueprint[multiple_name]["xml_fields"].append(element)
    element["tkString"] = sv



# ── handle_cadgroups_dropdown ─────────────────────────────────────────────────
# Like a normal dropdown, but options are the GROUP NAMES currently defined
# in the embedded CAD tab (StepEmbedWidget). Auto-refreshes whenever groups
# are added/renamed/deleted, and writes a plain string value to data_instance
# so the output XML gets <name>groupname</name> just like a regular dropdown.
def _get_cad_group_names():
    """Return current group names from any live StepEmbedWidget, or a
    placeholder list if none is open yet."""
    try:
        from step_surface_selector import StepEmbedWidget
        for w in QApplication.instance().allWidgets():
            if isinstance(w, StepEmbedWidget):
                groups = list(w._step.groups.keys())
                return groups if groups else ["(no groups defined)"]
    except Exception:
        pass
    return ["(no groups defined)"]


def handle_cadgroups_dropdown(qt_string_map, frame, sub_frame,
                              element, row_num, multiple_name):
    is_layer = multiple_name is not None
    active = sub_frame if sub_frame else frame

    lbl = QLabel(element["name"])
    active.grid_layout().addWidget(lbl, row_num, 0)

    sv = QtStringVar()
    trace_id = on_change_update(frame, sub_frame, sv, element, multiple_name)
    element["trace_id"] = trace_id

    combo = QComboBox()
    combo.setMinimumWidth(180)
    opts = _get_cad_group_names()
    combo.addItems(opts)

    # The XML text content (e.g. 'pick a group') is just placeholder/instructional
    # text — it is NEVER a real option and must never become the stored value.
    # The actual initial value is whatever the combo currently shows (first
    # real group, or the placeholder '(no groups defined)' if none exist yet).
    initial_value = combo.currentText()

    if is_layer:
        multi_obj = data_instance.multiple_struct_blueprint[multiple_name]
        multi_obj[element["name"]] = initial_value
        sv.set(initial_value, _silent=True)
        element["tkString"] = sv
    else:
        # Bypass update_maps' use of element["default"] — set our own initial value
        if frame.frame_name not in qt_string_map:
            qt_string_map[frame.frame_name] = {"sub_frames": {}, "data": {}}
        if sub_frame is None:
            data_instance.all_data[frame.frame_name]["data"][element["name"]] = initial_value
            qt_string_map[frame.frame_name]["data"][element["name"]] = sv
        else:
            data_instance.all_data[frame.frame_name]["sub_frames"][sub_frame.frame_name]["data"][element["name"]] = initial_value
            if sub_frame.frame_name not in qt_string_map[frame.frame_name]["sub_frames"]:
                qt_string_map[frame.frame_name]["sub_frames"][sub_frame.frame_name] = {"sub_frames": {}, "data": {}}
            qt_string_map[frame.frame_name]["sub_frames"][sub_frame.frame_name]["data"][element["name"]] = sv
        sv.set(initial_value, _silent=True)

    def _on_combo_text(text):
        sv.set(text)
    combo.currentTextChanged.connect(_on_combo_text)

    _busy = {"v": False}
    def _refresh():
        if _busy["v"]:
            return
        _busy["v"] = True
        try:
            cur = combo.currentText()
            opts2 = _get_cad_group_names()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(opts2)
            target = cur if cur in opts2 else (opts2[0] if opts2 else "")
            if target:
                combo.setCurrentText(target)
            combo.blockSignals(False)
            # Sync sv silently — a refresh shouldn't count as a user edit
            sv.set(combo.currentText(), _silent=True)
        finally:
            _busy["v"] = False

    _attachment_refresh_callbacks.append(_refresh)

    active.grid_layout().addWidget(combo, row_num, 1)
    element["widget"] = {"field": combo, "label": lbl}
    if is_layer:
        data_instance.multiple_struct_blueprint[multiple_name]["xml_fields"].append(element)
    element["tkString"] = sv



# ── handle_cad_type ───────────────────────────────────────────────────────────
def handle_cad_type(frame, tab_widget, element, mandatory_groups=None):
    """Embed the STEP management UI into the current frame tab.
    The frame (created by create_tab_frame for the parent <Geometry> element)
    already has a tab with the correct name. We embed the widget there directly
    so the tab name comes from the XML frame, not from the CAD element name.

    IMPORTANT: StepEmbedWidget (and the OCC qtViewer3d inside it) must NOT be
    constructed until the main window is actually shown/realised on screen.
    pythonocc's qtViewer3d performs X11 calls on construction; if the widget
    hierarchy isn't yet mapped to a real window (which is the case while
    generate_GUI() is still building tabs, before win.show()/app.exec_()),
    those calls can hit an invalid/not-yet-existing X11 window and raise a
    fatal 'BadWindow' X protocol error that crashes the whole application.

    Fix: insert a lightweight placeholder now, then use QTimer.singleShot(0, ...)
    to defer the real construction to the next Qt event-loop iteration — by
    which point the window has been shown and has a valid native handle.
    """
    placeholder = QLabel("Loading STEP viewer…")
    placeholder.setAlignment(Qt.AlignCenter)
    placeholder.setStyleSheet("color: #888; font-size: 13px; padding: 24px;")
    frame.grid_layout().addWidget(placeholder, 0, 0, 1, 4)

    def _build_real_widget():
        try:
            from step_surface_selector import StepEmbedWidget
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            placeholder.setText(
                f"STEP viewer unavailable:\n{type(e).__name__}: {e}\n\n{err}"
            )
            placeholder.setWordWrap(True)
            placeholder.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            placeholder.setStyleSheet(
                "color: red; font-family: monospace; font-size: 10px; padding: 8px;"
            )
            return

        # Only safe to construct the OCC-backed widget once the top-level
        # window is actually visible AND exposed by the platform — isVisible()
        # alone can return True before the X server has finished mapping the
        # window, which is what was causing intermittent BadWindow X errors.
        QApplication.processEvents()  # let any pending map/configure events land
        top = frame.window()
        win_handle = top.windowHandle() if top is not None else None
        exposed = bool(win_handle.isExposed()) if win_handle is not None else False
        if top is None or not top.isVisible() or not exposed:
            # Window still not ready — try again shortly.
            QTimer.singleShot(30, _build_real_widget)
            return

        widget = StepEmbedWidget()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # When STL files are exported, auto-import them into every file field
        def _on_exported(paths):
            bd = _read_stl_bridge()
            all_p = bd["stl_files"] + bd["vtk_files"]
            for frame_val in data_instance.all_data.values():
                for field_val in frame_val.get("data", {}).values():
                    if isinstance(field_val, dict):
                        for p in all_p:
                            if p not in field_val:
                                field_val[p] = None
            _notify_attachment_dropdowns()

        widget.files_exported.connect(_on_exported)
        widget._step.groups_changed.connect(_notify_attachment_dropdowns)

        # ── Requirements declared in the setup file (both optional) ────────
        # probePoint="true" attribute → probe placement required before export
        # <option> children              → mandatory group names, pre-created
        widget._step._probe_required = bool(element.get("probePoint", False))
        widget._step._mandatory_groups = list(mandatory_groups or [])
        for _g in widget._step._mandatory_groups:
            if _g not in widget._step.groups:
                widget._step.groups[_g] = []
        if widget._step._mandatory_groups:
            widget._step._refresh_group_tree()
        from IO_service import _CAD_FIELD_REGISTRY
        _CAD_FIELD_REGISTRY.add(element['name'])
        data_instance.all_data[frame.frame_name]['data'][element['name']] = ''

        gl = frame.grid_layout()
        # Remove the placeholder and put the real widget in its place
        gl.removeWidget(placeholder)
        placeholder.deleteLater()
        gl.addWidget(widget, 0, 0, 1, 4)
        gl.setAlignment(Qt.AlignmentFlag(0))
        gl.setRowStretch(0, 1)
        gl.setColumnStretch(0, 1)
        gl.setColumnStretch(1, 1)
        gl.setColumnStretch(2, 1)
        gl.setColumnStretch(3, 1)
        gl.setContentsMargins(0, 0, 0, 0)

        parent = frame.parentWidget()
        while parent is not None and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        if parent is not None:
            parent.setWidgetResizable(True)
            frame.setMinimumSize(0, 0)
            frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    QTimer.singleShot(0, _build_real_widget)


# ── handle_software_type ──────────────────────────────────────────────────────
def handle_software_type(qt_string_map, frame, sub_frame, element, row_num):
    active = sub_frame if sub_frame else frame
    lbl = QLabel("Open " + element["name"])
    active.grid_layout().addWidget(lbl, row_num, 0)
    err_lbl = QLabel(); err_lbl.setStyleSheet("color:red;")

    def run_sw():
        try:
            subprocess.run([element["default"]], check=True); err_lbl.setText("")
        except FileNotFoundError:
            err_lbl.setText(f"Can't find {element['name']} executable.")
        except subprocess.CalledProcessError:
            err_lbl.setText(f"Error opening {element['name']}.")

    btn = QPushButton(element["name"]); btn.clicked.connect(run_sw)
    active.grid_layout().addWidget(btn, row_num, 1)
    active.grid_layout().addWidget(err_lbl, row_num, 2)
    data_instance.all_data[frame.frame_name]["data"]["software"] = \
        f"{element['name']}#{element['default']}"


# ── handle_file_type ──────────────────────────────────────────────────────────
def handle_file_type(root, XML_representation, qt_string_map, frame, sub_frame,
                     element, row_num, index, callback=None):
    active = sub_frame if sub_frame else frame
    fname = element["name"]
    fframe = frame.frame_name

    # Single authoritative dict — always accessed via data_instance
    data_instance.all_data[fframe]["data"][fname] = {}
    sv = QtStringVar()
    extensions = [e.strip() for e in element["default"].split(",")]
    data_instance.display_callback = callback

    # Helper: always returns the live dict
    def _files():
        return data_instance.all_data[fframe]["data"][fname]

    # Auto-load from bridge
    _bridge = _read_stl_bridge()
    for _p in _bridge["stl_files"] + _bridge["vtk_files"]:
        if os.path.splitext(_p)[1].lstrip('.').lower() in [e.lower() for e in extensions]:
            if _p not in _files():
                _files()[_p] = None

    options = []
    j = index + 1
    while j < len(XML_representation) and XML_representation[j]["name"] == "option":
        options.append(str(XML_representation[j]["default"])); j += 1

    lbl = QLabel(f"Choose {'file' if element.get('singleFile') else 'files'} ({element['default']})")
    active.grid_layout().addWidget(lbl, row_num, 0)

    # File list container
    list_w = QWidget()
    list_l = QVBoxLayout(list_w)
    list_l.setContentsMargins(0, 0, 0, 0)
    list_l.setSpacing(2)
    active.grid_layout().addWidget(list_w, row_num + 1, 0, 1, 4)

    def display_selected_files():
        # Destroy old rows
        while list_l.count():
            item = list_l.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        # Render one row per file from the live dict
        for fp in list(_files().keys()):
            exists = os.path.isfile(fp)
            rw = QWidget()
            rl = QHBoxLayout(rw)
            rl.setContentsMargins(2, 1, 2, 1)

            nl = QLabel(os.path.basename(fp) + ("" if exists else " (missing)"))
            if not exists:
                nl.setStyleSheet("color: red;")
            rl.addWidget(nl, stretch=1)

            def _rm(f=fp):
                _files().pop(f, None)
                _notify_attachment_dropdowns()
                display_selected_files()

            rb = QPushButton("Remove")
            rb.setFixedWidth(70)
            rb.clicked.connect(_rm)
            rl.addWidget(rb)

            if options:
                oc = QComboBox()
                oc.addItems(options)
                cur_val = _files().get(fp)
                if cur_val is None:
                    oc.setCurrentIndex(0)
                    _files()[fp] = options[0]
                else:
                    oc.setCurrentText(str(cur_val))

                def _opt_ch(text, f=fp):
                    _files()[f] = text

                oc.currentTextChanged.connect(_opt_ch)
                rl.addWidget(oc)

            if not exists:
                def _browse(f=fp):
                    nf, _ = QFileDialog.getOpenFileName(
                        None, "Locate file", "",
                        "Files (" + " ".join([f"*.{e}" for e in extensions]) + ")"
                    )
                    if nf and nf not in _files():
                        new_d = change_key(_files(), f, nf)
                        data_instance.all_data[fframe]["data"][fname] = new_d
                        _notify_attachment_dropdowns()
                        display_selected_files()

                bb = QPushButton("Browse Again")
                bb.clicked.connect(_browse)
                rl.addWidget(bb)

            list_l.addWidget(rw)

    def _pick():
        ft = "Files (" + " ".join([f"*.{e}" for e in extensions]) + ")"
        if element.get("singleFile"):
            p, _ = QFileDialog.getOpenFileName(None, "Choose file", "", ft)
            paths = [p] if p else []
        else:
            paths, _ = QFileDialog.getOpenFileNames(None, "Choose files", "", ft)
        for p in paths:
            if p and p not in _files():
                _files()[p] = None
        sv.set(", ".join(_files().keys()))
        _notify_attachment_dropdowns()
        display_selected_files()

    ch_btn = QPushButton("Choose...")
    ch_btn.clicked.connect(_pick)
    vis_btn = QPushButton("Visualize CAD")
    vis_btn.clicked.connect(lambda: openpyvista(list(_files().keys())))

    active.grid_layout().addWidget(ch_btn,  row_num, 1)
    active.grid_layout().addWidget(vis_btn, row_num, 2)

    element["widget"] = {"field": ch_btn, "label": lbl}
    element["tkString"] = sv
    display_selected_files()
    return list(_files().keys())


# ── handle_single_value_type ──────────────────────────────────────────────────
def handle_single_value_type(qt_string_map, frame, sub_frame, element,
                              row_num, multiple_name):
    is_layer = multiple_name is not None
    active = sub_frame if sub_frame else frame
    lbl = QLabel(element["name"])
    active.grid_layout().addWidget(lbl, row_num, 0)

    sv = QtStringVar()
    if is_layer:
        data_instance.multiple_struct_blueprint[multiple_name][element["name"]] = element["default"]
        sv.set(str(data_instance.multiple_struct_blueprint[multiple_name][element["name"]]))
        element["tkString"] = sv
    else:
        update_maps(frame, sub_frame, element, sv, qt_string_map)

    trace_id = on_change_update(frame, sub_frame, sv, element, multiple_name)
    element["trace_id"] = trace_id

    entry = QLineEdit(sv.get())
    entry.textChanged.connect(lambda t: sv.set(t) if sv.get() != t else None)
    sv.changed.connect(lambda t: entry.setText(t) if entry.text() != t else None)
    active.grid_layout().addWidget(entry, row_num, 1)

    element["widget"] = {"field": entry, "label": lbl}
    if is_layer:
        data_instance.multiple_struct_blueprint[multiple_name]["xml_fields"].append(element)
    element["tkString"] = sv


# ── handle_multiple ───────────────────────────────────────────────────────────
def add_multiple_separator(frame, row_num, label=None):
    """Insert a thick, coloured horizontal rule spanning the frame's full
    width at row_num. Used to visually bracket the start/end of a
    type='multiple' block so it's easy to see where it begins and ends
    among the surrounding fields.
    A QWidget with a fixed height is used instead of QFrame.HLine so we
    can control the exact pixel thickness via stylesheet.
    """
    container = QWidget()
    container.setFixedHeight(4)
    container.setStyleSheet(
        "background-color: #5588cc;"   # blue-grey — visible but not alarming
    )
    frame.grid_layout().addWidget(container, row_num, 0, 1, 4)
    return container


def handle_multiple(qt_string_map, root, frame, sub_frame, element, row_num, index):
    multiple_name = element["name"]
    is_cadgroups = (element.get("specifyName", False) == "CADgroups")

    if element["indent"] == 1:
        data_instance.all_data[multiple_name] = {"sub_frames": {}, "data": {}}
        data_instance.all_data[multiple_name]["data"][multiple_name] = {
            "max_layers": 1, "selected_layer": 0, "collection": []}
        row_num = 0
    else:
        data_instance.all_data[frame.frame_name]["data"][multiple_name] = {
            "max_layers": 1, "selected_layer": 0, "collection": []}

    # ── Visual separator: marks the start of this "multiple" block ─────────
    top_sep = add_multiple_separator(frame, row_num)
    row_num += 1

    sv = QtStringVar(multiple_name + " 1")
    combo = QComboBox(); combo.setMinimumWidth(160)

    def get_multi():
        if data_instance.all_data[frame.frame_name]["data"].get(multiple_name):
            return data_instance.all_data[frame.frame_name]["data"][multiple_name]
        return data_instance.all_data[multiple_name]["data"][multiple_name]

    def _display_labels(multi):
        """Labels shown in the layer-picker combo. In CADgroups mode these
        are fixed IDs (patch_1, patch_2, ...) that never change when a CAD
        group is assigned — the group is stored in layer['name'] for the
        XML export, but the picker label stays stable."""
        if is_cadgroups:
            return [f"{multiple_name}_{l['multipleID']}" for l in multi["collection"]]
        return [l["name"] for l in multi["collection"]]

    _refresh_busy = {'v': False}
    def refresh_combo():
        if _refresh_busy['v']:
            return
        _refresh_busy['v'] = True
        try:
            multi = get_multi(); cur = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            names = _display_labels(multi)
            combo.addItems(names)
            if cur in names:
                combo.setCurrentText(cur)
            elif names:
                combo.setCurrentText(names[-1])
            combo.blockSignals(False)
        finally:
            _refresh_busy['v'] = False

    def add_option(_=None):
        multi = get_multi()
        new_layer = dict(data_instance.multiple_struct_blueprint[multiple_name])
        multi["max_layers"] += 1
        new_layer["multipleID"] = multi["max_layers"]
        new_layer.pop("xml_fields", None)
        new_layer["name"] = (f"{multiple_name}_{multi['max_layers']}"
            if element.get("specifyName", True) else
            f"{multiple_name}_cloudHPC_{multi['max_layers']}")
        multi["collection"].append(new_layer)
        multi["selected_layer"] = len(multi["collection"]) - 1
        refresh_combo()
        # Jump the picker to the newly created layer and load its fields
        labels = _display_labels(multi)
        new_label = labels[multi["selected_layer"]]
        combo.blockSignals(True)
        combo.setCurrentText(new_label)
        combo.blockSignals(False)
        sv.set(new_label, _silent=True)
        update_multiple_visual_data(frame, sub_frame, qt_string_map,
                                    multiple_name, multi["selected_layer"])

    def rm_option_fn():
        multi = get_multi(); idx = multi["selected_layer"]
        if 0 <= idx < len(multi["collection"]):
            multi["collection"].pop(idx)
        if not multi["collection"]:
            refresh_combo()
            multi["selected_layer"] = -1; multi["max_layers"] = 0
            combo.setVisible(False); rm_btn.setVisible(False)
            show_multiple_fields(qt_string_map, frame, multiple_name, False)
            return
        # Select the nearest remaining layer and refresh the nested fields,
        # so the UI never keeps showing values of the just-removed patch.
        multi["selected_layer"] = min(idx, len(multi["collection"]) - 1)
        refresh_combo()
        labels = _display_labels(multi)
        sel_label = labels[multi["selected_layer"]]
        combo.blockSignals(True)
        combo.setCurrentText(sel_label)
        combo.blockSignals(False)
        sv.set(sel_label, _silent=True)
        update_multiple_visual_data(frame, sub_frame, qt_string_map,
                                    multiple_name, multi["selected_layer"])

    rm_buttons_map[multiple_name] = rm_option_fn

    _on_combo_busy = {'v': False}
    def _on_combo(text):
        if _on_combo_busy['v']:
            return
        _on_combo_busy['v'] = True
        try:
            multi = get_multi()
            labels = _display_labels(multi)
            if text in labels:
                idx = labels.index(text); multi["selected_layer"] = idx
                sv.set(text, _silent=True)
                update_multiple_visual_data(frame, sub_frame, qt_string_map, multiple_name, idx)
        finally:
            _on_combo_busy['v'] = False

    combo.currentTextChanged.connect(_on_combo)

    add_btn = QPushButton(f"Add new {multiple_name}"); add_btn.clicked.connect(add_option)
    rm_btn  = QPushButton(f"Remove {multiple_name}");  rm_btn.clicked.connect(rm_option_fn)

    frame.grid_layout().addWidget(add_btn, row_num, 0)
    frame.grid_layout().addWidget(rm_btn,  row_num, 1)
    row_num += 1
    frame.grid_layout().addWidget(combo, row_num, 1)
    row_num += 1

    if frame.frame_name not in qt_string_map:
        qt_string_map[frame.frame_name] = {"sub_frames": {}, "data": {}}
    if "OptionMenu" not in qt_string_map[frame.frame_name]["data"]:
        qt_string_map[frame.frame_name]["data"]["OptionMenu"] = {}
        qt_string_map[frame.frame_name]["data"]["rmButton"]   = {}
        qt_string_map[frame.frame_name]["data"][frame.frame_name] = {}

    qt_string_map[frame.frame_name]["data"]["OptionMenu"][multiple_name] = combo
    qt_string_map[frame.frame_name]["data"]["rmButton"][multiple_name]   = rm_btn
    qt_string_map[frame.frame_name]["data"][frame.frame_name][multiple_name] = sv
    element["tkString"] = sv; element["tkOptionMenu"] = combo

    row_num = create_multiple_name_field(frame, element, multiple_name,
                                         qt_string_map, row_num, callback=refresh_combo)
    return row_num


def rm_option(element, multiple_name, frame):
    combo = element.get("tkOptionMenu"); sv = element.get("tkString")
    multi = None
    if data_instance.all_data[frame.frame_name]["data"].get(multiple_name):
        multi = data_instance.all_data[frame.frame_name]["data"][multiple_name]
    else:
        multi = data_instance.all_data[multiple_name]["data"][multiple_name]
    idx = multi["selected_layer"]
    if 0 <= idx < len(multi["collection"]): multi["collection"].pop(idx)
    if combo:
        combo.blockSignals(True); combo.removeItem(idx); combo.blockSignals(False)
        if combo.count() > 0:
            ni = max(idx-1, 0); combo.setCurrentIndex(ni)
            if sv: sv.set(combo.currentText())
        elif sv:
            sv.set("")


# ── create_multiple_name_field ────────────────────────────────────────────────
def create_multiple_name_field(frame, element, multiple_name, qt_string_map,
                                row_num, callback=None):
    specify = element.get("specifyName", False)
    if not specify:
        return row_num

    lbl = QLabel(f"{multiple_name} Name")
    frame.grid_layout().addWidget(lbl, row_num, 0)

    sv = QtStringVar(f"{multiple_name}_1")

    def on_name_change():
        multi = None
        if data_instance.all_data[frame.frame_name]["data"].get(multiple_name):
            multi = data_instance.all_data[frame.frame_name]["data"][multiple_name]
        else:
            try:
                multi = data_instance.all_data[multiple_name]["data"][multiple_name]
            except KeyError:
                return
        name = sv.get()
        if 0 <= multi["selected_layer"] < len(multi["collection"]):
            multi["collection"][multi["selected_layer"]]["name"] = name
        if callback:
            try: callback()
            except Exception as e: print(f"callback error: {e}")

    trace_id = sv.trace("w", on_name_change)

    if specify == "CADgroups":
        # ── Dropdown of live CAD group names — and ONLY group names ────────
        combo = QComboBox()
        combo.setMinimumWidth(180)
        # Purity flag: tells update_multiple_visual_data (GUI_logic) to NEVER
        # inject a missing value into this combo's item list. Layer names
        # like "patch_1" must not appear here — only real CAD groups.
        combo.setProperty("cad_groups_only", True)
        opts = _get_cad_group_names()
        combo.blockSignals(True)
        combo.addItems(opts)
        combo.blockSignals(False)
        sv.set(combo.currentText(), _silent=True)

        def _on_user_pick(text):
            sv.set(text)   # fires on_name_change → renames the layer

        combo.currentTextChanged.connect(_on_user_pick)

        _busy = {"v": False}
        def _refresh_groups():
            if _busy["v"]:
                return
            _busy["v"] = True
            try:
                cur = combo.currentText()
                opts2 = _get_cad_group_names()
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(opts2)
                if cur in opts2:
                    combo.setCurrentText(cur)
                combo.blockSignals(False)
                sv.set(combo.currentText(), _silent=True)
            finally:
                _busy["v"] = False

        _attachment_refresh_callbacks.append(_refresh_groups)

        frame.grid_layout().addWidget(combo, row_num, 1)
        fe = {"name": "name", "type": "string", "default": sv.get(),
              "indent": -1, "tkString": sv, "trace_id": trace_id,
              "widget": {"field": combo, "label": lbl}}
    else:
        # ── Standard free-text entry (specifyName="true") ──────────────────
        entry = QLineEdit(sv.get())
        entry.textChanged.connect(sv.set)
        frame.grid_layout().addWidget(entry, row_num, 1)
        fe = {"name": "name", "type": "string", "default": sv.get(),
              "indent": -1, "tkString": sv, "trace_id": trace_id,
              "widget": {"field": entry, "label": lbl}}

    data_instance.multiple_struct_blueprint[multiple_name]["xml_fields"].append(fe)
    row_num += 1
    return row_num


# ── Tab / frame creation ──────────────────────────────────────────────────────
def create_tab_frame(frames_map, tab_widget, element):
    proxy = _FrameProxy(element["name"])
    scroll = QScrollArea(); scroll.setWidget(proxy); scroll.setWidgetResizable(True)
    tab_widget.addTab(scroll, element["name"])
    frames_map[proxy.frame_name] = {"frame": proxy, "sub_frames": {}}
    data_instance.all_data[proxy.frame_name] = {"sub_frames": {}, "data": {}}
    return proxy


def create_basic_settings_frame(frames_map, tab_widget):
    proxy = _FrameProxy(BASIC_SETTINGS_TAB_NAME)
    scroll = QScrollArea(); scroll.setWidget(proxy); scroll.setWidgetResizable(True)
    tab_widget.addTab(scroll, BASIC_SETTINGS_TAB_NAME)
    frames_map[proxy.frame_name] = {"frame": proxy, "sub_frames": {}}
    data_instance.all_data[proxy.frame_name] = {"sub_frames": {}, "data": {}}
    return proxy


def create_sub_frame(parent_frame, frames_map, row_num, element):
    sub = _FrameProxy(element["name"])
    sub.setStyleSheet("_FrameProxy { border:1px solid #aaa; padding:4px; }")
    header = QLabel(f"<b>{element['name']}</b>")
    sub.grid_layout().addWidget(header, 0, 0, 1, 3)
    sub._row = 1
    parent_frame.grid_layout().addWidget(sub, row_num, 0, 1, 4)
    frames_map[parent_frame.frame_name]["sub_frames"][sub.frame_name] = sub
    data_instance.all_data[parent_frame.frame_name]["sub_frames"][sub.frame_name] = \
        {"sub_frames": {}, "data": {}}
    return sub, row_num


# ── Main window ───────────────────────────────────────────────────────────────
def initialize_window(qt_string_map, frames_map, xml_filename,
                      root_title, guisetup_filename, width=900, height=620):
    app = QApplication.instance() or QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle(root_title)
    win.resize(width, height)

    mb = win.menuBar()
    file_menu  = mb.addMenu("File")
    cloud_menu = mb.addMenu("CloudHPC")
    debug_menu = mb.addMenu("Debug")

    def _save(): export_to_xml(xml_filename)
    def _open(): load_xml(qt_string_map, frames_map)
    def _reset():
        _save()
        data_instance.all_data = copy.deepcopy(data_instance.default_data)
    def _debug():
        from PySide6.QtWidgets import QMessageBox as MB
        MB.information(win, "Debug", str(data_instance.all_data)[:2000])

    for label, fn in [("New", _reset), ("Open", _open), ("Save As...", _save)]:
        a = win.menuBar().addAction(""); a = file_menu.addAction(label); a.triggered.connect(fn)
    file_menu.addSeparator()
    ex = file_menu.addAction("Exit"); ex.triggered.connect(win.close)

    da = debug_menu.addAction("Debug"); da.triggered.connect(_debug)

    try:
        from CloudHPCApp import CloudHPCApp, CloudHPCDownload
        dl = cloud_menu.addAction("Download")
        dl.triggered.connect(lambda: CloudHPCDownload(xml_filename, guisetup_filename))
        ka = cloud_menu.addAction("Change Api Key")
        ka.triggered.connect(lambda: CloudHPCApp(xml_filename, guisetup_filename, first_time=False))
    except ImportError:
        pass

    central = QWidget(); win.setCentralWidget(central)
    main_l = QVBoxLayout(central); main_l.setContentsMargins(4,4,4,4)

    nav = QWidget(); nav_l = QHBoxLayout(nav); nav_l.setContentsMargins(2,2,2,2)
    prev_btn = QPushButton("<-"); next_btn = QPushButton("->")
    # Centre the whole control cluster: stretch | <- vCPU Run -> | stretch
    nav_l.addStretch()
    nav_l.addWidget(prev_btn)

    try:
        from CloudHPCApp import CloudHPCApp
        vcpu = QComboBox(); vcpu.addItems(["Select vCPU","2","16","48","192"])
        run_btn = QPushButton("Run on Cloud")
        run_btn.clicked.connect(lambda: CloudHPCApp(xml_filename, guisetup_filename, vcpu.currentText()))
        nav_l.addWidget(vcpu); nav_l.addWidget(run_btn)
    except ImportError:
        pass

    nav_l.addWidget(next_btn)
    nav_l.addStretch()
    main_l.addWidget(nav)

    tab_widget = QTabWidget(); main_l.addWidget(tab_widget)

    prev_btn.clicked.connect(lambda: tab_widget.setCurrentIndex(max(tab_widget.currentIndex()-1, 0)))
    next_btn.clicked.connect(lambda: tab_widget.setCurrentIndex(min(tab_widget.currentIndex()+1, tab_widget.count()-1)))

    # ── Clean up any embedded OCC/StepEmbedWidget before the window closes ──
    # Without this, the OCC native X11 window can be torn down out of band
    # by Qt's own widget-destruction order, producing BadWindow X errors.
    _original_close_event = win.closeEvent
    def _close_event_with_occ_cleanup(event):
        try:
            from step_surface_selector import StepEmbedWidget
            for i in range(tab_widget.count()):
                w = tab_widget.widget(i)
                # The CAD widget may be embedded directly in a frame, not as
                # the tab's top-level widget, so search descendants too.
                for child in w.findChildren(StepEmbedWidget):
                    child.cleanup_occ()
                if isinstance(w, StepEmbedWidget):
                    w.cleanup_occ()
        except Exception as e:
            print(f'OCC cleanup before window close failed (non-fatal): {e}')
        _original_close_event(event)
    win.closeEvent = _close_event_with_occ_cleanup

    screen = QApplication.primaryScreen().geometry()
    win.move((screen.width()-win.width())//2, (screen.height()-win.height())//2)
    win.show()
    return win, tab_widget


def on_closing_gui(win, xml_filename):
    from PySide6.QtWidgets import QMessageBox as MB
    r = MB.question(win, "Save?", "Save configuration before closing?",
                    MB.Save | MB.Discard | MB.Cancel)
    if r == MB.Save: export_to_xml(xml_filename); win.close()
    elif r == MB.Discard: win.close()
