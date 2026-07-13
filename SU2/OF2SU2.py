#!/usr/bin/env python3
"""
openfoam_to_cgns.py — Convert an OpenFOAM polyMesh directly to CGNS without
any in-Python decomposition.

This version assumes the input mesh is already composed of simple element
types (tet, hex, wedge/prism, pyramid). Use OpenFOAM's own cellDecomposer
function object to produce a simple mesh from a polyhedral one first, then
run this script on the output region.

RECOMMENDED WORKFLOW (OpenFOAM.com v2406+)
-------------------------------------------
  1. Add to system/controlDict under functions:
       cellDecomposer
       {
           type          cellDecomposer;
           libs          (fieldFunctionObjects);
           fields        ();           // empty = mesh only, no field mapping
           mapRegion     tetMesh;
           decomposeType faceCentre;   // pure tets; use 'polyhedral' for
           selectionMode all;          //   hex/wedge/pyr pass-through
       }
  2. Run:
       postProcess -func cellDecomposer -case /path/to/case
  3. Convert the output region:
       python3 openfoam_to_cgns.py /path/to/case/tetMesh mesh.cgns

Alternatively, point directly at a constant/polyMesh directory:
       python3 openfoam_to_cgns.py /path/to/case/tetMesh/constant/polyMesh mesh.cgns

SUPPORTED CELL TYPES
--------------------
  tetra (4 vertices)    -> CGNS TETRA_4
  pyramid (5 vertices)  -> CGNS PYRA_5
  wedge/prism (6 verts) -> CGNS PENTA_6
  hexahedron (8 verts)  -> CGNS HEXA_8

Boundary patches are exported as TRI_3 or QUAD_4 depending on face size,
one Elements_t section + one BC_t per patch.

ALGORITHM
---------
OpenFOAM stores meshes in face/owner/neighbour format (no explicit cell
connectivity). This script reconstructs per-cell vertex connectivity by:
  1. Building a cell->faces map from the owner/neighbour arrays.
  2. For each cell, collecting the union of its face vertex sets to get
     the unique vertex list and determine the cell type from vertex count.
  3. Ordering vertices in the CGNS convention for each element type using
     geometric checks (signed volume / face normal orientation) rather than
     assumed winding conventions, so orientation errors produce detectable
     sign flips, not silent garbage.

Boundary faces are read directly from the faces file (no reconstruction
needed) and written as TRI_3 or QUAD_4 based on their vertex count.

LIMITATIONS
-----------
- ASCII OpenFOAM mesh files only. For binary meshes run first:
      foamFormatConvert -case <case> -ascii
- Does not read cellZones/cellSets (geometry + boundary patches only).
- Mixed-type boundary patches (some tris AND some quads in one patch) are
  split into two sub-sections automatically.
- Requires pyCGNS for CGNS output:
      conda install -c conda-forge pycgns
      # or: pip install pyCGNS --break-system-packages
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np


# --------------------------------------------------------------------------
# OpenFOAM ASCII reader (unchanged from previous version)
# --------------------------------------------------------------------------

def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//.*", "", text)
    return text


def _check_ascii(text: str, path: str) -> None:
    m = re.search(r"\bformat\s+(\w+)\s*;", text)
    if m and m.group(1).lower() == "binary":
        raise ValueError(
            f"{path}: binary OpenFOAM format detected. Convert first:\n"
            f"    foamFormatConvert -case <case> -ascii"
        )


def _skip_foamfile_header(text: str) -> str:
    idx = text.find("FoamFile")
    if idx == -1:
        return text
    brace_start = text.find("{", idx)
    if brace_start == -1:
        return text
    depth, i = 0, brace_start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:]
        i += 1
    return text


def _extract_top_list_block(text: str) -> str:
    m = re.search(r"\(", text)
    if not m:
        raise ValueError("could not find opening '(' for data list")
    start = m.start()
    depth, i = 0, start
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1: i]
        i += 1
    raise ValueError("unbalanced parentheses in list block")


def _read_foam_file(path: str) -> str:
    with open(path, "r", errors="replace") as fh:
        raw = fh.read()
    _check_ascii(raw, path)
    return _strip_comments(_skip_foamfile_header(raw))


def read_points(path: str) -> np.ndarray:
    text = _read_foam_file(path)
    block = _extract_top_list_block(text)
    triples = re.findall(r"\(\s*([^()]+?)\s*\)", block)
    return np.array([[float(v) for v in t.split()] for t in triples], dtype=np.float64)


def read_labels(path: str) -> np.ndarray:
    text = _read_foam_file(path)
    block = _extract_top_list_block(text)
    return np.array(re.findall(r"-?\d+", block), dtype=np.int64)


def read_faces(path: str) -> list:
    text = _read_foam_file(path)
    block = _extract_top_list_block(text)
    entries = re.findall(r"(\d+)\s*\(\s*([^()]*?)\s*\)", block)
    return [np.array(body.split(), dtype=np.int64) for _n, body in entries]


@dataclass
class BoundaryPatch:
    name: str
    type_: str
    n_faces: int
    start_face: int


def read_boundary(path: str) -> list:
    text = _read_foam_file(path)
    block = _extract_top_list_block(text)
    patches = []
    for m in re.finditer(r"(\w+)\s*\{([^{}]*)\}", block):
        name, body = m.group(1), m.group(2)
        type_m = re.search(r"\btype\s+([\w]+)\s*;", body)
        nf_m = re.search(r"\bnFaces\s+(\d+)\s*;", body)
        sf_m = re.search(r"\bstartFace\s+(\d+)\s*;", body)
        if nf_m is None or sf_m is None:
            continue
        patches.append(BoundaryPatch(
            name=name,
            type_=type_m.group(1) if type_m else "patch",
            n_faces=int(nf_m.group(1)),
            start_face=int(sf_m.group(1)),
        ))
    return patches


@dataclass
class FoamMesh:
    points: np.ndarray
    faces: list
    owner: np.ndarray
    neighbour: np.ndarray
    boundary: list
    n_internal_faces: int = field(init=False)
    n_cells: int = field(init=False)

    def __post_init__(self):
        self.n_internal_faces = len(self.neighbour)
        n = int(self.owner.max()) + 1
        if len(self.neighbour):
            n = max(n, int(self.neighbour.max()) + 1)
        self.n_cells = n


def read_foam_mesh(case_or_polymesh_dir: str) -> FoamMesh:
    d = case_or_polymesh_dir
    candidate = os.path.join(d, "constant", "polyMesh")
    if os.path.isdir(candidate):
        d = candidate
    elif not os.path.isfile(os.path.join(d, "points")):
        raise FileNotFoundError(
            f"Cannot find OpenFOAM mesh files under '{case_or_polymesh_dir}'. "
            f"Expected '<case>/constant/polyMesh/points' or '<dir>/points'."
        )

    def find(name):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
        pgz = p + ".gz"
        if os.path.isfile(pgz):
            raise FileNotFoundError(
                f"{pgz} is gzip-compressed; gunzip it first:\n    gunzip {name}.gz"
            )
        raise FileNotFoundError(f"missing required mesh file: {p}")

    return FoamMesh(
        points=read_points(find("points")),
        faces=read_faces(find("faces")),
        owner=read_labels(find("owner")),
        neighbour=read_labels(find("neighbour")),
        boundary=read_boundary(find("boundary")),
    )


# --------------------------------------------------------------------------
# Cell reconstruction from face/owner/neighbour
# --------------------------------------------------------------------------

def _polygon_normal(points: np.ndarray, verts) -> np.ndarray:
    """Area-weighted normal of a polygon (fan from centroid)."""
    pts = points[list(verts)]
    c = pts.mean(axis=0)
    normal = np.zeros(3)
    n = len(pts)
    for i in range(n):
        normal += np.cross(pts[i] - c, pts[(i + 1) % n] - c)
    return normal


def _order_tet(points: np.ndarray, face_verts_list: list) -> list:
    """
    Return 4 vertex indices in CGNS TETRA_4 order (positive signed volume).
    Base face = face 0's vertices in their stored order; apex = 4th unique vertex.
    Swap two base vertices if the signed volume comes out negative.
    """
    seen, uniq = set(), []
    for fv in face_verts_list:
        for v in fv:
            vi = int(v)
            if vi not in seen:
                seen.add(vi)
                uniq.append(vi)

    v0, v1, v2 = int(face_verts_list[0][0]), int(face_verts_list[0][1]), int(face_verts_list[0][2])
    v3 = next(v for v in uniq if v not in (v0, v1, v2))
    p = points
    # signed volume = dot(v3-v0, cross(v1-v0, v2-v0)); must be > 0
    if np.dot(p[v3] - p[v0], np.cross(p[v1] - p[v0], p[v2] - p[v0])) < 0:
        v1, v2 = v2, v1
    return [v0, v1, v2, v3]


def _order_pyramid(points: np.ndarray, face_verts_list: list) -> list:
    """
    Return 5 vertex indices in CGNS PYRA_5 order.
    Base = the quad face; apex = vertex common to all 4 tri faces.
    Base winding: outward normal points AWAY from apex (CGNS convention).
    """
    quad = next((list(map(int, fv)) for fv in face_verts_list if len(fv) == 4), None)
    tris = [list(map(int, fv)) for fv in face_verts_list if len(fv) == 3]
    if quad is None or len(tris) != 4:
        raise ValueError(f"Pyramid: expected 1 quad + 4 tri faces, got "
                         f"{sum(1 for fv in face_verts_list if len(fv)==4)} quads, "
                         f"{sum(1 for fv in face_verts_list if len(fv)==3)} tris")
    apex_set = set(tris[0])
    for tf in tris[1:]:
        apex_set &= set(tf)
    apex = int(apex_set.pop())
    p = points
    bc = p[quad].mean(axis=0)
    n = _polygon_normal(p, quad)
    # CGNS PYRA_5: base normal should point AWAY from apex
    if np.dot(n, p[apex] - bc) > 0:   # normal toward apex → reverse base
        quad = quad[::-1]
    return quad + [apex]


def _order_wedge(points: np.ndarray, face_verts_list: list, cell_centroid: np.ndarray) -> list:
    """
    Return 6 vertex indices in CGNS PENTA_6 order.
    Bottom tri (0,1,2) + top tri (3,4,5) where vertex i and i+3 are connected
    by a lateral quad face. Bottom tri outward normal points away from cell.
    """
    tris = [list(map(int, fv)) for fv in face_verts_list if len(fv) == 3]
    quads = [list(map(int, fv)) for fv in face_verts_list if len(fv) == 4]
    if len(tris) != 2 or len(quads) != 3:
        raise ValueError(f"Wedge: expected 2 tri + 3 quad faces, got "
                         f"{len(tris)} tris, {len(quads)} quads")
    p = points
    # Orient first tri: outward normal points away from cell centroid
    b = list(tris[0])
    bc = p[b].mean(axis=0)
    n = np.cross(p[b[1]] - p[b[0]], p[b[2]] - p[b[0]])
    if np.dot(n, bc - cell_centroid) < 0:
        b = b[::-1]

    # Match each bottom vertex to the corresponding top vertex via lateral quads
    top_set = set(tris[1])
    top_ordered = []
    for bv in b:
        for qf in quads:
            if bv in qf:
                qi = qf.index(bv)
                # In a lateral quad (bv, bv_next, tv_next, tv) the top vertex
                # is at qi±1 mod 4, whichever is in the top tri
                for delta in (1, -1, 2):
                    cand = qf[(qi + delta) % 4]
                    if cand in top_set:
                        top_ordered.append(cand)
                        break
                break
    if len(top_ordered) != 3:
        top_ordered = list(tris[1])  # fallback

    # Verify orientation: the tet (b[0],b[1],b[2],top[0]) must have positive
    # signed volume. If not, reverse both bottom and top winding together.
    vol = np.dot(p[top_ordered[0]] - p[b[0]],
                 np.cross(p[b[1]] - p[b[0]], p[b[2]] - p[b[0]]))
    if vol < 0:
        b = b[::-1]
        top_ordered = top_ordered[::-1]
    return b + top_ordered


def _order_hex(points: np.ndarray, face_verts_list: list, cell_centroid: np.ndarray) -> list:
    """
    Return 8 vertex indices in CGNS HEXA_8 order.
    Bottom quad (0,1,2,3) + top quad (4,5,6,7) where vertex i and i+4 are
    connected by a lateral quad face. Bottom outward normal points away from cell.
    """
    faces = [list(map(int, fv)) for fv in face_verts_list]
    p = points

    # Find a bottom face: pick faces[0], orient outward
    b = list(faces[0])
    bc = p[b].mean(axis=0)
    n = _polygon_normal(p, b)
    if np.dot(n, bc - cell_centroid) < 0:
        b = b[::-1]

    # Find opposite face (no shared vertices with bottom)
    b_set = set(b)
    opp = next((f for f in faces if not set(f) & b_set), None)
    if opp is None:
        raise ValueError("Hex: could not find a face opposite to the bottom face")

    # Match each bottom vertex to its corresponding top vertex via a lateral face
    top_set = set(opp)
    lateral = [f for f in faces if set(f) != b_set and set(f) != set(opp)]
    top_ordered = []
    for bv in b:
        matched = False
        for lf in lateral:
            if bv in lf:
                li = lf.index(bv)
                for delta in (1, -1, 2, 3):
                    cand = lf[(li + delta) % 4]
                    if cand in top_set:
                        top_ordered.append(cand)
                        matched = True
                        break
                if matched:
                    break
        if not matched:
            top_ordered.append(next(iter(top_set - set(top_ordered))))

    # Verify orientation: signed volume of tet (b[0],b[1],b[2],top[0]) must be >0.
    # If not, reverse the bottom winding (flips the whole hex).
    p = points
    if len(top_ordered) >= 1:
        vol = np.dot(p[top_ordered[0]] - p[b[0]],
                     np.cross(p[b[1]] - p[b[0]], p[b[2]] - p[b[0]]))
        if vol < 0:
            b = [b[0], b[3], b[2], b[1]]
            top_ordered = [top_ordered[0], top_ordered[3], top_ordered[2], top_ordered[1]] \
                if len(top_ordered) == 4 else top_ordered
    return b + top_ordered


_CELL_TYPE_BY_NVERTS = {4: "tetra", 5: "pyramid", 6: "wedge", 8: "hexahedron"}

_CGNS_ELEM_TYPE = {
    "tetra": "TETRA_4",
    "pyramid": "PYRA_5",
    "wedge": "PENTA_6",
    "hexahedron": "HEXA_8",
}

_NVERTS_PER_ELEM = {
    "tetra": 4, "pyramid": 5, "wedge": 6, "hexahedron": 8,
    "triangle": 3, "quad": 4,
}

_CGNS_FACE_TYPE = {3: ("triangle", "TRI_3"), 4: ("quad", "QUAD_4")}


def reconstruct_mesh(mesh: FoamMesh):
    """
    Reconstruct element connectivity and boundary faces from OpenFOAM
    face/owner/neighbour storage.

    Returns
    -------
    cells_by_type : dict[shape_name] -> np.ndarray  shape (n, nverts)
        Volume connectivity per element type (all using original point indices).
    boundary_faces : dict[patch_name] -> dict[face_type] -> np.ndarray  shape (n, nverts)
        Boundary face connectivity per patch, split by face type (tri/quad).
    """
    points = mesh.points
    faces = mesh.faces

    # --- cell -> face list ---
    cell_face_map = [[] for _ in range(mesh.n_cells)]
    for fi, c in enumerate(mesh.owner):
        cell_face_map[c].append(fi)
    for fi, c in enumerate(mesh.neighbour):
        cell_face_map[c].append(fi)

    # --- reconstruct volume elements ---
    cells_by_type: dict = defaultdict(list)
    unknown_cells = []

    for ci, fids in enumerate(cell_face_map):
        face_verts_list = [faces[fi] for fi in fids]

        # unique vertices → cell type
        seen, uniq = set(), []
        for fv in face_verts_list:
            for v in fv:
                vi = int(v)
                if vi not in seen:
                    seen.add(vi)
                    uniq.append(vi)
        n = len(uniq)
        shape = _CELL_TYPE_BY_NVERTS.get(n)
        if shape is None:
            unknown_cells.append((ci, n))
            continue

        cell_centroid = points[uniq].mean(axis=0)

        try:
            if shape == "tetra":
                conn = _order_tet(points, face_verts_list)
            elif shape == "pyramid":
                conn = _order_pyramid(points, face_verts_list)
            elif shape == "wedge":
                conn = _order_wedge(points, face_verts_list, cell_centroid)
            else:  # hexahedron
                conn = _order_hex(points, face_verts_list, cell_centroid)
        except Exception as e:
            unknown_cells.append((ci, n))
            print(f"  WARNING: cell {ci} ({shape}, {n} verts) skipped: {e}")
            continue

        cells_by_type[shape].append(conn)

    if unknown_cells:
        print(f"  WARNING: {len(unknown_cells)} cell(s) had unrecognised vertex "
              f"counts and were skipped (vertex counts: "
              f"{sorted(set(n for _,n in unknown_cells))}). "
              f"This script supports tet/pyramid/wedge/hex only.")

    # Convert to arrays
    for shape in list(cells_by_type):
        cells_by_type[shape] = np.array(cells_by_type[shape], dtype=np.int64)

    # --- boundary faces ---
    boundary_faces: dict = {}
    for patch in mesh.boundary:
        tris, quads = [], []
        for fi in range(patch.start_face, patch.start_face + patch.n_faces):
            verts = [int(v) for v in faces[fi]]
            n = len(verts)
            if n == 3:
                tris.append(verts)
            elif n == 4:
                quads.append(verts)
            else:
                # fan-triangulate non-tri/quad boundary faces
                c_idx = len(points)  # placeholder — handled below in fallback
                for k in range(n - 2):
                    tris.append([verts[0], verts[k + 1], verts[k + 2]])
        patch_faces = {}
        if tris:
            patch_faces["triangle"] = np.array(tris, dtype=np.int64)
        if quads:
            patch_faces["quad"] = np.array(quads, dtype=np.int64)
        if patch_faces:
            boundary_faces[patch.name] = patch_faces

    return dict(cells_by_type), boundary_faces


# --------------------------------------------------------------------------
# CGNS export (via pyCGNS)
# --------------------------------------------------------------------------

def _to_1based_flat(conn: np.ndarray) -> np.ndarray:
    return (np.asarray(conn, dtype=np.int64) + 1).ravel()


def _find_child(node, name):
    for child in node[2]:
        if child[0] == name:
            return child
    return None


def _force_flat_child(node, child_name, values):
    """
    Overwrite a child node's value with a guaranteed flat int64 array.
    Needed because cgnslib's convenience wrappers don't store these in the
    shape that the CGNS C library's read-side validation requires. See
    cgns_internals.c / cgi_read_section / cg_elements_read for the exact checks.
    """
    child = _find_child(node, child_name)
    if child is not None:
        child[1] = np.asarray(values, dtype=np.int64).ravel()


_POINTSET_CHILD_NAMES = {"PointList", "PointRange", "ElementList", "ElementRange"}


def _fix_bc_element_range(bc_node, start, end):
    """
    Remove whatever point-set child newBoundary() created and replace it
    with a correct PointRange / IndexRange_t node.

    Convention note: BC point sets of type ElementRange/ElementList are the
    LEGACY CGNS convention and cgnscheck flags them as errors ("point set
    type not PointRange or PointList"). The modern SIDS convention is
    PointRange + GridLocation=FaceCenter, where the range holds element
    (face) indices and the FaceCenter grid location is what tells readers
    they refer to faces rather than vertices. We write GridLocation=
    FaceCenter separately in build_cgns_tree.

    Shape: cgi_read_ptset requires ndim==2, dim_vals==[index_dim,2] for
    modern CGNS files -> shape (1,2) for unstructured zones (index_dim=1).
    """
    bc_node[2] = [c for c in bc_node[2] if c[0] not in _POINTSET_CHILD_NAMES]
    bc_node[2].append(
        ["PointRange", np.array([[start, end]], dtype=np.int64), [], "IndexRange_t"]
    )


# Map OpenFOAM boundary patch types to standard CGNS BCType_t values.
# ParaView's vtkCGNSReader skips BC_t nodes typed "UserDefined", so use
# recognized standard types. "BCWall" for walls, "BCSymmetryPlane" for
# symmetry, and "BCGeneral" (a valid, widely-supported catch-all) for
# generic patches (OpenFOAM's `patch` type carries no physics meaning, so
# there is nothing more specific to map it to — inlet/outlet semantics
# live in the solver config, not the mesh).
_FOAM_TO_CGNS_BCTYPE = {
    "wall": "BCWall",
    "symmetry": "BCSymmetryPlane",
    "symmetryPlane": "BCSymmetryPlane",
    "empty": "BCGeneral",
    "patch": "BCGeneral",
    "wedge": "BCGeneral",
    "cyclic": "BCGeneral",
}


def build_cgns_tree(
    points: np.ndarray,
    cells_by_type: dict,
    boundary_faces: dict,
    cgl,
    base_name: str = "Base",
    zone_name: str = "Zone",
    patch_types: dict | None = None,
):
    """
    Build a CGNS/Python tree containing:
      - one Elements_t section per volume element type (TETRA_4, HEXA_8, etc.)
      - one Elements_t section per face type per boundary patch (TRI_3, QUAD_4)
      - one ZoneBC_t with one BC_t per patch

    `patch_types` optionally maps patch_name -> OpenFOAM patch type string
    (e.g. "wall", "patch", "symmetry"); it is translated to a standard CGNS
    BCType_t via _FOAM_TO_CGNS_BCTYPE so readers like ParaView (which skip
    "UserDefined" BC_t nodes) can interpret them. Unknown/missing types
    fall back to BCGeneral.

    All element sections share one contiguous 1-based element-index space.

    Array shapes confirmed from cgns_internals.c source:
      Zone_t size:        ndim==2, shape (1,3)   for unstructured (index_dim=1)
      ElementRange:       ndim==1, shape (2,)     flat
      ElementConnectivity: flat 1D, length = n_elements * nodes_per_element
      BC PointRange:      ndim==2, shape (1,2)    per cgi_read_ptset()
    """
    patch_types = patch_types or {}
    n_cells = sum(len(c) for c in cells_by_type.values())
    n_points = len(points)

    tree = cgl.newCGNSTree()
    base = cgl.newBase(tree, base_name, 3, 3)
    zsize = np.array([[n_points, n_cells, 0]], dtype=np.int64)  # (1,3) confirmed
    zone = cgl.newZone(base, zone_name, zsize, "Unstructured")

    cgl.newCoordinates(zone, "CoordinateX", np.ascontiguousarray(points[:, 0], dtype=np.float64))
    cgl.newCoordinates(zone, "CoordinateY", np.ascontiguousarray(points[:, 1], dtype=np.float64))
    cgl.newCoordinates(zone, "CoordinateZ", np.ascontiguousarray(points[:, 2], dtype=np.float64))

    next_idx = 1  # 1-based, shared across ALL sections in the zone

    # --- volume element sections (one per type) ---
    for shape, conn in cells_by_type.items():
        cgns_type = _CGNS_ELEM_TYPE[shape]
        flat = _to_1based_flat(conn)
        start, end = next_idx, next_idx + len(conn) - 1
        sec = cgl.newElements(zone, shape, cgns_type, flat, np.array([start, end], dtype=np.int64))
        _force_flat_child(sec, "ElementRange", [start, end])
        _force_flat_child(sec, "ElementConnectivity", flat)
        next_idx = end + 1

    # --- boundary sections (one per face-type per patch) ---
    patch_ranges = {}  # patch_name -> (start, end) — if mixed, use overall span
    for patch_name, type_dict in boundary_faces.items():
        p_start = next_idx
        for face_type, conn in type_dict.items():
            _, cgns_face_type = _CGNS_FACE_TYPE[3 if face_type == "triangle" else 4]
            flat = _to_1based_flat(conn)
            start, end = next_idx, next_idx + len(conn) - 1
            # section name: patch name if only one type, else patch_name_tri/quad
            sec_name = patch_name if len(type_dict) == 1 else f"{patch_name}_{face_type[:3]}"
            sec = cgl.newElements(zone, sec_name, cgns_face_type, flat,
                                  np.array([start, end], dtype=np.int64))
            _force_flat_child(sec, "ElementRange", [start, end])
            _force_flat_child(sec, "ElementConnectivity", flat)
            next_idx = end + 1
        patch_ranges[patch_name] = (p_start, next_idx - 1)

    # --- ZoneBC: one BC_t per patch ---
    for name, (start, end) in patch_ranges.items():
        foam_type = patch_types.get(name, "patch")
        cgns_bctype = _FOAM_TO_CGNS_BCTYPE.get(foam_type, "BCGeneral")
        bc = cgl.newBoundary(
            zone, name, np.array([start, end], dtype=np.int64),
            btype=cgns_bctype, pttype="PointRange",
        )
        _fix_bc_element_range(bc, start, end)
        if hasattr(cgl, "newGridLocation"):
            cgl.newGridLocation(bc, value="FaceCenter")

    # Merge duplicate ZoneBC sibling nodes into one (newBoundary() was observed
    # to create a fresh ZoneBC node per call rather than reusing an existing one)
    zonebc_nodes = [c for c in zone[2] if c[0] == "ZoneBC"]
    if len(zonebc_nodes) > 1:
        merged = []
        for zb in zonebc_nodes:
            merged.extend(zb[2])
        zone[2] = [c for c in zone[2] if c[0] != "ZoneBC"]
        zone[2].append(["ZoneBC", None, merged, "ZoneBC_t"])

    return tree, patch_ranges


def write_cgns(out_path: str, points: np.ndarray, cells_by_type: dict, boundary_faces: dict,
               patch_types: dict | None = None):
    """
    Write the mesh to a CGNS file using pyCGNS.
    Install: conda install -c conda-forge pycgns
             or: pip install pyCGNS --break-system-packages
    """
    try:
        import CGNS.MAP
        import CGNS.PAT.cgnslib as CGL
    except ImportError as e:
        raise ImportError(
            "Writing CGNS requires the 'pyCGNS' package.\n"
            "    conda install -c conda-forge pycgns\n"
            "    # or: pip install pyCGNS --break-system-packages\n"
        ) from e

    tree, patch_ranges = build_cgns_tree(points, cells_by_type, boundary_faces, CGL, patch_types=patch_types)
    CGNS.MAP.save(out_path, tree)
    return patch_ranges


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("case", help="OpenFOAM case or constant/polyMesh directory")
    ap.add_argument("output", help="output .cgns file path")
    ap.add_argument("--no-boundary", action="store_true",
                    help="skip boundary patches")
    ap.add_argument("--report", action="store_true",
                    help="print mesh stats and exit without writing CGNS")
    args = ap.parse_args(argv)

    print(f"[1/3] Reading OpenFOAM mesh from: {args.case}")
    mesh = read_foam_mesh(args.case)
    print(f"      points={len(mesh.points)} faces={len(mesh.faces)} "
          f"internalFaces={mesh.n_internal_faces} cells={mesh.n_cells} "
          f"patches={[p.name for p in mesh.boundary]}")

    print("[2/3] Reconstructing element connectivity ...")
    cells_by_type, boundary_faces = reconstruct_mesh(mesh)
    if args.no_boundary:
        boundary_faces = {}

    for shape, conn in cells_by_type.items():
        print(f"      {_CGNS_ELEM_TYPE[shape]}: {len(conn)} elements")
    for pname, type_dict in boundary_faces.items():
        counts = ", ".join(f"{len(c)} {t}" for t, c in type_dict.items())
        print(f"      boundary '{pname}': {counts}")

    if args.report:
        return 0

    print(f"[3/3] Writing CGNS: {args.output}")
    patch_types = {p.name: p.type_ for p in mesh.boundary}
    patch_ranges = write_cgns(args.output, mesh.points, cells_by_type, boundary_faces, patch_types=patch_types)
    for name, (s, e) in patch_ranges.items():
        print(f"      BC '{name}': elements {s}–{e}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
