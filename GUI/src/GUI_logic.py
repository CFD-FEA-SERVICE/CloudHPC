"""
GUI_logic.py  —  Qt version
All Tkinter StringVar / widget references are replaced with QtStringVar
(a thin QObject-based wrapper) and Qt widget calls.
"""
from utils import get_frame_by_name_recursive, get_tkstring_by_name_recursive, print_debug_util
from data_singleton import DataSingleton

data_instance = DataSingleton.get_instance()


# ── QtStringVar ──────────────────────────────────────────────────────────────
# Replaces tk.StringVar throughout the codebase.

from PySide6.QtCore import QObject, Signal

class QtStringVar(QObject):
    """Thin replacement for tk.StringVar: holds a string, emits changed()."""
    changed = Signal(str)

    def __init__(self, value=""):
        super().__init__()
        self._value = str(value)
        self._traces = []          # list of callables

    def get(self):
        return self._value

    def set(self, value, _silent=False):
        self._value = str(value)
        if _silent:
            return
        self.changed.emit(self._value)
        for cb in list(self._traces):  # copy so removals during iteration are safe
            try:
                cb()
            except Exception:
                pass

    def trace(self, mode, callback):
        """Mimic tk.StringVar.trace('w', cb). Returns a trace_id (the cb)."""
        self._traces.append(callback)
        return callback

    def trace_vdelete(self, mode, trace_id):
        if trace_id in self._traces:
            self._traces.remove(trace_id)


# ── Logic functions ───────────────────────────────────────────────────────────

def update_fields(qt_string_map, frames_map, current_frame=None):
    if hasattr(data_instance, 'display_callback') and callable(data_instance.display_callback):
        data_instance.display_callback()

    if current_frame is None:
        current_frame = data_instance.all_data

    for frame_name, frame_content in current_frame.items():
        sub_frames = frame_content.get("sub_frames", {})
        data = frame_content.get("data", {})

        for var_name, var_value in data.items():
            if isinstance(var_value, dict):
                contains_list = any(isinstance(v, list) for v in var_value.values())
                if contains_list:
                    ref_frame = get_frame_by_name_recursive(frames_map, frame_name)
                    update_multiple_dropdown(qt_string_map, var_name, ref_frame["frame"], None)
                else:
                    for field_name, field_value in var_value.items():
                        if isinstance(field_value, dict):
                            update_multiple_dropdown(qt_string_map, field_name,
                                get_frame_by_name_recursive(frames_map, frame_name), None)
                        else:
                            sv = get_tkstring_by_name_recursive(qt_string_map, frame_name, field_name)
                            if sv:
                                sv.set(str(field_value))
            else:
                sv = get_tkstring_by_name_recursive(qt_string_map, frame_name, var_name)
                if sv:
                    sv.set(str(var_value))

        if sub_frames:
            update_fields(qt_string_map, frames_map, sub_frames)


_umvd_guard = set()  # re-entrancy guard for update_multiple_visual_data

def update_multiple_visual_data(frame, sub_frame, qt_string_map, multiple_name, layer_num):
    guard_key = (id(frame), multiple_name, layer_num)
    if guard_key in _umvd_guard:
        return
    _umvd_guard.add(guard_key)
    try:
        multi = {}
        if data_instance.all_data[frame.frame_name]["data"].get(multiple_name):
            multi = data_instance.all_data[frame.frame_name]["data"][multiple_name]
        else:
            multi = data_instance.all_data[multiple_name]["data"]
        collection = multi.get("collection")
        if collection:
            layer = collection[layer_num]
            for field in data_instance.multiple_struct_blueprint[multiple_name]["xml_fields"]:
                field_name = field["name"]
                sv = field.get("tkString")
                if sv and field_name and field_name in layer:
                    # Remove old trace, update value silently, re-add trace
                    if "trace_id" in field:
                        sv.trace_vdelete("w", field["trace_id"])
                    sv.set(layer[field_name], _silent=True)
                    # Update underlying widget directly to avoid signal loops
                    w = field.get("widget", {}).get("field")
                    if w is not None:
                        try:
                            from PySide6.QtWidgets import QLineEdit, QComboBox
                            if isinstance(w, QLineEdit) and w.text() != sv.get():
                                w.blockSignals(True); w.setText(sv.get()); w.blockSignals(False)
                            elif isinstance(w, QComboBox) and w.currentText() != sv.get():
                                w.blockSignals(True)
                                target = sv.get()
                                existing = [w.itemText(i) for i in range(w.count())]
                                if target not in existing:
                                    if w.property("cad_groups_only"):
                                        # This combo must ONLY ever list CAD
                                        # group names — never inject a layer
                                        # name like "patch_1" into it. Leave
                                        # the current selection as is.
                                        w.blockSignals(False)
                                        if "trace_id" in field:
                                            field["trace_id"] = on_change_update(frame, sub_frame, sv, field, multiple_name)
                                        continue
                                    # Otherwise: add it temporarily so the
                                    # stored selection is never silently lost.
                                    w.addItem(target)
                                w.setCurrentText(target)
                                w.blockSignals(False)
                        except Exception:
                            pass
                    if "trace_id" in field:
                        field["trace_id"] = on_change_update(frame, sub_frame, sv, field, multiple_name)

        if not is_multiple_visible(multiple_name) and collection and len(collection) > 0:
            show_multiple_fields(qt_string_map, frame, multiple_name, True)
    finally:
        _umvd_guard.discard(guard_key)


def update_multiple_dropdown(qt_string_map, multiple_name, frame, sub_frame):
    option_menu_dict = get_tkstring_by_name_recursive(qt_string_map, frame.frame_name, "OptionMenu")
    tk_string_dict   = get_tkstring_by_name_recursive(qt_string_map, frame.frame_name, frame.frame_name)
    if not option_menu_dict or not tk_string_dict:
        return
    combo    = option_menu_dict[multiple_name]   # QComboBox
    sv       = tk_string_dict[multiple_name]

    multi = {}
    if data_instance.all_data[frame.frame_name]["data"].get(multiple_name):
        multi = data_instance.all_data[frame.frame_name]["data"][multiple_name]
    else:
        multi = data_instance.all_data[multiple_name][multiple_name]

    combo.blockSignals(True)
    combo.clear()
    collection = multi.get("collection")
    if collection and len(collection) > 0:
        for item in collection:
            combo.addItem(item["name"])
        combo.setCurrentIndex(len(collection) - 1)
        sv.set(collection[-1]["name"])
        multi["selected_layer"] = 0
    else:
        multi["selected_layer"] = -1
    combo.blockSignals(False)
    update_multiple_visual_data(frame, sub_frame, qt_string_map, multiple_name, multi["selected_layer"])


def show_multiple_fields(qt_string_map, frame, multiple_name, is_show):
    for f in data_instance.multiple_struct_blueprint[multiple_name]["xml_fields"]:
        widget = f["widget"]["field"]
        label  = f["widget"]["label"]
        widget.setVisible(is_show)
        label.setVisible(is_show)

    opt_dict = get_tkstring_by_name_recursive(qt_string_map, frame.frame_name, "OptionMenu")
    rm_dict  = get_tkstring_by_name_recursive(qt_string_map, frame.frame_name, "rmButton")
    if opt_dict and multiple_name in opt_dict:
        opt_dict[multiple_name].setVisible(is_show)
        opt_dict[multiple_name].setEnabled(is_show)
    if rm_dict and multiple_name in rm_dict:
        rm_dict[multiple_name].setVisible(is_show)
        rm_dict[multiple_name].setEnabled(is_show)


def is_multiple_visible(multiple_name):
    try:
        first_field = data_instance.multiple_struct_blueprint[multiple_name]["xml_fields"][0]
        return first_field["widget"]["field"].isVisible()
    except (IndexError, KeyError):
        return False


def on_change_update(frame, sub_frame, sv, element, multiple_name):
    """Attach a value-changed callback to a QtStringVar. Returns trace_id."""
    is_multiple = multiple_name is not None

    def on_entry_change():
        value = sv.get()
        element_type = element.get("type", "")

        if element_type == "int":
            value = int(value) if value.isdigit() else 0
        elif element_type == "float":
            try:
                value = float(value) if value else 0.0
            except ValueError:
                return

        if is_multiple:
            multi = {}
            if data_instance.all_data[frame.frame_name]["data"].get(multiple_name):
                multi = data_instance.all_data[frame.frame_name]["data"][multiple_name]
            else:
                multi = data_instance.all_data[multiple_name]["data"]
            if len(multi["collection"]) > 0:
                layer = multi["collection"][multi["selected_layer"]]
                layer[element["name"]] = value
        else:
            if sub_frame is None:
                data_instance.all_data[frame.frame_name]["data"][element["name"]] = value
            else:
                data_instance.all_data[frame.frame_name]["sub_frames"][sub_frame.frame_name]["data"][element["name"]] = value

    trace_id = sv.trace("w", on_entry_change)
    return trace_id


def update_maps(frame, sub_frame, element, sv, qt_string_map):
    if sub_frame is None:
        data_instance.all_data[frame.frame_name]["data"][element["name"]] = element["default"]
        sv.set(str(data_instance.all_data[frame.frame_name]["data"][element["name"]]))
        if frame.frame_name not in qt_string_map:
            qt_string_map[frame.frame_name] = {"sub_frames": {}, "data": {}}
        qt_string_map[frame.frame_name]["data"][element["name"]] = sv
    else:
        data_instance.all_data[frame.frame_name]["sub_frames"][sub_frame.frame_name]["data"][element["name"]] = element["default"]
        sv.set(str(data_instance.all_data[frame.frame_name]["sub_frames"][sub_frame.frame_name]["data"][element["name"]]))
        if frame.frame_name not in qt_string_map:
            qt_string_map[frame.frame_name] = {"sub_frames": {}, "data": {}}
        if sub_frame.frame_name not in qt_string_map[frame.frame_name]["sub_frames"]:
            qt_string_map[frame.frame_name]["sub_frames"][sub_frame.frame_name] = {"sub_frames": {}, "data": {}}
        qt_string_map[frame.frame_name]["sub_frames"][sub_frame.frame_name]["data"][element["name"]] = sv
