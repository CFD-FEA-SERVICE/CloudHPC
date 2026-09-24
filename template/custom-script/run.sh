#!/bin/bash
# cloudHPC custom-script template
#
# The custom-script command executes every bash (.sh) or python (.py) script
# found in the selected storage folder: keep just the scripts you want to run
# in the folder, together with all the input files they need.
#
# Results written in this folder are uploaded back to the storage at the end
# of the run, every 10 hours and when SYNC is pressed. Any CSV file produced
# is plotted at runtime in the simulation page.

set -euo pipefail
cd "$(dirname "$0")"

# Number of cores available on the instance
NPROC=$(nproc)
echo "Running on $(hostname) with ${NPROC} cores"

# ---------------------------------------------------------------------------
# Replace the lines below with your own workflow, e.g.:
#   mpirun -np "${NPROC}" mySolver input.dat > log.mySolver 2>&1
#   python3 postProcess.py
# ---------------------------------------------------------------------------
echo "step,value" > monitor.csv
for i in $(seq 1 10); do
    echo "${i},$((i * i))" >> monitor.csv
    sleep 1
done

echo "Done"
