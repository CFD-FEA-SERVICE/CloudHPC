# naca0012-su2830 — SU2 8.3 · transonic NACA 0012

The reference transonic Euler benchmark. At Mach 0.8 and 1.25° incidence a
strong shock sits on the upper surface of the NACA 0012 at about 60 % chord and
a weaker one on the lower surface near 35 %. Because the flow is inviscid, all
of the drag is wave drag, which makes the case a clean check that the solver,
the mesh and the numerics are behaving.

Together with `SU2_8.3_Turbulent_ONERAM6/` this gives the two ends of the SU2
range on cloudHPC: a 2D inviscid case that converges in seconds, and a 3D RANS
case that does not.

## Case at a glance

| | |
|---|---|
| Solver script | `SU2_CFD8.3.0` |
| Suggested vCPU / RAM | 4 / `standard` |
| Mesh | 19 860 triangles, 10 632 points, circular farfield 100 chords out |
| Physics | Euler, M = 0.8, AoA = 1.25°, JST scheme, implicit Euler, 3-level W-cycle multigrid |
| Convergence | RMS density < 1e-10 |
| Indicative runtime | 259 iterations, ~15 s on 4 vCPU |
| Source | modelled on the SU2 Quick Start case — see [Source and credits](#source-and-credits) |

## Files

| File | Purpose |
|---|---|
| `inv_NACA0012.cfg` | the SU2 configuration — physics, numerics, boundary markers, I/O |
| `mesh_NACA0012_inv.su2` | the mesh, with markers `airfoil` and `farfield` |
| `makeMesh.py` | regenerates the mesh from scratch with gmsh; edit the constants at the top to refine it |

`makeMesh.py` is only a convenience for rebuilding the grid locally — it is not
executed on the cluster, and the `SU2_CFD8.3.0` script simply picks up the
`.cfg` file in the folder.

To rebuild the mesh (needs `gmsh` on your PATH):

```bash
python3 makeMesh.py
```

## Run it on cloudhpc.cloud

1. Compress the **contents** of this folder into `naca0012-su2830.zip` — the
   archive must open directly on `inv_NACA0012.cfg` and
   `mesh_NACA0012_inv.su2`.
2. **STORAGE → Add**: type `naca0012-su2830` in the *Dirname* text box, drop the
   archive in, press **Save**.
3. **SIMULATIONS → Add**:
   - **vCPU** `4`
   - **RAM** `standard`
   - **Folder** `naca0012-su2830`
   - **Script** `SU2_CFD8.3.0`
4. **Save**, then watch the residual and the force coefficients scroll past in
   the live log.
5. Download the results from **STORAGE**.

## Run it with cloudHPCexec

```bash
cd naca0012-su2830

cloudHPCexec                                                  # interactive menus
cloudHPCexec -batch 4 standard SU2_CFD8.3.0 naca0012-su2830   # non-interactive
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

## What to expect

On 4 MPI ranks the run converges to RMS density = −10.0 in 259 iterations and
gives

| Coefficient | Value |
|---|---|
| CL | 0.3318 |
| CD | 0.0216 |

which matches the accepted range for this configuration. Outputs:

| File | Contains |
|---|---|
| `history.csv` | residuals and coefficients per iteration |
| `flow.vtu` | the volume solution, for ParaView |
| `surface_flow.vtu` | surface quantities — plot `Pressure_Coefficient` against x to see the two shocks |
| `restart_flow.dat` | restart file; set `RESTART_SOL= YES` to continue from it |

## Things worth changing

- **Angle of attack and Mach**: `AOA` and `MACH_NUMBER`. Below M ≈ 0.75 the
  shocks disappear and the case converges even faster.
- **Mesh resolution**: `H_LE`, `H_AIRFOIL` and `N_AIRFOIL` in `makeMesh.py`.
  The shock position is sensitive to the surface spacing.
- **Viscous flow**: switching to `SOLVER= RANS` needs a mesh with a proper
  boundary-layer resolution — this one has none. Start from
  `SU2_8.3_Turbulent_ONERAM6/` instead.


## Source and credits

The configuration is modelled directly on the **SU2 Quick Start** case, which
uses the same flow conditions (Euler, M = 0.8, AoA = 1.25°) and, deliberately,
the same file names — so the two are easy to compare side by side.

| | |
|---|---|
| Upstream case | [`SU2/QuickStart`](https://github.com/su2code/SU2/tree/master/QuickStart) (`inv_NACA0012.cfg`, `mesh_NACA0012_inv.su2`) |
| Tutorial write-ups | [Quick Start](https://su2code.github.io/docs_v7/Quick-Start/) and [Inviscid 2D Unconstrained NACA 0012](https://su2code.github.io/tutorials/Inviscid_2D_Unconstrained_NACA0012/) |
| Copyright | the SU2 Foundation — [su2code.github.io](https://su2code.github.io/) |
| Licence | [GNU LGPL v2.1](https://github.com/su2code/SU2/blob/master/LICENSE.md) |

Differences from the upstream case:

- **The mesh is not the upstream one.** `mesh_NACA0012_inv.su2` is generated
  from scratch by `makeMesh.py` with [gmsh](https://gmsh.info/) ([GNU GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)),
  as an unstructured triangular grid with a farfield at 100 chords. The upstream
  QuickStart mesh is a different grid, so cell counts and the exact coefficients
  will not match to the last digit.
- The numerics block has been written out in full and commented, in the style of
  `SU2_8.3_Turbulent_ONERAM6/` in this repository.
