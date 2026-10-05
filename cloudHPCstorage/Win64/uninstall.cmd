@echo off
rem Removes cloudHPCstorage and all its drives (also in Settings - Apps).
rem Only one storage: uninstall.cmd -Storage <storage name>
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Uninstall %*
