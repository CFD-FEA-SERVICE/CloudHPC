<p align="center">
   <img width="600" src="https://cloudhpc.cloud/wp-content/uploads/2023/03/CloudHPC-logo.png">
</p>

# Welcome to the CloudHPC User Guide!
CFD FEA SERVICE provides cloudHPC, a cloud service for running CFD, FEM and other engineering simulations. Supported solvers include OpenFOAM, FDS, code_aster, CalculiX, SU2, code_saturne, OpenRADIOSS, EnergyPlus and many more, as well as your own bash or Python scripts (see the [full list of available software](https://cloudhpc.cloud/#softwareavail)). cloudHPC (High Performance Computing) lets you rent computing power on demand to run heavy, long-running engineering analyses. Your simulations run in the cloud and are managed entirely from the [web app](https://cloud.cfdfeaservice.it/), so your local computer stays free. The results are stored in the web app, where you can easily download them.

The service is dedicated to running simulations, so that you can:

* take advantage of large computing resources available on demand;
* avoid using your own servers or workstations;
* save time, by monitoring your analyses as they run and making the best use of the computing capacity you select.

## Workflow
Running a simulation on cloudHPC follows these steps:

* **Prepare the input files**: build the model on your local computer. The input files must be complete before you upload them to cloudHPC. Our [templates](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/template) contain the recommended settings for the most common solvers, and the [ready-to-run examples](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC) show how a case folder must be organised for each solver.
Give each case a unique name. If you modify a case and want to keep the results of the previous run, upload it under a new name: running a simulation on a file or folder with the same name overwrites the monitoring data and results of the previous run. The only exception is a case set up for restart (see the [Restart](simulation.md#restart) section): the new run continues from where the previous one stopped, so the earlier results are not lost.

* **Upload the input files**: upload your input files to the STORAGE of your account in the web app, either as single files or as a compressed archive (see [Storage](storage.md)).

* **Run the analysis**: start your analyses from the SIMULATIONS menu. Before launching, choose the computing power and memory by selecting the number of vCPU and the amount of RAM. Base this choice on the size of your model: you can then monitor the analysis while it runs and adjust the settings for the next runs (see [Simulations](simulation.md)).

* **Download the results**: download the results from the STORAGE menu. They are saved in the same folder where you uploaded the input files.

Each of these steps is described in detail in this guide.

## Case settings
Every case needs computing resources suited to its size. cloudHPC offers machines with:

* from 1 to 224 vCPU [each virtual CPU (vCPU) is a single hardware hyper-thread]
* 1.0 GB, 4.0 GB or 8.0 GB of RAM per vCPU, or 2.0 GB per physical core
* a 400 GB hard disk [standard for all simulations, with a few exceptions: see [Instance hard disk](simulation.md#instance_hard_disk)]
* unlimited cloud storage space, with files kept for a maximum of 60 days. After that, they are automatically deleted.

Each simulation runs on a virtual machine created when the simulation starts and destroyed when it ends. Two types of virtual machine are available:

- hyper-threaded [with both physical and logical processing units]
- multi-core only [with physical processing units only]

Depending on the software, your simulation may run best on physical cores only, or it may also benefit from logical (hyper-threaded) cores. We strongly recommend contacting the cloudHPC support team or the software developer to learn how your software behaves and achieve the best possible scalability. See also the [Scalability](scalability.md) section.
