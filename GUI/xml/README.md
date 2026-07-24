# GUI/xml — tool setup files

One XML *setup* file per tool. Each of them describes the whole interface —
tabs, fields, dropdowns, repeatable blocks, CAD tab — which
[`../src/xmlreader.py`](../src/) turns into a running application. Adding a new
tool means adding a file here, not writing new code.

```bash
python ../src/xmlreader.py GUIsetup-carParks.xml
```

| File | Tool |
|---|---|
| `GUIsetup-bcSnappy.xml` | bcSnappy — OpenFOAM snappyHexMesh boundary-condition setup |
| `GUIsetup-carParks.xml` | carParks — car park ventilation |
| `GUIsetup-turboApp.xml` | turboApp — turbomachinery |
| `GUIsetup-envyFlow.xml` | envyFlow — environmental/external flows |
| `GUIsetup-fea.xml` | fea — structural analysis |
| `GUIsetup-bestgate.xml`, `GUIsetup-cloudIA.xml`, `GUIsetup-tenuFEM.xml`, `GUIsetup-valveFlow.xml`, `GUIsetup-watAirFlux.xml` | Additional tools, not part of the current installer |

The tools included in the Windows installer are listed in
[`../build/InnoSetup_eseguibile_unico.iss`](../build/) and in the build
workflow. When a tool is installed, its setup file is copied next to the
executable as `GUIsetup.xml`.

The syntax of these files — including the CAD-specific types and the
`specifyName` options — is documented in [`../README.md`](../README.md).

---

Part of the [CloudHPC](https://github.com/CFD-FEA-SERVICE/CloudHPC) repository.
