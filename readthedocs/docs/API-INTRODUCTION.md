The API lets you control all the cloudHPC features through web calls. It is especially useful to integrate third-party software with cloudHPC. A working client, `cloudHPCexec`, is available in the [exampleAPI folder](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleAPI) of our repository.

Before going into the details of each API, keep in mind that every user is assigned a unique _{api_key}_, which is required by every API call. The api\_key is available on the user account page, as shown in the following image:

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/APIKEY.jpg">
</p>

cloudHPC also provides a _license file_, a JSON file with your username and apikey, which avoids mistakes when copying and pasting the apikey.

## Simulation status codes
The API calls described in the following pages use some codes, the most important being the STATUS of each simulation. The following table explains these codes.

| CODE | NAME | Description |
|------|------|-------------|
|10    | COMPLETED | analysis terminated correctly |
|60    | ERROR     | analysis terminated with errors |
|20    | PENDING   | analysis submitted and waiting for the system to start it |
|30    | RUNNING   | analysis in progress |
|50    | STOPPED   | analysis terminated because of a “STOP” signal |
|40    | STOPPING  | analysis terminating due to a “STOP” signal |

