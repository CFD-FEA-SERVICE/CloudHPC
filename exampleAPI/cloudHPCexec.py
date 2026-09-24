#!/usr/bin/env python3
###############################################################################
#
#   cloudHPCexec.py - launch a cloudHPC simulation from a local folder (GUI)
#
#   Script developed by CFD FEA SERVICE SRL
#   License: GPLv3
#
#   Flow (same as the bash cloudHPCexec):
#     1. read vCPU / RAM / solver options from the API
#     2. zip the selected folder (files at the root of the archive)
#     3. POST storage/upload-url  -> signed URL
#     4. PUT the zip to the signed URL (raw body, same Content-Type)
#     5. DELETE user/delete-cache (optional refresh of the storage listing)
#     6. POST simulation/add      -> simulation ID
#
#   Dependencies: python3 with tkinter, requests  (pip install requests)
#   Environment:  CLOUDHPC_BASEURL to use another server (e.g. staging)
#
###############################################################################

import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

BASEURL = os.environ.get("CLOUDHPC_BASEURL", "cloud.cfdfeaservice.it")
API = f"https://{BASEURL}/api/v2"

APIKEY_DIR = os.path.join(str(Path.home()), ".cfscloudhpc")
APIKEY_FILE = os.path.join(APIKEY_DIR, "apikey")

ARCHIVE_NAME = "simulation.zip"
UPLOAD_CONTENT_TYPE = "application/octet-stream"
TIMEOUT = 60            # seconds for API calls
UPLOAD_TIMEOUT = 3600   # seconds for the file upload


###############################################################################
# API key storage (owner-only permissions)
###############################################################################

def read_apikey():
    """Return the stored API key, or '' if none."""
    try:
        with open(APIKEY_FILE, "r") as f:
            return f.readline().strip()
    except OSError:
        return ""


def write_apikey(apikey):
    """Store the API key readable by its owner only (0600, dir 0700)."""
    os.makedirs(APIKEY_DIR, exist_ok=True)
    try:
        os.chmod(APIKEY_DIR, 0o700)
    except OSError:
        pass
    fd = os.open(APIKEY_FILE, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(apikey.strip())
    try:
        os.chmod(APIKEY_FILE, 0o600)   # in case the file already existed
    except OSError:
        pass


def delete_apikey():
    try:
        os.remove(APIKEY_FILE)
    except OSError:
        pass


###############################################################################
# API client
###############################################################################

class APIError(Exception):
    pass


class CloudHPC:
    def __init__(self, apikey, api=API):
        self.api = api
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": apikey.strip(),
            "Accept": "application/json",
        })

    def _call(self, method, path, json=None):
        try:
            r = self.session.request(method, self.api + path, json=json, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise APIError(f"Connection error: {e}") from e

        try:
            data = r.json()
        except ValueError:
            raise APIError(f"HTTP {r.status_code}: non-JSON reply from {path}")

        if isinstance(data, dict) and data.get("errors"):
            raise APIError(f"HTTP {r.status_code}: {data['errors'][0]}")
        if r.status_code >= 400:
            raise APIError(f"HTTP {r.status_code} on {path}")
        if not isinstance(data, dict) or "response" not in data:
            raise APIError(f"Unexpected reply from {path}")
        return data["response"]

    # options -----------------------------------------------------------------
    def cpu_options(self):
        return self._call("GET", "/simulation/view-cpu")

    def ram_options(self):
        return self._call("GET", "/simulation/view-ram")

    def script_options(self):
        return self._call("GET", "/simulation/view-scripts")

    # storage -----------------------------------------------------------------
    def upload_file(self, local_path, dirname, filename, progress=None):
        """Upload local_path to STORAGE as dirname/filename via signed URL."""
        reply = self._call("POST", "/storage/upload-url", json={
            "dirname": dirname,
            "filename": filename,
            "contentType": UPLOAD_CONTENT_TYPE,
        })
        url = reply.get("url") if isinstance(reply, dict) else None
        if not url:
            raise APIError("storage/upload-url did not return an upload URL")

        size = os.path.getsize(local_path)
        if progress:
            progress(f"Uploading {size / 1e6:.1f} MB ...")

        # Raw body (NOT multipart): the storage object must be the zip itself.
        # Content-Type must match the one used to sign the URL.
        with open(local_path, "rb") as f:
            try:
                r = requests.put(url, data=f,
                                 headers={"Content-Type": UPLOAD_CONTENT_TYPE,
                                          "Content-Length": str(size)},
                                 timeout=UPLOAD_TIMEOUT)
            except requests.RequestException as e:
                raise APIError(f"Upload failed: {e}") from e
        if r.status_code >= 300:
            raise APIError(f"Upload failed: HTTP {r.status_code} {r.text[:200]}")

        # Optional: refresh the storage listing so the new file is seen at once
        try:
            self._call("DELETE", "/user/delete-cache")
        except APIError:
            pass

    # simulations -------------------------------------------------------------
    def add_simulation(self, cpu, ram, script, folder, regular=False):
        body = {"cpu": int(cpu), "ram": ram, "script": script, "folder": folder}
        if regular:
            body["nopre"] = 1
        return self._call("POST", "/simulation/add", json=body)


###############################################################################
# Launch procedure (no GUI code here)
###############################################################################

def zip_folder(folder, workdir):
    """Zip the CONTENT of folder (files at archive root) into workdir."""
    base = os.path.join(workdir, os.path.splitext(ARCHIVE_NAME)[0])
    return shutil.make_archive(base, "zip", root_dir=folder)


def launch(client, cpu, ram, script, folder, regular=False, progress=print):
    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        raise APIError(f"Folder not found: {folder}")
    if not os.listdir(folder):
        raise APIError(f"Folder is empty: {folder}")

    storage_folder = os.path.basename(folder.rstrip(os.sep))

    # temporary dir outside the case folder: nothing left behind on errors
    with tempfile.TemporaryDirectory(prefix="cloudhpc-") as tmp:
        progress(f"Compressing {storage_folder} ...")
        archive = zip_folder(folder, tmp)
        client.upload_file(archive, storage_folder, ARCHIVE_NAME, progress)

    progress(f"Launching {script} on {cpu} vCPU / {ram} ...")
    sim_id = client.add_simulation(cpu, ram, script, storage_folder, regular)
    return sim_id


###############################################################################
# GUI
###############################################################################

def main():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("Cloud HPC - Run")
    root.resizable(False, False)
    root.attributes("-topmost", 1)

    frm = ttk.Frame(root, padding=10)
    frm.grid(sticky="nsew")

    apikey = tk.StringVar(value=read_apikey())
    cpu_var, ram_var, script_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
    folder_var = tk.StringVar()
    regular_var = tk.BooleanVar(value=False)
    status = tk.StringVar(value=f"Server: {BASEURL}")

    ttk.Label(frm, text="APIKEY:").grid(row=0, column=0, sticky="w")
    ttk.Entry(frm, textvariable=apikey, width=40, show="*").grid(row=0, column=1, columnspan=2, sticky="we")

    widgets = {}

    def load_options():
        key = apikey.get().strip()
        if not key:
            status.set("Insert your APIKEY and press 'Load'")
            return
        client = CloudHPC(key)
        try:
            cpus = client.cpu_options()
            rams = client.ram_options()
            scripts = client.script_options()
        except APIError as e:
            status.set(f"ERROR: {e}")
            messagebox.showerror("cloudHPC", f"{e}\n\nCheck your APIKEY.")
            return

        write_apikey(key)

        for name, var, values, row in (("vCPU", cpu_var, cpus, 2),
                                       ("RAM", ram_var, rams, 3),
                                       ("SOLVER", script_var, scripts, 4)):
            values = [str(v) for v in (values or [])]
            if not values:
                status.set(f"ERROR: no {name} options returned")
                return
            ttk.Label(frm, text=f"{name}:").grid(row=row, column=0, sticky="w")
            cb = ttk.Combobox(frm, textvariable=var, values=values, state="readonly", width=37)
            cb.grid(row=row, column=1, columnspan=2, sticky="we")
            var.set(values[0])
            widgets[name] = cb

        ttk.Label(frm, text="FOLDER:").grid(row=5, column=0, sticky="w")
        ttk.Entry(frm, textvariable=folder_var, width=28).grid(row=5, column=1, sticky="we")
        ttk.Button(frm, text="Browse",
                   command=lambda: folder_var.set(filedialog.askdirectory() or folder_var.get())
                   ).grid(row=5, column=2)
        ttk.Checkbutton(frm, text="Regular instance (not preemptible)",
                        variable=regular_var).grid(row=6, column=1, columnspan=2, sticky="w")
        launch_btn.grid(row=8, column=1, sticky="e")
        status.set("Select options and folder, then 'Launch'")

    def do_launch():
        if not folder_var.get():
            messagebox.showwarning("cloudHPC", "Select the case folder")
            return
        launch_btn.state(["disabled"])
        client = CloudHPC(apikey.get().strip())

        def worker():
            try:
                sim_id = launch(client, cpu_var.get(), ram_var.get(), script_var.get(),
                                folder_var.get(), regular_var.get(),
                                progress=lambda m: root.after(0, status.set, m))
            except APIError as e:
                root.after(0, lambda: (status.set(f"ERROR: {e}"),
                                       messagebox.showerror("cloudHPC", str(e)),
                                       launch_btn.state(["!disabled"])))
                return
            print(f"Simulation launched with ID = {sim_id}")
            root.after(0, lambda: (status.set(f"Launched: ID {sim_id}"),
                                   messagebox.showinfo("cloudHPC", f"Simulation launched\nID = {sim_id}"),
                                   root.destroy()))

        threading.Thread(target=worker, daemon=True).start()

    ttk.Button(frm, text="Load", command=load_options).grid(row=1, column=2, sticky="e")
    launch_btn = ttk.Button(frm, text="Launch", command=do_launch)
    ttk.Button(frm, text="Cancel", command=root.destroy).grid(row=8, column=2, sticky="e")
    ttk.Label(frm, textvariable=status, wraplength=380, foreground="gray").grid(
        row=9, column=0, columnspan=3, sticky="w", pady=(8, 0))

    if apikey.get():
        load_options()

    root.mainloop()


if __name__ == "__main__":
    main()
