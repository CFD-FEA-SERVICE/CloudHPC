"""
xmlreader.py  —  Qt version, fully self-contained entry point.

Run this directly:
    python xmlreader.py [path/to/GUIsetup.xml]

If no XML file is given (as a CLI argument or via the GUISETUP_FILE env var),
a file-picker dialog is shown on startup.

This used to be launched via a separate main.py "launcher" that spawned both
this script and step_surface_selector.py as subprocesses. That extra process
boundary turned out to make X11/OpenGL window-realisation timing for the
embedded CAD tab (StepEmbedWidget / pythonocc qtViewer3d) considerably less
predictable, contributing to intermittent 'BadWindow' X protocol errors.
Running everything in a single process/QApplication avoids that entirely,
since there's only ever one X connection and one event loop to reason about.
"""
import os, sys, copy

# X11-only: on Linux force the xcb plugin (part of the BadWindow fixes).
# On Windows/macOS Qt must pick its native platform plugin — forcing xcb
# there makes every frozen app abort with "no Qt platform plugin".
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PySide6.QtWidgets import QApplication, QFileDialog

from IO_service import create_xml_datastructure
from GUI_drawer import (
    create_basic_settings_frame, create_sub_frame, create_tab_frame,
    handle_dropdown, handle_cadgroups_dropdown, handle_cad_type,
    handle_file_type, handle_image,
    handle_single_value_type, handle_multiple, handle_software_type,
    initialize_window, add_multiple_separator,
)
from utils import add_default_multiples_to_data, set_multiples_association, rm_buttons_map
from data_singleton import DataSingleton

data_instance = DataSingleton.get_instance()

qt_string_map = {}
widget_map    = {}
frames_map    = {}

XML_representation = []

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Bridge files (written by step_surface_selector.py's "Export to CAE", read by
# the CADgroups-dropdown / file-type widgets). Default to the script folder.
os.environ.setdefault("STL_BRIDGE_FILE", os.path.join(_SCRIPT_DIR, "stl_bridge.json"))
os.environ.setdefault("BRIDGE_PTR_FILE", os.path.join(_SCRIPT_DIR, "stl_bridge.ptr"))

# Clear any stale bridge pointer left over from a previous run, so we never
# accidentally pick up file lists that no longer correspond to anything.
try:
    os.remove(os.environ["BRIDGE_PTR_FILE"])
except FileNotFoundError:
    pass


def _resolve_guisetup_path() -> str:
    """Determine which GUIsetup XML file to load, in priority order:
    1. A CLI argument (python xmlreader.py path/to/file.xml)
    2. The GUISETUP_FILE environment variable
    3. GUIsetup.xml next to this script, if it exists
    4. A file-picker dialog, as a last resort
    """
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        return sys.argv[1]

    env_path = os.environ.get("GUISETUP_FILE")
    if env_path and os.path.isfile(env_path):
        return env_path

    default_path = os.path.join(_SCRIPT_DIR, "GUIsetup.xml")
    if os.path.isfile(default_path):
        return default_path

    # Need a QApplication instance before showing any Qt dialog
    app = QApplication.instance() or QApplication(sys.argv)
    chosen, _ = QFileDialog.getOpenFileName(
        None, "Select GUIsetup.xml", _SCRIPT_DIR,
        "XML files (*.xml);;All files (*)"
    )
    if not chosen:
        print("No XML setup file selected. Exiting.")
        sys.exit(0)
    return chosen


GUIsetup_filename = _resolve_guisetup_path()

FileProperties = create_xml_datastructure(XML_representation, GUIsetup_filename)
XML_filename   = FileProperties[0]
rootTitle      = FileProperties[1]


def generate_GUI():
    row_num = 0
    current_tab_frame   = None
    sub_frame           = None
    basic_settings_frame = None
    is_multiple         = False
    current_multiple_name = None
    multiple_start_indent = 1
    multiple_render_frame = None   # the active_frame the multiple block was drawn into

    root, tab_control = initialize_window(
        qt_string_map, frames_map, XML_filename, rootTitle, GUIsetup_filename
    )

    for i in range(len(XML_representation)):
        if (XML_representation[i]["indent"] == 1 and
                XML_representation[i]["type"] not in ("frame", "multiple")):
            basic_settings_frame = create_basic_settings_frame(frames_map, tab_control)
            break

    for i in range(len(XML_representation)):
        if is_multiple and XML_representation[i]["indent"] == multiple_start_indent:
            add_default_multiples_to_data(current_tab_frame.frame_name, current_multiple_name)
            # ── Visual separator: marks the end of this "multiple" block ───
            if multiple_render_frame is not None:
                add_multiple_separator(multiple_render_frame, row_num)
                row_num += 1
            current_multiple_name = None
            is_multiple = False
            multiple_render_frame = None

        if XML_representation[i]["name"] == "option" and "id" not in XML_representation[i]:
            continue

        t = XML_representation[i]["type"]

        if t == "dropdown":
            id_prev = i - 1
            while XML_representation[id_prev]["name"] == "option": id_prev -= 1
            if XML_representation[i]["indent"] == 1:
                current_tab_frame = basic_settings_frame; active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] < XML_representation[id_prev]["indent"]:
                active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] <= 3 and active_frame == sub_frame:
                active_frame = current_tab_frame
            handle_dropdown(XML_representation, qt_string_map, active_frame, sub_frame,
                            XML_representation[i], row_num, i, current_multiple_name)

        elif t == "CADgroups-dropdown":
            id_prev = i - 1
            while XML_representation[id_prev]["name"] == "option": id_prev -= 1
            if XML_representation[i]["indent"] == 1:
                current_tab_frame = basic_settings_frame; active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] < XML_representation[id_prev]["indent"]:
                active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] <= 3 and active_frame == sub_frame:
                active_frame = current_tab_frame
            handle_cadgroups_dropdown(qt_string_map, active_frame, sub_frame,
                                      XML_representation[i], row_num, current_multiple_name)

        elif t == "image":
            id_prev = i - 1
            while XML_representation[id_prev]["name"] == "option": id_prev -= 1
            if XML_representation[i]["indent"] == 1:
                current_tab_frame = basic_settings_frame; active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] < XML_representation[id_prev]["indent"]:
                active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] <= 3 and active_frame == sub_frame:
                active_frame = current_tab_frame
            handle_image(XML_representation, qt_string_map, active_frame, sub_frame,
                         XML_representation[i], row_num, i, current_multiple_name)

        elif t in ("int", "float", "string"):
            id_prev = i - 1
            while XML_representation[id_prev]["name"] == "option": id_prev -= 1
            if XML_representation[i]["indent"] == 1:
                current_tab_frame = basic_settings_frame; active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] < XML_representation[id_prev]["indent"]:
                active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] <= 3 and active_frame == sub_frame:
                active_frame = current_tab_frame
            handle_single_value_type(qt_string_map, active_frame, sub_frame,
                                     XML_representation[i], row_num, current_multiple_name)

        elif t == "file":
            if XML_representation[i]["indent"] == 1:
                current_tab_frame = basic_settings_frame; active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] <= 3 and active_frame == sub_frame:
                active_frame = current_tab_frame
            handle_file_type(root, XML_representation, qt_string_map, active_frame, sub_frame,
                             XML_representation[i], row_num, i)

        elif t == "software":
            if XML_representation[i]["indent"] == 1:
                current_tab_frame = basic_settings_frame; active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] <= 3 and active_frame == sub_frame:
                active_frame = current_tab_frame
            handle_software_type(qt_string_map, active_frame, sub_frame,
                                 XML_representation[i], row_num)

        elif t == "CAD":
            # Embed STEP management into the current frame (tab name = parent frame name)
            if XML_representation[i]["indent"] == 1:
                current_tab_frame = basic_settings_frame; active_frame = current_tab_frame; sub_frame = None
            # <option> children of the CAD element declare mandatory groups
            mandatory_groups = []
            j = i + 1
            while j < len(XML_representation) and XML_representation[j]["name"] == "option":
                mandatory_groups.append(str(XML_representation[j]["default"]))
                j += 1
            handle_cad_type(active_frame, tab_control, XML_representation[i],
                            mandatory_groups)

        elif t == "frame":
            if XML_representation[i]["indent"] > 1:
                sub_frame, row_num = create_sub_frame(current_tab_frame, frames_map,
                                                      row_num, XML_representation[i])
                active_frame = sub_frame
            else:
                sub_frame = None
                current_tab_frame = create_tab_frame(frames_map, tab_control, XML_representation[i])
                active_frame = current_tab_frame

        elif t == "multiple":
            is_multiple = True
            multiple_start_indent = XML_representation[i]["indent"]
            current_multiple_name = XML_representation[i]["name"]
            if XML_representation[i].get("specifyName", False):
                data_instance.multiple_struct_blueprint[current_multiple_name] = {
                    "name": f"{current_multiple_name}_1", "multipleID": 1, "xml_fields": []}
            else:
                data_instance.multiple_struct_blueprint[current_multiple_name] = {
                    "name": f"{current_multiple_name}_cloudHPC_1", "multipleID": 1, "xml_fields": []}
            if XML_representation[i]["indent"] == 1:
                current_tab_frame = create_tab_frame(frames_map, tab_control, XML_representation[i])
                sub_frame = None; active_frame = current_tab_frame
            elif XML_representation[i]["indent"] < XML_representation[i-1]["indent"]:
                active_frame = current_tab_frame; sub_frame = None
            elif XML_representation[i]["indent"] <= 2 and active_frame == sub_frame:
                active_frame = current_tab_frame
            row_num = handle_multiple(qt_string_map, root, active_frame, sub_frame,
                                      XML_representation[i], row_num, i)
            multiple_render_frame = active_frame   # remember where to put the bottom separator

        else:
            print(f"ERROR: unknown type {XML_representation[i]['type']} {XML_representation[i]['name']}")

        row_num += 1

    if is_multiple:
        add_default_multiples_to_data(current_tab_frame.frame_name, current_multiple_name)
        if multiple_render_frame is not None:
            add_multiple_separator(multiple_render_frame, row_num)
            row_num += 1

    set_multiples_association()

    for func in rm_buttons_map.values():
        func()

    data_instance.default_data = copy.deepcopy(data_instance.all_data)
    return root


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    win = generate_GUI()
    sys.exit(app.exec_())
