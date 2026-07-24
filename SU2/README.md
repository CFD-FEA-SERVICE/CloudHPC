# SU2 utilities

Utilities related to the SU2 solver as used on the cloudHPC platform.

## Content

### `OF2SU2.py`
Converts an **OpenFOAM polyMesh** directly to **CGNS** (readable by SU2) without any in-Python decomposition.

The script assumes the input mesh is already composed of simple element types (tet, hex, wedge/prism, pyramid). For polyhedral meshes, first use OpenFOAM's own `cellDecomposer` function object to produce a simple mesh, then run this script on the output region.

Recommended workflow (OpenFOAM.com v2406+): add a `cellDecomposer` entry to `system/controlDict` under `functions` (see the script header for the complete snippet), run the decomposition, then convert the decomposed region.

See also `OpenFOAM/cgns2foam.py` in this repository for the opposite conversion (CGNS → OpenFOAM).

---

Part of the [CloudHPC](https://github.com/CFD-FEA-SERVICE/CloudHPC) repository.
