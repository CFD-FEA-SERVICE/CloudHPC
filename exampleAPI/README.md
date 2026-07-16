# exampleAPI — cloudHPCexec clients

Working clients for the cloudHPC **REST API**: upload files, choose solver/script/vCPU, launch simulations and follow their execution directly from your machine. The API key is stored locally in `~/.cfscloudhpc/apikey`. For the full API reference see the API pages of the [online documentation](https://docs.cloudhpc.cloud) (sources in `readthedocs/docs/API-*.md`).

## Content

| File / folder | Description |
|---|---|
| `cloudHPCexec` | Bash client — submit a simulation from the Linux terminal (`cloudHPCexec -help`) |
| `cloudHPCexec.py` | Python 3 / Tkinter GUI client (cross-platform; needs `requests`, `touch`) |
| `cloudHPCexec.ps1` | PowerShell client for Windows |
| `cloudHPCexec-1.1/` | Debian packaging tree (`DEBIAN/`, `usr/`) used to build the installable `.deb` of the Bash client |

Pre-built packages are published in the repository [releases](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases).
