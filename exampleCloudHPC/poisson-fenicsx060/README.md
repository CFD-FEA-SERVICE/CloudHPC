# poisson-fenicsx060 — FEniCSx 0.6.0 · Poisson problem

The canonical finite-element "hello world", solved with DOLFINx:

```
-Δu = f   in Ω = (0,1)²
   u = u_D on ∂Ω
```

with the manufactured solution `u_D = 1 + x² + 2y²`, for which `f = -6`. Because
the exact answer is known, the script reports the L2 and maximum nodal errors —
so a successful run is not just "it did not crash", it is a quantitative check
that the installation, the assembly and the MPI decomposition are all correct.

This example is the entry point for using cloudHPC as a **general FEM
development platform** rather than as a pre-packaged solver service: you write
the weak form in Python and the platform runs it across as many ranks as you
ask for.

## Case at a glance

| | |
|---|---|
| Solver script | `FEniCSx-0.6.0-r1` |
| Suggested vCPU / RAM | 4 / `standard` |
| Mesh | unit square, `N × N × 2` triangles, `N = 256` by default → 131 072 cells |
| Discretisation | continuous Lagrange P1, CG + GAMG, rtol 1e-12 |
| Indicative runtime | seconds |
| Source | follows the standard DOLFINx Poisson demo — see [Source and credits](#source-and-credits) |

## Files

| File | Purpose |
|---|---|
| `poisson.py` | the whole case — mesh, function space, boundary conditions, solve, error norms, XDMF output |

The mesh is built in memory by `dolfinx.mesh.create_unit_square`, so there is no
mesh file to upload. Pass a different resolution as the first argument:

```bash
mpirun -np 4 python3 poisson.py 512
```

## Run it on cloudhpc.cloud

1. **STORAGE → Add**: type `poisson-fenicsx060` in the *Dirname* text box, drop
   `poisson.py` in the *File* box, press **Save**.
2. **SIMULATIONS → Add**:
   - **vCPU** `4`
   - **RAM** `standard`
   - **Folder** `poisson-fenicsx060`
   - **Script** `FEniCSx-0.6.0-r1`
3. **Save**. The first run spends a few seconds JIT-compiling the variational
   forms with FFCx before the solve starts — that is normal.
4. Download the results from **STORAGE**.

## Run it with cloudHPCexec

```bash
cd poisson-fenicsx060

cloudHPCexec                                                       # interactive
cloudHPCexec -batch 4 standard FEniCSx-0.6.0-r1 poisson-fenicsx060
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

## What to expect

The log ends with a short report, for example on 4 ranks at `N = 128`:

```
MPI ranks      : 4
cells          : 32768
degrees of freedom : 16641
L2 error       : 3.216835e-05
max nodal error: 1.018563e-11
```

Two things to check:

- The **L2 error drops by a factor of 4 every time you double N** — that is the
  second-order convergence expected of P1 elements on this problem.
- The **max nodal error is at round-off**. For this particular manufactured
  solution the P1 interpolant is exact at the vertices, so anything much larger
  than 1e-10 means something is wrong.

`poisson.xdmf` and `poisson.h5` hold the solution field; open the `.xdmf` in
ParaView.

## Extending it

The script is deliberately a single flat file. Swap in your own domain
(`dolfinx.io.gmshio.read_from_msh` reads a gmsh mesh), your own weak form, or a
nonlinear problem with `dolfinx.nls.petsc.NewtonSolver`. Any Python package your
script imports beyond the DOLFINx stack has to be available in the image — if
you need more, the `custom-script-u24` script with a `requirements.txt` is the
more flexible route (see `python3.12/`).


## Source and credits

`poisson.py` follows the **standard DOLFINx Poisson demo** and the
*Fundamentals* chapter of the FEniCSx tutorial, including their manufactured
solution `u = 1 + x² + 2y²` and the error checks built around it. It was
verified by running it with DOLFINx 0.6.0 on 1 and 4 MPI ranks.

| | |
|---|---|
| Upstream demo | [`dolfinx/python/demo/demo_poisson.py`](https://github.com/FEniCS/dolfinx/blob/v0.6.0/python/demo/demo_poisson.py) (v0.6.0) |
| Tutorial chapter | [The FEniCSx tutorial — Fundamentals](https://jsdokken.com/dolfinx-tutorial/chapter1/fundamentals.html), by Jørgen S. Dokken |
| Project | [FEniCS Project](https://fenicsproject.org/) — source at [github.com/FEniCS/dolfinx](https://github.com/FEniCS/dolfinx) |
| Licence | [GNU LGPL v3](https://www.gnu.org/licenses/lgpl-3.0.html) |

Differences from the upstream demo: the script takes the resolution as a command
line argument, reports the MPI rank count, cell count and degree-of-freedom
count alongside the error norms, and uses CG + GAMG rather than a direct solve so
that it stays usable as the mesh is refined.
