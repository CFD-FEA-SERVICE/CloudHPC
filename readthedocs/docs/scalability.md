# Scalability of Your Simulations

In order to achieve good scalability, it is important for you to know exactly the possibilities made available by the cloudHPC platform. There are, in fact, two different types of parallelizations:

* MPI - Multicore approach
* Hyper-threading

The differences between these two approaches are discussed in [this post](https://cloudhpc.cloud/2022/03/18/multicore-vs-multithread-a-little-guide/). Depending on the RAM selection for each instance, you are simultaneously selecting which of the two parallelization methods is activated for your simulation. The following table gives you an overview of the possibilities available.

| RAM         | MULTICORE   | HYPERTHREAD | GPU         |
| ----------- |:-----------:|:-----------:|:-----------:|
| highcpu     | ✅ | ✅ | ❌ |
| standard    | ✅ | ✅ | ❌ |
| highmem     | ✅ | ✅ | ❌ |
| highcore    | ✅ | ❌ | ❌ |
| hypercpu    | ✅ | ✅ | ❌ |
| hypercore   | ✅ | ❌ | ❌ |
| basegpu     | ✅ | ✅ | ✅ |

It is important to highlight that for _highcpu_, _standard_, and _highmem_ instances, as the machine configuration is exactly the same, the only difference is the RAM which is actually allocated (from 1GB per vCPU to 8GB per vCPU). It is suggested to attempt the execution on _highcpu_ [cheaper configuration] before trying _standard_ or _highmem_ as from the scalability point of view allocating more RAM does not give any speedup in your analysis.

## FDS
FDS has the possibility to use both scalability methods. Good scalability requires the user to properly set up the input `.fds` file, and in particular, the mesh definitions. The simulation scalability is generally affected by several parameters among which:

1. Mesh size in terms of total number of cells
1. Cells distribution among the the cores allocated
1. HRR curve type and location in the fluid domain
1. Number of pressure zones
1. Presence of particles
1. Chemical reaction calculation

The following procedure represents a simple guideline that can help users achieve good scalability. Thanks to the following instructions it is possible to avoid issues for the first two points in the above list which are the ones with a clearer mathematical representation.

!!! note
    The cloudHPC attempts to provide guidelines also for some of the other points in the above list even if there are no precise guidelines to assess them. An example is the [pressure zone warning](errors.md#high_number_of_pressure_zones).

### Choosing the right vCPU for your FDS simulation
* In order to reach good scalability, **you must have** multiple &MESH lines in your FDS file - so in case you have to [split your big meshes](https://cloudhpc.cloud/2022/09/15/split-fds-mesh-using-blenderfds/) into smaller ones.

* Calculate the number of cells for each &MESH line of your FDS input file. E.g., ```&MESH ID='mesh1', IJK=24,38,14, XB=... /``` Number of cells -> 24 * 38 * 14 = 12,768 cells.

* Make sure each &MESH has at least 15,000/20,000 cells. If this condition is not met, use the MPI\_PROCESS to assign two or more meshes to a single core.

* Ensure that all the &MESH have a similar number of cells - cells are equally distributed among all the meshes. If this condition is not met, use the MPI\_PROCESS to improve the load balancing.

* If all the above conditions are satisfied, select vCPU according to the following rules:
  - vCPU = Number of &MESH * 2 for instances _highcpu_, _standard_, _highmem_ or _hypercpu_.
  - vCPU = Number of &MESH for instances _highcore_ or _hypercore_.

!!! note
    Due to processors infrastructure, the presence of some DEVC in your FDS simulation as for example GAUGE HEAT FLUX GAS, RADIATIVE HEAT FLUX and VISIBILITY may reduce the computational performance on AMD processors. In these cases and if the simulation delivery time is important, we recommend using _hypercore_ or _hypercpu_ instances.

### MPI\_PROCESS Parameter
In case your &MESH are smaller than 15,000/20,000 cells or cells are not equally distributed among meshes in your FDS analysis, you can use the MPI\_PROCESS parameter to fix this situation. This is a parameter each &MESH can be assigned and represents a group number we are assigning the specific mesh [starting from group 0]. An example is reported here:


```
&MESH ID='mesh1', IJK=..., XB=..., MPI_PROCESS=0 /
&MESH ID='mesh2', IJK=..., XB=..., MPI_PROCESS=1 /
&MESH ID='mesh3', IJK=..., XB=..., MPI_PROCESS=1 /
&MESH ID='mesh4', IJK=..., XB=..., MPI_PROCESS=2 /
&MESH ID='mesh5', IJK=..., XB=..., MPI_PROCESS=3 /
&MESH ID='mesh6', IJK=..., XB=..., MPI_PROCESS=3 /
```

Since each group assigned is executed by one single core, it is possible to assign now at least 15,000/20,000 cells to each group and improve the cell distributions among the groups as shown in the following image.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/MPIprocessAssign.jpg">
</p>

Once the groups have been assigned with MPI\_PROCESS, the user can now move forward by following these instructions:

* Order the &MESH so that MPI\_PROCESS are in ascending order.

* Execute a simulation and select vCPU according to the following rules:
  - vCPU = Two times the MPI\_PROCESS groups number for instances _highcpu_, _standard_, _highmem_ or _hypercpu_.
  - vCPU = Number of MPI\_PROCESS groups for instances _highcore_ or _hypercore_.

!!! note
    Due to processors infrastructure, the presence of some DEVC in your FDS simulation as for example GAUGE HEAT FLUX GAS, RADIATIVE HEAT FLUX and VISIBILITY may reduce the computational performance on AMD processors. In these cases and if the simulation delivery time is important, we recommend using _hypercore_ or _hypercpu_ instances.

### Load Distribution Feedback
The computational load assigned to each process is proportional to the total number of cells every process needs to compute during the calculation. For this reason, at the beginning of your analysis, a process load bar graph is generated to provide you info about load distribution. Each bar represents the cells to be computed by each single process of the analysis. An ideal case requires a similar number of cells among all processes, and if this condition is not satisfied, it is recommended to use the MPI\_PROCESS parameter to redistribute cells.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/ProcessorsLoad.png">
</p>

The above situation represents an ideal case: all processors are assigned a similar number of cells and consequently are expected to have a similar workload to complete. A situation like the one sketched below shows an imbalance in the workload among processors: the processor 0 is assigned almost 200,000 cells while all the other processors are assigned at most 60,000 cells. To improve this situation you can follow instructions [given earlier](scalability.md#fds) to redistribute cells among processors.

<p align="center">
   <img width="400" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/MeshLoadDistributionToImprove.png">
</p>

If the above method is not sufficient to distribute cells equally among processors, you can split [bigger meshes](https://cloudhpc.cloud/2022/09/15/split-fds-mesh-using-blenderfds/) and attempt again a distribution.

### FDS Mesh Decomposition
The cloudHPC platform is able to decompose the FDS simulation in some peculiar cases. This lets the user an easier way to achieve good scalability thanks to a mesh division performed by the system. The pre-conditions to meet in order to let the system decompose your mesh are:

* Generate an input FDS file with just one _&MESH_ line.
* The mesh must be made of at least 40,000 cells.
* Select vCPU to be 4 or more.

In these situations, the _output_ provides you the following plot when the mesh decomposition occurs:

<p align="center">
   <img width="400" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/fdsdecomposition.png">
</p>

In there you can find the following parameters:

* INPUT MESH: string of the input mesh.
* REQU. DIVS: required divisions - usually equals to the number of vCPU.
* Init. IJK: I, J, K set on the input mesh.
* MESH CELLS: Input mesh total number of cells.
* Limit. DIV: Max number of divisions allowed to achieve good scalability (15,000 cells per each _&MESH_ line).
* INPUT XB: Input mesh bounding box.
* DECOMPOS.: Decomposition performed along the three axes: X, Y, and Z.
* Final MESH: Number of the decomposed meshes performed. It can be lower than the Limit. DIV value depending on I, J, and K possible divisions.

Once the mesh decomposition is performed, you can check the final results using the [load distribution feedback](scalability.md#load_distribution_feedback).

!!! note
    Always perform a check by using smokeview to verify the smoke and temperature diffusion when the decomposition occurs.

### More
* <a href="https://www.youtube.com/watch?v=sMQwgKK_GYM" target="_blank">Cloud HPC - Use the best scalability for your FDS analyses</a>
* <a href="https://cloudhpc.cloud/2022/01/28/fds-scalability/" target="_blank">How to reach good scalability in FDS</a>

## OpenFOAM
As far as scalability is concerned, OpenFOAM only uses a multi-core approach. This makes the _highcore_ and the _hypercore_ instances the most suitable when running these analyses on cloudHPC. The system automatically adapts your _decomposeParDict_ file to match the required number of vCPU you made available to the analysis. As far as this update works correctly, just follow the [hints](errors.md#decomposepardict) on the decomposeParDict file.
Some example of decomposeParDict where cloudHPC automatically updates the main variables to match the selected number of cores are provided below.

```
method          scotch;
numberOfSubdomains 112; #Automatic updated by cloudHPC
```

```
method  hierarchical;
numberOfSubdomains  8;  #Automatic updated by cloudHPC

coeffs
{
    n   (4 2 3);        #Automatic updated by cloudHPC
}

hierarchicalCoeffs
{
    n   (7 4 4);        #Automatic updated by cloudHPC
    order   xyz;
}
```

* <a href="https://cloudhpc.cloud/2025/07/08/pushing-the-boundaries-cloudhpcs-journey-at-the-openfoam-workshop-2025-hpc-challenge-in-vienna/" target="_blank">Pushing the Boundaries: CloudHPC’s Journey at the OpenFOAM Workshop 2025 HPC Challenge in Vienna!</a>

## Code Aster
Code Aster can take advantage of both OpenMPI and OpenMP at the same time. The versions currently compiled under the cloudHPC platform do not always implement both methodologies. You can execute simultaneously OpenMPI/OpenMP on versions marked with the suffix _\_mpi_ such as:

* 14.6 - Compiled with OpenMPI/OpenMP
* 15.4 - Compiled with OpenMPI/OpenMP
* 16.4 - Compiled with OpenMPI/OpenMP
* 17.0 - Compiled with OpenMPI/OpenMP

When using an OpenMP-only version, the `.comm` file coming from the AsterStudy is usually adequate to use the hardware resources you are selecting. For OpenMPI/OpenMP versions instead you have to adapt the `.comm` file following [our template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/code-aster/input.comm).

```
mesh = LIRE_MAILLAGE(FORMAT='MED', UNITE=2, PARTITIONNEUR='PTSCOTCH', ...)
...
nCORE = 4 #Assign the number of cores to match mpi_nbcpu
model = AFFE_MODELE(  ..., DISTRIBUTION=_F(METHODE='SOUS_DOMAINE', NB_SOUS_DOMAINE=nCORE,), ... )
...
#Possible solvers
stat  = STAT_NON_LINE( ..., SOLVEUR=_F( METHODE='MUMPS', MATR_DISTRIBUEE='OUI' ), ... )
stat  = STAT_NON_LINE( ..., SOLVEUR=_F( METHODE='PETSC', MATR_DISTRIBUEE='OUI' ), ... )
mech  = MECA_STATIQUE( ..., SOLVEUR=_F( METHODE='PETSC', MATR_DISTRIBUEE='OUI' ), ... )
```

From your `.export` file, the system detects the `mpi_nbcpu` value and assign as a consequence it to the MPI CPUs to use. Any exceeding vCPU then allocated as thread (OpenMP) to your analysis. An example for the lines of your export file affecting scalability is reported here:

```
P mpi_nbcpu 4      #number of MPI cores - USER defined
P mpi_nbnoeud 1    #number of nodes     - always 1 on cloudHPC
P ncpus 8          #number of threads   - cloudHPC updated
```

* <a href="https://cloudhpc.cloud/2024/10/02/scalability-performance-code_aster-vs-calculix/" target="_blank">Scalability performance code_aster Vs calculiX</a>
* <a href="https://cloudhpc.cloud/2025/09/15/decoding-performance-a-scalability-showdown-between-calculix-and-code_aster/" target="_blank">Decoding Performance: A Scalability Showdown Between CalculiX and Code_Aster</a>

## CalculiX
CalculiX is a finite element analysis (FEA) program that comes in a few different versions, primarily based on how it's set up to solve complex problems.

* Default Version: The standard version of CalculiX uses a built-in solver library called SPOOLES. This is a good general-purpose option for many simulations.

* Custom Versions: For more demanding calculations, CalculiX can be compiled with different, more advanced solver libraries. These custom versions are easy to spot because their names have a specific ending, or "suffix."

    * PARDISO or PASTIX: These suffixes indicate that the program uses a powerful third-party solver library designed for high-performance computing.

    * MPI: This suffix means the program was compiled with OpenMPI, a library that allows it to run on multiple computers or processors at the same time (also known as parallel processing). This is crucial for solving very large and complex models much faster.

In short, the names of the CalculiX solvers tell you exactly what's inside—whether it's the standard SPOOLES library or a more specialized, high-performance option like PARDISO, PASTIX, or one optimized for parallel computing with MPI.

* <a href="https://cloudhpc.cloud/2024/10/02/scalability-performance-code_aster-vs-calculix/" target="_blank">Scalability performance code_aster Vs calculiX</a>
* <a href="https://cloudhpc.cloud/2025/09/15/decoding-performance-a-scalability-showdown-between-calculix-and-code_aster/" target="_blank">Decoding Performance: A Scalability Showdown Between CalculiX and Code_Aster</a>

## OpenRADIOSS
* <a href="https://cloudhpc.cloud/2025/05/27/unlocking-extreme-performance-openradioss-scalability-on-cloudhpc-with-amd-epyc-processors/" target="_blank">Unlocking Extreme Performance: OpenRADIOSS Scalability on CloudHPC with AMD EPYC Processors</a>

## SU2

* <a href="https://cloudhpc.cloud/2025/10/01/su2-and-the-challenge-of-scalability-how-cloudhpc-is-speeding-up-cfd-simulations/" target="_blank">SU2 and the Challenge of Scalability: How CloudHPC is Speeding Up CFD Simulations</a>
