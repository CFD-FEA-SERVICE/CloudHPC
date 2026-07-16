# salome — Salome plugins and scripts

Python scripts and plugins for the [Salome](https://www.salome-platform.org/) platform, used to prepare geometries and FEM models for cloudHPC runs.

## Content

| File | Description |
|---|---|
| `geoBBcells.py` | Computes the geometry bounding box and estimates mesh cell counts/sizes from it — useful to size a mesh before submitting a job |
| `geom_plugins.py` | Collection of geometry plugins/helpers for the Salome GEOM module |
| `tenuFemPreprocessing.py` | FEM pre-processing script (generated with Salome's dump-python functionality, Salome v9.4.0) for structural analyses |

To use a script inside Salome: `File → Load Script...` (or add it to your Salome plugins folder for the plugins).
