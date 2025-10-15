# API V2 INTRODUCTION

Full documentation for API v2 can be found in the API SWAGGER documentation directly in the [cloudHPC](https://cloud.cfdfeaservice.it/en/catuser/view-api) if your user has been anabled to use it.

!!! note
    If you want to get access to the API service, contact our support team via chat or send us an email.

## APIKEY AND API v2
You APIKEY can be found under the [profile page](APIKEY.md). APIKEY has to be passed to EVERY api call as a header argument. The correct way to do that is:

    -H 'X-API-key: $apikey'

So, an example call becomes:

    curl -X GET https://cloud.cfdfeaservice.it/api/v2/simulation/view-cpu -H 'accept: application/json' -H 'X-API-key: $apikey'

## USING THE SWAGGER
It is possible to test the use of each API directly on the Swagger. To do so you need to click on the "Try it out" button to enter the test mode of the API as shown on the following image:

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/APISwagger-1.jpg">
</p>

After that, some of the API might require you to enter a json file (for example the ADD a new simulation one). In such a case it is possible to edit this json using the assigned editor as in the following image.

<p align="center">
   <img width="600" src="https://cfdfeaservice.it/wiki/cloud-hpc/images/APISwagger-2.jpg">
</p>

Once you are happy with the settings, you can test the API clicking on "EXECUTE". Under the "Response" section you can see the response code and body of the API call you have just made.

## SUGGESTED WORKFLOWS
Here below the sequence of API call recommended for specific operations. The intention of these is just helping the developpers into their integration with our cloudHPC and do not required to be executed specifically. The list of the following API doesn't contain most of the arguments which are required by each API to work properly, for this refer to the complete [API SWAGGER documentation](https://cloud.cfdfeaservice.it/en/catuser/view-api).

### UPLOAD A FILE
The upload mechanism is a two step execution. The first step consist of an API call which returns the UPLOAD_URL where we are going to upload the file:

    POST /storage/upload-url Get upload URL

The second step is the actual upload of a FILE. This can be made via a PUT with the following settings:

    curl -X PUT -H 'Content-Type: application/octet-stream' -T FILE_NAME UPLOAD_URL

If the file is uploaded in this way, it is recommendable to delete the cache before proceeding with further steps to inform the system that the file upload has been completed.

    DELETE /user/delete-cache Delete the cache

### POST A NEW SIMULATION
The main purpose of the cloudHPC is obviously starting new simulations. To do that you can use the following API:

    POST /simulation/add  -> Add one

To controll the simulation it is possible to send a STOP signal. This signal can be of two types: 
* 	{ "signal": "SIGINT" }	 for hard stop
* 	{ "signal": "SIGTSTP" }	for soft stop

Once the signal has been generated it has to be passed to the simulation using the following API call:

    PUT /simulation/stop/{id} -> Stop one by id

### DOWNLOAD RESULTS
Downloading the FILES from the storage is made via a single API call:

    GET /storage/download/{id} -> Download one by id

This API requires you to enter the id of the file you need to download. To retrieve it you can search the storage by using the file name and path with the following API call:

    POST /storage/view-by-path -> Get one

The download API returns an URL where the file can be saved, this can be used with a simple wget to actually download the file:

    wget DOWNLOAD_URL
