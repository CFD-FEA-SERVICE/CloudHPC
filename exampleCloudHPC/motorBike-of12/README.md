# motorBike-of12 — OpenFOAM 12 · external aerodynamics

The best-known OpenFOAM tutorial: steady incompressible RANS flow around a
motorbike and its rider at 20 m/s. `snappyHexMesh` carves a body-fitted mesh out
of a background block using the `motorBike.obj` surface, `potentialFoam`
initialises the velocity field, and `foamRun` converges the momentum and
turbulence equations while writing force coefficients.

Of the examples in this repository this is the one that genuinely rewards
parallel hardware: the mesh generation and the solve both scale, and it is the
right case to use when you want to see what a given vCPU count actually buys
you.

## Case at a glance

| | |
|---|---|
| Solver script | `openFoam-of12` |
| Suggested vCPU / RAM | 8 / `standard` |
| Mesh | generated at run time by `blockMesh` + `snappyHexMesh` (castellate + snap, no layers) |
| Physics | incompressible RAS, Spalart–Allmaras, steady, 500 iterations |
| Indicative runtime | tens of minutes on 8 vCPU, meshing included |
| Source | OpenFOAM 12 tutorial `incompressibleFluid/motorBike` — see [Source and credits](#source-and-credits) |

## Files

| File | Purpose |
|---|---|
| `Allrun` | the full chain: fetch geometry, `blockMesh`, `decomposePar`, `snappyHexMesh`, `renumberMesh`, `potentialFoam`, `foamRun`, `reconstructPar` |
| `Allclean` | resets the case |
| `0/` | initial and boundary conditions, with the reusable fragments in `0/include/` |
| `constant/physicalProperties` | kinematic viscosity |
| `constant/momentumTransport` | Spalart–Allmaras |
| `constant/geometry/` | empty placeholder; `Allrun` copies `motorBike.obj.gz` into it from the OpenFOAM installation |
| `system/blockMeshDict` | the background block |
| `system/snappyHexMeshDict` | refinement levels and surface snapping |
| `system/decomposeParDict` | 8 subdomains, `scotch` — **match it to the vCPU you request** |
| `system/controlDict` | solver module, 500 iterations, binary output |
| `system/forceCoeffs`, `system/streamlines`, `system/cutPlane`, `system/functions` | run-time post-processing |

The geometry is **not** shipped in this folder — `Allrun` copies it from
`$FOAM_TUTORIALS/resources/geometry`, which exists in the cluster image.

## Run it on cloudhpc.cloud

1. Compress the **contents** of this folder into `motorBike-of12.zip` — the
   archive must open directly on `0`, `constant`, `system`, `Allrun`,
   `Allclean`.
2. **STORAGE → Add**: type `motorBike-of12` in the *Dirname* text box, drop the
   archive in, press **Save**.
3. **SIMULATIONS → Add**:
   - **vCPU** `8` — matching `numberOfSubdomains`
   - **RAM** `standard`
   - **Folder** `motorBike-of12`
   - **Script** `openFoam-of12`
4. **Save**, then follow the log through the meshing and solving phases.
5. Download the results from **STORAGE**.

## Run it with cloudHPCexec

```bash
cd motorBike-of12

cloudHPCexec                                                  # interactive
cloudHPCexec -batch 8 standard openFoam-of12 motorBike-of12   # non-interactive
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download
```

## Reusing the mesh

Meshing is the expensive part of this case, and cloudHPC lets you skip it. Run
`snappyHexMesh-of12` once against this folder to produce the mesh, then on later
solver runs fill in the optional **Mesh** field on the simulation page with that
folder name: the platform copies `constant/polyMesh` and `constant/triSurface`
into the case before starting the solver. From the terminal the mesh folder is
the fifth positional argument:

```bash
cloudHPCexec -batch 8 standard openFoam-of12 motorBike-of12 motorBike-mesh
```

## What to expect

`postProcessing/forceCoeffs/` holds the drag and lift history — the coefficients
should be flat well before iteration 500. `postProcessing/cutPlane/` and
`streamlines/` give you something to look at in ParaView without loading the
full volume field.

## Restarting and SPOT instances

For SPOT instances set

```
startFrom       latestTime;
writeInterval   100;
purgeWrite      5;
```

in `system/controlDict`, so a reboot resumes from the last written iteration
instead of starting over.


## Source and credits

Taken from the **`incompressibleFluid/motorBike`** case of the OpenFOAM 12
tutorial suite.

| | |
|---|---|
| Upstream case | [`OpenFOAM-12/tutorials/incompressibleFluid/motorBike`](https://github.com/OpenFOAM/OpenFOAM-12/tree/master/tutorials/incompressibleFluid/motorBike) |
| Copyright | The OpenFOAM Foundation — [openfoam.org](https://openfoam.org/) |
| Licence | [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) |

The `motorBike.obj.gz` surface is part of the OpenFOAM tutorial resources and is
copied in by `Allrun` at run time rather than stored here.
