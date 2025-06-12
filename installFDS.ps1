#Installing new script
cd Downloads
$wsh = New-Object -ComObject Wscript.Shell

wget "https://repo.anaconda.com/archive/Anaconda3-2024.10-1-Windows-x86_64.exe" -OutFile "Anaconda3-2024.10-1-Windows-x86_64.exe"
$wsh.Popup("Complete anaconda installation process ...")
Start-Process .\Anaconda3-2024.10-1-Windows-x86_64.exe -NoNewWindow -Wait
#pip install numpy scipy matplotlib fdsreader argparse cantera

wget "https://github.com/firemodels/fds/releases/download/FDS-6.10.1/FDS-6.10.1_SMV-6.10.1_win.exe" -OutFile "FDS-6.10.1_SMV-6.10.1_win.exe"
$wsh.Popup("Complete FDS installation process ...")
Start-Process .\FDS-6.10.1_SMV-6.10.1_win.exe -NoNewWindow -Wait

wget "https://ftp.halifax.rwth-aachen.de/blender/release/Blender4.4/blender-4.4.3-windows-x64.msi" -OutFile "blender-4.4.3-windows-x64.msi"
$wsh.Popup("Complete blender installation process ...")
Start-Process .\blender-4.4.3-windows-x64.msi -NoNewWindow -Wait

wget "https://github.com/firetools/blenderfds/releases/download/v6.0.0/blenderfds.zip" -OutFile "blenderfds.zip"
$wsh.Popup("Follow instructions in the browser to complete blenderFDS installation on blender")
Start-Process chrome.exe '--new-window https://github.com/firetools/blenderfds/wiki/Install#install-a-stable-version'

wget "https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.8.1/npp.8.8.1.Installer.x64.exe" -OutFile "npp.8.8.1.Installer.x64.exe"
$wsh.Popup("Complete notepad++ installation process ...")
Start-Process .\npp.8.8.1.Installer.x64.exe -NoNewWindow -Wait
$wsh.Popup("Follow instructions in the browser to complete FDS highlight on notepad++")
Start-Process chrome.exe '--new-window https://github.com/firetools/notepad-plus-plus-fds?tab=readme-ov-file#how-to-install-notepad-fds-syntax-highlight-plugin'
