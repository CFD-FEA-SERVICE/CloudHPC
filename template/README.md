# template — recommended solver input templates

Recommended, cloudHPC-ready input templates for the most common solvers available on the platform. Start from these files to make sure your case uses settings compatible with the cluster environment (parallel decomposition, restart, runtime monitoring, ...).

All the recommendations collected here come from the [cloudHPC help guide](https://docs.cloudhpc.cloud/). For complete, ready-to-run cases see [`exampleCloudHPC/`](../exampleCloudHPC).

## Content

| Folder | Solver | Files |
|---|---|---|
| [`OpenFOAM/system/`](OpenFOAM/system) | OpenFOAM | `controlDict`, `decomposeParDict` — run control, restart and runtime monitors; domain decomposition automatically adapted to the vCPU selected |
| [`OpenFOAM-custom/`](OpenFOAM-custom) | OpenFOAM (v2412) | complete case with a custom solver (`myScalarTransportFoam/`) and a custom boundary condition library (`myCustomBC/`) compiled by cloudHPC before the run |
| [`code-aster/`](code-aster) | code_aster | `export` (job definition), `input.comm` (MPI-ready command file skeleton), `base-stage1/` (database folder for restarts) |
| [`FDS/`](FDS) | FDS | `template.fds` — multi-mesh input with `MPI_PROCESS`, restart dump, pressure-zone settings and devices for runtime plots |
| [`custom-script/`](custom-script) | custom-script | `run.sh` — skeleton of a bash script executed by the _custom-script_ command |
| [`python-script/`](python-script) | custom-script | `script.py`, `requirements.txt`, `input.json` — parallel Python job with dependencies, runtime CSV monitor and checkpoint/restart |

Copy the relevant template into your case, adapt it to your model, then upload the case folder to the storage.

## General rules

* **Folder and file names** must not contain special characters such as `, ( ) ' $ ~ " #`.
* **Compressed uploads**: the archive name must match the folder it contains (or leave the folder inside and fill the _Dirname_ box). See [storage](https://docs.cloudhpc.cloud/storage/).
* **Instance selection**: _highcpu_, _standard_ and _highmem_ use the same hardware and only differ in RAM (1, 4, 8 GB per vCPU): start from _highcpu_ and move up only if you get the `RAM used > 80.0%` warning. _highcore_ and _hypercore_ give physical cores without hyper-threading, best for MPI-only solvers such as OpenFOAM.
* **SPOT instances** can be rebooted at any time: only FDS and OpenFOAM are set up to restart automatically from the last saved results. Other software and custom scripts lose the computed time on reboot.
* **Runtime plots**: every CSV file produced during the run is plotted in the simulation page.
* **Results** are uploaded to the storage at the end of the run, every 10 hours and when pressing _SYNC_. Storage files are deleted after 60 days.

## OpenFOAM

Files: [`OpenFOAM/system/controlDict`](OpenFOAM/system/controlDict), [`OpenFOAM/system/decomposeParDict`](OpenFOAM/system/decomposeParDict).

* The case needs the `0`, `constant` and `system` folders, and `constant/polyMesh` unless the mesh is generated in the run (or copied from the _Mesh_ folder selected when launching the simulation).
* `controlDict`
  * `application` selects the solver. On openfoam.org v11+ use `application foamRun;` plus `solver <module>;`.
  * `startFrom latestTime;` is required: it makes SPOT reboots and restarts continue from the last saved time. The system enforces it with a warning if missing.
  * `writeInterval` is also the restart frequency on SPOT instances; `purgeWrite N` keeps only the last N saved times.
  * Every function object in `functions` writing into `postProcessing/` becomes a runtime chart.
  * To restart a finished or soft-stopped run, increase `endTime` and launch a new simulation with the same vCPU, RAM, folder and script.
  * Custom cloudHPC entries (see below) switch on extra steps of the run.
* `decomposeParDict`
  * Use `method scotch;` (suggested) or `hierarchical`. `numberOfSubdomains` and the `n` coefficients are updated automatically to match the vCPU selected. Other methods trigger the `incorrect decomposeParDict file` error and are not adapted to the vCPU.
  * OpenFOAM always runs in parallel: select at least vCPU = 2 on _highcore_/_hypercore_ or vCPU = 4 on the other instances.

### Custom `controlDict` entries

cloudHPC reads a few extra entries from `system/controlDict` to trigger optional steps. OpenFOAM ignores them, so they can stay in the file when running elsewhere. They are listed, commented out, in the template: uncomment the ones you need. Boolean switches must be written exactly as `true` (`yes`/`on` are not recognised).

Mesh stage — applied only when the mesh is generated during the run (no `constant/polyMesh` uploaded, or a meshing script selected), in the order of the table, after snappyHexMesh/cfMesh/blockMesh:

| Entry | Values | Effect | Extra files required |
|---|---|---|---|
| `splitMesh` | `true` | splits the mesh into one region per cellZone (every cell must belong to a cellZone), e.g. for CHT cases | — |
| | `largest` | keeps only the largest connected region, removing mesh generated on the wrong side of the STL surfaces | — |
| `nExtrusion` | `N` | performs N mesh extrusions from boundary patches, in sequence | `system/extrudeMeshDict.0` … `system/extrudeMeshDict.<N-1>` |
| `scaleFactor` | number | scales the final mesh uniformly, e.g. `0.001` for a geometry drawn in mm | — |

Solver stage:

| Entry | Values | Effect |
|---|---|---|
| `potentialFoam` | `true` | runs potentialFoam before the solver to initialise the U and p fields |

## OpenFOAM custom code

Folder: [`OpenFOAM-custom/`](OpenFOAM-custom) — solver script `openFoam-v2412`.

Upload your source code **inside the case folder**, next to `0`, `constant` and `system`. Before running, cloudHPC compiles it on the instance with the same OpenFOAM version selected for the run:

```
OpenFOAM-custom/
├── Allwmake                    optional master build script: library first, then solver
├── 0/                          T (uses the custom BC), U (frozen velocity)
├── constant/transportProperties DT and decayRate read by the custom solver
├── system/                     controlDict, blockMeshDict, decomposeParDict, fvSchemes, fvSolution
├── myScalarTransportFoam/      custom solver: ddt(T) + div(phi,T) - laplacian(DT,T) = -decayRate*T
│   ├── Make/files              EXE = $(FOAM_USER_APPBIN)/myScalarTransportFoam
│   ├── Make/options
│   ├── createFields.H
│   └── myScalarTransportFoam.C
└── myCustomBC/                 custom library: sineWaveFixedValue boundary condition
    ├── Make/files              LIB = $(FOAM_USER_LIBBIN)/libmyCustomBC
    ├── Make/options
    └── sineWaveFixedValueFvPatchScalarField.{H,C}
```

Compilation sequence:

1. The OpenFOAM environment of the selected version is sourced.
2. If an `Allwmake` is present in the case root, it is executed first (highest priority): use it when the build order matters, e.g. a solver linking a library of the same case. The template one builds `myCustomBC` and then `myScalarTransportFoam`; delete it to rely on the automatic per-folder build below.
3. Every subfolder of the case root is then visited: a local `Allwmake` is executed if present, otherwise the binary paths in `Make/files` are patched and `wmake .` is run. The output goes to `<folder>_compilation.log` (`Allwmake.log` for the root script).
4. The solver in `controlDict/application` is executed as usual.

Rules:

* With an `Allwmake` (root or folder level) the binary paths are **not** patched: `Make/files` must already target `$(FOAM_USER_APPBIN)` / `$(FOAM_USER_LIBBIN)`, as in the template. Keep the script executable and in Unix line endings.
* Each source folder must sit directly in the case root and contain the standard `Make/files` and `Make/options`. Target `$(FOAM_USER_APPBIN)` for applications and `$(FOAM_USER_LIBBIN)` for libraries.
* Select the custom solver with `application myScalarTransportFoam;` and load custom libraries with `libs ("libmyCustomBC.so");` in `system/controlDict`.
* Do not upload binaries (`.so`, executables, `Make/linux64*`, `lnInclude`) compiled on your workstation: the code is always compiled fresh on the cloud.
* Code written for openfoam.com does not usually compile on openfoam.org and vice versa: the template is written and tested for **v2412**. On openfoam.org v11+ custom physics are written as solver modules run by `foamRun`.
* If the run stops right after start, check the `*_compilation.log` files for compiler errors.

More: [How to compile and execute custom OpenFOAM code on cloudHPC](https://cloudhpc.cloud/2026/07/24/how-to-compile-and-execute-custom-openfoam-code-on-cloudhpc-cloud/).

## code_aster

Files: [`code-aster/export`](code-aster/export), [`code-aster/input.comm`](code-aster/input.comm), [`code-aster/base-stage1/`](code-aster/base-stage1).

Upload at least three files: the `.export`, the `.comm` and the mesh (`.med` or `.unv`). The file names in the `F` lines of the export must match the uploaded files, and the `UNITE` numbers in the `.comm` must match the unit numbers in the export (mesh on 2, results on 3 in the template).

Parallel settings in `export`:

```
P mpi_nbcpu 4      # number of MPI processes - USER defined, = nCORE in the .comm
P mpi_nbnoeud 1    # number of nodes         - always 1 on cloudHPC
P ncpus 8          # number of threads       - updated by cloudHPC
```

* **MPI versions** (suffix `_mpi`, e.g. 17.0): set `mpi_nbcpu` and `nCORE` in `input.comm` to the same value. Any extra vCPU is used as OpenMP threads. The template reads the mesh with `PARTITIONNEUR='PTSCOTCH'`, decomposes the model with `DISTRIBUTION=_F(METHODE='SOUS_DOMAINE', ...)` and uses a distributed solver (`MUMPS` or `PETSC` with `MATR_DISTRIBUEE='OUI'`).
* **OpenMP-only versions**: set `P mpi_nbcpu 1`; the `.comm` produced by AsterStudy is usually adequate as it is.
* **Restart**: the line `R base base-stage1 RC 0` saves the database into `base-stage1/`. To continue the analysis replace `DEBUT()` with `POURSUITE()` in the `.comm` and read the saved database back (see [Resume your code_aster analysis](https://cloudhpc.cloud/2022/09/14/resume-your-code_aster-analysis/)).

## FDS

File: [`FDS/template.fds`](FDS/template.fds).

* Upload a single `.fds` file (export it from PyroSim or any other UI — `.psm` files are not accepted).
* **Meshes and vCPU**
  * Use several `&MESH` lines, each with at least 15,000-20,000 cells and a similar number of cells.
  * Use `MPI_PROCESS` to group small meshes on one core; the values must be in **ascending order**.
  * vCPU = number of `&MESH` (or `MPI_PROCESS` groups) × 2 on _highcpu_/_standard_/_highmem_/_hypercpu_, × 1 on _highcore_/_hypercore_.
  * A file with a single `&MESH` of at least 40,000 cells run with vCPU ≥ 4 is decomposed automatically by cloudHPC. Check the result in Smokeview.
* **Restart**: `&DUMP DT_RESTART=...` writes restart files used after SPOT reboots and when running again with a higher `T_END`. Aim for one restart file every 2-5 hours of wall time.
* **Pressure zones**: `&MISC MINIMUM_ZONE_VOLUME=1.0` avoids a large number of tiny pressure zones that hurt scalability.
* **Devices**: `&DEVC` outputs are written to CSV and plotted at runtime. `VISIBILITY`, `RADIATIVE HEAT FLUX` and `GAUGE HEAT FLUX GAS` devices slow down AMD processors: use _hypercore_/_hypercpu_ instances with them.
* ETA of the simulation is reported in the output for FDS runs.

More: [FDS scalability](https://docs.cloudhpc.cloud/scalability/#fds), [split FDS meshes with BlenderFDS](https://cloudhpc.cloud/2022/09/15/split-fds-mesh-using-blenderfds/).

## CalculiX

No dedicated template: see [`exampleCloudHPC/beam-ccx221`](../exampleCloudHPC/beam-ccx221) for a complete `.inp` case. The solver name selected on cloudHPC tells which linear solver library it was built with:

| Version suffix | Library | `.inp` keyword |
|---|---|---|
| none (default) | SPOOLES | `*STATIC, SOLVER=SPOOLES` |
| `PARDISO` | PARDISO | `*STATIC, SOLVER=PARDISO` |
| `PASTIX` | PaStiX | `*STATIC, SOLVER=PASTIX` |
| `MPI` | compiled with OpenMPI | — |

Results are packed into `CALCULIX.tar.gz`. More: [code_aster vs CalculiX scalability](https://cloudhpc.cloud/2025/09/15/decoding-performance-a-scalability-showdown-between-calculix-and-code_aster/).

## SU2

No dedicated template: see [`exampleCloudHPC/naca0012-su2830`](../exampleCloudHPC/naca0012-su2830) and [`exampleCloudHPC/SU2_8.3_Turbulent_ONERAM6`](../exampleCloudHPC/SU2_8.3_Turbulent_ONERAM6). Settings useful on cloudHPC:

```
TABULAR_FORMAT= CSV            % history.csv is plotted at runtime
CONV_FILENAME= history
OUTPUT_WRT_FREQ= 500           % save restart/solution files regularly
RESTART_FILENAME= restart_flow
% to continue a previous run:
% RESTART_SOL= YES
% SOLUTION_FILENAME= restart_flow
```

The SU2 GUI is available on the `ubuntu-2404-static` instance. OpenFOAM meshes can be converted with [`SU2/OF2SU2.py`](../SU2/OF2SU2.py). More: [SU2 scalability on cloudHPC](https://cloudhpc.cloud/2025/10/01/su2-and-the-challenge-of-scalability-how-cloudhpc-is-speeding-up-cfd-simulations/).

## Custom script

Files: [`custom-script/run.sh`](custom-script/run.sh) (bash), [`python-script/`](python-script) (python).

The _custom-script_ command (e.g. `custom-script-u24`, Ubuntu 24.04 with Python 3.12) executes the scripts of the selected folder in this order:

1. every bash (`.sh`) file: made executable (`chmod ugo+x`), run, output saved to a `.log` file;
2. every python (`.py`) file: a virtual environment `py-cloudhpc` is created and activated, `pip install -r requirements.txt` installs the dependencies, the script is run with `python3` and its output saved to a `.log` file.

Keep in the folder only the scripts to run plus their input files: helper modules imported by your script go in a subfolder, or drive everything from one `.sh`.

### Python with dependencies

Folder: [`python-script/`](python-script).

| File | Purpose |
|---|---|
| `script.py` | the job: Monte Carlo estimate of pi spread on all the cores with `multiprocessing` |
| `requirements.txt` | packages installed in the `py-cloudhpc` venv before the script starts (`numpy`, `matplotlib`) |
| `input.json` | run parameters, so the script does not need editing between runs |

Patterns worth reusing:

* **Dependencies**: list in `requirements.txt` only what you import, pinning versions (`numpy==2.1.3`) for reproducible runs. Every package is installed at the start of the job, so a long list slows down short runs.
* **Parallelism**: size the work on `os.cpu_count()` so the same script uses all the vCPU selected. Guard the entry point with `if __name__ == "__main__":` when using `multiprocessing`.
* **Runtime plots**: `monitor.csv` is appended every iteration and plotted live in the simulation page. Use `matplotlib.use("Agg")` to save figures, there is no display.
* **Restart**: custom scripts are not restarted automatically after a SPOT reboot. `checkpoint.json` stores the progress: raise `iterations` in `input.json` and launch again on the same folder to continue from the last completed iteration, or delete `checkpoint.json` and `monitor.csv` to start over.
* **Results**: everything written in the working folder (`results.json`, `convergence.png`, logs) is uploaded back to the storage.

For another example see [`exampleCloudHPC/python3.12`](../exampleCloudHPC/python3.12).

## Other solvers

* **OpenRADIOSS**: results are packed into `OPENRADIOSS.tar.gz`. More: [OpenRADIOSS scalability on cloudHPC](https://cloudhpc.cloud/2025/05/27/unlocking-extreme-performance-openradioss-scalability-on-cloudhpc-with-amd-epyc-processors/).
* **code_saturne**: results are packed into `SATURNE-solution.tar.gz`.

---

Part of the [CloudHPC](https://github.com/CFD-FEA-SERVICE/CloudHPC) repository.
