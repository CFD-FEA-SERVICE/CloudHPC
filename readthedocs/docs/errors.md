# Detecting execution errors

When running an analysis on cloudHPC, your simulation may finish (STATUS = COMPLETED) even though it actually ended with an error. This depends on how the analysis was set up, usually on its input files and on the vCPU and RAM selected. The easiest way to spot the error is to read the 'Output' section of your simulation page, highlighted in the following image.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/ErrorOutput.png">
</p>

Below is a list of the most common errors and the simplest ways to fix them. Many of them can be avoided by starting from our [templates](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/template), or by comparing your case with the [ready-to-run examples](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC).

### Low RAM available
A common problem is undersizing the computing power and memory assigned to your simulation, so monitor vCPU and RAM usage during the first hours of the run. This issue is usually reported with the following message in the output:

!!! warning
    ```
	@@@ RAM used > 80.0%: increase vCPU or use highmem instance
    ```

When the system runs out of RAM, the behaviour depends on the solver. The most common messages are:

```
@@@ ERROR: SWAP unresolved after 5 attempts => turningoff
```

```
===================================================================================
=   BAD TERMINATION OF ONE OF YOUR APPLICATION PROCESSES
=   RANK 0 PID XXXX RUNNING AT hpc-serverXXXXX
=   KILLED BY SIGNAL: 9 (Killed)
===================================================================================
```

In all cases, the solution is to increase either the number of vCPU or the RAM, by selecting 'standard' or 'highmem'.

!!! note
    RAM issues are more frequent with few vCPU and with the 'highcpu' or 'hypercpu' RAM options. In particular, with 1 vCPU the small amount of RAM allocated is only enough for simple scripts, and most software cannot run in this configuration.

### Hard disk use
Every simulation runs on a dedicated virtual machine with a fixed-size hard disk, whose [size](simulation.md#instance_hard_disk) ranges from 200 GB to 2000 GB. If your simulation produces a very large amount of data, the hard disk may not be big enough to store it all. In this case the system shows the following warning in the output window:

!!! warning
    ```
	@@@ HARD DISK used > 80.0%: SOFT STOP your analysis to prevent data loss - System automatically stops analysis at 90.0% hard disk use
    ```

This message is just a warning. If your data keep growing, the system shows this second warning:

!!! warning
    ```
	@@@ HARD DISK used > 90.0% - @@@ AUTOMATIC SOFT STOP procedure
    ```

This time, right after the warning, the system starts a [soft stop](simulation.md#soft_and_hard_stop).

### Incorrect compressed file
If the input file was compressed or uploaded incorrectly, the following error appears in the simulation output.

!!! danger
    ```
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	@@@ Not found folder _name_ inside of compressed file _FOLDER_
	@@@ Make sure the compressed file name match exactly the      
	@@@ folder contained inside of it                             
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ```

To upload a compressed file correctly, pay attention to two things:

* compress the file correctly

* upload the file correctly

Both steps are described in detail in the section [“Upload of a folder”](storage.md#upload_of_a_folder). The key point is that, once extracted, the files must end up inside a single folder in the STORAGE list. So, if you compressed a local folder containing the files, upload the archive without placing it in another folder, by leaving the Dirname box empty. If instead you compressed the files themselves, so that they are not inside a folder when extracted, upload the archive into a new folder created in the web app, by typing the folder name in the Dirname box.

### Incorrect file or folder name
Sometimes your input file or folder name is not recognised, so cloudHPC cannot handle it. This is reported by the following message in the output:

!!! danger
    ```
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
	@@@ FOLDER _Folder-Name_ not detected
	@@@ - make sure you correctly defined the FOLDER in STORAGE
	@@@ - characters like , ( ) MUST NOT be present in FOLDER name
	@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ```

To fix this error:

* Make sure your input file is in one of the formats accepted by the application. In this case, the system also reports the message: _Folder-Name_ not recognized as an available compressed format


* Check that the file or folder name does not contain invalid characters. cloudHPC does not accept special characters such as: , ( ) ' $ ~ " # . If any of them is present, rename your input file or folder to remove them.

## FDS incorrect settings
Every FDS analysis takes a single `.fds` file as input. The following error is reported when the system cannot find the `.fds` file, so the analysis cannot start.

!!! danger
    ```
	@@@ ERROR: No FDS file detected
    ```

This is usually caused by an incorrect upload, such as a different file format or a modified file extension. Make sure you upload the correct `.fds` file and run the simulation again. The [FDS template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/FDS/template.fds) and the [roomFire-fds691 example](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/roomFire-fds691) show a correct FDS input.

### Scalability issue with MPI\_PROCESS
When running a multi-core FDS analysis, two kinds of issues may prevent it from running properly. The first one concerns the MPI\_PROCESS parameter assigned to each mesh: its values must be in **ASCENDING ORDER**. If the following error is reported, edit the input FDS file and reorder the &MESH lines so that the values are in ascending order.

!!! danger
    ```
	@@@ ERROR: MPI_MPI_PROCESS incorrect
	@@@        MPI_MPI_PROCESS parameter must be in ASCENDING ORDER
	@@@        Reorder &MESH in FDS file if simulation fails
    ```

If your input FDS file requires a specific number of CORES, because of the number of &MESH lines or of the MPI\_PROCESS groups, make sure the vCPU selected match it. Otherwise, the following error is reported, with two possible solutions: increase the number of vCPU assigned to your simulation, or change MPI\_PROCESS to reduce the number of vCPU required. See the [scalability section](scalability.md#choosing_the_right_vcpu_for_your_fds_simulation) for how to choose vCPU.

!!! danger
    ```
	@@@ ERROR: low vCPU selected
	@@@        Number of MESHES higher than available CORES. CORES available: XX
	@@@        -> increase the number of vCPU
	@@@        -> use the MPI_PROCESS parameter to assign 2 or more meshes to one single CORE
    ```

### Warning messages by FDS
If your FDS analysis is not set up correctly, in particular when some objects or devices do not fall within any mesh, FDS issues warning messages. Since there can be many of them, the system stops displaying them after a certain number and shows the following message:

!!! danger
    ```
	@@@ ERROR: no other WARNING messages showed
	@@@        check logs for more details
    ```

### Pyrosim input file
cloudHPC runs FDS input files only. If you upload, for example, a .psm file generated by the PyroSim UI, the system cannot run your analysis and reports the following error:

!!! danger
    ```
	@@@ ERROR: _filename_.psm is a pyrosim file. Please upload a `.fds` one instead
    ```

To run an FDS analysis, remember to export the `.fds` file from the user interface you are using.

### High number of threads
The following warning represents an issue with the scalability of your FDS analysis:

!!! warning
    ```
	@@@ WARNING: high number of threads used
	             The number of vCPU selected and the settings in your .fds file
	             lead to a high number of threads. This generally is not recommendable
	             Split your mesh in order to achieve a better scalability
    ```

Given the number of meshes defined in your `.fds` file, the vCPU selected forced the system to use a high number of threads for this analysis. Your simulation runs, but it may not make the best use of the allocated hardware. We recommend reading the [scalability section](scalability.md#fds).

### High number of Pressure ZONES
A pressure zone is a part of your fluid domain separated from the rest of the domain by an obstruction (OBST) or other solid. Recent versions of FDS automatically detect pressure zones and solve them as separate domains. This may create a very high number of pressure zones, especially when the geometry is much more detailed than the local cell size. In this case, cloudHPC reports the following warning in the output.

!!! warning
    ```
	@@@ WARNING: high number of Pressure Zones found - risk of poor scalability
    ```

Your simulation usually runs correctly, but experience shows that scalability may suffer: the simulation may not run as fast as it could. In these cases we recommend reducing the number of pressure zones with two parameters of the &MISC namelist (the [FDS template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/FDS/template.fds) already sets the first one):

* MINIMUM\_ZONE\_VOLUME=1.0: sets a threshold volume. Pressure zones smaller than the threshold are converted into solid obstructions.
* NO\_PRESSURE\_ZONES=T: for debugging only, removes all pressure zones separated from the main one.

### DEVC affecting performances
Some specific DEVC in your FDS simulation have been found to reduce performance on AMD processors. The issue is still being investigated with the FDS developers at NIST, but it affects at least the following DEVC:

* VISIBILITY
* RADIATIVE HEAT FLUX
* GAUGE HEAT FLUX GAS

Other DEVC may be affected, and a complete list is not available yet. Your simulation will run, but it will not use 100% of the computing power of the AMD processors allocated. No solution has been found yet for AMD processors: the best alternative is to use _hypercore_ or _hypercpu_ instances, which run on INTEL processors. In any case, you will receive the following warning:

!!! warning
    ```
	@@@ WARNING: DEVC for _VARIABLE_ may slow down your simulation.
	             Make sure you run on a hyper type of instances
    ```

## OpenFOAM incorrect settings

### Incorrect dictionary
OpenFOAM requires a specific case structure to work properly. At a minimum, the case needs three folders:

* 0
* constant
* system

When running any OpenFOAM solver, cloudHPC checks that the system/controlDict file exists and, if it is missing, reports the following error.

!!! danger
    ```
	@@@ ERROR: Cannot find system/controlDict
	@@@        check your openFoam dictionary
	@@@        Current folder content:
    ```

This is often caused by an incorrect upload of the case, which must be uploaded as a [folder](storage.md#upload_of_a_folder). The [OpenFOAM examples](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/pitzDaily-of13) show the expected case layout.

### Multi-core analysis
On cloudHPC, OpenFOAM is configured to always run in parallel. For this reason, any OpenFOAM solver, as well as mesh generation with snappyHexMesh, requires more than one process (nProc > 1). This means selecting at least vCPU = 2 on highcore/hypercore machines, or vCPU = 4 on highcpu, standard or highmem machines.

The error message depends on the step that fails. If it is the OpenFOAM solver:

!!! danger
    ```
	@@@ ERROR: openFoam script runs with nProc > 1
	@@@        select a higher number of vCPU
    ```

or if it is the snappyHexMesh mesh generation:

!!! danger
    ```
	@@@ ERROR: snappy script runs with nProc > 1
	@@@        select a higher number of vCPU
    ```

### SnappyHexMesh general error
snappyHexMesh may fail to generate a mesh for many reasons: insufficient RAM, geometry issues in the input STL files, etc. If snappyHexMesh does not finish properly, the following error message is reported:

!!! danger
    ```
	@@@ ERROR: snappyHexMesh failure
	@@@        check log.snappyHexMesh
    ```

### General problem with OpenFOAM solver
When running any OpenFOAM solver, the first check is for the _polyMesh_ folder in the uploaded case. If this folder is missing, the simulation reports the following error.

!!! danger
    ```
	@@@ ERROR: polyMesh folder not found
	@@@        Your simulation may fail
    ```


### decomposeParDict
To run your OpenFOAM analysis with our standard solvers, _decomposeParDict_ must be set correctly. The solver assumes:

* decomposition method: _scotch_ or _hierarchical_
* numberOfSubdomains: automatically adjusted according to vCPU selected
* coeffs and hierarchicalCoeffs: automatically adjusted according to vCPU selected

With incorrect settings, the simulation shows the following error message in the output:

!!! danger
    ```
	@@@ ERROR: incorrect decomposeParDict file
	@@@        suggested method is scotch"
	@@@        current cores set in decomposeParDict:
	numberOfSubdomains 10
	@@@        make sure vCPUS matches this
    ```


The OpenFOAM analysis may start anyway, but _numberOfSubdomains_ is not adjusted by the system: it is then up to you to make sure the simulation uses all the vCPU allocated to the instance.

If you need help, replace your decomposeParDict with our [template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/OpenFOAM/system/decomposeParDict), which meets these requirements.

### controlDict
To set up your controlDict file correctly, remember to:

* use the '_application_' entry to specify the solver to run (on openfoam.org v11 and newer, `application foamRun;` plus `solver <module>;`)
* use '_functions_' to extract the quantities you want to monitor. Everything defined here that writes into the postProcessing folder during the run is converted into a chart at runtime.

We recommend starting from this [template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/OpenFOAM/system/controlDict) to set up this file. It also lists the optional [cloudHPC custom entries](simulation.md#custom_controldict_entries).

cloudHPC requires the '_startFrom_' entry to be set to the latest available time (`startFrom latestTime;`). If your setting is different, the system changes it automatically and reports the following warning:
 
!!! warning
    ```
	@@@ WARNING -> suggested to use startFrom latestTime in system/controlDict

    ```

## code_aster settings
To run code\_aster on cloudHPC you need to upload at least three files:

* `.export`: specifies which input files are run, where the mesh is and which outputs are produced
* `.comm`: the actual simulation, basically a Python script where a sequence of code\_aster commands defines the FEM analysis and its results
* `.med` or `.unv`: the mesh, in MED or UNV format

[This template](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/template/code-aster) contains an example of the `.export` and `.comm` files, and the [flange-ca136 example](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC/flange-ca136) is a complete, ready-to-run case.

### export file missing
The three files mentioned above (`.export`, `.comm` and `.med`/`.unv`) are required to run any analysis. If the `.export` file is missing, the system reports the following error.

!!! danger
    ```
	@@@ ERROR: no export file detected
    ```
