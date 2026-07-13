#!/usr/bin/env python3
"""
cgns_to_openfoam.py — Convert a CGNS unstructured mesh (tetra / hexahedron /
wedge(prism) / pyramid elements) into a native OpenFOAM polyMesh
(points, faces, owner, neighbour, boundary).

This is the inverse direction of openfoam_to_cgns.py: instead of decomposing
polyhedra into tets, here every face of every element becomes an OpenFOAM
*polyhedral* face directly (tets keep their 4 triangular faces, hexahedra
keep their 6 quad faces, etc.) — OpenFOAM cells are arbitrary polyhedra, so
no decomposition is needed in this direction, only correct face/owner/
neighbour bookkeeping.

ALGORITHM
---------
1. Read points + volume elements from the CGNS file via `meshio`. Supported
   element types: tetra (4 nodes), pyramid (5), wedge/prism (6),
   hexahedron (8). If the CGNS file additionally contains 2D element
   sections (triangle/quad) — the usual way boundary patches are recorded —
   these are read too and used to recover boundary-patch names.

2. For every volume cell, generate its faces from a fixed per-shape
   topology table (which groups of local vertices form each face — this
   grouping is the standard CGNS/VTK/Exodus linear-element convention and
   is unambiguous). Each face is then *oriented* so its outward normal
   points away from that cell's centroid — computed directly from the
   geometry (sign of (faceCentroid - cellCentroid)·normal), not assumed
   from a hand-coded winding convention, so a mistake in remembered vertex
   winding order cannot silently produce inverted cells.

3. Faces are matched across cells by their node *set* (sorted tuple):
     - a node-set seen in exactly 2 cells -> internal face. owner = the
       cell with the smaller index, neighbour = the other; the stored
       point loop is the *owner's* version of the face — by construction
       (step 2) that loop's normal points outward from the owner, i.e.
       from owner into neighbour, which is exactly OpenFOAM's required
       convention.
     - a node-set seen in exactly 1 cell -> boundary face, owner = that
       cell, stored loop = that cell's outward-oriented version (normal
       points out of the domain, also required by OpenFOAM).
     - any other count means the input mesh is not a valid, manifold
       volume mesh (a hole, a duplicated cell, etc.) and conversion stops
       with a diagnostic.

4. Faces are re-ordered to satisfy OpenFOAM's "upper-triangular" addressing
   rule: every internal face must come before every boundary face, and
   internal faces must be sorted by (owner, neighbour) ascending. Boundary
   faces are grouped contiguously by patch.

5. Boundary patch assignment: if the CGNS file had 2D surface sections,
   every boundary face whose node set matches one of those sections is
   placed in that section's patch; everything else (and *everything*, if
   the CGNS had no surface sections at all) goes into a single catch-all
   patch named "defaultFaces" (type `patch`) — exactly the convention
   tools like gmshToFoam use for untagged boundary faces. All patches are
   written with type `patch`; rename them (`wall`, `symmetry`, ...) by
   hand in the boundary file, or with `createPatch`, if you need OpenFOAM
   to treat them specially.

6. As a self-check, every cell's set of outward-oriented face area vectors
   is summed; for a closed, non-self-intersecting cell this must be ~0
   (this is the same invariant `checkMesh` itself relies on, and a strong
   automatic check that the topology/orientation logic above is correct).
   A summary is printed; any cell that fails the check is reported.

LIMITATIONS
-----------
- Only first-order tetra/pyramid/wedge/hexahedron elements (no quadratic
  elements, no CGNS NGON_n/NFACE_n general-polyhedron elements).
- Boundary patch *names* are only recovered if the CGNS file stores
  explicit 2D surface element sections that meshio exposes via
  `mesh.cell_sets`; otherwise all exterior faces land in one
  "defaultFaces" patch (this is the same limitation any external-mesh
  importer without proper SIDS BC parsing has).
- Requires `meshio` + `h5py` to read the .cgns file itself
  (`pip install meshio h5py --break-system-packages`); the face/owner/
  neighbour construction only needs numpy.

USAGE
-----
    python3 cgns_to_openfoam.py mesh.cgns /path/to/case
        -> writes /path/to/case/constant/polyMesh/{points,faces,owner,neighbour,boundary}

    python3 cgns_to_openfoam.py mesh.cgns /path/to/case --default-patch-name outerWall
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from dataclasses import dataclass

import numpy as np


# --------------------------------------------------------------------------
# Per-shape face topology (grouping only — orientation is fixed by geometry)
# --------------------------------------------------------------------------

# Standard linear-element local connectivity, same convention used by
# CGNS/VTK/Exodus/meshio: hexahedron has bottom quad 0-1-2-3 and top quad
# 4-5-6-7 with vertex i+4 directly "above" vertex i; wedge/pyramid analogous.
FACE_TABLES = {
    "tetra": [
        (1, 2, 3),
        (0, 2, 3),
        (0, 1, 3),
        (0, 1, 2),
    ],
    "pyramid": [
        (0, 1, 2, 3),  # quad base
        (0, 1, 4),
        (1, 2, 4),
        (2, 3, 4),
        (3, 0, 4),
    ],
    "wedge": [
        (0, 1, 2),  # bottom tri
        (3, 4, 5),  # top tri
        (0, 1, 4, 3),
        (1, 2, 5, 4),
        (2, 0, 3, 5),
    ],
    "hexahedron": [
        (0, 1, 2, 3),  # bottom quad
        (4, 5, 6, 7),  # top quad
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ],
}


def _polygon_normal_and_centroid(pts: np.ndarray):
    """Outward-direction-agnostic normal (via fan from mean point) + centroid."""
    n = len(pts)
    c = pts.mean(axis=0)
    if n == 3:
        normal = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        return normal, c
    normal = np.zeros(3)
    for i in range(n):
        normal += np.cross(pts[i] - c, pts[(i + 1) % n] - c)
    return normal, c


def _oriented_face(points: np.ndarray, node_ids, cell_centroid: np.ndarray):
    """
    Return node_ids reordered (if needed) so the face's normal (right-hand
    rule on the returned order) points away from cell_centroid.
    """
    pts = points[list(node_ids)]
    normal, face_c = _polygon_normal_and_centroid(pts)
    outward = face_c - cell_centroid
    if np.dot(normal, outward) < 0.0:
        node_ids = tuple(reversed(node_ids))
    return tuple(int(n) for n in node_ids)


# --------------------------------------------------------------------------
# Per-cell face generation + closed-cell self-check
# --------------------------------------------------------------------------

@dataclass
class RawFaceInstance:
    cell: int
    nodes: tuple  # outward-oriented node loop


def generate_cell_faces(points: np.ndarray, volume_cells: list):
    """
    volume_cells: list of (shape_name, connectivity ndarray (ncells, nverts))
    Returns:
        faces_by_key : dict[frozenset(node_ids)] -> list[RawFaceInstance]
        n_cells      : int
        closure_residuals : list of per-cell max(|sum of outward area vectors|)
                             (small numbers are good; this is the self-check)
    """
    faces_by_key = defaultdict(list)
    closure_residuals = []
    cell_index = 0
    for shape, conn in volume_cells:
        table = FACE_TABLES.get(shape)
        if table is None:
            raise ValueError(
                f"Unsupported volume element type '{shape}'. Supported: "
                f"{sorted(FACE_TABLES)}."
            )
        for row in conn:
            cell_centroid = points[row].mean(axis=0)
            area_sum = np.zeros(3)
            for local_face in table:
                node_ids = tuple(int(row[i]) for i in local_face)
                oriented = _oriented_face(points, node_ids, cell_centroid)
                pts = points[list(oriented)]
                normal, _ = _polygon_normal_and_centroid(pts)
                area_sum += normal
                key = frozenset(oriented)
                faces_by_key[key].append(RawFaceInstance(cell=cell_index, nodes=oriented))
            # scale residual by a characteristic area so it's dimensionless-ish
            char_len = np.linalg.norm(points[row].max(axis=0) - points[row].min(axis=0))
            scale = max(char_len ** 2, 1e-300)
            closure_residuals.append(float(np.linalg.norm(area_sum)) / scale)
            cell_index += 1
    return faces_by_key, cell_index, closure_residuals


# --------------------------------------------------------------------------
# Owner/neighbour/boundary assembly (the OpenFOAM-specific bookkeeping)
# --------------------------------------------------------------------------

@dataclass
class BoundaryPatch:
    name: str
    type_: str
    n_faces: int
    start_face: int


@dataclass
class FoamMeshOut:
    points: np.ndarray
    faces: list  # list[tuple[int,...]] in final OpenFOAM order
    owner: np.ndarray
    neighbour: np.ndarray
    boundary: list  # list[BoundaryPatch]


def assemble_openfoam_mesh(
    points: np.ndarray,
    faces_by_key: dict,
    n_cells: int,
    patch_face_keys=None,
    default_patch_name: str = "defaultFaces",
) -> FoamMeshOut:
    patch_face_keys = patch_face_keys or {}

    internal = []  # (owner, neighbour, nodes)
    boundary_by_patch = defaultdict(list)  # patch_name -> [(owner, nodes)]

    for key, instances in faces_by_key.items():
        if len(instances) == 2:
            a, b = instances
            if a.cell <= b.cell:
                owner_inst, nbr_inst = a, b
            else:
                owner_inst, nbr_inst = b, a
            internal.append((owner_inst.cell, nbr_inst.cell, owner_inst.nodes))
        elif len(instances) == 1:
            inst = instances[0]
            patch_name = None
            for name, keyset in patch_face_keys.items():
                if key in keyset:
                    patch_name = name
                    break
            if patch_name is None:
                patch_name = default_patch_name
            boundary_by_patch[patch_name].append((inst.cell, inst.nodes))
        else:
            raise ValueError(
                f"Face with nodes {sorted(key)} is shared by {len(instances)} "
                f"cells (expected 1 or 2) — the input volume mesh is not a "
                f"valid manifold mesh."
            )

    internal.sort(key=lambda t: (t[0], t[1]))

    n_internal = len(internal)
    owner = np.empty(n_internal, dtype=np.int64)
    neighbour = np.empty(n_internal, dtype=np.int64)
    out_faces = []
    for i, (own, nbr, nodes) in enumerate(internal):
        owner[i] = own
        neighbour[i] = nbr
        out_faces.append(nodes)

    patches = []
    # Deterministic patch order: alphabetical, with the catch-all patch last.
    patch_names = sorted(p for p in boundary_by_patch if p != default_patch_name)
    if default_patch_name in boundary_by_patch:
        patch_names.append(default_patch_name)

    owner_list = list(owner)
    for name in patch_names:
        entries = sorted(boundary_by_patch[name], key=lambda t: t[0])
        start_face = len(out_faces)
        for own, nodes in entries:
            owner_list.append(own)
            out_faces.append(nodes)
        patches.append(BoundaryPatch(name=name, type_="patch", n_faces=len(entries), start_face=start_face))

    owner_full = np.array(owner_list, dtype=np.int64)

    return FoamMeshOut(points=points, faces=out_faces, owner=owner_full, neighbour=neighbour, boundary=patches)


# --------------------------------------------------------------------------
# CGNS reading (via meshio)
# --------------------------------------------------------------------------

_SURFACE_TYPES = {"triangle", "quad"}


def read_cgns(path: str):
    """
    Returns:
        points        : (Np,3) float64
        volume_cells  : list[(shape_name, connectivity ndarray)]
        patch_face_keys: dict[name] -> set[frozenset(node_ids)]   (possibly empty)
    """
    try:
        import meshio
    except ImportError as e:
        raise ImportError(
            "Reading CGNS requires the 'meshio' and 'h5py' packages.\n"
            "    pip install meshio h5py --break-system-packages"
        ) from e

    mesh = meshio.read(path, file_format="cgns")
    points = np.asarray(mesh.points, dtype=np.float64)

    volume_cells = []
    surface_blocks = []  # (block_index, shape, connectivity)
    for i, block in enumerate(mesh.cells):
        shape = block.type if hasattr(block, "type") else block[0]
        data = block.data if hasattr(block, "data") else block[1]
        data = np.asarray(data, dtype=np.int64)
        if shape in FACE_TABLES:
            volume_cells.append((shape, data))
        elif shape in _SURFACE_TYPES:
            surface_blocks.append((i, shape, data))
        # silently skip lines/points/other metadata blocks if present

    patch_face_keys: dict = {}
    cell_sets = getattr(mesh, "cell_sets", None) or {}
    if cell_sets and surface_blocks:
        for name, per_block in cell_sets.items():
            keyset = set()
            for (block_idx, _shape, data) in surface_blocks:
                if block_idx >= len(per_block):
                    continue
                local_ids = np.asarray(per_block[block_idx])
                if local_ids.size == 0:
                    continue
                for row in data[local_ids]:
                    keyset.add(frozenset(int(n) for n in row))
            if keyset:
                patch_face_keys[name] = keyset
    elif surface_blocks:
        # No names available — still use the surface elements to define
        # patch membership, just with generic names.
        for n, (block_idx, _shape, data) in enumerate(surface_blocks):
            patch_face_keys[f"section_{n}"] = {
                frozenset(int(x) for x in row) for row in data
            }

    if not volume_cells:
        raise ValueError(
            "No supported volume elements (tetra/pyramid/wedge/hexahedron) "
            "found in the CGNS file."
        )

    return points, volume_cells, patch_face_keys


# --------------------------------------------------------------------------
# OpenFOAM ASCII writers
# --------------------------------------------------------------------------

_HEADER_TMPL = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {obj};
}}
"""


def _write_header(fh, cls: str, obj: str):
    fh.write(_HEADER_TMPL.format(cls=cls, obj=obj))
    fh.write("\n")


def write_points(path: str, points: np.ndarray):
    with open(path, "w") as fh:
        _write_header(fh, "vectorField", "points")
        fh.write(f"{len(points)}\n(\n")
        for p in points:
            fh.write(f"({float(p[0]):.9g} {float(p[1]):.9g} {float(p[2]):.9g})\n")
        fh.write(")\n")


def write_faces(path: str, faces: list):
    with open(path, "w") as fh:
        _write_header(fh, "faceList", "faces")
        fh.write(f"{len(faces)}\n(\n")
        for f in faces:
            fh.write(f"{len(f)}({' '.join(str(int(i)) for i in f)})\n")
        fh.write(")\n")


def write_labels(path: str, cls: str, obj: str, values: np.ndarray, note: str = ""):
    with open(path, "w") as fh:
        fh.write("FoamFile\n{\n")
        fh.write("    version     2.0;\n    format      ascii;\n")
        fh.write(f"    class       {cls};\n")
        if note:
            fh.write(f"    note        \"{note}\";\n")
        fh.write(f"    object      {obj};\n}}\n\n")
        fh.write(f"{len(values)}\n(\n")
        for v in values:
            fh.write(f"{int(v)}\n")
        fh.write(")\n")


def write_boundary(path: str, patches: list):
    with open(path, "w") as fh:
        _write_header(fh, "polyBoundaryMesh", "boundary")
        fh.write(f"{len(patches)}\n(\n")
        for p in patches:
            fh.write(f"    {p.name}\n    {{\n")
            fh.write(f"        type            {p.type_};\n")
            fh.write(f"        nFaces          {p.n_faces};\n")
            fh.write(f"        startFace       {p.start_face};\n")
            fh.write("    }\n")
        fh.write(")\n")


def write_openfoam_mesh(case_dir: str, mesh: FoamMeshOut):
    poly_dir = os.path.join(case_dir, "constant", "polyMesh")
    os.makedirs(poly_dir, exist_ok=True)
    n_internal = len(mesh.neighbour)
    n_cells = int(mesh.owner.max()) + 1 if len(mesh.owner) else 0

    write_points(os.path.join(poly_dir, "points"), mesh.points)
    write_faces(os.path.join(poly_dir, "faces"), mesh.faces)
    write_labels(
        os.path.join(poly_dir, "owner"), "labelList", "owner", mesh.owner,
        note=f"nPoints:{len(mesh.points)} nCells:{n_cells} nFaces:{len(mesh.faces)} nInternalFaces:{n_internal}",
    )
    write_labels(os.path.join(poly_dir, "neighbour"), "labelList", "neighbour", mesh.neighbour)
    write_boundary(os.path.join(poly_dir, "boundary"), mesh.boundary)
    return poly_dir


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cgns_file", help="input .cgns file")
    ap.add_argument("case", help="output OpenFOAM case directory (constant/polyMesh will be created under it)")
    ap.add_argument("--default-patch-name", default="defaultFaces", help="name for untagged boundary faces (default: defaultFaces)")
    args = ap.parse_args(argv)

    print(f"[1/4] Reading CGNS file: {args.cgns_file}")
    points, volume_cells, patch_face_keys = read_cgns(args.cgns_file)
    shape_counts = {s: len(c) for s, c in volume_cells}
    print(f"      points={len(points)} volume cells by type: {shape_counts}")
    if patch_face_keys:
        print(f"      tagged boundary sections found: {list(patch_face_keys.keys())}")
    else:
        print("      no tagged boundary sections found; all exterior faces will "
              f"go into patch '{args.default_patch_name}'")

    print("[2/4] Building cell faces and checking closure ...")
    faces_by_key, n_cells, residuals = generate_cell_faces(points, volume_cells)
    residuals = np.array(residuals)
    bad = np.where(residuals > 1e-6)[0]
    print(f"      {n_cells} cells, max closure residual = {residuals.max():.3e}")
    if len(bad):
        print(f"      WARNING: {len(bad)} cell(s) failed the closed-surface check "
              f"(residual > 1e-6); mesh may be degenerate or non-manifold. "
              f"First few cell indices: {bad[:10].tolist()}")

    print("[3/4] Assembling owner/neighbour/boundary ...")
    mesh = assemble_openfoam_mesh(
        points, faces_by_key, n_cells,
        patch_face_keys=patch_face_keys,
        default_patch_name=args.default_patch_name,
    )
    print(
        f"      faces={len(mesh.faces)} internal={len(mesh.neighbour)} "
        f"boundary={len(mesh.faces) - len(mesh.neighbour)}"
    )
    for p in mesh.boundary:
        print(f"      patch '{p.name}': type={p.type_} nFaces={p.n_faces} startFace={p.start_face}")

    print(f"[4/4] Writing OpenFOAM polyMesh under: {args.case}")
    poly_dir = write_openfoam_mesh(args.case, mesh)
    print(f"Done. Wrote: {poly_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
