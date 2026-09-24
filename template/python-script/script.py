#!/usr/bin/env python3
"""cloudHPC python template

The custom-script command runs every .py file of the selected storage folder
inside a fresh virtual environment (py-cloudhpc) after installing the packages
listed in requirements.txt. The output of each script is saved to a .log file.

This example estimates pi with a Monte Carlo method spread over all the cores
of the instance. It shows the features worth reusing in your own script:

* parameters read from an input file (input.json) instead of hard-coded
* parallel work sized on the vCPU available
* a CSV file updated during the run  -> plotted live in the simulation page
* a checkpoint file                  -> the run continues after a restart
* results written in the working folder -> uploaded back to the storage
"""

import csv
import json
import os
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")  # no display on the cloud instance
import matplotlib.pyplot as plt

WORKDIR = Path(__file__).resolve().parent
INPUT = WORKDIR / "input.json"
MONITOR = WORKDIR / "monitor.csv"
CHECKPOINT = WORKDIR / "checkpoint.json"

DEFAULTS = {"iterations": 50, "samples_per_core": 2_000_000, "seed": 1234}


def load_input():
    params = dict(DEFAULTS)
    if INPUT.exists():
        params.update(json.loads(INPUT.read_text()))
    return params


def count_inside(args):
    """Work unit executed on one core: points falling inside the unit circle."""
    seed, n = args
    rng = np.random.default_rng(seed)
    xy = rng.random((n, 2))
    return int(np.count_nonzero((xy ** 2).sum(axis=1) <= 1.0))


def main():
    params = load_input()
    nproc = os.cpu_count() or 1
    print(f"Running on {nproc} cores with {params}", flush=True)

    # Restart from the checkpoint if present (e.g. after a new launch)
    state = {"iteration": 0, "inside": 0, "total": 0}
    if CHECKPOINT.exists():
        state = json.loads(CHECKPOINT.read_text())
        print(f"Restarting from iteration {state['iteration']}", flush=True)
    else:
        with MONITOR.open("w", newline="") as f:
            csv.writer(f).writerow(["iteration", "pi", "error"])

    n = params["samples_per_core"]
    with Pool(nproc) as pool:
        for it in range(state["iteration"], params["iterations"]):
            t0 = time.time()
            seeds = [params["seed"] + it * nproc + i for i in range(nproc)]
            inside = sum(pool.map(count_inside, [(s, n) for s in seeds]))

            state["iteration"] = it + 1
            state["inside"] += inside
            state["total"] += n * nproc
            pi = 4.0 * state["inside"] / state["total"]

            with MONITOR.open("a", newline="") as f:
                csv.writer(f).writerow([it + 1, pi, abs(pi - np.pi)])
            CHECKPOINT.write_text(json.dumps(state))

            print(f"iteration {it + 1:4d}  pi = {pi:.8f}  "
                  f"({time.time() - t0:.2f} s)", flush=True)

    # Final results
    pi = 4.0 * state["inside"] / max(state["total"], 1)
    data = np.genfromtxt(MONITOR, delimiter=",", names=True)
    fig, ax = plt.subplots()
    ax.semilogy(data["iteration"], data["error"])
    ax.set_xlabel("iteration")
    ax.set_ylabel("|pi - estimate|")
    fig.savefig(WORKDIR / "convergence.png", dpi=150)

    (WORKDIR / "results.json").write_text(json.dumps(
        {"pi": pi, "samples": state["total"], "cores": nproc}, indent=2))
    print(f"Done: pi = {pi:.8f}")


if __name__ == "__main__":  # required by multiprocessing
    main()
