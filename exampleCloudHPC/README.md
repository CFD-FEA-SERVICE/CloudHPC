# exampleCloudHPC — ready-to-run example cases

Complete, self-contained cases that can be uploaded and run as-is on
[cloudhpc.cloud](https://cloudhpc.cloud). They serve three purposes: a smoke
test of a new account, a reference for how a case folder must be laid out for
each solver, and a starting point for your own simulations.

Every folder has its own `README.md` with the case description, the exact
settings to use on the web app, the equivalent `cloudHPCexec` command line, and
what the results should look like.

## The examples

### Computational fluid dynamics

| Folder | Solver script | vCPU | What it is |
|---|---|---|---|
| [`pitzDaily-of13/`](pitzDaily-of13/) | `openFoam-of13` | 4 | Turbulent flow over a backward-facing step. Shows the OpenFOAM 11+ modular solver (`foamRun -solver incompressibleFluid`). ~15 s. |
| [`damBreak-v2412/`](damBreak-v2412/) | `openFoam-v2412` | 4 | Collapsing water column, two-phase VOF with `interFoam`. Shows the ESI/OpenCFD dictionary layout. ~3 s. |
| [`motorBike-of12/`](motorBike-of12/) | `openFoam-of12` | 8 | External aerodynamics around a motorbike, meshed at run time with `snappyHexMesh`. The one case here that really rewards parallel hardware. |
| [`naca0012-su2830/`](naca0012-su2830/) | `SU2_CFD8.3.0` | 4 | Transonic inviscid NACA 0012. Converges to CL = 0.332, CD = 0.0216 in 259 iterations. |
| [`SU2_8.3_Turbulent_ONERAM6/`](SU2_8.3_Turbulent_ONERAM6/) | `SU2_CFD8.3.0` | 16 | Transonic RANS over the ONERA M6 wing — the standard 3D validation case. |

### Fire and safety

| Folder | Solver script | vCPU | What it is |
|---|---|---|---|
| [`roomFire-fds691/`](roomFire-fds691/) | `fds6.9.1` | 2 | 360 kW compartment fire with a doorway, split over two MPI meshes. ~2 min. |
| [`fds-6.7.5/`](fds-6.7.5/) | `fds6.7.5` | 1–8 | The same stairwell fire at three grid resolutions — a direct look at what resolution and MPI decomposition cost you. |

### Structural and multiphysics

| Folder | Solver script | vCPU | What it is |
|---|---|---|---|
| [`beam-ccx221/`](beam-ccx221/) | `calculiX-2.21` | 4 | Cantilever beam: linear static plus the first ten modes, both checked against closed-form results. ~2 s. |
| [`flange-ca136/`](flange-ca136/) | `codeAster-17.0_mpi` | 8 | Flange FEM analysis driven by a parametric command file — flip a boolean to switch between static, modal, dynamic and fatigue runs. |
| [`poisson-fenicsx060/`](poisson-fenicsx060/) | `FEniCSx-0.6.0-r1` | 4 | Poisson problem with a manufactured solution, so the run reports its own error. Use cloudHPC as a FEM development platform. |

### Discrete elements, building energy, and custom code

| Folder | Solver script | vCPU | What it is |
|---|---|---|---|
| [`silo-liggghts380/`](silo-liggghts380/) | `LIGGGHTS-3.8.0` | 4 | DEM: 1200 spheres poured into a cylindrical silo, analytical walls, no STL needed. |
| [`office-ep2520/`](office-ep2520/) | `EnergyPlus-25.2.0` | 1 | Single-zone office on design days only — no weather file required. Runs in 0.15 s. |
| [`gpuBenchmark-cuda123/`](gpuBenchmark-cuda123/) | `custom-script-cuda12.3` | 4 + `basegpu` | GPU smoke test: device query, SAXPY bandwidth, tiled SGEMM. |
| [`python3.12/`](python3.12/) | `custom-script-u24` | 1 | The minimal custom-script job: one Python file plus `requirements.txt`. |

## Solver versions

The platform carries many versions of each solver side by side, and for most of
them **the input files are not interchangeable**. The folder names here record
the version each case was built for. A quick orientation:

| Solver | Versions available | What changes between them |
|---|---|---|
| OpenFOAM — Foundation | `of5` … `of14` | From v11 a single `foamRun` replaces the per-physics executables, with the module named in `controlDict`; recent releases use `constant/physicalProperties` and `constant/momentumTransport` |
| OpenFOAM — ESI/OpenCFD | `v1706` … `v2606` | Keeps per-physics executables and the `transportProperties` / `turbulenceProperties` names; `0.orig/` restored by `restore0Dir` |
| FDS | `fds6.7.0` … `fds6.11.1`, `fdsNighly` | Mostly forward-compatible, but NIST changes defaults and retires parameters between minor releases — results can move |
| SU2 | `SU2_CFD8.3.0` | — |
| CalculiX | `2.18-PARDISO-MPI`, `2.19-PARDISO`, `2.21` | Same input syntax; the PARDISO builds are much faster on large models |
| code_aster | `codeAster-17.0_mpi` | Deprecated keywords are reported as alarms in `message.dat`, not as failures — read it |
| EnergyPlus | `9.4.0`, `9.6.0`, `25.2.0` | Strict: the `Version` object must match the executable, and the schema changes nearly every release. Convert with `IDFVersionUpdater` |

The list above is a snapshot. The authoritative list for **your** account is the
*Script* dropdown on the simulation page, or the menu `cloudHPCexec` shows you.

## How to run any of these — the web app

1. **Package the case.** Compress the *contents* of the folder, so that opening
   the archive shows the case files directly rather than a wrapper directory.
   `zip`, `tar.gz`, `7z`, `rar` and `xz` are all accepted. Single-file cases
   (FDS, EnergyPlus, FEniCSx) need no compression at all.
2. **Upload.** **STORAGE → Add**, type a folder name in the *Dirname* text box
   to create it, drop the file in the *File* box, **Save**. The platform unpacks
   archives for you.
3. **Launch.** **SIMULATIONS → Add**, then set **vCPU**, **RAM**, **Folder** and
   **Script**. *Mesh* is optional and only used by some solvers.
4. **Monitor.** The simulation list shows the live log. **Soft stop** ends a run
   and keeps the results; **hard stop** discards them.
5. **Collect.** Results land back in the storage folder for download.

The full walkthrough, with screenshots, is in the
[online documentation](https://docs.cloudhpc.cloud).

## How to run any of these — cloudHPCexec

[`cloudHPCexec`](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/exampleAPI/cloudHPCexec)
does all four steps from the terminal: it compresses the current directory,
uploads it, launches the job and hands you the simulation ID. Install it from
the [releases](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases) page:

```bash
sudo dpkg -i cloudHPCexec.Ubuntu.deb
cloudHPCexec -help
```

On first use it asks for your API key and stores it in `~/.cfscloudhpc/apikey`
(see the [API key documentation](https://docs.cloudhpc.cloud)).

```bash
cd <example-folder>

# interactive: menus for vCPU, RAM and solver
cloudHPCexec

# non-interactive: vCPU, RAM, script, storage folder [, mesh folder]
cloudHPCexec -batch 4 standard openFoam-of13 pitzDaily-of13
```

The interactive mode prints the equivalent `-batch` line before it launches,
which is the easiest way to discover the exact arguments for a new solver.

Useful follow-ups:

| Command | Does |
|---|---|
| `cloudHPCexec -wait <ID>` | blocks until the simulation finishes |
| `cloudHPCexec -download` | fetches and unpacks results from the storage |
| `cloudHPCexec -ssh <ID>` | opens a shell on the running instance |
| `cloudHPCexec -vnc <ID>` | opens a remote desktop on the running instance |
| `cloudHPCexec -soft <ID>` | stops the run and keeps the results |
| `cloudHPCexec -hard <ID>` | kills the run and discards them |
| `cloudHPCexec -batchONL …` | re-runs a folder already in the storage, with no upload |
| `cloudHPCexec -batchREG …` | runs on a REG instance instead of SPOT |
| `cloudHPCexec -update` | updates the tool itself |

`-batchONL` is the one to remember for the larger cases: re-uploading the 22 MB
ONERA M6 mesh on every launch gets old quickly.

Scripting the tool is how parameter sweeps are done here —
[`scripts/codeAster-13.6`](../scripts/codeAster-13.6) loops over solver settings
and core counts and fires one `-batch` per combination.

## Choosing vCPU and RAM

**RAM** selects the instance family, and the amount quoted is *per vCPU*:

| Selection | RAM per vCPU | Notes |
|---|---|---|
| `highcpu` | 1 GB | hyper-threaded |
| `standard` | 4 GB | hyper-threaded — the default choice |
| `highmem` | 8 GB | hyper-threaded; what direct FEM solvers want |
| `highcore` | 2 GB | physical cores, no hyper-threading |
| `hypercpu` / `hypercore` | 1 / 2 GB | premium vCPU |
| `basegpu` | 8 GB | plus one NVIDIA T4 per 2 vCPU |

**vCPU** should match how the case is decomposed, and this is the single most
common mistake:

| Solver | What sets the parallelism |
|---|---|
| OpenFOAM | `numberOfSubdomains` in `system/decomposeParDict` |
| FDS | the number of `&MESH` blocks (or `MPI_PROCESS`) |
| code_aster | `mpi_nbcpu` × `ncpus` in the `export` file |
| CalculiX | shared memory only — `OMP_NUM_THREADS`, no MPI |
| EnergyPlus | single-threaded; parallelism means running many variants at once |

Asking for 32 vCPU on a case decomposed into 4 wastes 28 of them.

## SPOT instances and restarts

SPOT instances are cheaper but can reboot mid-run, and the platform then resumes
from the last checkpoint your solver wrote. That only works if the case is set
up for it:

- **OpenFOAM**: `startFrom latestTime;` in `system/controlDict`
- **FDS**: `&DUMP DT_RESTART=300.0 /` — aim for a checkpoint every 2–5 hours
- **code_aster**: `POURSUITE()` in place of `DEBUT()`, with the base directory kept
- **Custom scripts**: not covered — checkpoint yourself, or use REG instances

## Sources, credits and licensing

Every case names its origin, its upstream link and its licence in the *Source
and credits* section of its own README. In summary:

### Cases adapted from an upstream tutorial

| Case | Upstream source | Licence |
|---|---|---|
| `pitzDaily-of13/` | [OpenFOAM 13 — `incompressibleFluid/pitzDaily`](https://github.com/OpenFOAM/OpenFOAM-13/tree/master/tutorials/incompressibleFluid/pitzDaily), © The OpenFOAM Foundation | [GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) |
| `damBreak-v2412/` | [OpenFOAM v2412 — `multiphase/interFoam/laminar/damBreak`](https://develop.openfoam.com/Development/openfoam/-/tree/OpenFOAM-v2412/tutorials/multiphase/interFoam/laminar/damBreak/damBreak), © OpenCFD Ltd (ESI Group) | [GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) |
| `motorBike-of12/` | [OpenFOAM 12 — `incompressibleFluid/motorBike`](https://github.com/OpenFOAM/OpenFOAM-12/tree/master/tutorials/incompressibleFluid/motorBike), © The OpenFOAM Foundation | [GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) |
| `SU2_8.3_Turbulent_ONERAM6/` | [SU2 — Turbulent ONERA M6 tutorial](https://su2code.github.io/tutorials/Turbulent_ONERAM6/), © the SU2 Foundation | [LGPL v2.1](https://github.com/su2code/SU2/blob/master/LICENSE.md) |
| `naca0012-su2830/` | modelled on [SU2 — QuickStart](https://github.com/su2code/SU2/tree/master/QuickStart); mesh regenerated with [gmsh](https://gmsh.info/) | [LGPL v2.1](https://github.com/su2code/SU2/blob/master/LICENSE.md) / [GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) |
| `poisson-fenicsx060/` | [DOLFINx Poisson demo](https://github.com/FEniCS/dolfinx/blob/v0.6.0/python/demo/demo_poisson.py) and the [FEniCSx tutorial](https://jsdokken.com/dolfinx-tutorial/chapter1/fundamentals.html) by Jørgen S. Dokken | [LGPL v3](https://www.gnu.org/licenses/lgpl-3.0.html) |
| `silo-liggghts380/` | follows the [LIGGGHTS public tutorials](https://github.com/CFDEMproject/LIGGGHTS-PUBLIC/tree/master/examples/LIGGGHTS/Tutorials_public), © DCS Computing GmbH / CFDEM project | [GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) |

### Cases written for this repository

`roomFire-fds691/`, `beam-ccx221/`, `office-ep2520/` and
`gpuBenchmark-cuda123/` are original, released under
[GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) with the rest of this
repository. `fds-6.7.5/`, `flange-ca136/` and `python3.12/` were prepared by
CFD FEA SERVICE. Each README says which published documentation the input
follows and how the case was verified.

### The solvers themselves

| Solver | Project | Licence |
|---|---|---|
| OpenFOAM | [openfoam.org](https://openfoam.org/) (Foundation) · [openfoam.com](https://www.openfoam.com/) (ESI) | GPL v3 |
| FDS | [github.com/firemodels/fds](https://github.com/firemodels/fds), NIST | public domain (US federal government work) |
| SU2 | [su2code.github.io](https://su2code.github.io/) | LGPL v2.1 |
| CalculiX | [calculix.de](http://www.calculix.de/) | GPL v2 |
| code_aster | [code-aster.org](https://www.code-aster.org/), EDF R&D | GPL v3 |
| DOLFINx / FEniCSx | [fenicsproject.org](https://fenicsproject.org/) | LGPL v3 |
| LIGGGHTS | [cfdem.com](https://www.cfdem.com/) (derived from [LAMMPS](https://www.lammps.org/)) | GPL v2 |
| EnergyPlus | [energyplus.net](https://energyplus.net/), NREL / US DOE | BSD-style, 3-clause |
| gmsh | [gmsh.info](https://gmsh.info/) | GPL v2 |

## Related folders in this repository

| Folder | Contains |
|---|---|
| [`../exampleAPI/`](../exampleAPI/) | `cloudHPCexec` in Bash, Python/Tk and PowerShell, plus the Debian packaging |
| [`../template/`](../template/) | recommended cloudHPC-ready input templates for OpenFOAM and code_aster |
| [`../scripts/`](../scripts/) | open-source versions of the cluster execution scripts, showing exactly how solvers are launched |
| [`../readthedocs/`](../readthedocs/) | the sources of [docs.cloudhpc.cloud](https://docs.cloudhpc.cloud) |

---

Part of the [CloudHPC](https://github.com/CFD-FEA-SERVICE/CloudHPC) repository.
