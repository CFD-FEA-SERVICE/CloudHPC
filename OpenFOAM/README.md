# OpenFOAM utilities

Utilities related to the OpenFOAM solver family as used on the cloudHPC platform.

## Content

### `cgns2foam.py`
Converts a **CGNS unstructured mesh** (tetrahedron / hexahedron / wedge-prism / pyramid elements) into a native **OpenFOAM polyMesh** (`points`, `faces`, `owner`, `neighbour`, `boundary`).

This is the inverse direction of `SU2/OF2SU2.py`: every face of every CGNS element becomes an OpenFOAM *polyhedral* face directly (tets keep their 4 triangular faces, hexahedra keep their 6 quad faces, etc.). Since OpenFOAM cells are arbitrary polyhedra, no decomposition is needed in this direction — only correct face/owner/neighbour bookkeeping.

Usage (see the script header for the full documentation and options):

```bash
python3 cgns2foam.py mesh.cgns -o case/constant/polyMesh
```
