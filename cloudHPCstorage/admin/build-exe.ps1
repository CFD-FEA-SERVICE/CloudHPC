<#
.SYNOPSIS
  Compiles Win64\install.ps1 into Win64\install.exe with ps2exe (run on Windows).

.DESCRIPTION
  The exe asks for administrator rights by itself (UAC) and has no console window.
  Writes Win64\install.exe.sha256 = SHA256 of install.ps1, used by build.sh to
  detect an install.exe older than install.ps1.

.PARAMETER CertThumbprint
  Optional: thumbprint of a code signing certificate (Cert:\CurrentUser\My) used
  to sign install.exe.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File admin\build-exe.ps1
#>
param([string]$CertThumbprint)

$ErrorActionPreference = 'Stop'
$win = Join-Path (Split-Path -Parent $PSScriptRoot) 'Win64'
$src = Join-Path $win 'install.ps1'
$exe = Join-Path $win 'install.exe'

if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Install-Module ps2exe -Scope CurrentUser -Force
}
Import-Module ps2exe

$version = (Select-String -Path $src -Pattern "^\`$SetupVersion\s*=\s*'([\d.]+)'").Matches[0].Groups[1].Value
Invoke-PS2EXE -inputFile $src -outputFile $exe -x64 -noConsole -noOutput -noError -requireAdmin `
    -title 'cloudHPCstorage setup' -description 'cloudHPCstorage setup' -product 'cloudHPCstorage' `
    -company 'CFD FEA Service' -copyright 'CFD FEA Service' -version "$version.0"

if ($CertThumbprint) {
    $cert = Get-Item "Cert:\CurrentUser\My\$CertThumbprint"
    Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -TimestampServer 'http://timestamp.digicert.com' | Out-Null
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $src).Hash.ToLower()
[System.IO.File]::WriteAllText((Join-Path $win 'install.exe.sha256'), $hash)
Write-Host "install.exe $version built from install.ps1 ($hash)"
