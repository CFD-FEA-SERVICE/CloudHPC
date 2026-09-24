# beam-ccx221 — CalculiX 2.21 · cantilever beam

A 1.0 × 0.05 × 0.05 m steel cantilever, clamped at one end and loaded by 1000 N
at the other. The job runs two steps in sequence:

1. a **linear static** analysis of the tip deflection, and
2. a **frequency** analysis of the first ten natural modes of the unloaded beam.

Both steps have closed-form references, so the case doubles as a verification of
the solver and of your post-processing chain.

## Case at a glance

| | |
|---|---|
| Solver script | `calculiX-2.21` |
| Suggested vCPU / RAM | 4 / `standard` |
| Mesh | 5 120 linear bricks (C3D8), 6 561 nodes — 80 × 8 × 8 |
| Material | steel, E = 210 GPa, nu = 0.3, rho = 7850 kg/m³ |
| Indicative runtime | ~2 s on 4 vCPU |
| Source | written for this repository — see [Source and credits](#source-and-credits) |

CalculiX is shared-memory parallel: it uses `OMP_NUM_THREADS`, not MPI. Asking
for more vCPU helps the linear solve up to a point, but this case is small
enough that four is plenty.

## Files

| File | Purpose |
|---|---|
| `beam.inp` | the input deck — material, section, boundary conditions and the two steps |
| `mesh.inp` | nodes, elements and the `FIXED` / `TIPLOAD` sets, pulled in by `*INCLUDE` |
| `makeMesh.py` | regenerates `mesh.inp`; change `NX`, `NY`, `NZ` at the top to refine |

To rebuild the mesh:

```bash
python3 makeMesh.py > mesh.inp
```

`makeMesh.py` is not run on the cluster — the `calculiX-2.21` script works from
the `.inp` deck.

## Run it on cloudhpc.cloud

1. Compress the **contents** of this folder into `beam-ccx221.zip` — the archive
   must open directly on `beam.inp` and `mesh.inp`.
2. **STORAGE → Add**: type `beam-ccx221` in the *Dirname* text box, drop the
   archive in, press **Save**.
3. **SIMULATIONS → Add**:
   - **vCPU** `4`
   - **RAM** `standard`
   - **Folder** `beam-ccx221`
   - **Script** `calculiX-2.21`
4. **Save**, then download the results from **STORAGE** when it finishes.

## Run it with cloudHPCexec

```bash
cd beam-ccx221

cloudHPCexec                                             # interactive menus
cloudHPCexec -batch 4 standard calculiX-2.21 beam-ccx221 # non-interactive
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

## What to expect

**Static step.** The tip deflects by 2.960 mm downwards. The Euler–Bernoulli
estimate is

```
I     = b h³ / 12 = 5.2083e-7 m⁴
delta = F L³ / (3 E I) = 1000 / (3 · 210e9 · 5.2083e-7) = 3.048 mm
```

The 3 % difference is the usual stiffness of fully-integrated linear bricks;
refining through the thickness or switching the element type to `C3D20R` closes
most of it.

**Frequency step.** The modes come in pairs, because the cross-section is
square and bends identically in y and z:

| Mode pair | CalculiX | Euler–Bernoulli |
|---|---|---|
| 1st bending | 42.38 Hz | 41.78 Hz |
| 2nd bending | 262.6 Hz | 261.8 Hz |
| 3rd bending | 722.8 Hz | 733.1 Hz |

Output files:

| File | Contains |
|---|---|
| `beam.dat` | tip displacements and the eigenvalue table |
| `beam.frd` | fields for CalculiX GraphiX (`cgx beam.frd`) or ParaView via `ccx2paraview` |
| `beam.sta` | step/increment summary |

## Notes

- The `*CLOAD, OP=NEW` line at the start of step 2 removes the tip load, so the
  eigenmodes are those of the *unloaded* beam. Without it CalculiX carries the
  load into the frequency step and the first eigenvalue comes out negative.
- The load is applied as 1000/81 N on each of the 81 nodes of the tip face.
  That is a fine approximation for tip deflection, but do not read the stresses
  in the last couple of element rows.
- The platform also carries `calculiX-2.18-PARDISO-MPI` and
  `calculiX-2.19-PARDISO`. Those builds link the PARDISO solver, which is
  considerably faster on large models; the deck here is plain CalculiX input and
  runs on any of the three.


## Source and credits

`beam.inp` and `makeMesh.py` were **written for this repository**; they are not
copies of an upstream case. The model is the textbook clamped-cantilever
verification problem, chosen precisely because both the static deflection and
the bending frequencies have closed-form references to check against. It was
verified by running it with CalculiX 2.21.

| | |
|---|---|
| Solver | CalculiX CrunchiX (`ccx`), by Guido Dhondt and Klaus Wittig |
| Home page | [calculix.de](http://www.calculix.de/) — documentation and source at [dhondt.de](http://www.dhondt.de/) |
| Licence | [GNU GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) |

The CalculiX distribution ships its own extensive test suite
(`ccx_*/test/`), which is the place to look for worked examples of element
types, contact and material models beyond the linear elastic case used here.
