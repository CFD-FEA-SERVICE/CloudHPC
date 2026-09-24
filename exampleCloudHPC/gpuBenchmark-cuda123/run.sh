#!/bin/bash
#
# cloudHPC custom-script entry point for the GPU benchmark.
#
# The platform executes every .sh file found in the folder, so this script is
# all that is needed: it reports the GPUs allocated to the job, builds
# benchmark.cu with the CUDA toolkit of the image and runs it.
#
set -e

echo "=============================================================="
echo " Allocated hardware"
echo "=============================================================="
nvidia-smi || { echo "nvidia-smi not available - is this a basegpu instance?"; exit 1; }
echo
echo "vCPU available: $(nproc)"
echo "CUDA compiler : $(nvcc --version | tail -n 2 | head -n 1)"
echo

echo "=============================================================="
echo " Building"
echo "=============================================================="
nvcc -O3 -o benchmark benchmark.cu
echo "build complete"
echo

echo "=============================================================="
echo " Running"
echo "=============================================================="
./benchmark 4096
