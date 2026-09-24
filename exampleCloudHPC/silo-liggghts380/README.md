# silo-liggghts380 — LIGGGHTS 3.8.0 · filling a cylindrical silo

A discrete-element case: 1200 spheres of 3 mm radius are inserted in packets at
the top of a 0.10 m diameter, 0.40 m tall silo and settle under gravity onto the
flat bottom. Contacts use the Hertzian model with tangential history.

The silo wall and the floor are **analytical (primitive) walls**, not imported
STL geometry, so the case is a single self-contained input file. That keeps it
easy to read and to modify, and it is the natural starting point before moving
on to meshed geometry with `fix mesh/surface`.

## Case at a glance

| | |
|---|---|
| Solver script | `LIGGGHTS-3.8.0` |
| Suggested vCPU / RAM | 4 / `standard` |
| Particles | 1 200 monodisperse spheres, r = 3 mm, rho = 2500 kg/m³ |
| Contact model | Hertz + tangential history; e = 0.3, mu = 0.5, E = 5 MPa, nu = 0.45 |
| Time step | 1e-5 s, 100 000 steps → 1.0 s of physical time |
| Indicative runtime | a few minutes on 4 vCPU |
| Source | follows the public LIGGGHTS pouring tutorials — see [Source and credits](#source-and-credits) |

LIGGGHTS is MPI-parallel and decomposes the domain spatially. With only 1200
particles the communication overhead dominates quickly — 4 vCPU is a sensible
ceiling for this case as written. Raise the particle count before raising the
core count.

## Files

| File | Purpose |
|---|---|
| `in.silo` | the complete LIGGGHTS input script |

The script creates a `post/` directory at run time for the dump files.

## Run it on cloudhpc.cloud

1. **STORAGE → Add**: type `silo-liggghts380` in the *Dirname* text box, drop
   `in.silo` in the *File* box, press **Save**.
2. **SIMULATIONS → Add**:
   - **vCPU** `4`
   - **RAM** `standard`
   - **Folder** `silo-liggghts380`
   - **Script** `LIGGGHTS-3.8.0`
3. **Save**, then download the results from **STORAGE**.

## Run it with cloudHPCexec

```bash
cd silo-liggghts380

cloudHPCexec                                                  # interactive
cloudHPCexec -batch 4 standard LIGGGHTS-3.8.0 silo-liggghts380
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

## What to expect

The thermo output every 1000 steps shows the particle count climbing to 1200 as
the insertions fire, and the kinetic energy rising during each drop and decaying
as the bed settles. By the end of the run the kinetic energy should be close to
zero — a settled packing.

`post/dump*.liggghts` holds one snapshot every 5000 steps with per-particle
position, velocity, force, angular velocity and radius. Open the series in
ParaView (the LAMMPS dump reader) or post-process it directly — the format is
plain text.

## Things worth changing

- **Particle count**: `particles_in_region` in the `fix ins` block. This is the
  single knob that turns the case from a smoke test into a benchmark.
- **Polydispersity**: add more `particletemplate/sphere` fixes and give them
  weights in `particledistribution/discrete`.
- **Discharge**: delete the `bottom` wall fix partway through, or replace it
  with a `fix mesh/surface` hopper, to study flow out of the silo rather than
  filling it.
- **Time step**: 1e-5 s is conservative for these properties. Check it against a
  fraction of the Rayleigh time before lowering it.

## Note

This case has not been executed on the platform as part of preparing this
repository — LIGGGHTS was not available locally to verify it end to end, unlike
the OpenFOAM, FDS, SU2, CalculiX, EnergyPlus and FEniCSx examples here. The
input follows the documented 3.8.0 syntax; if the run stops on a parse error,
the offending line is named in the log.


## Source and credits

`in.silo` was **written for this repository**, following the structure of the
packing and pouring cases in the public LIGGGHTS tutorial suite: the same
sequence of `property/global` material fixes, a Hertzian `pair_style gran`,
analytical `wall/gran ... primitive` walls, a `particletemplate/sphere` fed into
`insert/pack`, and `nve/sphere` integration.

| | |
|---|---|
| Upstream tutorials | [`LIGGGHTS-PUBLIC/examples/LIGGGHTS/Tutorials_public`](https://github.com/CFDEMproject/LIGGGHTS-PUBLIC/tree/master/examples/LIGGGHTS/Tutorials_public) |
| Documentation | [LIGGGHTS manual](https://www.cfdem.com/media/DEM/docu/Manual.html) |
| Copyright | DCS Computing GmbH, Linz, and the CFDEM project — [cfdem.com](https://www.cfdem.com/) |
| Licence | [GNU GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) |

LIGGGHTS derives from [LAMMPS](https://www.lammps.org/) (Sandia National
Laboratories), which is also GPL v2 — most of the input-script syntax above is
LAMMPS syntax.
