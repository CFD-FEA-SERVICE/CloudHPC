# API V2 INTRODUCTION

The full API v2 documentation is available in the API SWAGGER page of [cloudHPC](https://cloud.cfdfeaservice.it/en/catuser/view-api), if your user has been enabled to use it.

!!! note
    To get access to the API service, contact our support team via chat or email.

## APIKEY AND API v2
Your APIKEY is on your [profile page](APIKEY.md). It must be passed to EVERY API call as a header. The correct way to do this is:

    -H 'X-API-key: $apikey'

So, an example call becomes:

    curl -X GET https://cloud.cfdfeaservice.it/api/v2/simulation/view-cpu -H 'accept: application/json' -H 'X-API-key: $apikey'

## USING THE SWAGGER
You can test each API directly in the Swagger page. Click the "Try it out" button to enter the API test mode, as shown in the following image:

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/APISwagger-1.jpg">
</p>

Some APIs require a JSON body (for example, the one that adds a new simulation). You can edit this JSON in the built-in editor, as shown in the following image.

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/APISwagger-2.jpg">
</p>

Once you are happy with the settings, test the API by clicking "EXECUTE". The "Response" section shows the response code and body of the call.

## SUGGESTED WORKFLOWS
Below are the recommended sequences of API calls for common operations. They are only meant to help developers integrate with cloudHPC, and are not mandatory. Most of the arguments required by each API are omitted here: for them, refer to the complete [API SWAGGER documentation](https://cloud.cfdfeaservice.it/en/catuser/view-api). The [exampleAPI folder](https://github.com/CFD-FEA-SERVICE/CloudHPC/tree/master/exampleAPI) contains a complete client implementing these workflows.

### UPLOAD A FILE
Uploading a file takes two steps. The first is an API call that returns the UPLOAD_URL where the file will be uploaded:

    POST /storage/upload-url Get upload URL

The second step is the actual upload of the FILE, with a PUT request such as:

    curl -X PUT -H 'Content-Type: application/octet-stream' -T FILE_NAME UPLOAD_URL

After uploading a file this way, we recommend deleting the cache before moving on, to tell the system that the upload has been completed.

    DELETE /user/delete-cache Delete the cache

### POST A NEW SIMULATION
The main purpose of cloudHPC is running simulations. To start a new one, use the following API:

    POST /simulation/add  -> Add one

To control the simulation, you can send a STOP signal. There are two types of signal:

* 	{ "signal": "SIGINT" }	 for hard stop
* 	{ "signal": "SIGTSTP" }	for soft stop

Send the signal to the simulation with the following API call:

    PUT /simulation/stop/{id} -> Stop one by id

### DOWNLOAD RESULTS
Files are downloaded from the storage with a single API call:

    GET /storage/download/{id} -> Download one by id

This API requires the id of the file to download. To find it, search the storage by file name and path with the following API call:

    POST /storage/view-by-path -> Get one

The download API returns a URL from which the file can be downloaded, for example with wget:

    wget DOWNLOAD_URL
