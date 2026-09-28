@echo off
rem Removes cloudHPCstorage from this PC (also available in Settings - Apps).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Uninstall %*
