# GUI — cloudHPC desktop pre-processing tools

XML-driven desktop applications used to set up a simulation and submit it to the
cloudHPC platform. A single engine reads an XML *setup* file and generates the
whole interface from it — tabs, fields, dropdowns, repeatable blocks — so every
tool (bcSnappy, carParks, turboApp, envyFlow, fea, ...) is the **same program**
driven by a different configuration file in [`xml/`](xml/).

The interface also embeds a **STEP/CAD viewer** (OpenCASCADE via pythonocc):
import a CAD model, group its surfaces, export one STL per group, and reference
those groups directly from the simulation parameters.

## Folder layout

| Folder | Content |
|---|---|
| [`src/`](src/) | Python sources — `xmlreader.py` is the single entry point |
| [`xml/`](xml/) | `GUIsetup-<tool>.xml` — one configuration per tool |
| [`build/`](build/) | PyInstaller specs, Inno Setup script and local build helper for the Windows installer |
| `requirements.txt` | Python dependencies (see the note on pythonocc-core inside) |
| `LOGO.png` | Logo installed next to each tool |

## Installation and launch

### Windows

Download `CFS_cloudHPC_tools-installer-0.1.exe` from the
[releases](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases) and pick the
tools you want during setup. Each one is installed with its own `GUIsetup.xml`
and can be started from its shortcut.

### Linux / from sources

`pythonocc-core` is only distributed on conda-forge (not on PyPI), so a conda
environment is the supported way to run from sources:

```bash
conda create -n cloudhpc-gui python=3.11
conda activate cloudhpc-gui
conda install -c conda-forge pythonocc-core
pip install -r requirements.txt

# Qt 6.5+ on Linux also needs:
sudo apt install libxcb-cursor0
```

Then launch the engine with the setup file of the tool you want:

```bash
python src/xmlreader.py xml/GUIsetup-carParks.xml
python src/xmlreader.py            # no argument → file picker (or GUIsetup.xml next to the script)
```

The setup file can also be given through the `GUISETUP_FILE` environment
variable. Without `pythonocc-core` the rest of the interface still works; only
the CAD tab shows an "unavailable" placeholder.

## Using the interface

The window is organised in tabs, generated from the setup file. The navigation
arrows move between tabs; `Run on Cloud` submits the job with the selected vCPU
count; `File > Save As...` writes the output XML and the attachments.

In a **CAD tab** you can import a STEP file, select surfaces (in the viewport or
in the surface list), assign them to named **groups**, place a probe point and
tune the STL export refinement. On save, one STL per group is written to an
`attachments/` folder next to the output XML, together with the probe point in
VTK format. The full CAD session (groups, colours, hidden faces, path of the
STEP file) is embedded directly inside the output XML as base64-encoded JSON, so
there is no separate session file to keep track of — reopening that XML restores
the whole session, provided the STEP file is still at its original path.

## Writing a setup file

On top of the basic types (`string`, `int`, `float`, `dropdown`, `file`,
`image`, `software`, `frame`), the engine understands the following.

### `type="CAD"` — embed the CAD tool

```xml
<Geometry type="frame">
    <CADdumb type="CAD">step</CADdumb>
</Geometry>
```

The tab takes the name of the parent `frame` (**Geometry** here); the name of
the `CAD` element itself is a placeholder and is never displayed. On export it
holds the encoded CAD session.

Two optional requirements can be declared, and are enforced when saving:

```xml
<Geometry type="frame">
    <CADdumb type="CAD" probePoint="true">step
        <option type="string">inlet</option>
        <option type="string">outlet</option>
        <option type="string">wall</option>
    </CADdumb>
</Geometry>
```

* `probePoint="true"` — a probe point must be placed before the export
* each `<option>` — a **mandatory group**: created empty at startup, shown in
  red in the Groups panel until at least one face is assigned to it

Without these attributes no requirement is enforced.

### `type="CADgroups-dropdown"` — pick a CAD group

```xml
<BoundaryConditions type="frame">
    <inletPatch type="CADgroups-dropdown">pick a group</inletPatch>
</BoundaryConditions>
```

A dropdown listing the groups currently defined in the CAD tab, refreshed
automatically whenever they change. The text content is only a placeholder: it
never appears among the options nor in the output. The selected group name is
exported like any other value: `<inletPatch>wall</inletPatch>`.

### `type="multiple"` — repeatable blocks

A block of fields that the user can add and remove several times (patches,
refinement regions, ...). The `specifyName` attribute controls how each
instance is named:

| `specifyName` | Behaviour |
|---|---|
| `"false"` *(default)* | No name field. Instances are named automatically: `patch_cloudHPC_1`, `patch_cloudHPC_2`, ... |
| `"true"` | A free-text field lets the user name each instance; default names are `patch_1`, `patch_2`, ... |
| `"CADgroups"` | The name is chosen from a dropdown of the CAD groups. The instance picker keeps its fixed labels (`patch_1`, `patch_2`, ...) while the assigned group is what gets exported |

```xml
<patch type="multiple" specifyName="CADgroups">
    <velocity   type="float">0.0</velocity>
    <turbulence type="float">0.05</turbulence>
</patch>
```

The prefix comes from the tag name, so `<refinement type="multiple">` produces
`refinement_1`, `refinement_2`, and so on.

## Building the Windows installer

Handled automatically by the
[`cloudhpc-tools.yml`](../.github/workflows/cloudhpc-tools.yml) workflow on every
push touching `GUI/`. To reproduce it locally see [`build/README.md`](build/).

---

Part of the [CloudHPC](https://github.com/CFD-FEA-SERVICE/CloudHPC) repository.
