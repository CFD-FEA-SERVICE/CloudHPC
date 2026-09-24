/*
 * GPU smoke test and benchmark for the cloudHPC custom-script-cuda12.3 image.
 *
 * Reports, for every CUDA device visible to the job:
 *   - device name, compute capability, memory and SM count
 *   - achieved device memory bandwidth, measured with a SAXPY kernel
 *   - achieved single-precision throughput, measured with a tiled SGEMM
 *
 * Build:  nvcc -O3 -o benchmark benchmark.cu
 * Run:    ./benchmark [matrix-size]
 *
 * License: GPLv3, consistent with the rest of this repository.
 */

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#define CHECK(call)                                                          \
    do {                                                                     \
        cudaError_t err = (call);                                            \
        if (err != cudaSuccess) {                                            \
            fprintf(stderr, "CUDA error %s at %s:%d\n",                      \
                    cudaGetErrorString(err), __FILE__, __LINE__);            \
            exit(EXIT_FAILURE);                                              \
        }                                                                    \
    } while (0)

#define TILE 32

__global__ void saxpy(int n, float a, const float *x, float *y)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) y[i] = a * x[i] + y[i];
}

__global__ void sgemm(int n, const float *A, const float *B, float *C)
{
    __shared__ float As[TILE][TILE];
    __shared__ float Bs[TILE][TILE];

    int row = blockIdx.y * TILE + threadIdx.y;
    int col = blockIdx.x * TILE + threadIdx.x;
    float acc = 0.0f;

    for (int t = 0; t < (n + TILE - 1) / TILE; ++t) {
        int tiledCol = t * TILE + threadIdx.x;
        int tiledRow = t * TILE + threadIdx.y;

        As[threadIdx.y][threadIdx.x] =
            (row < n && tiledCol < n) ? A[row * n + tiledCol] : 0.0f;
        Bs[threadIdx.y][threadIdx.x] =
            (tiledRow < n && col < n) ? B[tiledRow * n + col] : 0.0f;
        __syncthreads();

        for (int k = 0; k < TILE; ++k)
            acc += As[threadIdx.y][k] * Bs[k][threadIdx.x];
        __syncthreads();
    }

    if (row < n && col < n) C[row * n + col] = acc;
}

static float timeKernel(void (*launch)(void *), void *arg, int repeats)
{
    cudaEvent_t start, stop;
    CHECK(cudaEventCreate(&start));
    CHECK(cudaEventCreate(&stop));

    launch(arg);                       /* warm-up */
    CHECK(cudaDeviceSynchronize());

    CHECK(cudaEventRecord(start));
    for (int i = 0; i < repeats; ++i) launch(arg);
    CHECK(cudaEventRecord(stop));
    CHECK(cudaEventSynchronize(stop));

    float ms = 0.0f;
    CHECK(cudaEventElapsedTime(&ms, start, stop));
    CHECK(cudaEventDestroy(start));
    CHECK(cudaEventDestroy(stop));
    return ms / repeats;
}

struct SaxpyArgs { int n; float *x, *y; };
struct GemmArgs  { int n; float *A, *B, *C; };

static void launchSaxpy(void *p)
{
    SaxpyArgs *a = (SaxpyArgs *)p;
    saxpy<<<(a->n + 255) / 256, 256>>>(a->n, 2.0f, a->x, a->y);
}

static void launchGemm(void *p)
{
    GemmArgs *a = (GemmArgs *)p;
    dim3 block(TILE, TILE);
    dim3 grid((a->n + TILE - 1) / TILE, (a->n + TILE - 1) / TILE);
    sgemm<<<grid, block>>>(a->n, a->A, a->B, a->C);
}

int main(int argc, char **argv)
{
    int n = (argc > 1) ? atoi(argv[1]) : 4096;

    int devices = 0;
    CHECK(cudaGetDeviceCount(&devices));
    if (devices == 0) {
        fprintf(stderr, "No CUDA device found. Did you request a basegpu "
                        "instance on cloudHPC?\n");
        return EXIT_FAILURE;
    }
    printf("CUDA devices visible to this job: %d\n\n", devices);

    for (int d = 0; d < devices; ++d) {
        cudaDeviceProp prop;
        CHECK(cudaSetDevice(d));
        CHECK(cudaGetDeviceProperties(&prop, d));

        printf("Device %d: %s\n", d, prop.name);
        printf("  compute capability : %d.%d\n", prop.major, prop.minor);
        printf("  multiprocessors    : %d\n", prop.multiProcessorCount);
        printf("  global memory      : %.1f GiB\n",
               prop.totalGlobalMem / (1024.0 * 1024.0 * 1024.0));
        printf("  peak memory clock  : %.0f MHz on a %d-bit bus\n",
               prop.memoryClockRate / 1000.0, prop.memoryBusWidth);

        /* ---- memory bandwidth via SAXPY ---- */
        const int nElem = 1 << 26;            /* 64 Mi elements = 256 MiB */
        float *x, *y;
        CHECK(cudaMalloc(&x, nElem * sizeof(float)));
        CHECK(cudaMalloc(&y, nElem * sizeof(float)));
        CHECK(cudaMemset(x, 0, nElem * sizeof(float)));
        CHECK(cudaMemset(y, 0, nElem * sizeof(float)));

        SaxpyArgs sa = {nElem, x, y};
        float ms = timeKernel(launchSaxpy, &sa, 20);
        /* SAXPY reads x and y and writes y: 3 transfers per element */
        double gbs = 3.0 * nElem * sizeof(float) / (ms * 1.0e-3) / 1.0e9;
        printf("  SAXPY bandwidth    : %.1f GB/s (%.3f ms per pass)\n", gbs, ms);

        CHECK(cudaFree(x));
        CHECK(cudaFree(y));

        /* ---- single-precision throughput via SGEMM ---- */
        float *A, *B, *C;
        size_t bytes = (size_t)n * n * sizeof(float);
        CHECK(cudaMalloc(&A, bytes));
        CHECK(cudaMalloc(&B, bytes));
        CHECK(cudaMalloc(&C, bytes));
        CHECK(cudaMemset(A, 0, bytes));
        CHECK(cudaMemset(B, 0, bytes));

        GemmArgs ga = {n, A, B, C};
        ms = timeKernel(launchGemm, &ga, 5);
        double gflops = 2.0 * n * n * (double)n / (ms * 1.0e-3) / 1.0e9;
        printf("  SGEMM %d^3        : %.0f GFLOP/s (%.1f ms per product)\n\n",
               n, gflops, ms);

        CHECK(cudaFree(A));
        CHECK(cudaFree(B));
        CHECK(cudaFree(C));
    }

    return EXIT_SUCCESS;
}
