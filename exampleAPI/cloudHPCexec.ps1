#Installing new script
Start-Process PowerShell -Verb RunAs -Wait -Argument "wget https://raw.githubusercontent.com/CFD-FEA-SERVICE/CloudHPC/master/exampleAPI/cloudHPCexec.ps1 -OutFile C:\Windows\System32\cloudHPCexec.ps1"

#APIKEY definition
$apikey="apikey_to_pass"

#Alternative WGET for windows
(Invoke-WebRequest -Method GET -Uri https://cloud.cfdfeaservice.it/api/v1/simulation/short/6250 -H @{'api-key' = $($apikey); 'Accept' = 'application/json'}).Content

Start-Sleep -s 30
