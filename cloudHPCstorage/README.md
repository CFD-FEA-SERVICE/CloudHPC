# cloudHPCstorage

Mounts your [cloudHPC](https://cloudhpc.cloud) storage (a Google Cloud Storage bucket)
as a local drive, through [rclone](https://rclone.org) (+ [WinFsp](https://winfsp.dev) on Windows):

- **Windows 10 / 11**: a network drive in File Explorer (`cloudHPCstorage (\\cloudHPC) (K:)`),
  connected at every logon;
- **Ubuntu / Debian** (amd64, systemd): the folder `~/cloudHPCstorage`, mounted at every boot.

**Users:** download `cloudHPCstorage.zip` from the
[releases](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases/download/v0.1-alpha/cloudHPCstorage.zip)
and follow [INSTALL.md](INSTALL.md). You also need your activation file
`cfd-fea-service-cloud.json`: ask [info@cloudhpc.cloud](mailto:info@cloudhpc.cloud).

```
cloudHPCstorage/
├── INSTALL.md          user instructions (also shipped in the ZIP)
├── build.sh            builds dist/cloudHPCstorage.zip (--update pins newer rclone/WinFsp)
├── vendor.lock         pinned versions + SHA256 of rclone and WinFsp
├── admin/
│   └── build-exe.ps1   compiles Win64/install.ps1 into install.exe (on Windows)
├── Win64/              install.ps1, install.cmd, uninstall.cmd
└── Debian64/           install.sh, uninstall.sh
```

## How it works

### Activation file

The activation file is the JSON key of a Google Cloud service account, with one extra
field, `storage`: the name of the bucket to mount.

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "<sa>@<project>.iam.gserviceaccount.com",
  "...": "...",
  "storage": "<bucket>"
}
```

Optional field: `"bucket_policy_only": true` when the bucket uses *uniform bucket-level
access* (otherwise rclone tries to set object ACLs and fails).

The installers reject the file if `type: service_account`, `client_email`, `private_key`
or `storage` are missing, and they check that the key can list the bucket **before**
touching an existing installation: if the key has been disabled, the previous
installation is left as it was.

Access is granted and revoked on the Google Cloud side only: disabling or deleting the
service account key (or removing its IAM permission on the bucket) revokes the access.

### Windows (`install.exe` / `install.cmd`)

A single window asks for the activation file (found automatically when it is next to the
installer) and a free drive letter (the previous one, when reinstalling). Then it:

1. removes any previous version: the old `cloudHPCstorage` Windows service, the
   `rclone.exe` processes started from the install folder, the scheduled task;
2. installs or updates WinFsp (only if the installed one is older; reports if a
   reboot is needed);
3. copies `rclone.exe` and `install.ps1` to
   `C:\Program Files (x86)\CFD FEA Service\cloudHPCstorage` and registers
   *cloudHPCstorage* in *Settings → Apps* (uninstall);
4. copies the activation file and writes `rclone.conf` in the same folder, readable only
   by SYSTEM, Administrators and the user;
5. creates the scheduled task `\CFD FEA Service\cloudHPCstorage` that runs
   `rclone mount` hidden at every logon of the user (through `conhost.exe --headless`:
   started directly, rclone would open a console window that unmounts the drive when
   closed) and starts it immediately.

The drive belongs to the user who opened the session, even when the UAC elevation uses
a different administrator account. A logon task is used instead of a Windows service
because `rclone.exe` is not a service and a drive mounted as SYSTEM would not be the
user's drive.

Command line (unattended installs):

```
install.exe -Silent -Drive K: [-ActivationFile C:\path\cfd-fea-service-cloud.json]
install.exe -Uninstall [-Silent]
```

Exit codes: 0 ok, 3010 reboot needed, 1 error.
Logs: `%TEMP%\cloudHPCstorage-setup.log` (setup),
`C:\Program Files (x86)\CFD FEA Service\cloudHPCstorage\rclone.log` (drive).

### Ubuntu / Debian (`install.sh`)

Run as a normal user (`bash install.sh [file.json]`); `sudo` is asked only when needed:

1. installs `fuse3`, `jq` and the bundled rclone `.deb` (if the installed rclone is older);
2. removes any previous version: `cloudHPCstorage.service`,
   `/usr/bin/cloudHPCstorage-service`, the `[cloudHPCstorage]` section of
   `~/.config/rclone/rclone.conf` (the other sections are kept) and
   `~/.config/rclone/cfd-fea-service-cloud.json`;
3. copies the activation file and writes `rclone.conf` in `~/.config/cloudHPCstorage/`
   (mode 600);
4. creates `/etc/systemd/system/cloudHPCstorage.service` (`Type=notify`, runs as the
   user, restarts on failure) that mounts the bucket in `~/cloudHPCstorage`;
5. adds a bookmark to the file manager (GNOME).

If `~/cloudHPCstorage` contains local files (written while the storage was not mounted),
they are moved to `~/cloudHPCstorage.local-<date>`: rclone does not mount on non-empty
folders.

Logs: `sudo journalctl -u cloudHPCstorage.service`.

## Building the package

Requirements (Ubuntu / WSL): `sudo apt install zip unzip jq curl`.

```bash
./build.sh            # downloads the pinned rclone/WinFsp into vendor/ and builds dist/cloudHPCstorage.zip
./build.sh --update   # pins the latest rclone and WinFsp in vendor.lock, then builds
```

The third-party binaries are **not stored in this repository**. `vendor.lock` records
their versions and SHA256 (taken from rclone's `SHA256SUMS` and from the GitHub digest
of the WinFsp release); `build.sh` downloads them and refuses to build if a checksum
does not match. After `--update`, test the package and commit `vendor.lock`.

`build.sh` also:

- includes only the files meant for the users (no `admin/`, no README);
- **refuses** to build if a `.json` file (a key) ends up in the package;
- converts the Windows text files to CRLF line endings;
- **leaves out `install.exe`** if it was not rebuilt after the last change of
  `install.ps1` (checked through `Win64/install.exe.sha256`).

### install.exe

`install.exe` is `install.ps1` compiled with [ps2exe](https://github.com/MScholtes/PS2EXE)
(`-requireAdmin`: the user just double-clicks it and accepts UAC; `-noConsole`: only the
graphical window). It is a build output, not stored in git. On Windows, after every
change of `install.ps1`:

```powershell
powershell -ExecutionPolicy Bypass -File admin\build-exe.ps1
# optional code signing:  ... build-exe.ps1 -CertThumbprint <thumbprint>
```

then run `./build.sh` again. Executables built with ps2exe are sometimes flagged by
antivirus software: this is why the ZIP also contains `install.cmd`, which runs the
same `install.ps1`. Signing the exe reduces the problem.

## Releasing

The [cloudHPCstorage workflow](../.github/workflows/cloudhpc-storage.yml) compiles
`install.exe` on a Windows runner, builds the ZIP on Linux and keeps it as a workflow
artifact on every push to `cloudHPCstorage/`. Run it manually from the *Actions* tab to
also publish `cloudHPCstorage.zip` on the `v0.1-alpha` release, after testing the
artifact on Windows and Ubuntu.

To release by hand: build `install.exe` (Windows), run `./build.sh`, test, upload
`dist/cloudHPCstorage.zip` to the release.

## Creating an activation file (administrators)

```bash
gcloud iam service-accounts keys create sa-key.json --iam-account=<sa>@<project>.iam.gserviceaccount.com
jq --arg s <bucket> '. + {storage: $s}' sa-key.json > cfd-fea-service-cloud.json && rm sa-key.json
```

The service account needs read/write access to the bucket (e.g. *Storage Object Admin*
on that bucket only).

## Third-party software

The ZIP redistributes, unmodified:

- [rclone](https://github.com/rclone/rclone), MIT license;
- [WinFsp](https://github.com/winfsp/winfsp), GPLv3 with FLOSS exception.

[ps2exe](https://github.com/MScholtes/PS2EXE) (MS-PL) is used only to build `install.exe`.

## License

GPLv3, like the rest of this repository: see [LICENSE](../LICENSE).
