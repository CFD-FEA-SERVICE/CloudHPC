The API is a methodology which allow to controll all the cloudHPC functionalities by web calls. This methodology is highly useful in case of integration of third part software with our functionalities.

Before entering the details of each API, keep in mind that every use is assigned a unique _{api_key}_ which is required by any API call to work properly. Api\_key is available in the user account page as described in the following image:

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/APIKEY.jpg">
</p>

The cloud HPC system also provide a _lincense file_ - a JSON with username and apikey - which can be used to avoid mistakes by the user when copying and pasting its apikey.

## Simulation status codes
The API calls we are going to mention later refer to some coding. The most important of which is the STATUS of every simulation. The following table gives an explanation of the codes used.

| CODE | NAME | Description |
|------|------|-------------|
|10    | COMPLETED | analysis terminated correctly |
|60    | ERROR     | analysis terminated with errors |
|20    | PENDING   | analysis submitted and waiting for the system to start it |
|30    | RUNNING   | analysis in progress |
|50    | STOPPED   | analysis terminated because of a “STOP” signal |
|40    | STOPPING  | analysis terminating due to a “STOP” signal |

