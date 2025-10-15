# Tools for Windows and Linux

CFD FEA SERVICE srl provides a number of tools to make it easier the interaction with the cloudHPC platform to the users. These tools often requires the use of the [APIKEY](APIKEY.md) which is available in your profile page.
You can have a look at the tools available, download and install them at [this link](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases).

## cloudHPCexec
This tool allows you to execute your simulations directly from your terminal or using a python executable. It is available in two separate versions:

* Linux DEBIAN package. DEB package installable on DEBIAN/UBUNTU linux versions, provides your terminal with the _cloudHPCexec_ command. This command allows you to manage your analysis on the cloudHPC platform without using the website. The operations you can do involves executing the analysis, downloading the results, SSH connection to running analysis, stopping your analysis and much more.

* Windows executable. WIN executable to launch your simulations directly from your desktop without opening the web site. An example on how setting up the executable and launch a new analysis is available in [this post](https://cloudhpc.cloud/2022/12/30/execute-codeaster-windows/).

### DEBIAN/UBUNTU package
1. Installation

Download the cloudHPCexec.Ubuntu.deb package from [this page](https://github.com/CFD-FEA-SERVICE/CloudHPC/releases).
Run on a terminal the command:

    cd <path-to-folder-with-downloaded-deb-package>
    dpkg -i cloudHPCexec.Ubuntu.deb

<p align="center">
   <a href="https://www.youtube.com/watch?v=pcALSbaXIvw"><img width="460" height="300" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/YoutubeVideo.png"></a>
</p>

## cloudHPCstorage
This tool allows you to mount the cloudHPC storage on your local PC, like any other hard drive or USB drive. In this way you can upload new analysis or download results by using the copy and paste or drag and drop features. This tool is just available for Windows and requires you to get a configuration file from our support by [sending them an email](mailto:info@cloudhpc.cloud).
