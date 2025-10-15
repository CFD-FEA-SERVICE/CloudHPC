# Welcome to the CloudHPC User Guide!

<p align="center">
   <img width="600" src="https://cloudhpc.cloud/wp-content/uploads/2023/03/CloudHPC-logo.png">
</p>


CFD FEA SERVICE offers the use of a CloudHPC service to run Your scripts for CFD, FEM and other simulations. The scripts accepted are: codeAster, code Saturne, FDS, OpenFoam, paraview and snappyHexMesh. The innovative CloudHPC system (High Performance Computing) allows you to rent the computational capacity made available, in order to run heavy and long engineering analyses. This method permits you to run your simulations in Cloud, thus directly on the [web-app](https://cloud.cfdfeaservice.it/), avoiding the use of your own local computer for this process. The results would be generated in the Web-app and easily downloaded.

The offered service is restricted to only run the simulations, in order to:

* take advantage of the large computational capabilities offered to your disposition; 
* avoid using your own servers or computers; 
* saving time for the simulations’ duration given the possibility to monitor properly the advance of the analyses and optimize the use of the computation capacity available.

## Workflow
The Workflow for the proper use of the CloudHPC system of CFD FEA SERVICE, to run your simulations, is the following:

* **Create File**: First of all, the script[s] file[s] should be developed on your local computer. Before using the cloud HPC, it is necessary to complete the model creation locally. The model script[s], input file[s], should be completed in your software.
Consider that each script to upload should have a different name. For instance, if you want to modify the script and re-upload it, without losing the results of the previous simulation, then you have to rename the file. Simulations of file with the same name, lead to losing the monitoring and simulation's results of previous analysis. This would not happen only if the script is implemented with the restart string (check Restart paragraph). If so, the simulation would not delete the previous results even if the script has the same name, because the simulation will continue from where it was stopped.

* **Upload File**: The input file should be uploaded in the web-app STORAGE available in your account. The script[s] can be uploaded in different ways as a single file or a compressed one.

* **Execute Analysis**: It is possible to run the analyses in the SIMULATION menu. To execute the analysis, it is necessary to size the computational power and memory. Therefore, assigning the amount of vCPU and RAM to use. These characteristics are chosen depending on the size of your simulations and it is possible to monitor your analysis while running, in order to optimize your choice.

* **Download results**: it is possible to download the results from the STORAGE menu. The results are uploaded by the web-app directly in the folder in which you uploaded the input file.

All these steps are explored in this Guide.

## Case settings
Every case should have tailored settings in terms of computational capacity. The CluodHPC System offers you machines with:

* vCPU from 1 to 224 [Each virtual CPU (vCPU) is implemented as a single hardware hyper-thread]
* RAM available of 1.0 GB RAM / 4.0 GB RAM / 8.0 GB RAM for each vCPU or 2.0 GB per each CORE
* 400 Gb Hard Disk [standard for all simulations with few exceptions]
* Unlimited Cloud Storage Space, for a maximum of 60 days. After this, the files will be automatically deleted.

Each simulation you execute is performed on a virtual machine generated right for the time the simulation requires it and destroyed at the end of your analysis. The virtual machines allocated can be of two types:

- hyperthreaded [with physical and logical processing units]
- multicore only [with only physical processing units]

The software you are going to run can benefit of physical only processing units or both physical and logical processing units. The users is strongly recommended to contact either the support team of cloudHPC or the software manufacturer in order to get information about the software features and benefit of the best possible scalability.
