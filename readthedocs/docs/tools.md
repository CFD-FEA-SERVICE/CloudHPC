# Tools for Windows and Linux

CFD FEA SERVICE srl provides several tools that make it easier to work with the cloudHPC platform. Most of them require your [APIKEY](APIKEY.md), available on your profile page.
You can browse, download and install the available tools from [this link](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases).

## cloudHPCexec
This tool lets you run your simulations directly from a terminal or through a Python executable. It is available in two versions:

* Linux DEBIAN package: a DEB package for Debian/Ubuntu Linux that adds the _cloudHPCexec_ command to your terminal. With this command you can manage your analyses on cloudHPC without using the website: run analyses, download results, connect via SSH to running analyses, stop them and much more.

* Windows executable: launches your simulations directly from your desktop, without opening the website. An example of how to set up the executable and launch a new analysis is available in [this post](https://cloudhpc.cloud/2022/12/30/execute-codeaster-windows/).

### DEBIAN/UBUNTU package
1. Installation

Download the cloudHPCexec.Ubuntu.deb package from [this page](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases).
Then run the following commands in a terminal:

    cd <path-to-folder-with-downloaded-deb-package>
    sudo dpkg -i cloudHPCexec.Ubuntu.deb

<p align="center">
   <a href="https://www.youtube.com/watch?v=pcALSbaXIvw"><img width="460" height="300" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/YoutubeVideo.png"></a>
</p>

2. Usage

On first use, cloudHPCexec asks for your API key and saves it. Then move into your case folder and run it:

    cd <case-folder>
    cloudHPCexec                                             # interactive: menus for vCPU, RAM and solver
    cloudHPCexec -batch 4 standard openFoam-of13 pitzDaily-of13   # non-interactive: vCPU, RAM, script, storage folder

Run `cloudHPCexec -help` for the full list of options. Every [ready-to-run example](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleCloudHPC) includes the exact cloudHPCexec command to launch it, and the source code of the tool is available in the [exampleAPI folder](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleAPI).

## cloudHPCstorage
This tool lets you mount the cloudHPC storage on your local PC, like any other hard drive or USB drive. You can then upload new analyses or download results with copy and paste or drag and drop. This tool is only available for Windows and requires a configuration file, which you can request from our support team by [sending an email](mailto:info@cloudhpc.cloud).
