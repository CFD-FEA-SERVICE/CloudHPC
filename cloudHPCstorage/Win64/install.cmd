@echo off
rem cloudHPCstorage setup - alternative to install.exe (same script).
rem Double-click it: Windows asks for administrator rights.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
