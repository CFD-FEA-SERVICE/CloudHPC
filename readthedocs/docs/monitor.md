# Monitor

## Simulation time
cloudHPC provides an estimate (ETA) of the total duration of the simulation. It is shown in the Output once the simulation has started, as highlighted in the image below. The ETA is only available for the following software:

* FDS [all versions]

<p align="center">
   <img width=650 src="https://cfdfeaservice.it/wiki/cloud-hpc/images/ETA.png">
</p>

!!! note
    The duration provided is a preliminary estimate and is not a contractual element or a binding quote. The final cost is based on the actual consumption measured at the end of the run.

### Manual estimate
To estimate the duration of a simulation yourself, check how much simulated time is computed in a given amount of real time. Do this after at least 2 hours of run time.
For example, suppose you want to simulate 600 seconds and, after 2 hours, 120 seconds have been computed. The simulation advances by about 60 seconds of simulated time per hour, so it will take about 10 hours to reach 600 seconds.

<p align="center">
120s : 2h = 60s/h

600s : 60s/h = 10 h
</p>

## Runtime monitor
cloudHPC lets you monitor your analysis while it runs and, at the same time, check how the hardware resources (vCPU and RAM) are being used. To open the monitor, click the "View" button of the analysis you want to follow.

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/FIG_13_VIEW_SIM.png">
</p>

The simulation view page shows information about the running analysis and lets you control it. Its sections are briefly explained below.

## Simulation output
The most important window is the simulation output: a real-time log of all the information produced by cloudHPC while your simulation is running. Here you can find:

1. [Errors and warnings](errors.md) produced by the cloudHPC
1. A basic plot of the runtime log of your solver
1. Information from cloudHPC about each phase of your analysis

The output is the main window of the simulation view page, as shown in the following image.

<p align="center">
   <img width="800" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/ErrorOutput.png">
</p>

## Runtime plots
While your solver runs, cloudHPC plots its most important outputs into charts that are easy to read. Every CSV file generated during the run is automatically plotted. In addition, some software packages produce more advanced outputs:

* **OPENFOAM**: cloudHPC automatically generates a chart for each runtime post-processing function enabled in _controlDict_. Set up the functions you want to monitor before launching the analysis: residuals, maximum pressure/velocity, temperatures, flow rates, etc. The [controlDict template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/OpenFOAM/system/controlDict) already contains residuals, maximum values and yPlus.

* **FDS**: the system automatically plots every CSV file written by FDS during the run. To see the results, define &DEVC (devices) and assign them the quantities to monitor, as done in the [FDS template](https://github.com/CFD-FEA-SERVICE/CloudHPC/blob/master/template/FDS/template.fds).

* **Custom scripts**: write your own CSV file during the run to get live charts, as done in the [python-script template](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/template/python-script).

<p align="center">
   <img width="300" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/FIG_15_data_monitoring.png">
</p>

## Runtime logs
Every simulation software writes a log file, which is displayed at runtime in the web app. You can check these logs in two ways:

1. In the **Output** section, which shows a brief summary of the simulation status
1. In the **Logs** section, which lists every log file produced. The logs remain available after the simulation has ended, for reference

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/LogFiles.jpg">
</p>

## Remote desktop
On enabled accounts, you can access the virtual machine running your simulation via remote desktop. This feature is available on the "view" page of each simulation and gives you access to all the hardware resources of the instance. With it you can:

* monitor the running process
* check the status of the hardware resources
* run your preferred post-processing software such as ParaView, SALOME or Smokeview

The remote desktop is available for all simulations with status RUNNING. To access it, open the "view" page of the simulation and scroll to the bottom of the page.

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/RemoteDesktop.jpg">
</p>

<p align="center">
   <a href="https://www.youtube.com/watch?v=yPJWTfmcsY4"><img width="460" height="300" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/YoutubeVideo.png"></a>
</p>

## Hardware monitor
Besides the solver results, you can monitor vCPU and RAM usage at any time. These charts help you understand whether the computing capacity you selected is sufficient or oversized.

As a general rule, try to always keep at least 1000 MB available on the _Free_ line (red).

<p align="center">
   <img width="300" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/FIG_16_CPU_good.png">
   <img width="300" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/FIG_17_RAM_good.png">
</p>

## SSH Connection
Advanced users can also connect via SSH to the instance running the simulation. This gives you full control of the running analysis: for example, you can create, edit or delete files.

!!! note
    CFD FEA SERVICE SRL cannot take responsibility for any action performed by users on the instance. In particular, if you stop the simulation or delete the results it produced, we cannot recover them.

### Prerequisites

!!! info
    For security reasons, SSH port 22 is closed for all accounts. To open it for your IP address, contact our support team.

To access running simulations via SSH, make sure you have saved your public key in your profile, as shown in the following image:

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/SSHkey.jpg">
</p>

To display your public key on Linux-based systems, run the following command in a terminal:

	cat .ssh/id_rsa.pub

### Connect via SSH
Once your public key has been saved, connect to a running instance with the following command:

	ssh -X -o "StrictHostKeyChecking no" cloudhpc@SIMULATION_IP_ADDRESS

where SIMULATION\_IP\_ADDRESS is shown on the "view" page of the running analysis. You can do the same with the [cloudHPCexec](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases) tool by typing:

	cloudHPCexec -ssh SIMULATION_ID
