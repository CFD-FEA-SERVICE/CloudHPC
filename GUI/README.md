# Merged Project — STEP Manager + XML GUI

## Structure

```
merged_project/
├── xmlreader.py               ← MAIN ENTRY POINT (start here)
├── step_surface_selector.py   ← STEP tool (PyQt5)
├── xmlreader.py               ← XML GUI engine (Tkinter)
├── GUI_drawer.py              ← XML GUI widget builder (patched)
├── GUI_logic.py
├── IO_service.py
├── data_singleton.py
├── tools.py
├── utils.py
├── CADvista.py
├── GUIsetup*.xml              ← XML config files (choose one at launch)
├── stl_bridge.json            ← auto-created at runtime (do not edit)
└── LOGO.png
```

## Requirements

```bash
pip install pythonocc-core PyQt5 numpy-stl Pillow pyvista pyvistaqt
```

> For PyQt5 xcb issues on Linux:
> ```bash
> pip uninstall PyQt5 PyQt5-Qt5 PyQt5-sip -y && pip install PyQt5
> export QT_QPA_PLATFORM=xcb
> ```

## Launch

```bash
python xmlreader.py                          # prompts for XML setup file if GUIsetup.xml is absent
python xmlreader.py GUIsetup-carParks.xml    # open a specific setup file directly
```

This starts **two windows**:

| Window | Toolkit | Purpose |
|---|---|---|
| STEP Surface Selector | PyQt5 | Import STEP, assign surfaces to groups, export STL |
| XML Parameter GUI | Tkinter | Fill simulation parameters, reference STL files |

## Workflow

1. **Open a STEP file** in the STEP tool (`Import STEP`)
2. **Create surface groups** and assign faces to them
3. **Export STL** (`File > Export STL...`) — choose output folder and resolution
   - STL files are written to the chosen folder
   - The file paths are automatically written to `stl_bridge.json`
4. **Switch to the XML GUI** window
5. In any `type="file"` field, click **"Import from STEP tool"**
   - The files from the last STEP export are loaded automatically
   - Only files matching the field's expected extensions (e.g. `stl,vtk`) are imported
6. Fill remaining parameters and **Save As...** to produce the output XML

## How the bridge works

`stl_bridge.json` is a simple JSON file:
```json
{
  "stl_files": [
    "/path/to/group_A.stl",
    "/path/to/group_B.stl"
  ]
}
```

- Written by `step_surface_selector.py` after each STL export
- Read by the patched `handle_file_type` in `GUI_drawer.py` when the user
  clicks "Import from STEP tool"
- Cleared at launch so stale paths from a previous session are never imported

## Running tools independently

Both tools still work standalone:

```bash
# STEP tool only
python step_surface_selector.py [file.step]

# XML GUI only
python xmlreader.py
```

## GEO requirements (optional)

The `type="CAD"` element can declare requirements that must be satisfied
before `File > Save As...` will export:

```xml
<Geometry type="frame">
    <CADdumb type="CAD" probePoint="true">step
        <option type="string">inlet</option>
        <option type="string">outlet</option>
        <option type="string">wall</option>
    </CADdumb>
</Geometry>
```

- `probePoint="true"` — the probe point must be placed before export
- each `<option>` — a mandatory group: pre-created (empty) in the Groups
  panel at startup, shown in red until at least one face is assigned,
  and required to be non-empty at export time

Both are optional: a plain `<CADdumb type="CAD">step</CADdumb>` behaves
exactly as before, with no requirements enforced.
