"""Offline tests with a mocked cloudHPC API (response shapes from the staging probe)."""

import io
import json
import os
import tarfile

import httpx
import pytest

os.environ["CLOUDHPC_MCP_MODE"] = "local"

from cloudhpc_mcp import advisor, files, server  # noqa: E402
from cloudhpc_mcp.client import CloudHPCClient, CloudHPCError  # noqa: E402

API = "https://api.test/api/v2"
RL = {"x-ratelimit-hourly-limit": "100", "x-ratelimit-hourly-used": "5",
      "x-ratelimit-daily-limit": "0", "x-ratelimit-daily-used": "5"}

SIM = {"id": 10030, "user_id": 4, "cpu": 48, "ram": "hypercore", "nopre": 0,
       "folder": "caseA", "mesh": "", "script": "openFoam-v2406", "clean": 0,
       "idate": "2026-09-24 09:31:20", "edate": "", "cpu_hrs": "", "cost": "",
       "status": 30, "logs": "", "images": [], "vnc_url": "https://vnc.example/x"}


def dir_item(i, name, parent=""):
    return {"id": i, "name": f"{parent}/{name}".strip("/"), "basename": name,
            "dirname": parent, "type": "dir", "size": ""}


def file_item(i, name, parent="", size=1234):
    return {"id": i, "name": f"{parent}/{name}".strip("/"), "basename": name,
            "dirname": parent, "type": "file", "size": size,
            "timeCreated": "2026-09-24T10:00:00Z"}


def make_tgz(members: dict) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, data in members.items():
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


class FakeAPI:
    def __init__(self):
        self.calls = []
        self.uploaded = None
        self.upload_ct = None
        self.sim_status = 30
        self.result_blob = make_tgz({"out/result.txt": b"ok"})

    def __call__(self, req: httpx.Request) -> httpx.Response:
        path, m = req.url.path, req.method
        self.calls.append((m, path))

        if req.url.host == "signed.test":
            if m == "PUT":
                self.uploaded = req.read()
                self.upload_ct = req.headers.get("content-type")
                return httpx.Response(200)
            return httpx.Response(200, content=self.result_blob)

        if req.headers.get("x-api-key") != "good":
            return httpx.Response(403, json={"errors": ["Unauthorized."]})

        def ok(resp):
            return httpx.Response(200, json={"response": resp}, headers=RL)

        p = path.replace("/api/v2", "")
        if p == "/simulation/view-cpu":
            return ok([1, 2, 4, 8, 16, 32, 48, 64, 96, 112, 192, 224])
        if p == "/simulation/view-ram":
            return ok(["highcpu", "standard", "highmem", "hypercpu", "basegpu", "highcore", "hypercore"])
        if p == "/simulation/view-scripts":
            return ok(["fds6.9.1", "openFoam-v2406", "calculiX-2.21-PARDISO", "codeAster-17.0_mpi"])
        if p.startswith("/simulation/index-short/"):
            pg = int(p.rsplit("/", 1)[1])
            return ok([dict(SIM, status=self.sim_status), dict(SIM, id=10029, status=10)] if pg == 1 else [])
        if p.startswith("/simulation/view-short/") or p.startswith("/simulation/view/"):
            if p.endswith("/999"):
                return httpx.Response(403, json={"errors": ["A technical problem has occurred, try again later."]})
            return ok(dict(SIM, status=self.sim_status, logs="line1\nline2"))
        if p == "/simulation/add":
            self.added = json.loads(req.read())
            return ok(12345)
        if p.startswith("/simulation/stop/"):
            self.stopped = json.loads(req.read())
            return ok(True)
        if p.startswith("/simulation/sync/"):
            return ok(True)
        if p.startswith("/storage/index/name/asc/parent_id/"):
            pid, pg = p.split("/")[-2:]
            if pg != "1":
                return ok([])
            if pid == "1":
                return ok([dir_item(3, "sub", "caseA"), file_item(10, "upload.tar.gz", "caseA"),
                           file_item(11, "FDS.tar.gz", "caseA", 5_000_000),
                           file_item(12, "CloudHPC-massive-files.tar.gz", "caseA")])
            if pid == "3":
                return ok([file_item(20, "x.txt", "caseA/sub")])
            return ok([])
        if p.startswith("/storage/index/name/asc/"):
            pg = p.rsplit("/", 1)[1]
            return ok([dir_item(1, "caseA"), file_item(2, "loose.fds")] if pg == "1" else [])
        if p == "/storage/view-by-path":
            path_q = json.loads(req.read())["path"]
            return ok(file_item(11, os.path.basename(path_q), os.path.dirname(path_q)))
        if p.startswith("/storage/view-url/"):
            return ok({"mediaLink": "https://signed.test/download"})
        if p == "/storage/upload-url":
            self.upload_req = json.loads(req.read())
            return ok({"url": "https://signed.test/upload"})
        if p == "/user/delete-cache":
            return ok(True)
        if p.startswith("/storage/delete/"):
            return ok(True)
        return httpx.Response(404, json={"errors": ["not mocked"]})


@pytest.fixture
def api(monkeypatch):
    fake = FakeAPI()
    transport = httpx.MockTransport(fake)
    monkeypatch.setattr(server, "client_for",
                        lambda ctx=None: CloudHPCClient(api_key="good", api_url=API, transport=transport))
    return fake


# ---------------------------------------------------------------- client

async def test_bad_key_message():
    c = CloudHPCClient(api_key="bad", api_url=API, transport=httpx.MockTransport(FakeAPI()))
    with pytest.raises(CloudHPCError, match="invalid"):
        await c.cpu_options()


async def test_missing_key():
    with pytest.raises(CloudHPCError, match="No cloudHPC API key"):
        CloudHPCClient(api_key="  ", api_url=API)


async def test_rate_limit_tracking_and_block():
    c = CloudHPCClient(api_key="good", api_url=API, transport=httpx.MockTransport(FakeAPI()))
    await c.cpu_options()
    assert c.rate.as_dict()["hourly"]["remaining"] == 95
    assert c.rate.as_dict()["daily"]["limit"] == "unlimited"
    c.rate.hourly_used = 100
    with pytest.raises(CloudHPCError, match="rate limit"):
        await c.cpu_options()


# ------------------------------------------------------------------ tools

async def test_list_solvers_grouped(api):
    r = await server.list_solvers()
    assert r["solvers"]["fds"] == ["fds6.9.1"]
    assert "openfoam" in r["solvers"]
    r = await server.list_solvers(search="PARDISO")
    assert r["solvers"] == {"calculix": ["calculiX-2.21-PARDISO"]}


async def test_list_storage_walks_tree(api):
    root = await server.list_storage()
    assert {i["name"] for i in root["items"]} == {"caseA", "loose.fds"}
    sub = await server.list_storage("caseA/sub")
    assert sub["items"][0]["path"] == "caseA/sub/x.txt"
    missing = await server.list_storage("nope")
    assert "not found" in missing["error"]


async def test_list_results_filters(api):
    r = await server.list_results("caseA")
    assert [x["name"] for x in r["results"]] == ["FDS.tar.gz"]


async def test_launch_requires_confirmation(api):
    r = await server.launch_simulation("fds6.9.1", 8, "highcpu", "caseA")
    assert r["confirmation_required"] and "fds6.9.1" in r["summary"]
    assert ("POST", "/api/v2/simulation/add") not in api.calls
    r = await server.launch_simulation("fds6.9.1", 8, "highcpu", "caseA", confirm=True)
    assert r["simulation_id"] == 12345
    assert api.added == {"cpu": 8, "ram": "highcpu", "script": "fds6.9.1", "folder": "caseA"}


async def test_launch_validation(api):
    r = await server.launch_simulation("openFoam-v2406", 7, "highcpu", "caseA", confirm=True)
    assert "problems" in r
    assert any("vCPU 7" in p for p in r["problems"])
    assert any("hyperthreading" in p for p in r["problems"])
    assert ("POST", "/api/v2/simulation/add") not in api.calls


async def test_launch_regular_and_mesh(api):
    await server.launch_simulation("openFoam-v2406", 32, "highcore", "caseA",
                                   mesh_folder="meshA", regular_instance=True, confirm=True)
    assert api.added["nopre"] == 1 and api.added["mesh"] == "meshA"


async def test_get_simulation_and_errors(api):
    r = await server.get_simulation(10030)
    assert r["status"] == "RUNNING" and r["solver"] == "openFoam-v2406"
    assert "vnc_url" not in r
    r = await server.get_simulation(10030, include_log=True)
    assert r["logs"].endswith("line2")
    r = await server.get_simulation(999)
    assert "technical problem" in r["error"]


async def test_list_simulations_filter(api):
    r = await server.list_simulations("active")
    assert [s["id"] for s in r["simulations"]] == [10030]
    r = await server.list_simulations("all")
    assert len(r["simulations"]) == 2


async def test_wait_returns_when_finished(api):
    api.sim_status = 10
    r = await server.wait_for_simulation(10030, max_minutes=1)
    assert r["finished"] and r["status"] == "COMPLETED"


async def test_stop_flow(api):
    r = await server.stop_simulation(10030)
    assert r["confirmation_required"]
    r = await server.stop_simulation(10030, mode="hard", confirm=True)
    assert r["stopping"] and api.stopped == {"signal": "SIGINT"}
    await server.stop_simulation(10030, confirm=True)
    assert api.stopped == {"signal": "SIGTSTP"}
    api.sim_status = 10
    r = await server.stop_simulation(10030, confirm=True)
    assert "not active" in r["error"]


async def test_delete_requires_confirmation(api):
    r = await server.delete_storage("caseA/FDS.tar.gz")
    assert r["confirmation_required"]
    assert not any(m == "DELETE" and "/storage/delete" in p for m, p in api.calls)
    r = await server.delete_storage("caseA/FDS.tar.gz", confirm=True)
    assert r["deleted"]


async def test_remote_desktop(api):
    r = await server.open_remote_desktop(10030)
    assert r["url"].startswith("https://vnc")
    api.sim_status = 10
    assert "error" in await server.open_remote_desktop(10030)


async def test_links(api):
    r = await server.get_download_link("caseA/FDS.tar.gz")
    assert r["url"] == "https://signed.test/download"
    r = await server.get_upload_link("caseB", "upload.tar.gz")
    assert "--upload-file" in r["curl"]
    assert api.upload_req == {"dirname": "caseB", "filename": "upload.tar.gz",
                              "contentType": "application/octet-stream"}


async def test_api_usage(api):
    r = await server.api_usage()
    assert r["hourly"]["limit"] == 100


# ------------------------------------------------------------- local tools

async def test_upload_folder_raw_targz(api, tmp_path):
    case = tmp_path / "myCase"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("x")
    (case / ".hidden").write_text("secret")
    r = await server.upload_folder(str(case))
    assert r["uploaded"] and r["storage_folder"] == "myCase"
    assert api.upload_req["dirname"] == "myCase"
    assert api.upload_ct == "application/octet-stream"
    with tarfile.open(fileobj=io.BytesIO(api.uploaded), mode="r:gz") as t:
        names = t.getnames()
    assert "system/controlDict" in names and ".hidden" not in names
    assert not any(n.startswith("myCase") for n in names)  # content at archive root


async def test_download_results_extracts(api, tmp_path):
    r = await server.download_results("caseA", str(tmp_path))
    assert r["downloads"][0]["file"] == "FDS.tar.gz"
    assert (tmp_path / "out" / "result.txt").read_text() == "ok"
    assert not (tmp_path / "FDS.tar.gz").exists()


async def test_download_rejects_path_traversal(api, tmp_path):
    api.result_blob = make_tgz({"../evil.txt": b"x"})
    r = await server.download_results("caseA", str(tmp_path / "d"))
    assert "Unsafe" in r["downloads"][0]["error"]
    assert not (tmp_path / "evil.txt").exists()


# ---------------------------------------------------------------- advisor

FDS_TEXT = """
&HEAD CHID='t' /
&MESH ID='m1', IJK=40,40,20, XB=0,4,0,4,0,2, MPI_PROCESS=0 /
&MESH ID='m2', IJK=40,40,20,
      XB=4,8,0,4,0,2, MPI_PROCESS=1 /
&MESH ID='m3', IJK=10,10,10, XB=8,9,0,1,0,1, MPI_PROCESS=1 /
&TAIL /
"""


def test_inspect_fds(tmp_path):
    (tmp_path / "case.fds").write_text(FDS_TEXT)
    info = advisor.inspect_case(str(tmp_path))
    f = info["fds"]
    assert info["family"] == "fds"
    assert f["meshes"] == 3 and f["mpi_groups"] == 2
    assert f["total_cells"] == 32000 + 32000 + 1000


def test_suggest_fds_rules(tmp_path):
    (tmp_path / "case.fds").write_text(FDS_TEXT)
    fds = advisor.inspect_case(str(tmp_path))["fds"]
    cpus = [1, 2, 4, 8, 16, 32]
    s = advisor.suggest("fds", cpus, [], fds=fds)
    assert s["ram"] == "highcpu" and s["cpu"] == 4  # 2 groups x 2
    s = advisor.suggest("fds", cpus, [], fds=fds, prefer_speed=True)
    assert s["ram"] == "hypercore" and s["cpu"] == 2  # 2 groups x 1


def test_suggest_fds_single_mesh_decomposition():
    fds = {"meshes": 1, "mpi_groups": 1, "total_cells": 1_000_000, "cells_per_group": [1_000_000],
           "uses_mpi_process": False, "uses_mult_id": False}
    s = advisor.suggest("fds", [1, 2, 4, 8, 16, 32, 48, 64, 96, 112], [], fds=fds)
    assert s["ideal_cpu"] == 66 * 2 and s["cpu"] == 112
    assert any("decomposes" in n for n in s["notes"])


def test_suggest_openfoam():
    s = advisor.suggest("openfoam", [1, 2, 4, 8, 16, 32, 48, 64], [], cells=2_000_000)
    assert s["cpu"] == 32 and s["ram"] == "highcore"  # 40 ideal -> 32


def test_suggest_fea():
    s = advisor.suggest("calculix", [1, 2, 4, 8], [], nodes=865_000)
    assert s["cpu"] == 4 and s["ram"] == "highcpu"
    s = advisor.suggest("code_aster", [1, 2, 4, 8, 16, 32], [], nodes=865_000)
    assert s["cpu"] == 16  # 8 ranks x 2 threads


def test_inspect_openfoam_and_calculix(tmp_path):
    of = tmp_path / "of"
    (of / "system").mkdir(parents=True)
    (of / "system" / "controlDict").write_text("x")
    (of / "constant" / "polyMesh").mkdir(parents=True)
    (of / "constant" / "polyMesh" / "owner").write_text(
        'FoamFile { note "nPoints:10 nCells:123456 nFaces:5 nInternalFaces:3"; }')
    info = advisor.inspect_case(str(of))
    assert info["cells"] == 123456
    assert any("decomposeParDict" in n for n in info["notes"])

    cx = tmp_path / "cx"
    cx.mkdir()
    (cx / "beam.inp").write_text("** c\n*NODE, NSET=all\n1,0,0,0\n2,1,0,0\n*ELEMENT, TYPE=C3D4\n1,1,2,3,4\n")
    assert advisor.inspect_case(str(cx))["nodes"] == 2


def test_family_of():
    assert advisor.family_of("snappyHexMesh-v2312") == "openfoam"
    assert advisor.family_of("codeAster-17.0_mpi") == "code_aster"
    assert advisor.family_of("OpenRadioss") == "openradioss"
    assert advisor.family_of("ubuntu-2404-static") == "other"


def test_result_file_filter():
    assert files.is_result_file("OPENFOAM-solution.tar.gz")
    assert files.is_result_file("case.rmed")
    assert not files.is_result_file("upload.tar.gz")
    assert not files.is_result_file("CloudHPC-massive-files.tar.gz")
    assert not files.is_result_file("CloudHPC-massive-files-20260925000914.tar.gz")


def test_single_highcpu_upgraded_to_standard():
    fds = {"meshes": 1, "mpi_groups": 1, "total_cells": 8000, "cells_per_group": [8000],
           "uses_mpi_process": False, "uses_mult_id": False}
    s = advisor.suggest("fds", [1, 2, 4], [], fds=fds)
    assert s["cpu"] == 2 and s["ram"] == "highcpu"   # 1 mesh x 2 (hyperthreading)
    s = advisor.suggest("fds", [1, 4], [], fds=fds)
    assert s["cpu"] == 4 and s["ram"] == "highcpu"   # rounded up, not 1 vCPU
    s = advisor.suggest("calculix", [1, 2, 4], [], nodes=10_000)
    assert s["cpu"] == 1 and s["ram"] == "standard"


async def test_launch_refuses_single_highcpu(api):
    r = await server.launch_simulation("fds6.9.1", 1, "highcpu", "caseA", confirm=True)
    assert any("1 vCPU highcpu" in p for p in r["problems"])
    r = await server.launch_simulation("fds6.9.1", 1, "standard", "caseA")
    assert r["confirmation_required"]


def test_ram_ladder_and_memory_detection():
    assert advisor.next_ram("highcpu") == "standard"
    assert advisor.next_ram("standard") == "highmem"
    assert advisor.next_ram("highmem") is None
    log = "MPIDU_Init_shm_alloc(139): Unable to allocate -2098937792 bytes of memory for segment (probably out of memory)"
    assert advisor.looks_like_memory_error(log)
    assert not advisor.looks_like_memory_error("STOP: FDS completed successfully")


async def test_get_simulation_memory_hint(api, monkeypatch):
    orig = api.__call__
    def patched(req):
        if "/simulation/view/" in req.url.path:
            import httpx as h
            return h.Response(200, json={"response": dict(SIM, ram="highcpu", status=60,
                              output="Unable to allocate 123 bytes (probably out of memory)")})
        return orig(req)
    monkeypatch.setattr(server, "client_for", lambda ctx=None: CloudHPCClient(
        api_key="good", api_url=API, transport=httpx.MockTransport(patched)))
    r = await server.get_simulation(10030, include_log=True)
    assert r["memory_error"] and "standard" in r["suggestion"]


# ------------------------------------------------------------ error catalogue

from cloudhpc_mcp import errors  # noqa: E402


def test_diagnose_catalogue():
    out = ("@@@ RAM used > 80.0%: increase vCPU or use highmem instance\n"
           "=   KILLED BY SIGNAL: 9 (Killed)\n"
           "@@@ ERROR: low vCPU selected\n"
           "@@@ WARNING: high number of Pressure Zones found - risk of poor scalability\n")
    ids = [d["id"] for d in errors.diagnose(out)]
    assert ids[:2] == ["ram_out", "fds_low_vcpu"] or set(ids[:2]) == {"ram_out", "fds_low_vcpu"}
    assert "ram_high" in ids and "fds_pressure_zones" in ids
    assert all(d["docs"].startswith("https://docs.cloudhpc.cloud/errors/#") for d in errors.diagnose(out))
    assert errors.diagnose("STOP: FDS completed successfully") == []
    assert errors.diagnose("@@@ ERROR: openFoam script runs with nProc > 1")[0]["id"] == "of_nproc"


async def test_wait_adds_diagnosis_on_completed_with_error(api, monkeypatch):
    orig = api.__call__

    def patched(req):
        if "/simulation/view/" in req.url.path:
            return httpx.Response(200, json={"response": dict(
                SIM, script="fds6.9.1", ram="highcpu", status=10,
                output="@@@ ERROR: MPI_MPI_PROCESS incorrect\n")})
        if "/simulation/view-short/" in req.url.path:
            return httpx.Response(200, json={"response": dict(SIM, status=10)})
        return orig(req)

    monkeypatch.setattr(server, "client_for", lambda ctx=None: CloudHPCClient(
        api_key="good", api_url=API, transport=httpx.MockTransport(patched)))
    r = await server.wait_for_simulation(10030, max_minutes=1)
    assert r["finished"] and r["status"] == "COMPLETED"
    assert r["diagnosis"][0]["id"] == "fds_mpi_order"
    assert "COMPLETED but" in r["warning"]


def test_preflight_fds_and_names(tmp_path):
    case = tmp_path / "bad(name)"
    case.mkdir()
    (case / "c.fds").write_text(
        "&MESH IJK=10,10,10, XB=0,1,0,1,0,1, MPI_PROCESS=1 /\n"
        "&MESH IJK=10,10,10, XB=1,2,0,1,0,1, MPI_PROCESS=0 /\n"
        "&DEVC ID='v', QUANTITY='VISIBILITY', XYZ=1,1,1 /\n")
    info = advisor.inspect_case(str(case))
    issues = errors.preflight(info)
    text = " ".join(i["issue"] for i in issues)
    assert "characters not accepted" in text
    assert "ascending order" in text
    assert "AMD" in text


def test_preflight_openfoam(tmp_path):
    of = tmp_path / "of"
    (of / "system").mkdir(parents=True)
    (of / "system" / "controlDict").write_text("startFrom startTime;\n")
    (of / "system" / "decomposeParDict").write_text("method simple;\n")
    issues = errors.preflight(advisor.inspect_case(str(of)))
    text = " ".join(i["issue"] for i in issues)
    assert "scotch or hierarchical" in text and "polyMesh" in text and "latestTime" in text


async def test_launch_name_and_openfoam_min(api):
    r = await server.launch_simulation("fds6.9.1", 4, "highcpu", "my case(1)", confirm=True)
    assert any("characters" in p for p in r["problems"])
    r = await server.launch_simulation("openFoam-v2406", 1, "highcore", "caseA", confirm=True)
    assert any("at least 2 vCPU" in p for p in r["problems"])


def test_fds_rounds_up_to_cover_meshes():
    fds = {"meshes": 3, "mpi_groups": 3, "total_cells": 90_000, "cells_per_group": [30_000] * 3,
           "uses_mpi_process": False, "uses_mult_id": False}
    s = advisor.suggest("fds", [1, 2, 4, 8, 16], [], fds=fds)
    assert s["cpu"] == 8  # 3 meshes x 2 = 6 -> round up to 8, never 4


def test_openfoam_minimum_two():
    s = advisor.suggest("openfoam", [1, 2, 4, 8], [], cells=30_000)
    assert s["cpu"] == 2 and s["ram"] == "highcore"


def test_fds_success_marker():
    ok = server._diagnosis({"script": "fds6.11.1", "status": 10,
                            "output": " Starting FDS ...\nSTOP: FDS completed successfully (CHID: x)"})
    assert ok["solver_finished_ok"] is True and "warning" not in ok
    bad = server._diagnosis({"script": "fds6.11.1", "status": 10,
                             "output": " Starting FDS ...\n Time Step: 5"})
    assert bad["solver_finished_ok"] is False and "did not print" in bad["warning"]
    assert "solver_finished_ok" not in server._diagnosis({"script": "fds6.11.1", "status": 10, "output": ""})
