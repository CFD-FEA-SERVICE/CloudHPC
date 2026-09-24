# gpuBenchmark-cuda123 — custom script · CUDA 12.3 GPU benchmark

A GPU smoke test and micro-benchmark for the CUDA images on cloudHPC. For every
device visible to the job it reports the name, compute capability, SM count and
memory, then measures:

- **achieved memory bandwidth**, with a SAXPY kernel over 256 MiB, and
- **single-precision throughput**, with a tiled SGEMM.

Run it before committing a long GPU job: it confirms that the instance really
has the GPUs you paid for, that the CUDA toolkit compiles, and it gives you a
baseline to compare your own kernels against.

This is also the shortest possible illustration of the **custom-script**
workflow, in which the platform runs your own code instead of a packaged solver.

## Case at a glance

| | |
|---|---|
| Solver script | `custom-script-cuda12.3` |
| Suggested vCPU / RAM | 4 / `basegpu` |
| Requires | a GPU instance — `basegpu` allocates one NVIDIA T4 per 2 vCPU |
| Indicative runtime | under a minute, compilation included |
| Source | written for this repository — see [Source and credits](#source-and-credits) |

With `basegpu` and 4 vCPU you get 2 GPUs, and the benchmark reports both.

## Files

| File | Purpose |
|---|---|
| `run.sh` | the entry point — prints `nvidia-smi`, compiles `benchmark.cu` with `nvcc -O3`, runs it |
| `benchmark.cu` | the CUDA source: device query, SAXPY bandwidth test, tiled SGEMM |

The custom-script images execute **every** `.sh` and `.py` file they find in the
folder. Keep exactly one entry point per folder, or you will launch things you
did not intend.

## Run it on cloudhpc.cloud

1. Compress the **contents** of this folder into `gpuBenchmark-cuda123.zip` —
   the archive must open directly on `run.sh` and `benchmark.cu`.
2. **STORAGE → Add**: type `gpuBenchmark-cuda123` in the *Dirname* text box,
   drop the archive in, press **Save**.
3. **SIMULATIONS → Add**:
   - **vCPU** `4`
   - **RAM** `basegpu` ← this is what allocates the GPUs
   - **Folder** `gpuBenchmark-cuda123`
   - **Script** `custom-script-cuda12.3`
4. **Save**. Everything is printed to the live log; there is nothing to download
   unless you want the log itself.

## Run it with cloudHPCexec

```bash
cd gpuBenchmark-cuda123

cloudHPCexec                                                            # interactive
cloudHPCexec -batch 4 basegpu custom-script-cuda12.3 gpuBenchmark-cuda123
```

```bash
cloudHPCexec -wait 12345
```

## What to expect

```
CUDA devices visible to this job: 2

Device 0: Tesla T4
  compute capability : 7.5
  multiprocessors    : 40
  global memory      : 14.6 GiB
  ...
  SAXPY bandwidth    : ... GB/s
  SGEMM 4096^3       : ... GFLOP/s
```

A T4 has roughly 320 GB/s of peak memory bandwidth; SAXPY should reach a large
fraction of that. The SGEMM figure comes from a hand-written tiled kernel, not
cuBLAS, so treat it as a floor rather than as the card's peak.

If the script exits with *"No CUDA device found"*, the instance was not
allocated a GPU — check that **RAM** was set to `basegpu`.

## Notes

- The platform also carries `custom-script-cuda13.1`. The source here is plain
  CUDA C and compiles on both; only the toolkit and driver version differ.
- For CPU-only Python work use `custom-script-u24` with a `requirements.txt` —
  see `python3.12/`.
- This case has not been executed on the platform as part of preparing this
  repository, since no GPU was available locally to verify it end to end.


## Source and credits

`benchmark.cu` and `run.sh` were **written for this repository** and are
released under [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html), consistent with the rest of the CloudHPC
repository. There is no upstream case: the two kernels are the textbook forms
that every CUDA introduction uses.

| | |
|---|---|
| SAXPY kernel | the canonical single-precision `a*x + y` example from NVIDIA's [*An Even Easier Introduction to CUDA*](https://developer.nvidia.com/blog/even-easier-introduction-cuda/) |
| Tiled SGEMM | the shared-memory tiled matrix multiply from the [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html) |
| Toolkit | [NVIDIA CUDA](https://developer.nvidia.com/cuda-toolkit) — the toolkit and driver are NVIDIA's, under their own licence terms |

The SGEMM figure comes from this hand-written kernel, not from cuBLAS, so it is
a floor rather than the card's peak — see the note under *What to expect*.
