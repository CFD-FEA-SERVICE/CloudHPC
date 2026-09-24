# fds-6.7.5 — FDS 6.7.5 · staircase fire, three resolutions

A propane fire in a 4.2 × 2.4 × 12.24 m stairwell, provided at three grid
resolutions. The point of the folder is not the fire itself but the comparison:
the same geometry solved coarse, fine, and fine-split-for-MPI, which is the
cheapest way to see what grid resolution and parallel decomposition actually do
to an FDS run.

`roomFire-fds691/` in this repository is the same idea on a newer FDS release.

## The three variants

The three files cover the same stairwell at three grid resolutions, each a
factor of two finer than the previous one in every direction:

| File | Cell size (dx × dy × dz) | Cells | `&MESH` blocks | `T_END` | vCPU |
|---|---|---|---|---|---|
| `staircase_fire_fds675-coarse.fds` | 0.150 × 0.150 × 0.085 m | 64 512 | 1 | 10 s | 1 |
| `staircase_fire_fds675-fine-8core.fds` | 0.075 × 0.075 × 0.0425 m | 516 096 | 8 (2 × 2 × 2) | 3600 s | 8 |
| `staircase_fire_fds675-fine.fds` | 0.0375 × 0.0375 × 0.02125 m | 4 128 768 | 1 | 300 s | 1 |

FDS parallelises by assigning **one MPI process per `&MESH` block**. The
single-mesh variants cannot use more than one core no matter how many vCPU you
request — `-fine`, at 4.1 million cells on one process, is a deliberately
painful illustration of that. The `-8core` variant splits the domain into eight
equal blocks and is the one to run when you want the job to finish; note that it
sits at the *intermediate* resolution, not at the `-fine` one.

**Upload one file per folder.** The cloudHPC FDS script takes the first `.fds`
it finds in the working directory, so put each variant in its own storage
folder.

## Case at a glance

| | |
|---|---|
| Solver script | `fds6.7.5` |
| Suggested vCPU / RAM | 8 / `standard` for the `-8core` variant; 1 / `standard` for the others |
| Fire | propane, `SOOT_YIELD` 0.03, `CO_YIELD` 0.07 |
| Source | prepared by CFD FEA SERVICE — see [Source and credits](#source-and-credits) |

## Run it on cloudhpc.cloud

1. **STORAGE → Add**: type a folder name — say `staircase-8core` — in the
   *Dirname* text box, drop **one** `.fds` file in the *File* box, press
   **Save**.
2. **SIMULATIONS → Add**:
   - **vCPU** `8` for the `-8core` file, `1` otherwise
   - **RAM** `standard`
   - **Folder** `staircase-8core`
   - **Script** `fds6.7.5`
3. **Save**. The log echoes the detected `&MESH` count and the CHID before the
   time-step banner starts.
4. Download the results and open the `.smv` file in Smokeview.

## Run it with cloudHPCexec

`cloudHPCexec` uploads the whole current directory, so work from a folder that
holds only the variant you want to run:

```bash
mkdir -p staircase-8core && cp staircase_fire_fds675-fine-8core.fds staircase-8core/
cd staircase-8core

cloudHPCexec                                                # interactive
cloudHPCexec -batch 8 standard fds6.7.5 staircase-8core     # non-interactive
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

## What to expect

`*_hrr.csv` for the heat release rate, `*_devc.csv` for any devices, and the
`.smv` file plus slice data for Smokeview. The coarse variant finishes in
minutes; `-fine` on a single core is an overnight job.

## Restarting and SPOT instances

These files do not set `DT_RESTART`. Before running anything long — and always
before running on a SPOT instance — add

```
&DUMP DT_RESTART=300.0 /
```

so FDS writes restart files and the platform can resume after a reboot. Aim for
a restart file every 2–5 hours of wall-clock time.

To extend a finished run, raise `T_END` in the `.fds` file and relaunch with
exactly the same vCPU, RAM, folder and script.

## A note on FDS versions

The platform carries `fds6.7.0` through `fds6.11.1` plus `fdsNighly`. NIST
changes defaults and occasionally retires parameters between minor releases, so
results can move. Pin the version your model was validated against — that is why
the folder name carries it.


## Source and credits

The three `.fds` files were **prepared by CFD FEA SERVICE** for this repository
as a resolution and parallel-scaling demonstration. They are not copies of an
upstream NIST case.

| | |
|---|---|
| Solver | Fire Dynamics Simulator (FDS), by NIST with VTT and others |
| Source code | [github.com/firemodels/fds](https://github.com/firemodels/fds) |
| Documentation | [pages.nist.gov/fds-smv](https://pages.nist.gov/fds-smv/) |
| Licence | public domain (a work of the U.S. federal government); third-party components carry their own terms |

For validated benchmark cases with matching experimental data, see the
[Validation](https://github.com/firemodels/fds/tree/master/Validation) suite in
the FDS repository.
