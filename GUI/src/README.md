# GUI/src — application sources

Python sources of the desktop tools. Everything is started through
**`xmlreader.py`**, which is the only entry point: it resolves which setup file
to load, builds the interface from it and runs the Qt event loop.

```bash
python xmlreader.py [path/to/GUIsetup.xml]
```

Setup file resolution order: command-line argument → `GUISETUP_FILE`
environment variable → `GUIsetup.xml` next to the script → file picker.

| File | Role |
|---|---|
| `xmlreader.py` | Entry point: resolves the setup file, walks the XML representation and dispatches each element to its handler |
| `IO_service.py` | XML parsing and export: builds the internal representation, writes the output XML, embeds/restores the CAD session, enforces the GEO requirements |
| `GUI_drawer.py` | Builds the Qt widgets for every XML type (fields, dropdowns, file pickers, `multiple` blocks, CAD tab) and the main window |
| `GUI_logic.py` | State plumbing: `QtStringVar`, synchronisation of the `multiple` blocks with the stored data |
| `step_surface_selector.py` | STEP/CAD tool: OpenCASCADE viewport, surface selection, groups, probe point, STL export. Embeddable as a tab and runnable standalone |
| `data_singleton.py` | Shared in-memory store of all the values entered in the interface |
| `utils.py` | Helpers used while generating the interface |
| `CADvista.py` | STL/VTK preview through pyvista ("Visualize CAD" button) |
| `CloudHPCApp.py` | Submission dialog behind "Run on Cloud" (cloudHPC REST API) |
| `tools.py` | Legacy STL-based mesh/bounding-box estimation, superseded by the CAD tab (kept for reference, not imported) |

`step_surface_selector.py` can also be used on its own:

```bash
python step_surface_selector.py [model.step]
```

At runtime the CAD tool writes `stl_bridge.json` / `stl_bridge.ptr` next to the
sources to advertise the files it exported; they are recreated at every launch
and can be deleted safely.

---

Part of the [CloudHPC](https://github.com/CFD-FEA-SERVICE/CloudHPC) repository.
