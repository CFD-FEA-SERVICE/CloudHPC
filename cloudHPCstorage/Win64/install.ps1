#Requires -Version 5.1
<#
.SYNOPSIS
  cloudHPCstorage setup for Windows: mounts the cloudHPC storage as a drive.

.DESCRIPTION
  - removes any previous installation (old "cloudHPCstorage" Windows service,
    previous scheduled task, old files)
  - installs/updates WinFsp; copies rclone.exe, the activation file (service
    account key + "storage" field) and rclone.conf to
    C:\Program Files (x86)\CFD FEA Service\cloudHPCstorage (key and config
    readable only by SYSTEM, Administrators and the user)
  - registers the scheduled task "\CFD FEA Service\cloudHPCstorage" that runs
    "rclone mount" hidden at every logon of the user
  - registers "cloudHPCstorage" in Settings > Apps for the uninstall

  Compile to install.exe with admin\build-exe.ps1 (ps2exe).
  Without the exe use install.cmd (same script, self-elevating).

.PARAMETER Uninstall
  Remove cloudHPCstorage (WinFsp is left installed).
.PARAMETER Silent
  No window. Install requires -Drive; -ActivationFile defaults to the
  key file next to the installer. Exit codes: 0 ok, 3010 reboot needed, 1 error.
#>
[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Silent,
    [string]$Drive,
    [string]$ActivationFile
)

$ErrorActionPreference = 'Stop'

$SetupVersion   = '2.0.1'
$RemoteName     = 'cloudHPCstorage'
$KeyFileName    = 'cfd-fea-service-cloud.json'
$SupportMail    = 'info@cloudhpc.cloud'
$InstallDir     = Join-Path ${env:ProgramFiles(x86)} 'CFD FEA Service\cloudHPCstorage'
$ConfFile       = Join-Path $InstallDir 'rclone.conf'
$KeyFile        = Join-Path $InstallDir $KeyFileName
$MountLog       = Join-Path $InstallDir 'rclone.log'
$SetupLog       = Join-Path $env:TEMP 'cloudHPCstorage-setup.log'
$TaskPath       = '\CFD FEA Service\'
$TaskName       = 'cloudHPCstorage'
$UninstallKey   = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\cloudHPCstorage'
# Previous version (service account key + Windows service running as SYSTEM)
$LegacyService  = 'cloudHPCstorage'

Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$script:LogBox   = $null
$script:Progress = $null

#region Helpers ----------------------------------------------------------------

function Get-BaseDir {
    # Folder of install.ps1, or of install.exe when compiled with ps2exe
    if ($PSCommandPath) { return Split-Path -Parent $PSCommandPath }
    return Split-Path -Parent ([System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName)
}

function Update-UI {
    if ($script:LogBox) { [System.Windows.Forms.Application]::DoEvents() }
}

function Write-Log([string]$Message) {
    $line = '{0:HH:mm:ss}  {1}' -f (Get-Date), $Message
    try { Add-Content -LiteralPath $SetupLog -Value $line -Encoding UTF8 } catch {}
    if ($script:LogBox) {
        $script:LogBox.AppendText($line + "`r`n")
        Update-UI
    } elseif (-not $Silent) {
        Write-Host $line
    }
}

function Set-Step([int]$Percent, [string]$Message) {
    if ($script:Progress) { $script:Progress.Value = $Percent }
    Write-Log $Message
}

function Show-Message([string]$Text, [string]$Icon = 'Information') {
    if ($Silent) { Write-Log $Text; return }
    [System.Windows.Forms.MessageBox]::Show($Text, 'cloudHPCstorage', 'OK', $Icon) | Out-Null
}

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-TargetUser {
    # The drive is mounted for the user logged on to this desktop session, which is
    # not necessarily the (administrator) account the setup is elevated with.
    $owner = $null
    $sessionId = (Get-Process -Id $PID).SessionId
    $explorers = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.SessionId -eq $sessionId }
    foreach ($p in $explorers) {
        $o = Invoke-CimMethod -InputObject $p -MethodName GetOwner -ErrorAction SilentlyContinue
        if ($o -and $o.ReturnValue -eq 0 -and $o.User) { $owner = "$($o.Domain)\$($o.User)"; break }
    }
    if (-not $owner) { $owner = [Security.Principal.WindowsIdentity]::GetCurrent().Name }
    $sid = (New-Object Security.Principal.NTAccount($owner)).Translate([Security.Principal.SecurityIdentifier]).Value
    return [pscustomobject]@{ Name = $owner; Sid = $sid }
}

function Get-InstalledTask {
    return Get-ScheduledTask -TaskPath $TaskPath -TaskName $TaskName -ErrorAction SilentlyContinue
}

function Test-Installed {
    return [bool]((Get-InstalledTask) -or (Get-Service -Name $LegacyService -ErrorAction SilentlyContinue) -or
                  (Test-Path -LiteralPath $InstallDir))
}

function Get-PreviousDrive {
    $task = Get-InstalledTask
    if ($task -and $task.Actions[0].Arguments -match '\s([A-Z]:)\s') { return $Matches[1] }
    $svc = Get-CimInstance Win32_Service -Filter "Name='$LegacyService'" -ErrorAction SilentlyContinue
    if ($svc -and $svc.PathName -match '\s([A-Z]):\\?(\s|$)') { return "$($Matches[1]):" }
    return $null
}

function Get-FreeDriveLetters([string]$Sid) {
    $used = @{}
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) { $used[$d.Name.Substring(0, 1).ToUpper()] = $true }
    # Network drives mapped by the user are not visible from the elevated setup
    $net = "Registry::HKEY_USERS\$Sid\Network"
    if (Test-Path $net) { Get-ChildItem $net | ForEach-Object { $used[$_.PSChildName.ToUpper()] = $true } }
    $free = @()
    foreach ($c in 'DEFGHIJKLMNOPQRSTUVWXYZ'.ToCharArray()) {
        if (-not $used["$c"]) { $free += "$($c):" }
    }
    return $free
}

function Find-ActivationFile([string]$Dir) {
    $preferred = Join-Path $Dir $KeyFileName
    if (Test-Path -LiteralPath $preferred) { return $preferred }
    foreach ($f in Get-ChildItem -LiteralPath $Dir -Filter *.json -File -ErrorAction SilentlyContinue) {
        try {
            $j = Get-Content -Raw -LiteralPath $f.FullName | ConvertFrom-Json
            if ($j.type -eq 'service_account') { return $f.FullName }
        } catch {}
    }
    return $null
}

function Read-Activation([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Activation file not found.`r`nPlace $KeyFileName next to the installer or select it with 'Browse'. To get one write to $SupportMail."
    }
    try { $j = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json }
    catch { throw "The file '$Path' is not a valid cloudHPCstorage activation file." }
    if ($j.type -ne 'service_account' -or -not $j.storage -or -not $j.client_email -or -not $j.private_key) {
        throw "The file '$Path' is not a valid cloudHPCstorage activation file (missing fields)."
    }
    if ($j.storage -notmatch '^[a-z0-9][a-z0-9._-]{1,221}[a-z0-9]$') {
        throw "Invalid storage name '$($j.storage)' in the activation file."
    }
    return $j
}

function Invoke-Rclone([string]$Exe, [string[]]$Arguments, [int]$TimeoutSec = 90) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.Arguments = $Arguments -join ' '
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    $out = $p.StandardOutput.ReadToEndAsync()
    $err = $p.StandardError.ReadToEndAsync()
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while (-not $p.HasExited) {
        if ($sw.Elapsed.TotalSeconds -gt $TimeoutSec) {
            try { $p.Kill() } catch {}
            throw "No answer from the cloudHPC storage within $TimeoutSec s. Check the internet connection (proxy / firewall)."
        }
        Start-Sleep -Milliseconds 200
        Update-UI
    }
    $p.WaitForExit()
    return [pscustomobject]@{ ExitCode = $p.ExitCode; Output = $out.Result; Error = $err.Result }
}

function Get-RcloneConfigText($Act, [string]$KeyPath) {
    $lines = @(
        "[$RemoteName]",
        'type = google cloud storage',
        "service_account_file = $KeyPath",
        'anonymous = false',
        'object_acl = bucketOwnerFullControl',
        'bucket_acl = private'
    )
    if ($Act.bucket_policy_only) { $lines += 'bucket_policy_only = true' }
    return ($lines -join "`r`n") + "`r`n"
}

function Write-Utf8File([string]$Path, [string]$Text) {
    # rclone does not accept a BOM, which Set-Content -Encoding UTF8 writes on PowerShell 5
    [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($false)))
}

#endregion

#region Steps ------------------------------------------------------------------

function Test-StorageAccess($Act, [string]$RcloneExe, [string]$Conf) {
    $r = Invoke-Rclone $RcloneExe @('lsf', "${RemoteName}:$($Act.storage)", '--max-depth', '1',
                                   '--config', "`"$Conf`"", '--retries', '1', '--low-level-retries', '2')
    if ($r.ExitCode -eq 0) { return }
    $detail = (($r.Error -split "`n") | Where-Object { $_ -match 'ERROR|CRITICAL|Failed' } | Select-Object -Last 3) -join "`r`n"
    Write-Log $r.Error
    if ($r.Error -match 'invalid_grant|invalid_client|unauthorized_client') {
        throw "Google rejected the activation file (key disabled or deleted).`r`nPlease ask $SupportMail for a new activation file."
    }
    if ($r.Error -match '403|AccessDenied|does not have') {
        throw "The activation file has no access to the storage '$($Act.storage)'.`r`nPlease contact $SupportMail."
    }
    throw "Cannot reach the cloudHPC storage '$($Act.storage)':`r`n$detail"
}

function Stop-Mounts {
    $task = Get-InstalledTask
    if ($task) {
        Write-Log 'Stopping the current cloudHPCstorage drive...'
        Stop-ScheduledTask -InputObject $task -ErrorAction SilentlyContinue
    }
    if (Get-Service -Name $LegacyService -ErrorAction SilentlyContinue) {
        Write-Log 'Stopping the previous cloudHPCstorage service...'
        # sc.exe does not wait: rclone.exe does not answer service controls
        & sc.exe stop $LegacyService 2>&1 | Out-Null
    }
    Get-CimInstance Win32_Process -Filter "Name='rclone.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($InstallDir, [StringComparison]::OrdinalIgnoreCase)
    } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

function Remove-Previous {
    Stop-Mounts
    if (Get-Service -Name $LegacyService -ErrorAction SilentlyContinue) {
        Write-Log 'Removing the previous cloudHPCstorage service...'
        & sc.exe delete $LegacyService 2>&1 | Out-Null
    }
    if (Get-InstalledTask) {
        Unregister-ScheduledTask -TaskPath $TaskPath -TaskName $TaskName -Confirm:$false
    }
    if (Test-Path -LiteralPath $InstallDir) {
        Write-Log "Removing $InstallDir"
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
        $parent = Split-Path -Parent $InstallDir
        if ((Test-Path -LiteralPath $parent) -and -not (Get-ChildItem -LiteralPath $parent -Force)) {
            Remove-Item -LiteralPath $parent -Force
        }
    }
}

function Get-WinFspProducts {
    $keys = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    foreach ($e in Get-ItemProperty $keys -ErrorAction SilentlyContinue) {
        if ($e.DisplayName -notlike 'WinFsp*' -or -not $e.DisplayVersion) { continue }
        try { $v = [version]$e.DisplayVersion } catch { continue }
        [pscustomobject]@{ Version = $v; ProductCode = $e.PSChildName }
    }
}

# Runs msiexec and returns its exit code
function Invoke-Msi([string[]]$Arguments) {
    $p = Start-Process msiexec.exe -PassThru -ArgumentList $Arguments
    $null = $p.Handle  # keeps ExitCode available after exit
    while (-not $p.HasExited) { Start-Sleep -Milliseconds 200; Update-UI }
    return $p.ExitCode
}

# Returns $true when a reboot is required
function Install-WinFsp([string]$BaseDir) {
    $msi = Get-ChildItem -LiteralPath $BaseDir -Filter 'winfsp-*.msi' | Sort-Object Name | Select-Object -Last 1
    if (-not $msi) { throw "WinFsp installer (winfsp-*.msi) not found in $BaseDir" }
    $bundled = [version]($msi.BaseName -replace '^winfsp-', '')
    $installed = @(Get-WinFspProducts | Sort-Object Version -Descending)
    if ($installed.Count -and $installed[0].Version -ge $bundled) {
        Write-Log "WinFsp $($installed[0].Version) already installed."
        return $false
    }

    $reboot = $false
    # WinFsp cannot upgrade across major versions (e.g. 1.x -> 2.x): remove the old one first
    foreach ($old in $installed) {
        if ($old.ProductCode -notmatch '^\{[0-9A-Fa-f-]{36}\}$') { continue }
        Write-Log "Removing the old WinFsp $($old.Version)..."
        $log = Join-Path $env:TEMP 'cloudHPCstorage-winfsp-uninstall.log'
        $code = Invoke-Msi @('/x', $old.ProductCode, '/qn', '/norestart', '/l*v', "`"$log`"")
        switch ($code) {
            { $_ -in 0, 1605 }    { }
            { $_ -in 3010, 1641 } { $reboot = $true }
            default { throw "Removal of the old WinFsp $($old.Version) failed (msiexec exit code $code). Log: $log" }
        }
    }

    Write-Log "Installing WinFsp $bundled..."
    $log = Join-Path $env:TEMP 'cloudHPCstorage-winfsp.log'
    $code = Invoke-Msi @('/i', "`"$($msi.FullName)`"", '/qn', '/norestart', '/l*v', "`"$log`"")
    switch ($code) {
        0       { }
        3010    { $reboot = $true }
        1641    { $reboot = $true }
        default { throw "WinFsp installation failed (msiexec exit code $code). Log: $log" }
    }
    if ($reboot) { Write-Log 'WinFsp requires a restart of the PC.' }
    return $reboot
}

function Install-Files([string]$BaseDir) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    Copy-Item -LiteralPath (Join-Path $BaseDir 'rclone.exe') -Destination $InstallDir -Force
    # Kept for the uninstall from Settings > Apps
    Copy-Item -LiteralPath (Join-Path $BaseDir 'install.ps1') -Destination $InstallDir -Force
    Get-ChildItem -LiteralPath $InstallDir -File | Unblock-File

    $ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    New-Item -Path $UninstallKey -Force | Out-Null
    $values = @{
        DisplayName     = 'cloudHPCstorage'
        DisplayVersion  = $SetupVersion
        Publisher       = 'CFD FEA Service'
        URLInfoAbout    = 'https://cloudhpc.cloud'
        InstallLocation = $InstallDir
        DisplayIcon     = Join-Path $InstallDir 'rclone.exe'
        UninstallString = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$InstallDir\install.ps1`" -Uninstall"
    }
    foreach ($k in $values.Keys) { Set-ItemProperty -Path $UninstallKey -Name $k -Value $values[$k] }
    Set-ItemProperty -Path $UninstallKey -Name NoModify -Value 1 -Type DWord
    Set-ItemProperty -Path $UninstallKey -Name NoRepair -Value 1 -Type DWord
}

function Install-Config($Act, [string]$KeyPath, $User) {
    Copy-Item -LiteralPath $KeyPath -Destination $KeyFile -Force
    Write-Utf8File $ConfFile (Get-RcloneConfigText $Act $KeyFile)
    # Key and config: only SYSTEM, Administrators and the user (read)
    foreach ($f in $KeyFile, $ConfFile) {
        & icacls.exe $f /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' "*$($User.Sid):R" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Unable to set the permissions of $f" }
    }
    # The mount runs as the user, who must be able to write its log
    Write-Utf8File $MountLog ''
    & icacls.exe $MountLog /grant "*$($User.Sid):M" 2>&1 | Out-Null
}

function Register-MountTask($Act, [string]$DriveLetter, $User) {
    $exe = Join-Path $InstallDir 'rclone.exe'
    $arguments = @(
        'mount', "${RemoteName}:$($Act.storage)", $DriveLetter,
        '--config', "`"$ConfFile`"",
        '--vfs-cache-mode', 'full',
        '--network-mode', '--volname', '\\cloudHPC\cloudHPCstorage',
        '--no-console',
        '--log-file', "`"$MountLog`"", '--log-level', 'NOTICE'
    ) -join ' '
    # rclone.exe is a console program: started directly it gets a console window (on
    # Windows 11 a Windows Terminal tab that --no-console cannot hide) and closing it
    # kills the mount. "conhost --headless" gives it a console without any window.
    $conhost = Join-Path $env:SystemRoot 'System32\conhost.exe'
    $action = New-ScheduledTaskAction -Execute $conhost -Argument "--headless `"$exe`" $arguments" -WorkingDirectory $InstallDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $User.Name
    $trigger.Delay = 'PT10S'
    $principal = New-ScheduledTaskPrincipal -UserId $User.Name -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskPath $TaskPath -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal `
        -Settings $settings -Description 'Mounts the cloudHPC storage (https://cloudhpc.cloud) as a drive.' -Force | Out-Null
}

function Start-Mount([string]$DriveLetter) {
    Start-ScheduledTask -TaskPath $TaskPath -TaskName $TaskName
    # The drive belongs to the user session and may be invisible from this elevated
    # process, so success = rclone still running after a few seconds without errors
    for ($i = 0; $i -lt 16; $i++) {
        Start-Sleep -Milliseconds 500
        Update-UI
        if (Test-Path "$DriveLetter\") { return }
    }
    $running = Get-CimInstance Win32_Process -Filter "Name='rclone.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($InstallDir, [StringComparison]::OrdinalIgnoreCase) }
    $errors = if (Test-Path -LiteralPath $MountLog) {
        Get-Content -LiteralPath $MountLog -Tail 20 | Where-Object { $_ -match 'ERROR|CRITICAL|Fatal' }
    }
    if (-not $running) {
        throw "The drive $DriveLetter could not be started.`r`n$($errors -join "`r`n")`r`nLog: $MountLog"
    }
}

function Invoke-Install([string]$BaseDir, [string]$KeyPath, [string]$DriveLetter) {
    Write-Log "cloudHPCstorage setup $SetupVersion"
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'A 64-bit version of Windows is required.' }
    if ($DriveLetter -notmatch '^[D-Z]:$') { throw "Invalid drive letter '$DriveLetter'." }

    Set-Step 5 'Checking the activation file...'
    $act = Read-Activation $KeyPath
    $user = Get-TargetUser
    Write-Log "Storage: $($act.storage) - user: $($user.Name) - drive: $DriveLetter"

    # Work on a copy: the key may be inside the previous installation, removed below
    $tempId = [guid]::NewGuid()
    $tempConf = Join-Path $env:TEMP "cloudHPCstorage-$tempId.conf"
    $tempKey = Join-Path $env:TEMP "cloudHPCstorage-$tempId.json"
    try {
        Copy-Item -LiteralPath $KeyPath -Destination $tempKey -Force
        $KeyPath = $tempKey

        Set-Step 15 'Checking the access to the cloudHPC storage...'
        Write-Utf8File $tempConf (Get-RcloneConfigText $act $KeyPath)
        Test-StorageAccess $act (Join-Path $BaseDir 'rclone.exe') $tempConf
        Write-Log 'Access OK.'

        Set-Step 35 'Removing the previous installation (if any)...'
        Remove-Previous

        Set-Step 50 'Installing WinFsp...'
        $reboot = Install-WinFsp $BaseDir

        Set-Step 70 'Installing rclone...'
        Install-Files $BaseDir

        Set-Step 80 'Saving the configuration...'
        Install-Config $act $KeyPath $user
    } finally {
        Remove-Item -LiteralPath $tempConf, $tempKey -Force -ErrorAction SilentlyContinue
    }

    Set-Step 90 "Creating the drive $DriveLetter..."
    Register-MountTask $act $DriveLetter $user
    if (-not $reboot) { Start-Mount $DriveLetter }
    Set-Step 100 'Done.'
    return $reboot
}

function Invoke-Uninstall {
    Write-Log "cloudHPCstorage uninstall $SetupVersion"
    Set-Step 20 'Stopping the drive...'
    Remove-Previous
    Remove-Item -Path $UninstallKey -Recurse -Force -ErrorAction SilentlyContinue
    Set-Step 100 'cloudHPCstorage removed (WinFsp is left installed).'
}

#endregion

#region GUI --------------------------------------------------------------------

function Show-Gui([string]$BaseDir) {
    [System.Windows.Forms.Application]::EnableVisualStyles()
    $user = Get-TargetUser

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "cloudHPCstorage setup $SetupVersion"
    $form.ClientSize = New-Object System.Drawing.Size(560, 480)
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.StartPosition = 'CenterScreen'
    $form.Font = New-Object System.Drawing.Font('Segoe UI', 9)

    $title = New-Object System.Windows.Forms.Label
    $title.Text = 'cloudHPCstorage'
    $title.Font = New-Object System.Drawing.Font('Segoe UI', 16, [System.Drawing.FontStyle]::Bold)
    $title.SetBounds(16, 12, 520, 34)
    $form.Controls.Add($title)

    $subtitle = New-Object System.Windows.Forms.Label
    $subtitle.Text = "Your cloudHPC storage as a drive in File Explorer (user $($user.Name))."
    if (Test-Installed) { $subtitle.Text += "`r`nAn existing installation was found: it will be replaced." }
    $subtitle.SetBounds(18, 48, 530, 34)
    $form.Controls.Add($subtitle)

    $lblKey = New-Object System.Windows.Forms.Label
    $lblKey.Text = '1. Activation file'
    $lblKey.Font = New-Object System.Drawing.Font('Segoe UI', 9, [System.Drawing.FontStyle]::Bold)
    $lblKey.SetBounds(16, 92, 300, 20)
    $form.Controls.Add($lblKey)

    $txtKey = New-Object System.Windows.Forms.TextBox
    $txtKey.SetBounds(18, 114, 430, 24)
    $found = if ($ActivationFile) { $ActivationFile } else { Find-ActivationFile $BaseDir }
    if ($found) { $txtKey.Text = $found }
    $form.Controls.Add($txtKey)

    $btnBrowse = New-Object System.Windows.Forms.Button
    $btnBrowse.Text = 'Browse...'
    $btnBrowse.SetBounds(456, 113, 88, 26)
    $btnBrowse.Add_Click({
        $dlg = New-Object System.Windows.Forms.OpenFileDialog
        $dlg.Filter = 'Activation file (*.json)|*.json|All files (*.*)|*.*'
        $dlg.InitialDirectory = $BaseDir
        if ($dlg.ShowDialog() -eq 'OK') { $txtKey.Text = $dlg.FileName }
    })
    $form.Controls.Add($btnBrowse)

    $lnkMail = New-Object System.Windows.Forms.LinkLabel
    $lnkMail.Text = "No activation file? Request it to $SupportMail"
    $lnkMail.SetBounds(18, 142, 520, 20)
    $lnkMail.Add_LinkClicked({
        Start-Process "mailto:$SupportMail`?subject=cloudHPCstorage activation&body=Please send me the activation file for cloudHPCstorage."
    })
    $form.Controls.Add($lnkMail)

    $lblDrive = New-Object System.Windows.Forms.Label
    $lblDrive.Text = '2. Drive letter'
    $lblDrive.Font = $lblKey.Font
    $lblDrive.SetBounds(16, 172, 300, 20)
    $form.Controls.Add($lblDrive)

    $cmbDrive = New-Object System.Windows.Forms.ComboBox
    $cmbDrive.DropDownStyle = 'DropDownList'
    $cmbDrive.SetBounds(18, 194, 90, 24)
    $letters = @(Get-FreeDriveLetters $user.Sid)
    $previous = Get-PreviousDrive
    if ($previous -and $letters -notcontains $previous) { $letters = @($previous) + $letters }
    foreach ($l in $letters) { [void]$cmbDrive.Items.Add($l) }
    $default = if ($previous) { $previous } elseif ($Drive) { $Drive.ToUpper() } else { $letters | Where-Object { $_ -ge 'G:' } | Select-Object -First 1 }
    if ($default -and $cmbDrive.Items.Contains($default)) { $cmbDrive.SelectedItem = $default }
    elseif ($cmbDrive.Items.Count) { $cmbDrive.SelectedIndex = 0 }
    $form.Controls.Add($cmbDrive)

    $lblDriveHint = New-Object System.Windows.Forms.Label
    $lblDriveHint.Text = 'Only free letters are listed.'
    $lblDriveHint.ForeColor = [System.Drawing.Color]::DimGray
    $lblDriveHint.SetBounds(118, 198, 400, 20)
    $form.Controls.Add($lblDriveHint)

    $progress = New-Object System.Windows.Forms.ProgressBar
    $progress.SetBounds(18, 234, 526, 16)
    $form.Controls.Add($progress)
    $script:Progress = $progress

    $log = New-Object System.Windows.Forms.TextBox
    $log.Multiline = $true
    $log.ReadOnly = $true
    $log.ScrollBars = 'Vertical'
    $log.BackColor = [System.Drawing.Color]::White
    $log.Font = New-Object System.Drawing.Font('Consolas', 8.5)
    $log.SetBounds(18, 258, 526, 164)
    $form.Controls.Add($log)
    $script:LogBox = $log

    $btnInstall = New-Object System.Windows.Forms.Button
    $btnInstall.Text = 'Install'
    $btnInstall.SetBounds(284, 436, 84, 30)
    $form.Controls.Add($btnInstall)
    $form.AcceptButton = $btnInstall

    $btnUninstall = New-Object System.Windows.Forms.Button
    $btnUninstall.Text = 'Uninstall'
    $btnUninstall.SetBounds(372, 436, 84, 30)
    $btnUninstall.Enabled = Test-Installed
    $form.Controls.Add($btnUninstall)

    $btnClose = New-Object System.Windows.Forms.Button
    $btnClose.Text = 'Close'
    $btnClose.SetBounds(460, 436, 84, 30)
    $btnClose.Add_Click({ $form.Close() })
    $form.Controls.Add($btnClose)
    $form.CancelButton = $btnClose

    $setBusy = {
        param([bool]$Busy)
        foreach ($c in $btnInstall, $btnUninstall, $btnClose, $btnBrowse, $txtKey, $cmbDrive) { $c.Enabled = -not $Busy }
        $form.UseWaitCursor = $Busy
        if (-not $Busy) { $btnUninstall.Enabled = Test-Installed }
    }

    $btnInstall.Add_Click({
        if (-not $cmbDrive.SelectedItem) { Show-Message 'Select a drive letter.' 'Warning'; return }
        $letter = [string]$cmbDrive.SelectedItem
        & $setBusy $true
        try {
            $reboot = Invoke-Install $BaseDir $txtKey.Text $letter
            if ($reboot) {
                Show-Message "cloudHPCstorage is installed.`r`n`r`nPlease RESTART the PC: after the restart your storage will appear as drive $letter in File Explorer > This PC."
            } else {
                Show-Message "cloudHPCstorage is ready!`r`n`r`nYour storage is the drive $letter in File Explorer > This PC.`r`nIt is connected automatically at every logon."
                try { Start-Process explorer.exe "$letter\" } catch {}
            }
        } catch {
            Write-Log "ERROR: $($_.Exception.Message)"
            Write-Log "Setup log: $SetupLog"
            $progress.Value = 0
            Show-Message $_.Exception.Message 'Error'
        } finally {
            & $setBusy $false
        }
    })

    $btnUninstall.Add_Click({
        $answer = [System.Windows.Forms.MessageBox]::Show('Remove cloudHPCstorage from this PC?', 'cloudHPCstorage', 'YesNo', 'Question')
        if ($answer -ne 'Yes') { return }
        & $setBusy $true
        try {
            Invoke-Uninstall
            Show-Message 'cloudHPCstorage has been removed.'
        } catch {
            Write-Log "ERROR: $($_.Exception.Message)"
            Show-Message $_.Exception.Message 'Error'
        } finally {
            & $setBusy $false
        }
    })

    $form.Add_Shown({
        $form.Activate()
        if (-not $txtKey.Text) {
            Write-Log "Activation file not found next to the installer: click 'Browse...' to select it."
        }
    })
    [void]$form.ShowDialog()
}

#endregion

#region Main -------------------------------------------------------------------

if ($ActivationFile -and (Test-Path -LiteralPath $ActivationFile)) {
    $ActivationFile = (Resolve-Path -LiteralPath $ActivationFile).Path
}

if (-not (Test-IsAdmin)) {
    if (-not $PSCommandPath) {
        Show-Message 'Administrator rights are required.' 'Error'
        exit 1
    }
    # Script mode (install.cmd): restart elevated, the UAC prompt appears
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass')
    if (-not $Silent) { $argList += @('-WindowStyle', 'Hidden') }
    $argList += @('-File', "`"$PSCommandPath`"")
    if ($Uninstall)      { $argList += '-Uninstall' }
    if ($Silent)         { $argList += '-Silent' }
    if ($Drive)          { $argList += @('-Drive', $Drive) }
    if ($ActivationFile) { $argList += @('-ActivationFile', "`"$ActivationFile`"") }
    try {
        $p = Start-Process powershell.exe -Verb RunAs -ArgumentList $argList -PassThru -Wait:$Silent
        if ($Silent) { exit $p.ExitCode }
    } catch {
        Show-Message 'Administrator rights are required: please answer "Yes" to the Windows prompt.' 'Error'
        exit 1
    }
    exit 0
}

$BaseDir = Get-BaseDir

if ($Uninstall) {
    if (-not $Silent) {
        $answer = [System.Windows.Forms.MessageBox]::Show('Remove cloudHPCstorage from this PC?', 'cloudHPCstorage', 'YesNo', 'Question')
        if ($answer -ne 'Yes') { exit 0 }
    }
    try {
        Invoke-Uninstall
        Show-Message 'cloudHPCstorage has been removed.'
        exit 0
    } catch {
        Write-Log "ERROR: $($_.Exception.Message)"
        Show-Message $_.Exception.Message 'Error'
        exit 1
    }
}

if ($Silent) {
    try {
        $key = if ($ActivationFile) { $ActivationFile } else { Find-ActivationFile $BaseDir }
        if (-not $Drive) { throw '-Drive is required with -Silent (e.g. -Drive K:).' }
        $reboot = Invoke-Install $BaseDir $key $Drive.ToUpper()
        if ($reboot) { exit 3010 }
        exit 0
    } catch {
        Write-Log "ERROR: $($_.Exception.Message)"
        exit 1
    }
}

Show-Gui $BaseDir

#endregion
