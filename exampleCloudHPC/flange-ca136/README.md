# flange-ca136 — code_aster · flange FEM analysis

A linear static analysis of a flange: a traction load of 2000 N is applied to
the `traction` face, two symmetry planes are enforced with normal constraints,
and the `fixed` group is clamped. The mesh is a MED file exported from
SALOME-Meca.

What makes this folder worth reading is `fem.comm`. It is not a minimal command
file — it is a **parametric template**, with a block of boolean switches at the
top that turn whole analysis types on and off:

```python
PESOPROPRIO  = False    # self weight
STATICA      = True     # linear static            <- the one enabled here
MODALE       = False    # modal
DINAMICA_VIB = False    # vibration dynamics
FATICA       = False    # Wöhler fatigue
FATICA_VIB   = False    # vibration fatigue
```

Flip a switch, upload, re-run. The `export` file already declares result units
for every one of those analyses, so nothing else needs changing.

## Case at a glance

| | |
|---|---|
| Solver script | `codeAster-17.0_mpi` (see *Versions* below) |
| Suggested vCPU / RAM | 8 / `highmem` |
| Mesh | 1 221 nodes; 4 220 linear tetrahedra, 1 792 triangles, 269 segments |
| Mesh groups | `solid`, `symmetry1`, `symmetry2`, `fixed`, `traction` |
| Analysis | linear static, 10 iterations, results saved every 5 |
| Source | prepared by CFD FEA SERVICE — see [Source and credits](#source-and-credits) |

## Files

| File | Purpose |
|---|---|
| `export` | the code_aster job definition: resources, and the unit number of every input and result file |
| `fem.comm` | the command file — materials, model, loads, analysis switches |
| `mesh.med` | the SALOME-Meca mesh, read at unit 2 |
| `base-stage1/` | the result database directory, declared as `R base base-stage1` in the `export` — needed for `POURSUITE()` restarts |

The cloudHPC code_aster script locates the `*export` file in the folder,
rewrites its paths for the cluster and launches the run. That is why the
`export` file must be present and must name the other files correctly.

Parallel behaviour is set inside the `export`, not by the platform:

```
P mpi_nbcpu 1     # MPI processes
P ncpus 8         # OpenMP threads per process
```

Keep `mpi_nbcpu × ncpus` at or below the vCPU you request.

## Run it on cloudhpc.cloud

1. Compress the **contents** of this folder into `flange-ca136.zip` — the
   archive must open directly on `export`, `fem.comm`, `mesh.med` and
   `base-stage1/`.
2. **STORAGE → Add**: type `flange-ca136` in the *Dirname* text box, drop the
   archive in, press **Save**.
3. **SIMULATIONS → Add**:
   - **vCPU** `8`
   - **RAM** `highmem` — code_aster's direct solvers are memory-hungry
   - **Folder** `flange-ca136`
   - **Script** `codeAster-17.0_mpi`
4. **Save**, then download the results from **STORAGE**.

## Run it with cloudHPCexec

```bash
cd flange-ca136

cloudHPCexec                                                    # interactive
cloudHPCexec -batch 8 highmem codeAster-17.0_mpi flange-ca136   # non-interactive
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

This case is also a good candidate for a scripted parameter sweep — see
`scripts/codeAster-13.6` in this repository, which loops over solver choices and
core counts and fires one `cloudHPCexec -batch` per combination.

## What to expect

With `STATICA = True` the run produces `analisi_statica2_carico-esterno.rmed`
(the unit 32 result declared in the `export`), plus `message.dat` and the
`code_aster.log`. Open the `.rmed` in ParaView or SALOME-Meca.

Always read `message.dat`: code_aster reports convergence, mesh quality and
solver warnings there rather than on the standard output.

## Restarting

To continue from the saved base rather than starting over, replace `DEBUT()`
with `POURSUITE()` at the top of `fem.comm` — the commented line is already
there — and relaunch with the same resources. The `base-stage1/` directory
carries the state.

## Versions

This case was built against code_aster 13.6, which the folder name records. The
solver list the platform currently exposes contains **`codeAster-17.0_mpi`**;
check what your own account offers, either from the script dropdown on the
simulation page or with `cloudHPCexec` and the interactive menu.

When moving a deck from 13.6 to 17.0, the two things that usually need attention
are the `P version` line in the `export` and any command keywords deprecated in
between — code_aster reports those in `message.dat` as alarms rather than
failing outright, so read the file even when the job succeeds.


## Source and credits

`fem.comm`, `export` and `mesh.med` were **prepared by CFD FEA SERVICE** for
this repository. The parametric command file is their own template rather than
an upstream code_aster test case.

| | |
|---|---|
| Solver | code_aster, developed by EDF R&D |
| Home page | [code-aster.org](https://www.code-aster.org/) |
| Licence | [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) |
| Mesh format | MED, exported from SALOME-Meca — the [SALOME platform](https://www.salome-platform.org/) bundled by EDF with code_aster |

code_aster ships a very large validation suite (the `astest` directory of the
source distribution, documented as the *V* series of the official
documentation), which is where to look for worked examples of a specific
command or element type.
