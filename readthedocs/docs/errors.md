## Find errors and understand them

When running analysis on the cloudHPC it may happen that your simulation finishes ( STATUS = COMPLETED ) even if it actually ended with an error. This situation depends on the way you configured your analysis to run on the system and it generally depends on the input file of the analysis and also on the choice in terms of vCPU and RAM. The easiest way to detect the error is reading the 'Output' section of your simulation page as highlighted by the following image.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/ErrorOutput.png">
</p>

Here below you can find a list of the most common errors with the easiest possible solutions you can apply to them.

## Low RAM available
A common problem is related to the sizing of the computational power and memory assigned to your simulation. It is important to monitor the vCPU and RAM in the first hours of simulation. This error is generally communicated with the following message in your output:

!!! warning
    ```
	@@@ RAM used > 80.0%: increase vCPU or use highmem instance
    ```
 
If the RAM increases all of a sudden, the above message may not appear and you could have a message like the following:

!!! danger
    ```
	===================================================================================
	=   BAD TERMINATION OF ONE OF YOUR APPLICATION PROCESSES
	=   RANK 0 PID XXXX RUNNING AT hpc-serverXXXXX
	=   KILLED BY SIGNAL: 9 (Killed)
	===================================================================================
    ```

In both cases, the solution is to increase either the number of vCPU or the RAM allocation by selecting 'standard' or 'highmem'.

### Hard disk use
Every simulation runs on a dedicated virtual machine. These are provided a fixed size hard disk whose ["size spans"](simulation.md#instance_hard_disk) from 100Gb to 2000Gb. It may happen that your simulation produces a huge amount of data and those hard disk sizes are not sufficient to store all your information. In this case the system provides you the following warning message in the output window:

!!! warning
    ```
	@@@ HARD DISK used > 80.0%: SOFT STOP your analysis to prevent data loss - System automatically stops analysis at 90.0% hard disk use
    ```

This message is just a warning. In case your data size increases even more the system provides you this new warning

!!! warning
    ```
	@@@ HARD DISK used > 90.0% - @@@ AUTOMATIC SOFT STOP procedure
    ```

This time, right after the warning the system starts a soft ["stop procedure"](simulation.md#soft_and_hard_stop).

## Incorrect compressed file
If the input file was compressed or uploaded incorrectly, the following error will appear in the outputs of the simulation.

!!! danger
    ```
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	@@@ Not found folder _name_ inside of compressed file _FOLDER_
	@@@ Make sure the compressed file name match exactly the      
	@@@ folder contained inside of it                             
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ```

To upload correctly a compressed file, two are the things you should pay attention to:

* Compress the file correctly

* Upload the file correctly

These two steps are described in detail in paragraph [“Upload of a compressed file”](storage.md#upload_of_a_locally_compressed_folder). The main concept is that in the web-app the file should appear to be in a folder in the STORAGE list when uncompressed. Hence, if the file is collected in local in a folder that is then compressed, when it is uploaded in the web-app, it should not be inserted in a second folder, achievable by leaving the Dirname box empty. If the files are compressed by themself, hence when they are extracted, they will not be in a folder, then it is important to upload the compressed file in the storage creating a folder directly in the web-app. This is possible simply by adding the folder name in the Dirname box.

## Incorrect file or folder name
There are situations where your input filename or foldername is not recognized and consequently the cloudHPC can't handle it. These situation are highlighted by the following message in the output:

!!! danger
    ```
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	@@@ FOLDER _Folder-Name_ not detected
	@@@ - make sure you correctly defined the FOLDER in STORAGE
	@@@ - characters like , ( ) MUST NOT be present in FOLDER name
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ```

To fix this error you have few alternatives:

* Make sure your input file is among the oneis accepted by the application. When this occurs, the system reports also the following message: _Folder-Name_ not recognized as an available compressed format


* The file or folder name contains invalid characters. Generally the cloudHPC system does not allow your input file name to have special characters such as the followings: , ( ) ' $ ~ " # . If any of these characters is present, rename your input file and remove these special characters.

## FDS incorrect settings
Every FDS analysis assumes as an input one single `.fds` file. The following error is reported when the system could not detect the `.fds` file and, consequently, the analysis cannot start.

!!! danger
    ```
	@@@ ERROR: No FDS file detected
    ```

Usually this depends on incorrect file upload, such as other file formats or modified file extension. Make sure you upload the correct `.fds` file and execute the simulation one more time.

### Scalability issue with MPI\_PROCESS
When running a multi-core analysis using FDS there might be two type of issues that prevent your analysis to run properly. The first issue regards the MPI\_PROCESS parameter to be assigned to every mesh: this parameter must be assigned in **ASCENDING ORDER** only. In case the followign error is reported, it is necessary to edit the input FDS file and reorder the &MESH elements so the ASCENDING ORDER is guaranteed.

!!! danger
    ```
	@@@ ERROR: MPI_MPI_PROCESS incorrect
	@@@        MPI_MPI_PROCESS parameter must be in ASCENDING ORDER
	@@@        Reorder &MESH in FDS file if simulation fails
    ```

In case your input FDS file requires a specific number of CORES, either because you have entered a certain number of &MESH lines or because you used a specific MPI\_PROCESS for all the meshes, make sure that vCPU matches this number. In case this is not verified, the following error reminds you to do so with the two possible solutions: increase the number of vCPU assigned to your simulation or modify the MPI_PROCESS to lower the number of required vCPU

!!! danger
    ```
	@@@ ERROR: low vCPU selected
	@@@        Number of MESHES higher than available CORES. CORES available: XX
	@@@        -> increase the number of vCPU
	@@@        -> use the MPI_PROCESS parameter to assign 2 or more meshes to one single CORE
    ```

### Warning messages by FDS
In case of incorrect setup of your FDS analysis, in particular when some objects or devices do not fall withing any mesh, you receive a warning message from FDS. Since these warning messages can be numerous, the system trims them once they reach a specific number and provides you the following error message:

!!! danger
    ```
	@@@ ERROR: no other WARNING messages showed
	@@@        check logs for more details
    ```

### Pyrosim input file
The cloudHPC platform can handle FDS simulation. If you upload for example a .psm file - generated by the UI Pyrosim - the system is not able to execute your analysis and report the following error:

!!! danger
    ```
	@@@ ERROR: _filename_.psm is a pyrosim file. Please upload a `.fds` one instead
    ```

To execute FDS analysis remember of exporting the `.fds` from any user interface you are using.

### High number of threads
The following warning represents an issue with the scalability of your FDS analysis:

!!! warning
    ```
	@@@ WARNING: high number of threads used
	             The number of vCPU selected and the settings in your .fds file
	             lead to a high number of threads. This generally is not recommendable
	             Split your mesh in order to achieve a better scalability
    ```

The configuration of vCPU, considering the restriction in your input `.fds` file where the number of meshes is defined, forced the system to select a high number of threads for the current analysis. Even if your simulation is running, it may not use the hardware resources allocated at their best. It is recommended to read the ["scalability paragraph"](scalability.md#fds).

### High number of Pressure ZONES
A pressure zone is a part of your fluid domain which is disconnected from the rest of your domain through an obstacle OBST or any other solid material. Recent versions of FDS authomatically detect pressure zones and solve them as a separate domain of your simulation. This feature may result in a generation of a very high number of Pressure Zones, in particular in cases where the geometry is extrimely refined compared to the local cells dimensions. In such a case the following working is reported by the cloudHPC output.

!!! warning
    ```
	@@@ WARNING: high number of Pressure Zones found - risk of poor scalability
    ```

Generally, your simulation can perform correctly even if experience showed that scalability may suffer: you may notice your simulation will not execute as fast as it could. It is recommendable to reduce the number of pressure zones in these cases by using two FDS commands specified under the &MISC namelist:

* MINIMUM\_ZONE\_VOLUME=1.0 . This command allows you to define a threshold volume value. Pressure zones with a volume lower than the threshold value are then converted into OBST or equivalent solid part
* NO\_PRESSURE\_ZONES=T . Options to use for debug only, completely delete any pressure zone generated and separated from the main one

### DEVC affecting performances
It's been noted that the presence of some specific DEVC in your FDS simulation may affect the performance of AMD processors. This issue is still under complete investigation with the FDS/NIST developpers, but it affects at least the following DEVC:

* VISIBILITY
* RADIATIVE HEAT FLUX
* GAUGE HEAT FLUX GAS

More DEVC may be affected and a complete list of all affected devices is not yet complete or available. Your simulation will run but it will not be able to use 100% of the computational power you are allocating of the AMD processors. For AMD processor a solution to this problem has not been found yet and the current best alternative would be to use either _hypercore_ or _hypercpu_ instances which are powered by INTEL processors. In any case, you'll receive the following warning message to monitor the situation:

!!! warning
    ```
	@@@ WARNING: DEVC for _VARIABLE_ may slow down your simulation.
	             Make sure you run on a hyper type of instances
    ```

## OpenFOAM incorrect settings

### Incorrect dictionary
OpenFOAM requires a specific dictionary to work properly. In particular the minimum configuration requires three folders:

* 0
* constant
* system

When executing any openFoam related solver, the cloudHPC checks for the existance of the system/controlDict file and, when missing, the following error is reported.

!!! danger
    ```
	@@@ ERROR: Cannot find system/controlDict
	@@@        check your openFoam dictionary
	@@@        Current folder content:
    ```

Often this issue is related to uploading correctly the dictionary which requires uploading a [folder](storage.md#upload_of_a_folder).

### Multi-core analysis
OpenFOAM is configured to run in multi-cores mode on the cloudHPC. For this reason, when attempting to execute any openfoam solver and also the mesh generation with snappy, it is required the user to select nProc to be higher than 1. This means that vCPU must be equals to 2 in case we are using highcore machines or vCPU = 4 in case we use highcpu, standard or highmem configuration.

The error message we are to receive depends on whether the openfoam solver is causing the issue:

!!! danger
    ```
	@@@ ERROR: openFoam script runs with nProc > 1
	@@@        select a higher number of vCPU
    ```

of if the snappyHexMesh generation is causing it:

!!! danger
    ```
	@@@ ERROR: snappy script runs with nProc > 1
	@@@        select a higher number of vCPU
    ```

### SnappyHexMesh general errory
It may happen that snappy is not able to generate a mesh. The reasons for this can be quite different: insufficient RAM, geometrical issues with input STL files, etc. Once the snappyHexMesh solver runs if the solver did not finish properly the following error message is reported:

!!! danger
    ```
	@@@ ERROR: snappyHexMesh failure
	@@@        check log.snappyHexMesh
    ```

### General problem with OpenFOAM solver
When executing any simulation with any openfoam solver, the first control regards the presence of the _polyMesh_ folder in the dictionary uploaded. If this folder is not present the simulation is going to report the following error.

!!! danger
    ```
	@@@ ERROR: polyMesh folder not found
	@@@        Your simulation may fail
    ```


### decomposeParDict
In order to run your OpenFOAM analysis, if you use our default solvers, it is recommended to use a correct settings of _decomposeParDict_. By default in fact the solver assumes:

* decomposition method: _scotch_ or _hierarchical_
* numberOfSubdomains: automatically adjusted according to vCPU selected
* coeffs and hierarchicalCoeffs: automatically adjusted according to vCPU selected

If you use an incorrect settings, the simulation will return an error message through the output as follows:

!!! danger
    ```
	@@@ ERROR: incorrect decomposeParDict file
	@@@        suggested method is scotch"
	@@@        current cores set in decomposeParDict:
	numberOfSubdomains 10
	@@@        make sure vCPUS matches this
    ```


The OpenFOAM analysis might start anyway with the only difference that _numberOfSubdomains_ is not adjusted by the system and is up to the user using all the vCPU and cores allocated in the instance for your simulation.

In case you need help, it is possible to refer to our [template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/OpenFOAM/system/decomposeParDict) and replace your current decomposeParDict with one that match the requests.

### controlDict
In order to correctly set-up your controlDict file, it is mandatory to remember:

* use '_application_' dictionary to specify the solver to use
* use '_functions_' in order to extract your monitoring parameters. Everything defined here which is returned during the executing in the postProcessing folder is converted into a graph by the solver at runtime.

It is recommandable to refer to this [template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/OpenFOAM/system/controlDict) to guide yourself into set-up this file.

The cloudHPC executable requires that the parameter '_startFrom_' is set to begin from the latest available time step. In case your settings are differently, automatically the system modifies it so that it matches this and the following warning is then reported:
 
!!! warning
    ```
	@@@ WARNING -> suggested to use startFrom latestTime in system/controlDict

    ```

## Code Aster settings
Runnin Code\_Aster on the cloudHPC requires the user to upload at least three files:

* `.export` . It's the file that specifies which input file are going to be executed, where your mesh is located and which output have to be produced
* `.comm` . It's your real simulation. It consist of basically a python script where a sequence of Code\_Aster functions generates the FEM analysis and the results 
* `.med` or `.unv` . It's your mesh. This can be in MED file format or UNV file format.

We made available [this template](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/template/code-aster) where you can actually see example of the above three files.

### export file missing
The three files mentioned before ( `.export`, `.comm` and `.med`/`.unv`) are mandatory to execute any analysis. In the file `.export` is missing the system reports you the following error.

!!! danger
    ```
	@@@ ERROR: no export file detected
    ```
