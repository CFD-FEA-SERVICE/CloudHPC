# template — recommended solver input templates

Recommended, cloudHPC-ready input templates for the most common solvers available on the platform. Start from these files to make sure your case uses settings compatible with the cluster environment (parallel decomposition, output control, ...).

## Content

| Folder | Solver | Files |
|---|---|---|
| `OpenFOAM/system/` | OpenFOAM | `controlDict`, `decomposeParDict` — recommended run control and domain-decomposition settings for parallel execution on cloudHPC |
| `code-aster/` | code_aster | `export` (job/export definition), `input.comm` (command file skeleton), `base-stage1` |

Copy the relevant template into your case, adapt it to your model, then upload the case (see `exampleCloudHPC/` for complete working examples).

---

Part of the [CloudHPC](https://github.com/CFD-FEA-SERVICE/CloudHPC) repository.
