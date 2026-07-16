# exampleCloudHPC — ready-to-run example cases

Complete example cases, one per solver, that can be uploaded and run as-is on the cloudHPC platform. They are useful both as smoke tests of your account/setup and as starting points for your own simulations.

## Content

| Folder | Solver | Description |
|---|---|---|
| `SU2_8.3_Turbulent_ONERAM6/` | SU2 8.3 | Turbulent transonic flow over the ONERA M6 wing (`turb_ONERAM6.cfg`, 100k-cell `.su2` mesh, sample `runCloud` output) |
| `fds-6.7.5/` | FDS 6.7.5 | Staircase fire scenario in three variants: coarse, fine, fine-8core (`.fds` input files) |
| `flange-ca136/` | code_aster 13.6 | Flange FEM analysis (`fem.comm`, `mesh.med`, `export`, `base-stage1`) |
| `motorBike-of12/` | OpenFOAM 12 | Classic motorBike external aerodynamics tutorial (`0/`, `constant/`, `system/`, `Allrun`/`Allclean`) |
| `python3.12/` | Python 3.12 | Minimal Python job: `script.py` + `requirements.txt` showing how to run generic Python workloads |
