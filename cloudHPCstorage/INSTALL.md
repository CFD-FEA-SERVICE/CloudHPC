# cloudHPCstorage

Access your cloudHPC storage as a local drive, directly from File Explorer (Windows) or from your home folder (Ubuntu / Debian).

## Before you start

- Download **[cloudHPCstorage.zip](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases/download/v0.1-alpha/cloudHPCstorage.zip)** and extract it.
- You need your key file **`cfd-fea-service-cloud.json`**. If you don't have it, write to [info@cloudhpc.cloud](mailto:info@cloudhpc.cloud?subject=cloudHPCstorage%20activation).

> **Keep the key file private:** anyone who has it can access your storage.

Any previous cloudHPCstorage installation is detected and replaced automatically: you don't need to uninstall it first.

## Windows

*Windows 10 / 11, 64-bit.*

1. Open the `cloudHPCstorage\Win64` folder.
2. Copy your key file `cfd-fea-service-cloud.json` into this folder.
3. Double-click **`install.exe`**. When Windows asks for permission, click **Yes**.
   - If Windows SmartScreen appears, click **More info** → **Run anyway**.
   - If your antivirus blocks `install.exe`, double-click **`install.cmd`** instead.
4. In the setup window:
   - check that the key file has been found (otherwise click **Browse...** to select it);
   - choose a free **drive letter**;
   - click **Install**.
5. Open **File Explorer → This PC**: your cloudHPC storage appears as a network drive.

The drive is connected automatically every time you log in.
If the setup asks you to restart the PC, do it: the drive will appear after the restart.

**Uninstall:** *Settings → Apps → cloudHPCstorage*, or double-click `uninstall.cmd`.

## Ubuntu / Debian

*64-bit (amd64), with systemd.*

1. Copy your key file `cfd-fea-service-cloud.json` into the `cloudHPCstorage/Debian64` folder.
2. Open a terminal in that folder and run, **as your normal user** (not with `sudo`):

   ```bash
   bash install.sh
   ```

3. Enter your password when asked.
4. Your storage is now available at:

   ```bash
   cd $HOME/cloudHPCstorage
   ```

The storage is mounted automatically at every boot.

**Uninstall:**

```bash
bash uninstall.sh
```

## Troubleshooting

| Problem | Solution |
|---|---|
| *"Google rejected the activation file"* | Your key has been disabled: ask [info@cloudhpc.cloud](mailto:info@cloudhpc.cloud) for a new one and run the installer again. |
| *"Activation file not found"* | Put `cfd-fea-service-cloud.json` in the same folder as the installer (Windows: or select it with **Browse...**). |
| The drive does not appear (Windows) | Log out and log in again, or restart the PC. |
| `install.exe` blocked | Use `install.cmd` from the same folder. |

When you contact us, please attach the log files:

- **Windows** – setup: `%TEMP%\cloudHPCstorage-setup.log`; drive: `C:\Program Files (x86)\CFD FEA Service\cloudHPCstorage\rclone.log`
- **Ubuntu / Debian** – output of `sudo journalctl -u cloudHPCstorage.service`
