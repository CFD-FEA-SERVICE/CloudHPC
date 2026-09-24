"""Known cloudHPC / solver messages and how to fix them.

Source: https://docs.cloudhpc.cloud/errors/  A run can end as COMPLETED even
when the solver failed, so the simulation output must always be checked.
"""

from __future__ import annotations

import glob
import os
import re
from typing import Any

DOCS = "https://docs.cloudhpc.cloud/errors/"

# id, severity, regex (case-insensitive), cause, fix, docs anchor
CATALOG: list[dict[str, str]] = [
    # ---------------------------------------------------------------- RAM
    {"id": "ram_high", "severity": "warning",
     "pattern": r"RAM used > \d+(\.\d+)?%",
     "cause": "RAM usage above 80%: the run may soon fail for lack of memory.",
     "fix": "Increase vCPU or move to the next RAM tier (highcpu -> standard -> highmem).",
     "anchor": "low_ram_available"},
    {"id": "ram_out", "severity": "error",
     "pattern": r"SWAP unresolved after \d+ attempts|KILLED BY SIGNAL: 9|Unable to allocate .* bytes|"
                r"out of memory|Cannot allocate memory|std::bad_alloc|oom[- ]kill",
     "cause": "The run ran out of RAM.",
     "fix": "Relaunch with more RAM: next tier (highcpu -> standard -> highmem) or more vCPU. "
            "1 vCPU has too little RAM for engineering solvers.",
     "anchor": "low_ram_available"},
    # --------------------------------------------------------------- disk
    {"id": "disk_80", "severity": "warning",
     "pattern": r"HARD DISK used > 80",
     "cause": "Disk above 80%. At 90% cloudHPC soft-stops the run automatically.",
     "fix": "Write fewer/lighter outputs (e.g. lower output frequency) or soft stop the run to "
            "keep the data produced so far.",
     "anchor": "hard_disk_use"},
    {"id": "disk_90", "severity": "error",
     "pattern": r"HARD DISK used > 90|AUTOMATIC SOFT STOP",
     "cause": "Disk above 90%: cloudHPC soft-stopped the run.",
     "fix": "Reduce the amount of output written by the solver and relaunch.",
     "anchor": "hard_disk_use"},
    # ------------------------------------------------------------- upload
    {"id": "archive_folder", "severity": "error",
     "pattern": r"Not found folder .* inside of compressed file",
     "cause": "The archive layout does not match the upload method.",
     "fix": "Either archive a folder named exactly like the archive and upload it to the storage "
            "root, or archive the files directly (no wrapping folder) and upload into a folder. "
            "upload_folder uses the second method automatically.",
     "anchor": "incorrect_compressed_file"},
    {"id": "folder_name", "severity": "error",
     "pattern": r"FOLDER .* not detected|not recognized as an available compressed format",
     "cause": "Folder/file name not accepted or archive format not supported.",
     "fix": "Remove special characters , ( ) ' $ ~ \" # from folder/file names; use zip, "
            "tar.gz, 7z, rar or xz.",
     "anchor": "incorrect_file_or_folder_name"},
    # ---------------------------------------------------------------- FDS
    {"id": "fds_missing", "severity": "error",
     "pattern": r"No FDS file detected",
     "cause": "No .fds file in the case folder.",
     "fix": "Upload the .fds input (exported from your pre-processor) in the case folder.",
     "anchor": "fds_incorrect_settings"},
    {"id": "fds_psm", "severity": "error",
     "pattern": r"is a pyrosim file",
     "cause": "A PyroSim .psm file was uploaded instead of the .fds input.",
     "fix": "Export the .fds file from PyroSim and upload that.",
     "anchor": "pyrosim_input_file"},
    {"id": "fds_mpi_order", "severity": "error",
     "pattern": r"MPI_PROCESS parameter must be in ASCENDING ORDER|MPI_MPI_PROCESS incorrect",
     "cause": "&MESH lines are not ordered by MPI_PROCESS.",
     "fix": "Reorder the &MESH lines so MPI_PROCESS values are ascending.",
     "anchor": "scalability_issue_with_mpi_process"},
    {"id": "fds_low_vcpu", "severity": "error",
     "pattern": r"low vCPU selected|Number of MESHES higher than available CORES",
     "cause": "More meshes/MPI groups than CPU cores.",
     "fix": "Increase vCPU (on highcpu/standard/highmem/hypercpu cores = vCPU/2) or group "
            "meshes with MPI_PROCESS.",
     "anchor": "scalability_issue_with_mpi_process"},
    {"id": "fds_warnings", "severity": "warning",
     "pattern": r"no other WARNING messages showed",
     "cause": "FDS printed many warnings (often objects or devices outside every mesh).",
     "fix": "Check the solver log (<CHID>.out / .log) and fix the geometry/devices.",
     "anchor": "warning_messages_by_fds"},
    {"id": "fds_threads", "severity": "warning",
     "pattern": r"high number of threads used",
     "cause": "Too few meshes for the vCPU selected: poor scalability.",
     "fix": "Split the mesh into more &MESH or select fewer vCPU.",
     "anchor": "high_number_of_threads"},
    {"id": "fds_pressure_zones", "severity": "warning",
     "pattern": r"high number of Pressure Zones",
     "cause": "Many pressure zones: the run may scale poorly.",
     "fix": "Add MINIMUM_ZONE_VOLUME=1.0 to &MISC (NO_PRESSURE_ZONES=T only for debugging).",
     "anchor": "high_number_of_pressure_zones"},
    {"id": "fds_devc_amd", "severity": "warning",
     "pattern": r"DEVC for .* may slow down your simulation",
     "cause": "VISIBILITY / RADIATIVE HEAT FLUX / GAUGE HEAT FLUX GAS devices slow down AMD CPUs.",
     "fix": "Run on hypercpu or hypercore (Intel) instances.",
     "anchor": "devc_affecting_performances"},
    # ----------------------------------------------------------- OpenFOAM
    {"id": "of_controldict", "severity": "error",
     "pattern": r"Cannot find system/controlDict",
     "cause": "system/controlDict not found: case uploaded with the wrong layout.",
     "fix": "The case folder must contain 0, constant and system at its root.",
     "anchor": "incorrect_dictionary"},
    {"id": "of_nproc", "severity": "error",
     "pattern": r"(openFoam|snappy) script runs with nProc > 1",
     "cause": "OpenFOAM always runs in parallel on cloudHPC.",
     "fix": "Select at least 2 vCPU on highcore/hypercore (4 on highcpu/standard/highmem).",
     "anchor": "multi-core_analysis"},
    {"id": "of_snappy", "severity": "error",
     "pattern": r"snappyHexMesh failure",
     "cause": "snappyHexMesh failed (RAM, STL geometry, settings).",
     "fix": "Read log.snappyHexMesh in the results; if it is a memory problem use more RAM.",
     "anchor": "snappyhexmesh_general_error"},
    {"id": "of_polymesh", "severity": "warning",
     "pattern": r"polyMesh folder not found",
     "cause": "constant/polyMesh missing: the solver has no mesh.",
     "fix": "Upload the mesh, generate it in the same run, or pass a mesh folder at launch.",
     "anchor": "general_problem_with_openfoam_solver"},
    {"id": "of_decompose", "severity": "error",
     "pattern": r"incorrect decomposeParDict file",
     "cause": "decomposeParDict not in the expected form: vCPU not applied automatically.",
     "fix": "Use method scotch (or hierarchical); template: "
            "https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/OpenFOAM/system/decomposeParDict",
     "anchor": "decomposepardict"},
    {"id": "of_startfrom", "severity": "info",
     "pattern": r"suggested to use startFrom latestTime",
     "cause": "controlDict startFrom is not latestTime (changed automatically).",
     "fix": "Set 'startFrom latestTime;' in system/controlDict.",
     "anchor": "controldict"},
    # -------------------------------------------------------- code_aster
    {"id": "ca_export", "severity": "error",
     "pattern": r"no export file detected",
     "cause": "code_aster .export file missing.",
     "fix": "Upload .export, .comm and the .med/.unv mesh (see the code_aster template).",
     "anchor": "export_file_missing"},
]

_COMPILED = [(e, re.compile(e["pattern"], re.IGNORECASE)) for e in CATALOG]


def diagnose(text: str) -> list[dict[str, Any]]:
    """Return catalogue entries found in a simulation output/log."""
    found = []
    for entry, rx in _COMPILED:
        m = rx.search(text or "")
        if m:
            line = next((ln.strip() for ln in (text or "").splitlines() if rx.search(ln)), m.group(0))
            found.append({
                "id": entry["id"], "severity": entry["severity"], "matched": line[:200],
                "cause": entry["cause"], "fix": entry["fix"],
                "docs": f"{DOCS}#{entry['anchor']}",
            })
    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(found, key=lambda f: order[f["severity"]])


# --------------------------------------------------------- pre-flight checks

INVALID_NAME_CHARS = set(",()'$~\"#*?")


def bad_name(name: str) -> list[str]:
    return sorted({c for c in name if c in INVALID_NAME_CHARS or c.isspace()})


def preflight(info: dict[str, Any]) -> list[dict[str, str]]:
    """Checks on a local case (output of advisor.inspect_case) before upload."""
    issues: list[dict[str, str]] = []
    folder = info["folder"]

    def add(severity, msg, anchor):
        issues.append({"severity": severity, "issue": msg, "docs": f"{DOCS}#{anchor}"})

    chars = bad_name(info["storage_name"])
    if chars:
        add("error", f"Folder name contains characters not accepted by cloudHPC: {' '.join(chars)} "
                     "(spaces included). Rename it or pass another storage_folder.",
            "incorrect_file_or_folder_name")

    fam = info.get("family")
    if glob.glob(os.path.join(folder, "*.psm")) and fam != "fds":
        add("error", "Only a PyroSim .psm file found: export and upload the .fds file.",
            "pyrosim_input_file")

    if fam == "fds":
        fds = info.get("fds", {})
        path = os.path.join(folder, fds.get("file", ""))
        try:
            with open(path, "r", errors="replace") as f:
                text = f.read()
            order = [int(x) for x in re.findall(r"&MESH\b[^/]*?\bMPI_PROCESS\s*=\s*(\d+)", text,
                                                 re.IGNORECASE | re.DOTALL)]
            if order and order != sorted(order):
                add("error", "MPI_PROCESS values are not in ascending order: reorder the &MESH lines.",
                    "scalability_issue_with_mpi_process")
            if re.search(r"\b(VISIBILITY|RADIATIVE HEAT FLUX|GAUGE HEAT FLUX GAS)\b", text, re.IGNORECASE):
                add("warning", "DEVC with VISIBILITY / RADIATIVE HEAT FLUX / GAUGE HEAT FLUX GAS slow "
                               "down AMD CPUs: prefer hypercpu/hypercore if delivery time matters.",
                    "devc_affecting_performances")
            if not re.search(r"MINIMUM_ZONE_VOLUME", text, re.IGNORECASE):
                add("info", "Consider MINIMUM_ZONE_VOLUME=1.0 in &MISC to avoid many pressure zones.",
                    "high_number_of_pressure_zones")
        except OSError:
            pass

    if fam == "openfoam":
        if not os.path.isdir(os.path.join(folder, "constant", "polyMesh")):
            add("warning", "constant/polyMesh not found: generate the mesh in the run "
                           "(snappyHexMesh/cfMesh) or pass a mesh folder at launch.",
                "general_problem_with_openfoam_solver")
        dpd = os.path.join(folder, "system", "decomposeParDict")
        if os.path.exists(dpd):
            with open(dpd, "r", errors="replace") as f:
                m = re.search(r"^\s*method\s+(\w+)\s*;", f.read(), re.MULTILINE)
            if m and m.group(1) not in ("scotch", "hierarchical"):
                add("error", f"decomposeParDict method is '{m.group(1)}': use scotch or hierarchical "
                             "so cloudHPC can set the subdomains.", "decomposepardict")
        cd = os.path.join(folder, "system", "controlDict")
        if os.path.exists(cd):
            with open(cd, "r", errors="replace") as f:
                m = re.search(r"^\s*startFrom\s+(\w+)\s*;", f.read(), re.MULTILINE)
            if m and m.group(1) != "latestTime":
                add("info", f"startFrom is '{m.group(1)}': cloudHPC sets it to latestTime.",
                    "controldict")
        if not (os.path.isdir(os.path.join(folder, "0")) or os.path.isdir(os.path.join(folder, "0.orig"))):
            add("warning", "No 0/ (or 0.orig/) folder with initial conditions.", "incorrect_dictionary")

    if fam == "code_aster":
        if not glob.glob(os.path.join(folder, "*.export")):
            add("error", "No .export file: code_aster needs .export, .comm and .med/.unv.",
                "export_file_missing")
        if not (glob.glob(os.path.join(folder, "*.med")) or glob.glob(os.path.join(folder, "*.unv"))):
            add("warning", "No .med or .unv mesh found in the folder.", "code_aster_settings")

    return issues
