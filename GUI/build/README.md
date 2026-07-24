# GUI/build — Windows packaging

Everything needed to turn the sources into the single Windows installer
published on the [releases](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases)
page. This is normally done by the
[`cloudhpc-tools.yml`](../../.github/workflows/cloudhpc-tools.yml) workflow at
every push touching `GUI/`.

| File | Role |
|---|---|
| `SPEC/<tool>.spec` | PyInstaller recipe, one per tool. All of them freeze the same `src/xmlreader.py`, differing only in the executable name |
| `SPEC/icon.ico` | Icon of the generated executables |
| `InnoSetup_eseguibile_unico.iss` | Inno Setup script: packs every tool with its `GUIsetup.xml` and the logo into one installer with selectable components |
| `InnoSetup.iss` | Older per-application installer script, kept for reference |
| `compilation.ps1` | Local build helper reproducing what the workflow does |

## Build pipeline

1. **PyInstaller** freezes `src/xmlreader.py` once per tool, into `dist/<tool>/`
   at the repository root. Each spec calls `collect_all('OCC')` so the
   OpenCASCADE libraries — imported lazily by the CAD tab, and therefore
   invisible to static analysis — end up inside the frozen application.
2. **Inno Setup** collects those folders, adds the matching
   `../xml/GUIsetup-<tool>.xml` (renamed `GUIsetup.xml`) and `../LOGO.png`, and
   produces `Output/CFS_cloudHPC_tools-installer-0.1.exe`.

## Building locally

`pythonocc-core` comes from conda-forge, so the build must run inside a conda
environment — otherwise the CAD tab would be missing from the executables:

```powershell
conda create -n cloudhpc-build python=3.11
conda activate cloudhpc-build
conda install -c conda-forge pythonocc-core
pip install -r GUI\requirements.txt pyinstaller

# from the repository root:
powershell -ExecutionPolicy Bypass -File GUI\build\compilation.ps1
```

The script refuses to start if `pythonocc-core` cannot be imported. The list of
tools to build is at the top of `compilation.ps1`; enabling a new one means
uncommenting it there, in the workflow and in the Inno Setup script.

Build products (`dist/`, `Output/`) are ignored by git.

---

Part of the [CloudHPC](https://github.com/CFD-FEA-SERVICE/CloudHPC) repository.
