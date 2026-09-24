# SU2_8.3_Turbulent_ONERAM6 — SU2 8.3 · ONERA M6 wing

Transonic turbulent flow over the ONERA M6 wing, the standard 3D validation case
for compressible CFD. At Mach 0.8395 and 3.06° incidence the wing carries the
characteristic lambda shock on the upper surface, and the experimental pressure
distributions are widely published, so the case is worth running whenever you
want to confirm that a solver build gives the answer it should.

Together with `naca0012-su2830/` this brackets the SU2 range available here: a
2D inviscid case that converges in seconds, and this one, which does not.

## Case at a glance

| | |
|---|---|
| Solver script | `SU2_CFD8.3.0` |
| Suggested vCPU / RAM | 16 / `standard` |
| Mesh | 315 806 tetrahedra, 126 539 points; markers `WING`, `FARFIELD`, `SYMMETRY` |
| Physics | RANS with Spalart–Allmaras, M = 0.8395, AoA = 3.06°, Re = 11.72e6 |
| Numerics | JST, implicit Euler, CFL 100, no multigrid |
| Convergence | Cauchy criterion on drag (100 elements, eps 1e-6) |
| Indicative runtime | tens of minutes, depending on the vCPU count |
| Source | the SU2 turbulent ONERA M6 tutorial — see [Source and credits](#source-and-credits) |

## Files

| File | Purpose |
|---|---|
| `turb_ONERAM6.cfg` | the SU2 configuration — physics, numerics, markers, I/O and a `DEFINITION_DV` block for shape-optimisation studies |
| `mesh_ONERAM6_100k.su2` | the 22 MB mesh |

## Run it on cloudhpc.cloud

1. Compress the **contents** of this folder into `SU2_8.3_Turbulent_ONERAM6.zip`
   — the archive must open directly on the `.cfg` and the `.su2` file. The mesh
   compresses well, which is worth it at this size.
2. **STORAGE → Add**: type `SU2_8.3_Turbulent_ONERAM6` in the *Dirname* text
   box, drop the archive in, press **Save**.
3. **SIMULATIONS → Add**:
   - **vCPU** `16`
   - **RAM** `standard`
   - **Folder** `SU2_8.3_Turbulent_ONERAM6`
   - **Script** `SU2_CFD8.3.0`
4. **Save**, then watch `RMS_DENSITY`, `RMS_NU_TILDE`, `LIFT` and `DRAG` in the
   live log.
5. Download the results from **STORAGE**.

## Run it with cloudHPCexec

```bash
cd SU2_8.3_Turbulent_ONERAM6

cloudHPCexec                                                             # interactive
cloudHPCexec -batch 16 standard SU2_CFD8.3.0 SU2_8.3_Turbulent_ONERAM6   # non-interactive
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

Uploading 22 MB of mesh on every launch gets old quickly. Once the folder is in
the storage, re-launch against it without re-uploading:

```bash
cloudHPCexec -batchONL 16 standard SU2_CFD8.3.0 SU2_8.3_Turbulent_ONERAM6
```

## What to expect

| File | Contains |
|---|---|
| `history.csv` | residuals and force coefficients per iteration |
| `flow.vtu` | the volume solution |
| `surface_flow.vtu` | surface pressure — slice at constant span and plot Cp to see the lambda shock |
| `restart_flow.dat` | restart file |

To continue a stopped run, set `RESTART_SOL= YES` in the `.cfg`, make sure
`solution_flow.dat` is present (rename the restart file if needed), and launch
again with the same resources.

## Notes

- `ITER= 999999` in the config means the run is ended by the Cauchy convergence
  criterion on drag, not by an iteration cap. Use a **soft stop** if you want to
  end it early and keep the results.
- `REF_AREA= 0` asks SU2 to compute the reference area from the geometry.
- The `DEFINITION_DV` line at the bottom defines Hicks–Henne bump design
  variables. It is inert for a direct solve and only matters if you move on to
  the adjoint and shape-optimisation drivers.


## Source and credits

Taken from the **turbulent ONERA M6** tutorial of the SU2 project. The header of
`turb_ONERAM6.cfg` credits Thomas D. Economon (Stanford University) as the
original author.

| | |
|---|---|
| Tutorial write-up | [Turbulent ONERA M6](https://su2code.github.io/tutorials/Turbulent_ONERAM6/) |
| Upstream case files | [`Tutorials/compressible_flow/Turbulent_ONERAM6`](https://github.com/su2code/Tutorials/tree/master/compressible_flow/Turbulent_ONERAM6) |
| Copyright | the SU2 Foundation — [su2code.github.io](https://su2code.github.io/) |
| Licence | [GNU LGPL v2.1](https://github.com/su2code/SU2/blob/master/LICENSE.md) |

The wing itself, and the pressure data the case is normally validated against,
come from V. Schmitt and F. Charpin, *Pressure distributions on the
ONERA-M6-Wing at transonic Mach numbers*, AGARD AR-138, 1979.
