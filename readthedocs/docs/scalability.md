# Scalability of Your Simulations

To achieve good scalability, you need to know the options offered by the cloudHPC platform. There are two types of parallelisation:

* MPI - Multicore approach
* Hyper-threading

The differences between these two approaches are discussed in [this post](https://cloudhpc.cloud/2022/03/18/multicore-vs-multithread-a-little-guide/). The RAM option you select for an instance also determines which parallelisation methods are available to your simulation. The following table gives an overview.

| RAM         | MULTICORE   | HYPERTHREAD | GPU         |
| ----------- |:-----------:|:-----------:|:-----------:|
| highcpu     | ✅ | ✅ | ❌ |
| standard    | ✅ | ✅ | ❌ |
| highmem     | ✅ | ✅ | ❌ |
| highcore    | ✅ | ❌ | ❌ |
| hypercpu    | ✅ | ✅ | ❌ |
| hypercore   | ✅ | ❌ | ❌ |
| basegpu     | ✅ | ✅ | ✅ |

Note that _highcpu_, _standard_ and _highmem_ instances use exactly the same hardware: they only differ in the amount of RAM allocated (from 1 GB to 8 GB per vCPU). We suggest trying _highcpu_ first [the cheapest option] and moving to _standard_ or _highmem_ only if needed, since allocating more RAM does not speed up your analysis.

## FDS
FDS can use both parallelisation methods. Good scalability requires a proper set-up of the `.fds` input file, and in particular of the mesh definitions. Scalability is generally affected by several parameters, including:

1. Mesh size in terms of total number of cells
1. Distribution of the cells among the allocated cores
1. HRR curve type and fire location in the fluid domain
1. Number of pressure zones
1. Presence of particles
1. Chemical reaction calculations

The following procedure is a simple guideline to achieve good scalability. It addresses the first two points of the list above, which are the easiest to quantify. The [FDS template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/FDS/template.fds) and the [fds-6.7.5 example](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/fds-6.7.5), which runs the same case at three grid resolutions, show these rules applied.

!!! note
    cloudHPC also tries to give hints on some of the other points of the list, even though there are no precise rules for them. An example is the [pressure zone warning](errors.md#high_number_of_pressure_zones).

### Choosing the right vCPU for your FDS simulation
* To reach good scalability, your FDS file **must have** multiple &MESH lines: if needed, [split your large meshes](https://cloudhpc.cloud/2022/09/15/split-fds-mesh-using-blenderfds/) into smaller ones.

* Calculate the number of cells for each &MESH line of your FDS input file. E.g., ```&MESH ID='mesh1', IJK=24,38,14, XB=... /``` Number of cells -> 24 * 38 * 14 = 12,768 cells.

* Make sure each &MESH has at least 15,000-20,000 cells. If not, use MPI\_PROCESS to assign two or more meshes to a single core.

* Make sure all the &MESH have a similar number of cells, so that cells are evenly distributed among the meshes. If not, use MPI\_PROCESS to improve the load balancing.

* If all the above conditions are satisfied, select vCPU according to the following rules:
  - vCPU = number of &MESH × 2 on _highcpu_, _standard_, _highmem_ or _hypercpu_ instances.
  - vCPU = number of &MESH on _highcore_ or _hypercore_ instances.

!!! note
    Some DEVC in your FDS simulation, such as GAUGE HEAT FLUX GAS, RADIATIVE HEAT FLUX and VISIBILITY, may reduce performance on AMD processors. In these cases, if the delivery time of the simulation matters, we recommend using _hypercore_ or _hypercpu_ instances.

### MPI\_PROCESS Parameter
If your &MESH have fewer than 15,000-20,000 cells, or the cells are not evenly distributed among the meshes, you can use the MPI\_PROCESS parameter to fix this. It can be assigned to each &MESH and is the number of the group (process) the mesh belongs to [starting from group 0]. For example:


```
&MESH ID='mesh1', IJK=..., XB=..., MPI_PROCESS=0 /
&MESH ID='mesh2', IJK=..., XB=..., MPI_PROCESS=1 /
&MESH ID='mesh3', IJK=..., XB=..., MPI_PROCESS=1 /
&MESH ID='mesh4', IJK=..., XB=..., MPI_PROCESS=2 /
&MESH ID='mesh5', IJK=..., XB=..., MPI_PROCESS=3 /
&MESH ID='mesh6', IJK=..., XB=..., MPI_PROCESS=3 /
```

Since each group is computed by a single core, you can now give each group at least 15,000-20,000 cells and balance the cells among the groups, as shown in the following image.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/MPIprocessAssign.jpg">
</p>

Once the groups have been assigned with MPI\_PROCESS:

* Order the &MESH so that the MPI\_PROCESS values are in ascending order.

* Run the simulation, selecting vCPU according to the following rules:
  - vCPU = number of MPI\_PROCESS groups × 2 on _highcpu_, _standard_, _highmem_ or _hypercpu_ instances.
  - vCPU = number of MPI\_PROCESS groups on _highcore_ or _hypercore_ instances.

!!! note
    Some DEVC in your FDS simulation, such as GAUGE HEAT FLUX GAS, RADIATIVE HEAT FLUX and VISIBILITY, may reduce performance on AMD processors. In these cases, if the delivery time of the simulation matters, we recommend using _hypercore_ or _hypercpu_ instances.

### Load Distribution Feedback
The computational load of each process is proportional to the number of cells it has to compute. For this reason, at the start of your analysis a bar chart shows the load distribution: each bar is the number of cells computed by one process. Ideally all processes have a similar number of cells; if not, use the MPI\_PROCESS parameter to redistribute them.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/ProcessorsLoad.png">
</p>

The chart above shows an ideal case: all processes have a similar number of cells and therefore a similar workload. The chart below instead shows an unbalanced workload: process 0 has almost 200,000 cells, while all the others have at most 60,000. To improve this, follow the [instructions above](scalability.md#fds) to redistribute the cells among the processes.

<p align="center">
   <img width="400" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/MeshLoadDistributionToImprove.png">
</p>

If this is not enough to distribute the cells evenly, [split the larger meshes](https://cloudhpc.cloud/2022/09/15/split-fds-mesh-using-blenderfds/) and try again.

### FDS Mesh Decomposition
In some cases cloudHPC can decompose the FDS mesh for you, making it easier to achieve good scalability. The system decomposes your mesh when:

* the input FDS file has a single _&MESH_ line;
* the mesh has at least 40,000 cells;
* 4 or more vCPU are selected.

When the mesh is decomposed, the _output_ shows the following summary:

<p align="center">
   <img width="400" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/fdsdecomposition.png">
</p>

It contains the following parameters:

* INPUT MESH: string of the input mesh.
* REQU. DIVS: required divisions, usually equal to the number of vCPU.
* Init. IJK: I, J, K set on the input mesh.
* MESH CELLS: total number of cells of the input mesh.
* Limit. DIV: maximum number of divisions allowed for good scalability (15,000 cells per _&MESH_ line).
* INPUT XB: bounding box of the input mesh.
* DECOMPOS.: number of divisions along the three axes X, Y and Z.
* Final MESH: number of meshes after the decomposition. It can be lower than Limit. DIV, depending on how I, J and K can be divided.

Once the mesh has been decomposed, you can check the result with the [load distribution feedback](scalability.md#load_distribution_feedback).

!!! note
    When the mesh is decomposed, always check the smoke and temperature spread in Smokeview.

### More
* <a href="https://www.youtube.com/watch?v=sMQwgKK_GYM" target="_blank">Cloud HPC - Use the best scalability for your FDS analyses</a>
* <a href="https://cloudhpc.cloud/2022/01/28/fds-scalability/" target="_blank">How to reach good scalability in FDS</a>

## OpenFOAM
OpenFOAM only uses the multi-core (MPI) approach, which makes _highcore_ and _hypercore_ the most suitable instances for OpenFOAM on cloudHPC. The system automatically updates your _decomposeParDict_ file to match the number of vCPU selected: for this to work, follow the [hints](errors.md#decomposepardict) on the decomposeParDict file, or start from our [decomposeParDict template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/OpenFOAM/system/decomposeParDict).
Below are some decomposeParDict examples, where cloudHPC automatically updates the main entries to match the selected number of cores.

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

* [motorBike-of12 example](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/motorBike-of12): a case that really benefits from parallel hardware
* <a href="https://cloudhpc.cloud/2025/07/08/pushing-the-boundaries-cloudhpcs-journey-at-the-openfoam-workshop-2025-hpc-challenge-in-vienna/" target="_blank">Pushing the Boundaries: CloudHPC’s Journey at the OpenFOAM Workshop 2025 HPC Challenge in Vienna!</a>

## code_aster
code_aster can use OpenMPI and OpenMP at the same time. However, not all the versions compiled on cloudHPC support both. You can run OpenMPI and OpenMP together on the versions with the _\_mpi_ suffix, such as:

* 17.0 - Compiled with OpenMPI/OpenMP

With an OpenMP-only version, the `.comm` file produced by AsterStudy usually makes good use of the selected hardware as it is. With OpenMPI/OpenMP versions, instead, you have to adapt the `.comm` file following [our template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/code-aster/input.comm). The [flange-ca136 example](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/flange-ca136) is a complete MPI case.

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

The system reads the `mpi_nbcpu` value from your `.export` file and uses it as the number of MPI processes. Any remaining vCPU are used as OpenMP threads. Here is an example of the export file lines that affect scalability:

```
P mpi_nbcpu 4      #number of MPI cores - USER defined
P mpi_nbnoeud 1    #number of nodes     - always 1 on cloudHPC
P ncpus 8          #number of threads   - cloudHPC updated
```

* <a href="https://cloudhpc.cloud/2024/10/02/scalability-performance-code_aster-vs-calculix/" target="_blank">Scalability performance code_aster Vs calculiX</a>
* <a href="https://cloudhpc.cloud/2025/09/15/decoding-performance-a-scalability-showdown-between-calculix-and-code_aster/" target="_blank">Decoding Performance: A Scalability Showdown Between CalculiX and Code_Aster</a>

## CalculiX
CalculiX is a finite element analysis (FEA) program available on cloudHPC in several versions, which mainly differ in the linear solver library they use.

* Default version: the standard version of CalculiX uses the built-in SPOOLES solver library, a good general-purpose option for many simulations.

* Custom versions: for more demanding calculations, CalculiX can be compiled with more advanced solver libraries. These versions are easy to spot because their names end with a specific suffix:

    * PARDISO or PASTIX: the program uses a powerful third-party solver library designed for high-performance computing. Select it in the `.inp` file, e.g. `*STATIC, SOLVER=PARDISO`.

    * MPI: the program was compiled with OpenMPI, a library that allows it to run on several processors at the same time (parallel processing). This is crucial to solve very large and complex models much faster.

In short, the name of each CalculiX solver tells you what is inside: the standard SPOOLES library, a high-performance option such as PARDISO or PASTIX, or a build for parallel computing with MPI. The [beam-ccx221 example](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/beam-ccx221) is a complete CalculiX case.

* <a href="https://cloudhpc.cloud/2024/10/02/scalability-performance-code_aster-vs-calculix/" target="_blank">Scalability performance code_aster Vs calculiX</a>
* <a href="https://cloudhpc.cloud/2025/09/15/decoding-performance-a-scalability-showdown-between-calculix-and-code_aster/" target="_blank">Decoding Performance: A Scalability Showdown Between CalculiX and Code_Aster</a>

## OpenRADIOSS
* <a href="https://cloudhpc.cloud/2025/05/27/unlocking-extreme-performance-openradioss-scalability-on-cloudhpc-with-amd-epyc-processors/" target="_blank">Unlocking Extreme Performance: OpenRADIOSS Scalability on CloudHPC with AMD EPYC Processors</a>

## SU2

* [naca0012-su2830](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/naca0012-su2830) and [SU2_8.3_Turbulent_ONERAM6](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/SU2_8.3_Turbulent_ONERAM6) examples
* <a href="https://cloudhpc.cloud/2025/10/01/su2-and-the-challenge-of-scalability-how-cloudhpc-is-speeding-up-cfd-simulations/" target="_blank">SU2 and the Challenge of Scalability: How CloudHPC is Speeding Up CFD Simulations</a>
