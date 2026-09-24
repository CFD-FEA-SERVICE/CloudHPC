# python3.12 — custom script · generic Python job

The minimal custom-script example: a Python file and a list of packages. It
exists to show the shape of the workflow rather than to compute anything —
`script.py` prints `HELLO WORLD`.

Use this pattern whenever the work you need does not correspond to a packaged
solver: post-processing a batch of results, running an optimisation loop that
drives other tools, training a model, or anything else you would normally run on
a workstation but want on 64 cores instead.

## Case at a glance

| | |
|---|---|
| Solver script | `custom-script-u24` (Ubuntu 24.04, Python 3.12) |
| Suggested vCPU / RAM | 1 / `standard`, then whatever your real workload needs |
| Source | prepared by CFD FEA SERVICE — see [Source and credits](#source-and-credits) |

## Files

| File | Purpose |
|---|---|
| `script.py` | the code that runs |
| `requirements.txt` | the Python packages to install before it runs |

**The custom-script images execute every `.sh` and `.py` file they find in the
folder.** With one script that is exactly what you want; with several, you get
all of them. If your job has helper modules, either keep a single entry point
and import the rest from a subdirectory, or drive everything from one `.sh`.

`requirements.txt` here is a grab-bag — `seaborn`, `scikit-learn`,
`tensorflow-cpu`, `google-genai`, `PyInstaller` and more. Trim it to what you
actually import: every line is a package to download and install before your
code starts, and on a short job that install can dominate the runtime.

## Run it on cloudhpc.cloud

1. Compress the **contents** of this folder into `python3.12.zip` — the archive
   must open directly on `script.py` and `requirements.txt`.
2. **STORAGE → Add**: type `python3.12` in the *Dirname* text box, drop the
   archive in, press **Save**.
3. **SIMULATIONS → Add**:
   - **vCPU** `1`
   - **RAM** `standard`
   - **Folder** `python3.12`
   - **Script** `custom-script-u24`
4. **Save**. The output appears in the live log.

## Run it with cloudHPCexec

```bash
cd python3.12

cloudHPCexec                                                # interactive
cloudHPCexec -batch 1 standard custom-script-u24 python3.12 # non-interactive
```

```bash
cloudHPCexec -wait 12345
cloudHPCexec -download      # only if your script writes files worth keeping
```

## What to expect

```
HELLO WORLD
```

Anything your script writes into the working directory is collected into the
storage folder at the end of the run, the same as for any solver.

## Related

| Need | Use |
|---|---|
| GPU work | `custom-script-cuda12.3` / `custom-script-cuda13.1` — see `gpuBenchmark-cuda123/` |
| A finite-element stack in Python | `FEniCSx-0.6.0-r1` — see `poisson-fenicsx060/` |
| An interactive desktop instead of a batch job | any `-static` script, reached over VNC or SSH |

## Notes on long jobs

Custom scripts are **not** covered by the platform's automatic restart
machinery: if a SPOT instance reboots, the job starts from nothing. Either run
custom scripts on REG instances, or make your script checkpoint its own progress
into the working directory and pick up from there on a restart.


## Source and credits

`script.py` and `requirements.txt` were **prepared by CFD FEA SERVICE** for this
repository as the minimal illustration of the custom-script workflow. There is
no upstream source — the script prints one line.

The image behind `custom-script-u24` is Ubuntu 24.04 with
[Python 3.12](https://www.python.org/); the packages listed in
`requirements.txt` are installed from [PyPI](https://pypi.org/) at run time and
each carries its own licence.
