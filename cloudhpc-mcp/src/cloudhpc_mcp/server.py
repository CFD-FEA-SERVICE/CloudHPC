"""cloudHPC MCP server.

Two modes, same code:
  local  (stdio)            runs on the user's PC; can zip/upload local folders
                            and download/extract results. API key from
                            CLOUDHPC_APIKEY or ~/.cfscloudhpc/apikey.
  remote (streamable-http)  runs on a server (e.g. Cloud Run); stateless; the
                            API key comes with each request in the X-API-Key
                            or Authorization: Bearer header. File transfers
                            are done by the client with signed URLs.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from . import advisor, errors, files
from .client import ACTIVE_STATUSES, STATUS, CloudHPCClient, CloudHPCError

MODE = os.environ.get("CLOUDHPC_MCP_MODE", "local").lower()  # local | remote
LOCAL = MODE == "local"

INSTRUCTIONS = """\
cloudHPC runs engineering simulations (FDS, OpenFOAM, code_aster, CalculiX,
OpenRadioss, SU2, ...) on cloud machines. Typical workflow:

1. Understand the case. In local mode call inspect_case on the user's folder:
   it detects the solver and the model size (FDS meshes, OpenFOAM cells, ...).
2. Choose the solver version with list_solvers and the resources with
   suggest_resources. Explain the suggestion briefly (vCPU, RAM type, why).
   RAM types: highcpu < standard < highmem use the same CPUs with 1 to 8 GB
   per vCPU and hyperthreading; highcore/hypercore use physical cores only
   (hypercore = faster CPU generation). OpenFOAM and other MPI-only solvers
   must use highcore or hypercore. For FDS/CalculiX/code_aster start on
   highcpu and move to standard, then highmem, only after a memory error.
3. Upload: local mode -> upload_folder (tar.gz of the folder content into a
   storage folder with the same name). Remote mode -> get_upload_link and
   give the user the curl command.
4. Launch with launch_simulation. It costs money: always show the user the
   summary returned by the first call and only then call again with
   confirm=true.
5. Monitor with get_simulation / wait_for_simulation. Status codes:
   10 COMPLETED, 20 PENDING, 30 RUNNING, 40 STOPPING, 50 STOPPED, 60 ERROR.
   sync_simulation uploads partial results of a running job.
   When a run ends, check the diagnosis (wait_for_simulation adds it, or
   get_simulation(include_log=true)): a run can be COMPLETED even if the
   solver failed. Each diagnosis item has cause, fix and docs link. When it
   reports memory_error, relaunch on the suggested RAM tier. Never use
   1 vCPU on highcpu for engineering solvers (not enough RAM to start).
   The solver's own log (e.g. <CHID>.log for FDS) is also in the storage
   folder and in the downloaded results.
6. Results are archives in the same storage folder (FDS.tar.gz,
   OPENFOAM-solution.tar.gz, CALCULIX.tar.gz, ...). list_results then
   download_results (local) or get_download_link (remote).

Storage files are deleted automatically after 60 days: remind the user to
download results. Avoid needless calls: the API is rate limited
(100 calls/hour on free accounts, 500 on full accounts).
"""

mcp = FastMCP(
    "cloudHPC",
    instructions=INSTRUCTIONS,
    host=os.environ.get("HOST", "0.0.0.0" if not LOCAL else "127.0.0.1"),
    port=int(os.environ.get("PORT", "8080")),
    stateless_http=True,
    json_response=True,
)

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)


# ------------------------------------------------------------------ helpers

def _local_api_key() -> str:
    key = os.environ.get("CLOUDHPC_APIKEY", "").strip()
    if key:
        return key
    keyfile = Path.home() / ".cfscloudhpc" / "apikey"  # shared with cloudHPCexec
    try:
        return keyfile.read_text().splitlines()[0].strip()
    except (OSError, IndexError):
        return ""


def _remote_api_key(ctx: Context | None) -> str:
    request = getattr(getattr(ctx, "request_context", None), "request", None) if ctx else None
    if request is None:
        return ""
    headers = request.headers
    key = headers.get("x-api-key", "")
    if not key:
        auth = headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            key = auth[7:]
    return key.strip()


def client_for(ctx: Context | None) -> CloudHPCClient:
    key = _local_api_key() if LOCAL else _remote_api_key(ctx)
    return CloudHPCClient(api_key=key)


def _sim_summary(s: dict) -> dict:
    status = s.get("status")
    return {
        "id": s.get("id"),
        "status": STATUS.get(status, str(status)),
        "status_code": status,
        "solver": s.get("script"),
        "cpu": s.get("cpu"),
        "ram": s.get("ram"),
        "regular_instance": bool(s.get("nopre")),
        "folder": s.get("folder"),
        "mesh_folder": s.get("mesh") or None,
        "submitted": s.get("idate") or None,
        "ended": s.get("edate") or None,
        "cpu_hours": s.get("cpu_hrs") or None,
        "cost": s.get("cost") or None,
    }


def _storage_item(i: dict) -> dict:
    out = {"name": i.get("basename"), "path": i.get("name"), "type": i.get("type")}
    if i.get("type") == "file":
        size = i.get("size")
        out["size_mb"] = round(int(size) / 1e6, 2) if str(size).isdigit() else None
        out["created"] = i.get("timeCreated") or None
    return out


def _diagnosis(s: dict) -> dict:
    """Scan the simulation output/log for known errors (docs.cloudhpc.cloud/errors)."""
    text = "\n".join(str(s.get(k) or "") for k in ("output", "logs"))
    found = errors.diagnose(text)
    out: dict[str, Any] = {}
    if found:
        out["diagnosis"] = found
    if any(f["id"] in ("ram_out", "ram_high") for f in found):
        nxt = advisor.next_ram(s.get("ram", ""))
        out["memory_error"] = any(f["id"] == "ram_out" for f in found)
        out["suggestion"] = (
            f"Relaunch the same case with the same vCPU on '{nxt}'." if nxt else
            "Increase vCPU (RAM grows with vCPU) or reduce the model size.")
    if s.get("status") == 10 and any(f["severity"] == "error" for f in found):
        out["warning"] = ("Status is COMPLETED but the output contains errors: the solver "
                          "probably did not finish correctly.")
    # FDS prints a definite success line; check it when the solver log is in the output
    if advisor.family_of(str(s.get("script", ""))) == "fds" and "Starting FDS" in text:
        ok = "FDS completed successfully" in text
        out["solver_finished_ok"] = ok
        if s.get("status") == 10 and not ok:
            out.setdefault("warning", "Status is COMPLETED but FDS did not print 'STOP: FDS "
                                      "completed successfully': check <CHID>.out in the results.")
    return out


def _err(e: Exception) -> dict:
    return {"error": str(e)}


# ------------------------------------------------------------ discovery

@mcp.tool(annotations=READ)
async def list_solvers(search: str | None = None, ctx: Context = None) -> dict:
    """List the solvers/scripts available on cloudHPC, grouped by family.

    search: optional case-insensitive substring (e.g. "openfoam", "fds6.9").
    """
    try:
        scripts = await client_for(ctx).scripts()
    except CloudHPCError as e:
        return _err(e)
    if search:
        scripts = [s for s in scripts if search.lower() in s.lower()]
    return {"solvers": advisor.group_scripts(scripts)}


@mcp.tool(annotations=READ)
async def list_machine_options(ctx: Context = None) -> dict:
    """List the vCPU counts and RAM/instance types that can be requested."""
    try:
        c = client_for(ctx)
        cpus, rams = await asyncio.gather(c.cpu_options(), c.ram_options())
    except CloudHPCError as e:
        return _err(e)
    return {
        "vcpu": cpus,
        "ram_types": rams,
        "ram_guide": {
            "highcpu": "cheapest, ~1 GB/vCPU, hyperthreading",
            "standard": "same CPUs, more RAM per vCPU",
            "highmem": "same CPUs, up to 8 GB/vCPU",
            "highcore": "physical cores only (no hyperthreading) - for MPI solvers like OpenFOAM",
            "hypercpu": "newer/faster CPU generation, hyperthreading",
            "hypercore": "newer/faster CPU generation, physical cores only",
            "basegpu": "GPU instance",
        },
    }


@mcp.tool(annotations=READ)
async def suggest_resources(
    solver: str,
    cells: int | None = None,
    nodes: int | None = None,
    elements: int | None = None,
    fds_meshes: int | None = None,
    fds_mpi_groups: int | None = None,
    fds_total_cells: int | None = None,
    case_folder: str | None = None,
    prefer_speed: bool = False,
    ctx: Context = None,
) -> dict:
    """Suggest vCPU and RAM type for a run, following cloudHPC scalability rules.

    solver: script name (e.g. "fds6.9.1", "openFoam-v2406") or family
            ("fds", "openfoam", "calculix", "code_aster", "openradioss", "su2").
    cells: CFD cells (OpenFOAM/SU2). nodes: FEA nodes (CalculiX/code_aster).
    elements: OpenRadioss elements.
    fds_*: FDS mesh info if the .fds file cannot be read directly.
    case_folder: (local mode) folder to inspect automatically instead.
    prefer_speed: favour the faster hypercore/hypercpu instances over cost.
    """
    family = solver if solver in advisor.FAMILIES else advisor.family_of(solver)
    fds_info = None
    if case_folder and LOCAL:
        try:
            info = advisor.inspect_case(case_folder)
        except FileNotFoundError as e:
            return _err(e)
        family = info["family"] if info["family"] != "other" else family
        fds_info = info.get("fds")
        cells = cells or info.get("cells")
        nodes = nodes or info.get("nodes")
    elif family == "fds" and (fds_meshes or fds_mpi_groups):
        groups = fds_mpi_groups or fds_meshes
        fds_info = {"meshes": fds_meshes or groups, "mpi_groups": groups,
                    "total_cells": fds_total_cells or 0,
                    "cells_per_group": [], "uses_mpi_process": bool(fds_mpi_groups),
                    "uses_mult_id": False}
    try:
        c = client_for(ctx)
        cpus, rams = await asyncio.gather(c.cpu_options(), c.ram_options())
    except CloudHPCError as e:
        return _err(e)
    return advisor.suggest(family, cpus, rams, cells=cells, nodes=nodes,
                           elements=elements, fds=fds_info, prefer_speed=prefer_speed)


# -------------------------------------------------------------- storage

@mcp.tool(annotations=READ)
async def list_storage(folder: str = "", ctx: Context = None) -> dict:
    """List files and folders in the user's cloudHPC storage.

    folder: storage folder path ("" = root, e.g. "myCase" or "myCase/sub").
    """
    try:
        items = await client_for(ctx).list_storage(folder)
    except CloudHPCError as e:
        return _err(e)
    return {"folder": folder or "/", "items": [_storage_item(i) for i in items],
            "note": "Files are deleted automatically 60 days after creation."}


@mcp.tool(annotations=READ)
async def list_results(folder: str, ctx: Context = None) -> dict:
    """List the result archives of a case folder (FDS.tar.gz, OPENFOAM-*.tar.gz, ...)."""
    try:
        items = await client_for(ctx).list_storage(folder)
    except CloudHPCError as e:
        return _err(e)
    results = [_storage_item(i) for i in items
               if i.get("type") == "file" and files.is_result_file(i.get("name", ""))]
    out: dict[str, Any] = {"folder": folder, "results": results}
    if not results:
        out["note"] = ("No result archives yet. They are written at the end of the run, "
                       "every 10 hours while running, or after sync_simulation.")
    return out


@mcp.tool(annotations=READ)
async def get_download_link(path: str, ctx: Context = None) -> dict:
    """Get a temporary download link for a storage file (e.g. "myCase/FDS.tar.gz")."""
    try:
        url = await client_for(ctx).download_url(path)
    except CloudHPCError as e:
        return _err(e)
    name = os.path.basename(path)
    return {"path": path, "url": url,
            "curl": f"curl -L -o '{name}' '{url}'",
            "note": "The link is temporary and gives access to this file: do not share it."}


@mcp.tool(annotations=WRITE)
async def get_upload_link(storage_folder: str, filename: str, ctx: Context = None) -> dict:
    """Get a signed URL to upload one file into a storage folder (remote clients).

    For a case folder: compress the CONTENT of the folder (files at the archive
    root, no wrapping folder) into e.g. upload.tar.gz or case.zip, then upload it
    into a storage folder with the case name. Accepted: zip, tar.gz, 7z, rar, xz.
    """
    try:
        c = client_for(ctx)
        url = await c.upload_url(storage_folder, filename)
    except CloudHPCError as e:
        return _err(e)
    return {
        "storage_path": f"{storage_folder.strip('/')}/{filename}",
        "url": url,
        "curl": f"curl -X PUT -H 'Content-Type: application/octet-stream' "
                f"--upload-file '{filename}' '{url}'",
        "compress_hint": {
            "linux_mac": "cd CASE_FOLDER && tar -czf ../upload.tar.gz *",
            "windows_powershell": "Compress-Archive -Path CASE_FOLDER\\* -DestinationPath case.zip",
        },
        "note": "Upload the raw file (not multipart form). The link expires.",
    }


@mcp.tool(annotations=DESTRUCTIVE)
async def delete_storage(path: str, confirm: bool = False, ctx: Context = None) -> dict:
    """Delete a file or folder from storage. Irreversible.

    Call first with confirm=false to get the summary, show it to the user, and
    call again with confirm=true only after the user explicitly agrees.
    """
    c = client_for(ctx)
    try:
        info = await c.view_by_path(path)
    except CloudHPCError as e:
        return _err(e)
    if not confirm:
        return {"confirmation_required": True,
                "summary": f"Delete {info.get('type', 'item')} '{path}' from cloudHPC storage. "
                           "This cannot be undone."}
    try:
        await c.delete_path(path)
    except CloudHPCError as e:
        return _err(e)
    return {"deleted": path}


# ----------------------------------------------------------- simulations

@mcp.tool(annotations=WRITE)
async def launch_simulation(
    solver: str,
    cpu: int,
    ram: str,
    folder: str,
    mesh_folder: str | None = None,
    regular_instance: bool = False,
    confirm: bool = False,
    ctx: Context = None,
) -> dict:
    """Launch a simulation on a case folder already in storage. Costs money.

    solver: exact script name from list_solvers (e.g. "fds6.9.1").
    cpu / ram: from suggest_resources or list_machine_options.
    folder: storage folder with the case.
    mesh_folder: optional storage folder with a mesh to reuse (OpenFOAM).
    regular_instance: non-preemptible machine (more expensive, no interruptions).
    Call first with confirm=false, show the returned summary to the user, and
    call again with confirm=true only after explicit approval.
    """
    c = client_for(ctx)
    try:
        cpus, rams, scripts = await asyncio.gather(c.cpu_options(), c.ram_options(), c.scripts())
    except CloudHPCError as e:
        return _err(e)
    problems = []
    if solver not in scripts:
        close = [s for s in scripts if solver.lower().split("-")[0] in s.lower()][:10]
        problems.append(f"Unknown solver '{solver}'. Similar: {close}")
    if cpu not in cpus:
        problems.append(f"vCPU {cpu} not available. Options: {cpus}")
    if ram not in rams:
        problems.append(f"RAM type '{ram}' not available. Options: {rams}")
    fam = advisor.family_of(solver)
    chars = errors.bad_name(folder)
    if chars:
        problems.append(f"Folder name '{folder}' contains characters cloudHPC does not accept: "
                        f"{' '.join(chars)}")
    if fam == "openfoam" and cpu < (2 if ram in advisor.PHYSICAL_RAM else 4):
        problems.append("OpenFOAM always runs in parallel on cloudHPC: at least 2 vCPU on "
                        "highcore/hypercore.")
    if cpu == 1 and ram == "highcpu" and fam != "other":
        problems.append("1 vCPU highcpu has too little RAM for engineering solvers and fails "
                        "at start-up: use standard (or more vCPU).")
    if fam in advisor.NO_HYPERTHREAD and ram not in advisor.PHYSICAL_RAM:
        problems.append(f"{solver} does not use hyperthreading: use highcore or hypercore.")
    if problems:
        return {"error": "Invalid launch parameters", "problems": problems}

    summary = (f"Run {solver} on {cpu} vCPU ({ram}"
               f"{', regular instance' if regular_instance else ', preemptible'}) "
               f"using storage folder '{folder}'"
               f"{f' with mesh from {mesh_folder}' if mesh_folder else ''}. "
               "Billed per vCPU-hour until the run ends or is stopped.")
    if not confirm:
        return {"confirmation_required": True, "summary": summary}
    try:
        sim_id = await c.add_simulation(cpu, ram, solver, folder, mesh_folder, regular_instance)
    except CloudHPCError as e:
        return _err(e)
    return {"launched": True, "simulation_id": sim_id, "summary": summary,
            "next": "Use get_simulation or wait_for_simulation to follow it."}


@mcp.tool(annotations=READ)
async def list_simulations(
    status: Literal["active", "all", "completed", "error", "stopped"] = "active",
    limit: int = 20,
    ctx: Context = None,
) -> dict:
    """List the user's simulations, most recent first.

    status: "active" (pending/running/stopping), "all", "completed", "error", "stopped".
    """
    try:
        sims = await client_for(ctx).list_simulations()
    except CloudHPCError as e:
        return _err(e)
    wanted = {"active": ACTIVE_STATUSES, "completed": {10}, "error": {60}, "stopped": {50}}
    if status != "all":
        sims = [s for s in sims if s.get("status") in wanted[status]]
    sims = sorted(sims, key=lambda s: s.get("id", 0), reverse=True)[: max(1, min(limit, 100))]
    return {"simulations": [_sim_summary(s) for s in sims]}


@mcp.tool(annotations=READ)
async def get_simulation(simulation_id: int, include_log: bool = False, ctx: Context = None) -> dict:
    """Get status and details of a simulation.

    include_log: add the last output/log lines and a diagnosis of known cloudHPC
    errors and warnings with their fix. Use it whenever a run ends, since a run
    can be COMPLETED even if the solver failed.
    """
    c = client_for(ctx)
    try:
        s = await (c.get_simulation_full(simulation_id) if include_log else c.get_simulation(simulation_id))
    except CloudHPCError as e:
        return _err(e)
    out = _sim_summary(s)
    if include_log:
        for key in ("logs", "output"):
            text = s.get(key) or ""
            if text:
                out[key] = text[-4000:]
        out.update(_diagnosis(s))
    return out


@mcp.tool(annotations=READ)
async def wait_for_simulation(
    simulation_id: int,
    max_minutes: int = 10,
    poll_seconds: int = 120,
    ctx: Context = None,
) -> dict:
    """Wait until a simulation is no longer pending/running, or until max_minutes.

    Polls every poll_seconds (min 60, to respect API rate limits). If it
    returns still running, call it again later rather than looping quickly.
    """
    c = client_for(ctx)
    max_minutes = max(1, min(max_minutes, 30))
    poll_seconds = max(60, poll_seconds)
    deadline = time.monotonic() + max_minutes * 60
    while True:
        try:
            s = await c.get_simulation(simulation_id)
        except CloudHPCError as e:
            return _err(e)
        finished = s.get("status") not in ACTIVE_STATUSES
        if finished or time.monotonic() + poll_seconds > deadline:
            if finished:
                try:  # one extra call: COMPLETED runs can still contain errors
                    s = await c.get_simulation_full(simulation_id)
                except CloudHPCError:
                    pass
            out = _sim_summary(s)
            out["finished"] = finished
            if finished:
                out.update(_diagnosis(s))
            return out
        if ctx is not None:
            try:
                await ctx.report_progress(0, None, f"{STATUS.get(s.get('status'))}")
            except Exception:
                pass
        await asyncio.sleep(poll_seconds)


@mcp.tool(annotations=WRITE)
async def sync_simulation(simulation_id: int, ctx: Context = None) -> dict:
    """Ask a running simulation to upload partial results to storage now."""
    try:
        await client_for(ctx).sync_simulation(simulation_id)
    except CloudHPCError as e:
        return _err(e)
    return {"requested": True,
            "note": "Partial results appear in the case folder after a few minutes."}


@mcp.tool(annotations=DESTRUCTIVE)
async def stop_simulation(
    simulation_id: int,
    mode: Literal["soft", "hard"] = "soft",
    confirm: bool = False,
    ctx: Context = None,
) -> dict:
    """Stop a running simulation.

    soft: the solver stops cleanly and results are saved (recommended).
    hard: immediate termination.
    Call first with confirm=false and show the summary; confirm=true only after
    the user agrees.
    """
    c = client_for(ctx)
    try:
        s = await c.get_simulation(simulation_id)
    except CloudHPCError as e:
        return _err(e)
    summary = (f"{mode.upper()} stop of simulation {simulation_id} "
               f"({s.get('script')} on {s.get('cpu')} vCPU, folder '{s.get('folder')}', "
               f"status {STATUS.get(s.get('status'))}).")
    if s.get("status") not in ACTIVE_STATUSES:
        return {"error": f"Simulation is not active: {STATUS.get(s.get('status'))}"}
    if not confirm:
        return {"confirmation_required": True, "summary": summary}
    try:
        await c.stop_simulation(simulation_id, hard=(mode == "hard"))
    except CloudHPCError as e:
        return _err(e)
    return {"stopping": True, "summary": summary}


@mcp.tool(annotations=READ)
async def open_remote_desktop(simulation_id: int, ctx: Context = None) -> dict:
    """Get the browser remote-desktop (VNC) link of a running simulation.

    The link is short-lived and personal: give it only to the user.
    """
    try:
        s = await client_for(ctx).get_simulation(simulation_id)
    except CloudHPCError as e:
        return _err(e)
    if s.get("status") != 30 or not s.get("vnc_url"):
        return {"error": "Remote desktop is available only while the simulation is RUNNING."}
    return {"url": s["vnc_url"], "note": "Short-lived link; ask again if it expires."}


@mcp.tool(annotations=READ)
async def api_usage(ctx: Context = None) -> dict:
    """Show the API rate limits and how many calls have been used."""
    c = client_for(ctx)
    try:
        await c.ram_options()  # cheap call to read the rate-limit headers
    except CloudHPCError as e:
        return _err(e)
    return c.rate.as_dict()


# ---------------------------------------------------- local-only tools

if LOCAL:

    @mcp.tool(annotations=READ)
    async def inspect_case(folder: str) -> dict:
        """Inspect a local case folder: detect the solver and the model size.

        Reads .fds meshes (cells, MPI_PROCESS groups), OpenFOAM polyMesh cells,
        CalculiX nodes, code_aster mpi_nbcpu, and runs pre-flight checks for the
        most common cloudHPC errors (folder name, MPI_PROCESS order,
        decomposeParDict, missing files). Makes no API calls. Fix 'error'
        items before uploading.
        """
        try:
            info = advisor.inspect_case(folder)
        except (FileNotFoundError, OSError) as e:
            return _err(e)
        info["preflight"] = errors.preflight(info)
        return info

    @mcp.tool(annotations=WRITE)
    async def upload_folder(folder: str, storage_folder: str | None = None,
                            ctx: Context = None) -> dict:
        """Compress a local case folder and upload it to cloudHPC storage.

        The CONTENT of the folder goes into upload.tar.gz, uploaded into the
        storage folder storage_folder (default: the local folder name).
        Hidden files are skipped. Returns the storage folder to use in
        launch_simulation.
        """
        folder = os.path.abspath(os.path.expanduser(folder))
        if not os.path.isdir(folder):
            return _err(FileNotFoundError(f"Folder not found: {folder}"))
        if not os.listdir(folder):
            return _err(ValueError(f"Folder is empty: {folder}"))
        target = (storage_folder or os.path.basename(folder.rstrip(os.sep))).strip("/")
        chars = errors.bad_name(target)
        if chars:
            return {"error": f"Storage folder name '{target}' contains characters cloudHPC does "
                             f"not accept: {' '.join(chars)}. Pass storage_folder with a clean name."}
        c = client_for(ctx)
        try:
            with tempfile.TemporaryDirectory(prefix="cloudhpc-") as tmp:
                archive = await asyncio.to_thread(files.make_case_archive, folder, tmp)
                size = os.path.getsize(archive)
                url = await c.upload_url(target, files.UPLOAD_ARCHIVE)
                await c.put_file(url, archive)
            await c.refresh_cache()
        except CloudHPCError as e:
            return _err(e)
        return {"uploaded": True, "storage_folder": target,
                "archive": f"{target}/{files.UPLOAD_ARCHIVE}",
                "size_mb": round(size / 1e6, 2)}

    @mcp.tool(annotations=WRITE)
    async def download_results(folder: str, local_dir: str, extract: bool = True,
                               files_to_get: list[str] | None = None,
                               ctx: Context = None) -> dict:
        """Download result archives of a storage folder to a local directory.

        folder: storage folder of the case. local_dir: where to save (created
        if missing). extract: unpack .tar.gz archives and delete them after.
        files_to_get: optional list of file names; default = all result archives.
        """
        c = client_for(ctx)
        local_dir = os.path.abspath(os.path.expanduser(local_dir))
        os.makedirs(local_dir, exist_ok=True)
        try:
            items = await c.list_storage(folder)
        except CloudHPCError as e:
            return _err(e)
        names = [i["basename"] for i in items if i.get("type") == "file"]
        wanted = files_to_get or [n for n in names if files.is_result_file(n)]
        if not wanted:
            return {"error": f"No result archives in '{folder}' yet.", "files_in_folder": names}
        done = []
        for name in wanted:
            if name not in names:
                done.append({"file": name, "error": "not found in storage folder"})
                continue
            dest = os.path.join(local_dir, name)
            try:
                url = await c.download_url(f"{folder.strip('/')}/{name}")
                size = await c.get_file(url, dest)
                entry: dict[str, Any] = {"file": name, "size_mb": round(size / 1e6, 2)}
                if extract and name.endswith((".tar.gz", ".tgz", ".tar")):
                    entry["extracted_entries"] = await asyncio.to_thread(files.safe_extract, dest, local_dir)
                    os.remove(dest)
                else:
                    entry["saved_as"] = dest
                done.append(entry)
            except (CloudHPCError, ValueError, OSError) as e:
                done.append({"file": name, "error": str(e)})
        return {"local_dir": local_dir, "downloads": done}


# ---------------------------------------------------------------- entry

def main() -> None:
    if LOCAL:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
