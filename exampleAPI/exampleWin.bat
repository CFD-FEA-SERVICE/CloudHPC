::ECHO OFF

SET apikey="XXXX"

ECHO APIKEY: %apikey%

::LIST ALL SIMULATIONS #########################################################
curl -X GET https://cloud.cfdfeaservice.it/api/v1/simulation -H %apikey% -H "Content-Type: application/json" -H "Accept: application/json"

PAUSE
