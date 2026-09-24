# roomFire-fds691 — FDS 6.9.1 · compartment fire with a single doorway

A 360 kW propane fire burns in a 3.6 × 2.4 × 2.4 m room whose only opening is a
0.9 × 2.0 m doorway. The hot layer builds under the ceiling, spills out of the
top of the door while fresh air is drawn in at the bottom, and a rake of
thermocouples records the vertical temperature profile. It is the smallest
useful compartment-fire setup: large enough to show the physics you actually
care about in fire engineering, small enough to finish in minutes.

The case is split into **two meshes** so it runs on 2 MPI processes, which is
how FDS parallelises: one MPI process per `&MESH` block. `fds-6.7.5/` in this
repository shows the same idea at three different resolutions.

## Case at a glance

| | |
|---|---|
| Solver script | `fds6.9.1` |
| Suggested vCPU / RAM | 2 / `standard` |
| Mesh | 2 blocks of 18 × 24 × 24 = 10 368 cells each (0.10 m uniform), 20 736 total |
| Fire | 0.6 × 0.6 m burner, HRRPUA 1000 kW/m² ramped over 10 s → 360 kW |
| Simulated time | 30 s |
| Indicative runtime | ~2 min on 2 vCPU |
| Source | written for this repository — see [Source and credits](#source-and-credits) |

## Files

| File | Purpose |
|---|---|
| `roomFire.fds` | the complete input file — geometry, combustion, boundary conditions and outputs |

The cloudHPC FDS script locates the single `.fds` file in the folder, counts the
`&MESH` blocks (or reads `MPI_PROCESS`) to decide how many MPI ranks to start,
and fills the remaining vCPU with OpenMP threads. There is nothing else to
configure.

## Run it on cloudhpc.cloud

An FDS case is a single file, so this is the simplest possible upload — no
compression needed.

1. **STORAGE → Add**: type `roomFire-fds691` in the *Dirname* text box, drop
   `roomFire.fds` in the *File* box, press **Save**.
2. **SIMULATIONS → Add**:
   - **vCPU** `2` — one per `&MESH`
   - **RAM** `standard`
   - **Folder** `roomFire-fds691`
   - **Script** `fds6.9.1`
3. **Save**. The log echoes the detected mesh count, the CHID and then the FDS
   time-step banner.
4. Download the results and open `roomFire.smv` in Smokeview, or plot
   `roomFire_devc.csv` and `roomFire_hrr.csv` in any spreadsheet.

## Run it with cloudHPCexec

```bash
cd roomFire-fds691

cloudHPCexec                                             # interactive menus
cloudHPCexec -batch 2 standard fds6.9.1 roomFire-fds691  # non-interactive
```

```bash
cloudHPCexec -wait 12345      # block until it is done
cloudHPCexec -download        # fetch and unpack the results
```

## What to expect

After 30 s the fire has reached its full 360 kW, the upper layer sits around
270–310 °C and the interface has descended to roughly 0.3 m above the floor.
Useful outputs:

| File | Contains |
|---|---|
| `roomFire_hrr.csv` | heat release rate and the energy balance |
| `roomFire_devc.csv` | the four thermocouples, the doorway velocity and the layer height |
| `roomFire.smv` + slice files | Smokeview animation: temperature, velocity vectors and HRRPUV on the y = 1.2 m plane |

## Scaling it up, and running on SPOT

Split the domain into more `&MESH` blocks to use more cores — FDS needs one
block per MPI process, so 4 vCPU wants 4 meshes. Keep the blocks similar in
size, otherwise the slowest one paces the whole run.

`&DUMP DT_RESTART=300.0` is already set. On a SPOT instance the platform detects
the restart file FDS leaves behind and resumes from it after a reboot; on a
30 s case that never triggers, but leave the parameter in when you lengthen
`T_END`.

To continue a finished run, raise `T_END` in the `.fds` file and launch again
with **exactly the same** vCPU, RAM, folder and script: FDS picks up the
`.restart` files automatically.

## A note on FDS versions

The platform carries everything from `fds6.7.0` to `fds6.11.1` plus
`fdsNighly`. Input files are broadly forward-compatible, but NIST does change
defaults and occasionally retires parameters between minor releases, and results
can shift. Pin the version you validated your model against — that is why the
folder name carries it — and re-run a known case before moving a study to a
newer one.


## Source and credits

`roomFire.fds` was **written for this repository**; it is not a copy of an
upstream case. It follows the modelling conventions of the FDS User's Guide for
compartment fires — a lined enclosure, a ramped `HRRPUA` burner, an `OPEN` vent
at the doorway and a thermocouple rake — and was verified by running it with
FDS 6.9.1.

| | |
|---|---|
| Solver | Fire Dynamics Simulator (FDS), by NIST with VTT and others |
| Source code | [github.com/firemodels/fds](https://github.com/firemodels/fds) |
| Documentation | [pages.nist.gov/fds-smv](https://pages.nist.gov/fds-smv/) — User's Guide, Technical Reference and Validation Guide |
| Licence | public domain (a work of the U.S. federal government); third-party components carry their own terms |

If you want validated benchmark cases rather than a demonstration, the FDS
repository ships an extensive
[Validation](https://github.com/firemodels/fds/tree/master/Validation) suite
with the corresponding experimental data.
