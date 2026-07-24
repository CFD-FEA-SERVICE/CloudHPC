# CloudHPC

This is the official repository linked to the cloudHPC service offered by CFD FEA SERVICE, hosted at https://cloud.cfdfeaservice.it (documentation: https://docs.cloudhpc.cloud). With this repository you can access advanced functionalities of the platform such as:

* download the recommended *templates* for the most common solvers available online
* create and upload *your personal scripts* to the cloudHPC platform
* check the *API usage* and take advantage of the examples reported here
* download ready-to-run *example cases* for the main solvers (OpenFOAM, SU2, FDS, code_aster, Python)
* use the *mesh conversion utilities* (CGNS ↔ OpenFOAM, OpenFOAM → SU2) and the *Salome plugins*

The whole content of this repository is under the [GPLv3 license](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/LICENSE). Security policy: see [SECURITY.md](SECURITY.md).

## Repository structure

| Folder | Content |
|---|---|
| [`GUI/`](GUI/) | cloudHPC tools to perform simulations [![APP generation](https://github.com/CFD-FEA-SERVICE/CloudHPC/actions/workflows/cloudhpc-tools.yml/badge.svg)](https://github.com/CFD-FEA-SERVICE/CloudHPC/actions/workflows/cloudhpc-tools.yml) |
| [`OpenFOAM/`](OpenFOAM/) | Mesh conversion utility: CGNS → OpenFOAM polyMesh |
| [`SU2/`](SU2/) | Mesh conversion utility: OpenFOAM polyMesh → CGNS (for SU2) |
| [`exampleAPI/`](exampleAPI/) | `cloudHPCexec` clients (Bash, Python/Tkinter, PowerShell) and Debian packaging — submit simulations from your terminal via the cloudHPC REST API |
| [`exampleCloudHPC/`](exampleCloudHPC/) | Ready-to-run example cases: SU2 (ONERA M6), FDS 6.7.5 (staircase fire), code_aster (flange), OpenFOAM (motorBike), Python 3.12 |
| [`readthedocs/`](readthedocs/) | MkDocs sources of the online documentation published at https://docs.cloudhpc.cloud |
| [`salome/`](salome/) | Salome plugins and scripts (bounding-box cell estimation, geometry plugins, FEM pre-processing) |
| [`scripts/`](scripts/) | Open-source versions of the execution scripts used on the cluster (code_aster 13.6, FDS 6.7.4) |
| [`template/`](template/) | Recommended input templates for the solvers (OpenFOAM `system/`, code_aster export/comm) |
| `installFDS.ps1` | Windows PowerShell helper that installs Anaconda + FDS/Smokeview locally |

## Description

OS: Ubuntu 16.04/18.04/20.04 LTS - CENTOS 6.10/7/8

### cloudHPCexec

`cloudHPCexec` is a script which allows you to execute simulations directly from your Linux terminal. To install it just download the package made available for your operating system and follow the procedure reported in the release.

To get help once the package has been installed:

```bash
cloudHPCexec -help
```

Sources and platform variants (Bash, Python GUI, PowerShell) are available in the [exampleAPI](exampleAPI/) folder.

### Installation

It is possible to replicate the system managed by CFD FEA SERVICE Cloud HPC directly on your own computer. To do that you can check the latest [release](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases) which guides you on installing most of the software available on the platform.

### Execution scripts

CFD FEA SERVICE provides the open-source version of the scripts made available on the cluster which allow you to use some of the software. These scripts are present in the [scripts](scripts/) folder of this repository. Make sure you complete the "Installation" point in order to take advantage of these scripts.

### API

The cloudHPC platform exposes a REST API to upload files, launch simulations and retrieve results programmatically. See the [exampleAPI](exampleAPI/) folder for working clients, and the API section of the [online documentation](https://docs.cloudhpc.cloud) (sources in [readthedocs](readthedocs/)) for the full reference.
