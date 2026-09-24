"""Async client for the cloudHPC REST API v2.

Only the user-facing endpoints (simulations, storage, cache refresh) are
wrapped. Administrative endpoints (groups, costs, currencies, logs, queues,
tokens, user management) are deliberately NOT exposed.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_API_URL = "https://cloud.cfdfeaservice.it/api/v2"

STATUS = {
    10: "COMPLETED",
    20: "PENDING",
    30: "RUNNING",
    40: "STOPPING",
    50: "STOPPED",
    60: "ERROR",
}
ACTIVE_STATUSES = {20, 30, 40}

UPLOAD_CONTENT_TYPE = "application/octet-stream"
API_TIMEOUT = httpx.Timeout(60.0, connect=15.0)
TRANSFER_TIMEOUT = httpx.Timeout(3600.0, connect=30.0)
MAX_PAGES = 50  # safety cap for paginated listings


class CloudHPCError(Exception):
    """Error returned by the cloudHPC API, with a user-readable message."""


@dataclass
class RateLimit:
    hourly_limit: int | None = None
    hourly_used: int | None = None
    daily_limit: int | None = None
    daily_used: int | None = None

    def update(self, headers: httpx.Headers) -> None:
        def _int(name: str) -> int | None:
            try:
                return int(headers[name])
            except (KeyError, ValueError):
                return None

        for attr, name in (
            ("hourly_limit", "x-ratelimit-hourly-limit"),
            ("hourly_used", "x-ratelimit-hourly-used"),
            ("daily_limit", "x-ratelimit-daily-limit"),
            ("daily_used", "x-ratelimit-daily-used"),
        ):
            value = _int(name)
            if value is not None:
                setattr(self, attr, value)

    def exhausted(self) -> bool:
        """True when a known, non-zero limit has been reached (0 = unlimited)."""
        for limit, used in ((self.hourly_limit, self.hourly_used),
                            (self.daily_limit, self.daily_used)):
            if limit and used is not None and used >= limit:
                return True
        return False

    def as_dict(self) -> dict[str, Any]:
        def fmt(limit: int | None, used: int | None) -> dict[str, Any]:
            if limit is None:
                return {"limit": "unknown", "used": used}
            if limit == 0:
                return {"limit": "unlimited", "used": used}
            return {"limit": limit, "used": used, "remaining": max(limit - (used or 0), 0)}

        return {"hourly": fmt(self.hourly_limit, self.hourly_used),
                "daily": fmt(self.daily_limit, self.daily_used)}


@dataclass
class CloudHPCClient:
    api_key: str
    api_url: str = field(default_factory=lambda: os.environ.get("CLOUDHPC_API_URL", DEFAULT_API_URL))
    transport: httpx.AsyncBaseTransport | None = None  # injectable for tests
    rate: RateLimit = field(default_factory=RateLimit)

    def __post_init__(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise CloudHPCError(
                "No cloudHPC API key. Set CLOUDHPC_APIKEY (local mode) or send it in the "
                "X-API-Key / Authorization: Bearer header (remote mode). The key is on "
                "your cloudHPC profile page."
            )
        self.api_key = self.api_key.strip()
        self.api_url = self.api_url.rstrip("/")

    # ------------------------------------------------------------------ core
    def _http(self, timeout: httpx.Timeout = API_TIMEOUT) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, transport=self.transport)

    async def call(self, method: str, path: str, json: Any = None) -> Any:
        if self.rate.exhausted():
            raise CloudHPCError(
                "cloudHPC API rate limit reached "
                f"({self.rate.as_dict()}). Wait before making more calls."
            )
        headers = {"X-API-Key": self.api_key, "Accept": "application/json"}
        try:
            async with self._http() as http:
                r = await http.request(method, self.api_url + path, json=json, headers=headers)
        except httpx.HTTPError as e:
            raise CloudHPCError(f"Cannot reach cloudHPC API: {e}") from e

        self.rate.update(r.headers)

        try:
            data = r.json()
        except ValueError:
            raise CloudHPCError(f"HTTP {r.status_code} with non-JSON reply on {path}")

        if isinstance(data, dict) and data.get("errors"):
            msg = str(data["errors"][0])
            if msg.strip().rstrip(".").lower() == "unauthorized":
                msg = "Unauthorized: the API key is invalid or not enabled for this endpoint."
            elif self.rate.exhausted():
                msg += " (rate limit reached)"
            raise CloudHPCError(msg)
        if r.status_code >= 400:
            raise CloudHPCError(f"HTTP {r.status_code} on {path}")
        if not isinstance(data, dict) or "response" not in data:
            raise CloudHPCError(f"Unexpected reply format on {path}")
        return data["response"]

    async def _paged(self, path_for_page) -> list[dict]:
        items: list[dict] = []
        seen: set = set()
        for pg in range(1, MAX_PAGES + 1):
            page = await self.call("GET", path_for_page(pg))
            if not page:
                break
            new = [i for i in page if i.get("id") not in seen]
            if not new:  # API returned the same page again: stop
                break
            seen.update(i.get("id") for i in new)
            items.extend(new)
        return items

    # --------------------------------------------------------------- options
    async def cpu_options(self) -> list[int]:
        return [int(c) for c in await self.call("GET", "/simulation/view-cpu")]

    async def ram_options(self) -> list[str]:
        return list(await self.call("GET", "/simulation/view-ram"))

    async def scripts(self) -> list[str]:
        return list(await self.call("GET", "/simulation/view-scripts"))

    # ----------------------------------------------------------- simulations
    async def list_simulations(self, max_pages: int = 3) -> list[dict]:
        items: list[dict] = []
        for pg in range(1, max_pages + 1):
            page = await self.call("GET", f"/simulation/index-short/id/desc/{pg}")
            if not page:
                break
            items.extend(page)
        return items

    async def get_simulation(self, sim_id: int) -> dict:
        return await self.call("GET", f"/simulation/view-short/{int(sim_id)}")

    async def get_simulation_full(self, sim_id: int) -> dict:
        return await self.call("GET", f"/simulation/view/{int(sim_id)}")

    async def add_simulation(self, cpu: int, ram: str, script: str, folder: str,
                             mesh: str | None = None, regular: bool = False) -> int:
        body: dict[str, Any] = {"cpu": int(cpu), "ram": ram, "script": script, "folder": folder}
        if mesh:
            body["mesh"] = mesh
        if regular:
            body["nopre"] = 1
        return await self.call("POST", "/simulation/add", json=body)

    async def stop_simulation(self, sim_id: int, hard: bool = False) -> Any:
        signal = "SIGINT" if hard else "SIGTSTP"
        return await self.call("PUT", f"/simulation/stop/{int(sim_id)}", json={"signal": signal})

    async def sync_simulation(self, sim_id: int) -> Any:
        return await self.call("PUT", f"/simulation/sync/{int(sim_id)}")

    # --------------------------------------------------------------- storage
    async def list_storage(self, folder: str = "") -> list[dict]:
        """List the content of a storage folder ('' = root)."""
        # Folder ids are resolved by walking the tree from the root (the same
        # approach used by the bash cloudHPCexec), one listing per level.
        items = await self._paged(lambda pg: f"/storage/index/name/asc/{pg}")
        walked = ""
        for part in [p for p in folder.strip("/").split("/") if p]:
            walked = f"{walked}/{part}".strip("/")
            match = [i for i in items if i.get("type") == "dir" and i.get("basename") == part]
            if not match:
                raise CloudHPCError(f"Folder '{walked}' not found in storage")
            fid = match[0]["id"]
            items = await self._paged(
                lambda pg, fid=fid: f"/storage/index/name/asc/parent_id/{fid}/{pg}")
        return items

    async def view_by_path(self, path: str) -> dict:
        return await self.call("POST", "/storage/view-by-path", json={"path": path.strip("/")})

    async def download_url(self, path: str, attempts: int = 10) -> str:
        info = await self.view_by_path(path)
        for _ in range(attempts):
            reply = await self.call("GET", f"/storage/view-url/{info['id']}")
            url = (reply or {}).get("mediaLink") if isinstance(reply, dict) else None
            if url:
                return url
            await asyncio.sleep(2)
        raise CloudHPCError(f"No download link available for '{path}'")

    async def upload_url(self, dirname: str, filename: str) -> str:
        reply = await self.call("POST", "/storage/upload-url", json={
            "dirname": dirname.strip("/"),
            "filename": filename,
            "contentType": UPLOAD_CONTENT_TYPE,
        })
        url = reply.get("url") if isinstance(reply, dict) else None
        if not url:
            raise CloudHPCError("storage/upload-url did not return an upload URL")
        return url

    async def refresh_cache(self) -> None:
        try:
            await self.call("DELETE", "/user/delete-cache")
        except CloudHPCError:
            pass  # optional

    async def delete_path(self, path: str) -> Any:
        info = await self.view_by_path(path)
        result = await self.call("DELETE", f"/storage/delete/{info['id']}")
        await self.refresh_cache()
        return result

    # ------------------------------------------------------------- transfers
    async def put_file(self, url: str, local_path: str) -> None:
        """Upload a local file to a signed URL as a raw body."""
        size = os.path.getsize(local_path)

        async def chunks():
            with open(local_path, "rb") as f:
                while True:
                    block = f.read(8 * 1024 * 1024)
                    if not block:
                        break
                    yield block

        try:
            async with self._http(TRANSFER_TIMEOUT) as http:
                r = await http.put(url, content=chunks(), headers={
                    "Content-Type": UPLOAD_CONTENT_TYPE,
                    "Content-Length": str(size),
                })
        except httpx.HTTPError as e:
            raise CloudHPCError(f"Upload failed: {e}") from e
        if r.status_code >= 300:
            raise CloudHPCError(f"Upload failed: HTTP {r.status_code} {r.text[:200]}")

    async def get_file(self, url: str, local_path: str) -> int:
        """Download a signed URL to local_path. Returns bytes written."""
        written = 0
        tmp = local_path + ".part"
        try:
            async with self._http(TRANSFER_TIMEOUT) as http:
                async with http.stream("GET", url) as r:
                    if r.status_code >= 300:
                        raise CloudHPCError(f"Download failed: HTTP {r.status_code}")
                    with open(tmp, "wb") as f:
                        async for block in r.aiter_bytes(8 * 1024 * 1024):
                            f.write(block)
                            written += len(block)
            os.replace(tmp, local_path)
        except httpx.HTTPError as e:
            raise CloudHPCError(f"Download failed: {e}") from e
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return written
