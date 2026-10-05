#Requires -Version 5.1
<#
.SYNOPSIS
  cloudHPCstorage setup for Windows: mounts cloudHPC storages as drives.

.DESCRIPTION
  Several storages (activation files) can be mounted at the same time, each one on
  its own drive letter: run the setup once per activation file. Installing an
  activation file whose storage is already mounted replaces only that drive.

  - converts the previous single-drive installation (setup 2.0) to this layout,
    keeping its drive, and removes the older "cloudHPCstorage" Windows service
  - installs/updates WinFsp; copies rclone.exe to
    C:\Program Files (x86)\CFD FEA Service\cloudHPCstorage
  - per storage: copies the activation file (service account key + "storage"
    field) and writes rclone.conf in ...\cloudHPCstorage\instances\<storage>
    (key and config readable only by SYSTEM, Administrators and the user), and
    registers the scheduled task "\CFD FEA Service\cloudHPCstorage-<storage>"
    that runs "rclone mount" hidden at every logon of the user
  - registers "cloudHPCstorage" in Settings > Apps for the uninstall (all storages)

  Compile to install.exe with admin\build-exe.ps1 (ps2exe).
  Without the exe use install.cmd (same script, self-elevating).

.PARAMETER Uninstall
  Remove cloudHPCstorage: all the storages, or only the one given with -Storage
  (WinFsp is left installed).
.PARAMETER Storage
  With -Uninstall: name of the storage to remove (the "storage" field of its
  activation file).
.PARAMETER Silent
  No window. Install requires -Drive; -ActivationFile defaults to the
  key file next to the installer. Exit codes: 0 ok, 3010 reboot needed, 1 error.
#>
[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Silent,
    [string]$Drive,
    [string]$ActivationFile,
    [string]$Storage
)

$ErrorActionPreference = 'Stop'

$SetupVersion   = '2.1.0'
$RemoteName     = 'cloudHPCstorage'
$KeyFileName    = 'cfd-fea-service-cloud.json'
$SupportMail    = 'info@cloudhpc.cloud'
$InstallDir     = Join-Path ${env:ProgramFiles(x86)} 'CFD FEA Service\cloudHPCstorage'
$InstancesDir   = Join-Path $InstallDir 'instances'
$RcloneExe      = Join-Path $InstallDir 'rclone.exe'
$SetupLog       = Join-Path $env:TEMP 'cloudHPCstorage-setup.log'
$TaskPath       = '\CFD FEA Service\'
$TaskPrefix     = 'cloudHPCstorage-'
$UninstallKey   = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\cloudHPCstorage'
# Setup 2.0: a single storage, files directly in $InstallDir, task "cloudHPCstorage"
$LegacyTaskName = 'cloudHPCstorage'
$LegacyKey      = Join-Path $InstallDir $KeyFileName
$LegacyConf     = Join-Path $InstallDir 'rclone.conf'
$LegacyLog      = Join-Path $InstallDir 'rclone.log'
# Older versions: Windows service running as SYSTEM
$LegacyService  = 'cloudHPCstorage'

Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$script:LogBox       = $null
$script:Progress     = $null
$script:StoppedTasks = @()   # drives stopped during the setup, restarted at the end

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
    return Resolve-User $owner
}

function Resolve-User([string]$Name) {
    $sid = (New-Object Security.Principal.NTAccount($Name)).Translate([Security.Principal.SecurityIdentifier]).Value
    return [pscustomobject]@{ Name = $Name; Sid = $sid }
}

function Get-InstancePaths([string]$Bucket) {
    $dir = Join-Path $InstancesDir $Bucket
    return [pscustomobject]@{
        Bucket   = $Bucket
        TaskName = "$TaskPrefix$Bucket"
        Dir      = $dir
        Key      = Join-Path $dir $KeyFileName
        Conf     = Join-Path $dir 'rclone.conf'
        Log      = Join-Path $dir 'rclone.log'
    }
}

# Installed drives, from their scheduled tasks (setup 2.0 one included, Legacy = $true)
function Get-Instances {
    foreach ($t in @(Get-ScheduledTask -TaskPath $TaskPath -ErrorAction SilentlyContinue)) {
        if ($t.TaskName -ne $LegacyTaskName -and -not $t.TaskName.StartsWith($TaskPrefix)) { continue }
        $a = [string]$t.Actions[0].Arguments
        if ($a -notmatch "mount\s+${RemoteName}:([a-z0-9._-]+)\s+([A-Za-z]:)") { continue }
        [pscustomobject]@{
            Bucket   = $Matches[1]
            Drive    = $Matches[2].ToUpper()
            TaskName = $t.TaskName
            User     = $t.Principal.UserId
            Legacy   = ($t.TaskName -eq $LegacyTaskName)
        }
    }
}

function Test-Installed {
    return [bool](@(Get-Instances).Count -or (Get-Service -Name $LegacyService -ErrorAction SilentlyContinue) -or
                  (Test-Path -LiteralPath $InstallDir))
}

function Get-FreeDriveLetters([string]$Sid, $Instances) {
    $used = @{}
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) { $used[$d.Name.Substring(0, 1).ToUpper()] = $true }
    # Letters of the installed drives, mounted or not (e.g. other users, reboot pending)
    foreach ($i in $Instances) { $used[$i.Drive.Substring(0, 1)] = $true }
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

# rclone.exe processes of the drives; with $ConfPath only the one using that config
function Get-RcloneProcesses([string]$ConfPath) {
    return @(Get-CimInstance Win32_Process -Filter "Name='rclone.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($InstallDir, [StringComparison]::OrdinalIgnoreCase) -and
        (-not $ConfPath -or ($_.CommandLine -and $_.CommandLine.IndexOf($ConfPath, [StringComparison]::OrdinalIgnoreCase) -ge 0))
    })
}

function Stop-Rclone([string]$ConfPath) {
    $procs = @(Get-RcloneProcesses $ConfPath)
    foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    if ($procs.Count) { Start-Sleep -Seconds 2 }
}

# Stops every running drive (rclone.exe or WinFsp are about to be replaced); they are
# restarted at the end of the setup
function Stop-AllDrives([string]$Reason) {
    foreach ($i in @(Get-Instances)) {
        $t = Get-ScheduledTask -TaskPath $TaskPath -TaskName $i.TaskName -ErrorAction SilentlyContinue
        if ($t -and $t.State -eq 'Running') {
            if ($script:StoppedTasks -notcontains $i.TaskName) { $script:StoppedTasks += $i.TaskName }
            Stop-ScheduledTask -InputObject $t -ErrorAction SilentlyContinue | Out-Null
        }
    }
    if ($script:StoppedTasks.Count) { Write-Log "Stopping the other drives ($Reason)..." }
    Stop-Rclone
}

function Remove-Instance([string]$Bucket) {
    $p = Get-InstancePaths $Bucket
    $task = Get-ScheduledTask -TaskPath $TaskPath -TaskName $p.TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Log "Stopping the drive of the storage '$Bucket'..."
        Stop-ScheduledTask -InputObject $task -ErrorAction SilentlyContinue | Out-Null
    }
    Stop-Rclone $p.Conf
    if ($task) { Unregister-ScheduledTask -TaskPath $TaskPath -TaskName $p.TaskName -Confirm:$false }
    $script:StoppedTasks = @($script:StoppedTasks | Where-Object { $_ -ne $p.TaskName })
    if (Test-Path -LiteralPath $p.Dir) { Remove-Item -LiteralPath $p.Dir -Recurse -Force }
}

# Setup 2.0 drive and older Windows service
function Remove-Legacy {
    $task = Get-ScheduledTask -TaskPath $TaskPath -TaskName $LegacyTaskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Log 'Stopping the drive of the previous installation...'
        Stop-ScheduledTask -InputObject $task -ErrorAction SilentlyContinue | Out-Null
        Stop-Rclone $LegacyConf
        Unregister-ScheduledTask -TaskPath $TaskPath -TaskName $LegacyTaskName -Confirm:$false
    }
    if (Get-Service -Name $LegacyService -ErrorAction SilentlyContinue) {
        Write-Log 'Removing the previous cloudHPCstorage service...'
        # sc.exe does not wait: rclone.exe does not answer service controls
        & sc.exe stop $LegacyService 2>&1 | Out-Null
        Get-RcloneProcesses | Where-Object {
            -not $_.CommandLine -or $_.CommandLine.IndexOf($InstancesDir, [StringComparison]::OrdinalIgnoreCase) -lt 0
        } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2
        & sc.exe delete $LegacyService 2>&1 | Out-Null
    }
    foreach ($f in $LegacyKey, $LegacyConf, $LegacyLog) {
        if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force }
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

    Stop-AllDrives 'WinFsp update'
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
    $src = Join-Path $BaseDir 'rclone.exe'
    if (-not (Test-Path -LiteralPath $RcloneExe) -or
        (Get-FileHash -LiteralPath $src).Hash -ne (Get-FileHash -LiteralPath $RcloneExe).Hash) {
        # Shared by all the drives: it cannot be replaced while one of them uses it
        Stop-AllDrives 'rclone update'
        Copy-Item -LiteralPath $src -Destination $InstallDir -Force
    }
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
        DisplayIcon     = $RcloneExe
        UninstallString = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$InstallDir\install.ps1`" -Uninstall"
    }
    foreach ($k in $values.Keys) { Set-ItemProperty -Path $UninstallKey -Name $k -Value $values[$k] }
    Set-ItemProperty -Path $UninstallKey -Name NoModify -Value 1 -Type DWord
    Set-ItemProperty -Path $UninstallKey -Name NoRepair -Value 1 -Type DWord
}

function Install-Config($Act, [string]$KeyPath, $User, $Paths) {
    New-Item -ItemType Directory -Force -Path $Paths.Dir | Out-Null
    Copy-Item -LiteralPath $KeyPath -Destination $Paths.Key -Force
    Write-Utf8File $Paths.Conf (Get-RcloneConfigText $Act $Paths.Key)
    # Key and config: only SYSTEM, Administrators and the user (read)
    foreach ($f in $Paths.Key, $Paths.Conf) {
        & icacls.exe $f /inheritance:r /grant:r '*S-1-5-18:F' '*S-1-5-32-544:F' "*$($User.Sid):R" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Unable to set the permissions of $f" }
    }
    # The mount runs as the user, who must be able to write its log
    Write-Utf8File $Paths.Log ''
    & icacls.exe $Paths.Log /grant "*$($User.Sid):M" 2>&1 | Out-Null
}

function Register-MountTask($Act, [string]$DriveLetter, $User, $Paths) {
    $exe = $RcloneExe
    # Each drive needs its own network name: \\cloudHPC\<storage>
    $arguments = @(
        'mount', "${RemoteName}:$($Act.storage)", $DriveLetter,
        '--config', "`"$($Paths.Conf)`"",
        '--vfs-cache-mode', 'full',
        '--network-mode', '--volname', "\\cloudHPC\$($Act.storage)",
        '--no-console',
        '--log-file', "`"$($Paths.Log)`"", '--log-level', 'NOTICE'
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
    Register-ScheduledTask -TaskPath $TaskPath -TaskName $Paths.TaskName -Action $action -Trigger $trigger -Principal $principal `
        -Settings $settings -Description "Mounts the cloudHPC storage '$($Act.storage)' (https://cloudhpc.cloud) as drive $DriveLetter." -Force | Out-Null
}

function Start-Mount([string]$DriveLetter, $Paths) {
    Start-ScheduledTask -TaskPath $TaskPath -TaskName $Paths.TaskName
    # The drive belongs to the user session and may be invisible from this elevated
    # process, so success = rclone still running after a few seconds without errors
    for ($i = 0; $i -lt 16; $i++) {
        Start-Sleep -Milliseconds 500
        Update-UI
        if (Test-Path "$DriveLetter\") { return }
    }
    $running = @(Get-RcloneProcesses $Paths.Conf)
    $errors = if (Test-Path -LiteralPath $Paths.Log) {
        Get-Content -LiteralPath $Paths.Log -Tail 20 | Where-Object { $_ -match 'ERROR|CRITICAL|Fatal' }
    }
    if (-not $running.Count) {
        throw "The drive $DriveLetter could not be started.`r`n$($errors -join "`r`n")`r`nLog: $($Paths.Log)"
    }
}

function Invoke-Install([string]$BaseDir, [string]$KeyPath, [string]$DriveLetter) {
    Write-Log "cloudHPCstorage setup $SetupVersion"
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'A 64-bit version of Windows is required.' }
    if ($DriveLetter -notmatch '^[D-Z]:$') { throw "Invalid drive letter '$DriveLetter'." }

    Set-Step 5 'Checking the activation file...'
    $act = Read-Activation $KeyPath
    $user = Get-TargetUser
    $paths = Get-InstancePaths $act.storage
    Write-Log "Storage: $($act.storage) - user: $($user.Name) - drive: $DriveLetter"

    $instances = @(Get-Instances)
    $busy = $instances | Where-Object { $_.Bucket -ne $act.storage -and $_.Drive -eq $DriveLetter } | Select-Object -First 1
    if ($busy) { throw "The drive $DriveLetter is already used by the storage '$($busy.Bucket)'. Choose another letter." }
    $legacy = $instances | Where-Object { $_.Legacy } | Select-Object -First 1
    $script:StoppedTasks = @()

    # Work on copies: the keys may be inside the installations removed below
    $tempId = [guid]::NewGuid()
    $tempConf = Join-Path $env:TEMP "cloudHPCstorage-$tempId.conf"
    $tempKey = Join-Path $env:TEMP "cloudHPCstorage-$tempId.json"
    $tempLegacyKey = Join-Path $env:TEMP "cloudHPCstorage-$tempId-legacy.json"
    $reboot = $false
    try {
        Copy-Item -LiteralPath $KeyPath -Destination $tempKey -Force
        $KeyPath = $tempKey

        Set-Step 15 'Checking the access to the cloudHPC storage...'
        Write-Utf8File $tempConf (Get-RcloneConfigText $act $KeyPath)
        Test-StorageAccess $act (Join-Path $BaseDir 'rclone.exe') $tempConf
        Write-Log 'Access OK.'

        Set-Step 35 'Removing the previous installation of this storage (if any)...'
        # Setup 2.0 drive of another storage: kept, converted to the new layout below
        $migrate = $null
        if ($legacy -and $legacy.Bucket -ne $act.storage -and (Test-Path -LiteralPath $LegacyKey)) {
            try {
                Copy-Item -LiteralPath $LegacyKey -Destination $tempLegacyKey -Force
                $migrate = [pscustomobject]@{ Act = (Read-Activation $tempLegacyKey); Drive = $legacy.Drive; User = $legacy.User }
            } catch { Write-Log "WARNING: the previous drive $($legacy.Drive) cannot be kept: $($_.Exception.Message)" }
        }
        Remove-Legacy
        Remove-Instance $act.storage

        Set-Step 50 'Installing WinFsp...'
        $reboot = Install-WinFsp $BaseDir

        Set-Step 70 'Installing rclone...'
        Install-Files $BaseDir

        Set-Step 80 'Saving the configuration...'
        Install-Config $act $KeyPath $user $paths

        if ($migrate) {
            try {
                $mUser = Resolve-User $migrate.User
                $mPaths = Get-InstancePaths $migrate.Act.storage
                Install-Config $migrate.Act $tempLegacyKey $mUser $mPaths
                Register-MountTask $migrate.Act $migrate.Drive $mUser $mPaths
                $script:StoppedTasks += $mPaths.TaskName
                Write-Log "The drive $($migrate.Drive) of the storage '$($migrate.Act.storage)' has been kept."
            } catch {
                Write-Log "WARNING: the drive $($migrate.Drive) of the storage '$($migrate.Act.storage)' could not be kept: $($_.Exception.Message). Install it again with its activation file."
            }
        }
    } finally {
        Remove-Item -LiteralPath $tempConf, $tempKey, $tempLegacyKey -Force -ErrorAction SilentlyContinue
    }

    Set-Step 90 "Creating the drive $DriveLetter..."
    Register-MountTask $act $DriveLetter $user $paths
    if (-not $reboot) {
        Start-Mount $DriveLetter $paths
        foreach ($n in $script:StoppedTasks) {
            Write-Log "Restarting $n..."
            Start-ScheduledTask -TaskPath $TaskPath -TaskName $n -ErrorAction SilentlyContinue
        }
    }
    Set-Step 100 'Done.'
    return $reboot
}

function Invoke-RemoveStorage([string]$Bucket) {
    Write-Log "cloudHPCstorage $SetupVersion - removing the storage '$Bucket'"
    $found = @(Get-Instances | Where-Object { $_.Bucket -eq $Bucket })
    if (-not $found.Count) { throw "The storage '$Bucket' is not installed on this PC." }
    Set-Step 20 "Stopping the drive $($found[0].Drive)..."
    foreach ($i in $found) { if ($i.Legacy) { Remove-Legacy } else { Remove-Instance $Bucket } }
    if (-not @(Get-Instances).Count) { Invoke-Uninstall; return }
    Set-Step 100 "Storage '$Bucket' removed."
}

function Invoke-Uninstall {
    Write-Log "cloudHPCstorage uninstall $SetupVersion"
    Set-Step 20 'Stopping the drives...'
    foreach ($i in @(Get-Instances)) { if ($i.Legacy) { Remove-Legacy } else { Remove-Instance $i.Bucket } }
    Remove-Legacy
    Stop-Rclone
    if (Test-Path -LiteralPath $InstallDir) {
        Write-Log "Removing $InstallDir"
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
        $parent = Split-Path -Parent $InstallDir
        if ((Test-Path -LiteralPath $parent) -and -not (Get-ChildItem -LiteralPath $parent -Force)) {
            Remove-Item -LiteralPath $parent -Force
        }
    }
    Remove-Item -Path $UninstallKey -Recurse -Force -ErrorAction SilentlyContinue
    Set-Step 100 'cloudHPCstorage removed (WinFsp is left installed).'
}

#endregion

#region GUI --------------------------------------------------------------------

function Show-Gui([string]$BaseDir) {
    [System.Windows.Forms.Application]::EnableVisualStyles()
    $user = Get-TargetUser
    $script:GuiInstances = @()

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "cloudHPCstorage setup $SetupVersion"
    $form.ClientSize = New-Object System.Drawing.Size(560, 552)
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
    $subtitle.Text = "Your cloudHPC storages as drives in File Explorer (user $($user.Name)).`r`nInstall once per activation file: each storage gets its own drive."
    $subtitle.SetBounds(18, 48, 530, 34)
    $form.Controls.Add($subtitle)

    $lblKey = New-Object System.Windows.Forms.Label
    $lblKey.Text = '1. Activation file'
    $lblKey.Font = New-Object System.Drawing.Font('Segoe UI', 9, [System.Drawing.FontStyle]::Bold)
    $lblKey.SetBounds(16, 92, 300, 20)
    $form.Controls.Add($lblKey)

    $txtKey = New-Object System.Windows.Forms.TextBox
    $txtKey.SetBounds(18, 114, 430, 24)
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
    $form.Controls.Add($cmbDrive)

    $lblDriveHint = New-Object System.Windows.Forms.Label
    $lblDriveHint.ForeColor = [System.Drawing.Color]::DimGray
    $lblDriveHint.SetBounds(118, 198, 426, 20)
    $form.Controls.Add($lblDriveHint)

    $lblInst = New-Object System.Windows.Forms.Label
    $lblInst.Text = 'Installed storages'
    $lblInst.Font = $lblKey.Font
    $lblInst.SetBounds(16, 228, 300, 20)
    $form.Controls.Add($lblInst)

    $lstInst = New-Object System.Windows.Forms.ListBox
    $lstInst.SetBounds(18, 250, 430, 70)
    $lstInst.Font = New-Object System.Drawing.Font('Consolas', 9)
    $form.Controls.Add($lstInst)

    $btnRemove = New-Object System.Windows.Forms.Button
    $btnRemove.Text = 'Remove'
    $btnRemove.SetBounds(456, 249, 88, 26)
    $form.Controls.Add($btnRemove)

    $progress = New-Object System.Windows.Forms.ProgressBar
    $progress.SetBounds(18, 332, 526, 16)
    $form.Controls.Add($progress)
    $script:Progress = $progress

    $log = New-Object System.Windows.Forms.TextBox
    $log.Multiline = $true
    $log.ReadOnly = $true
    $log.ScrollBars = 'Vertical'
    $log.BackColor = [System.Drawing.Color]::White
    $log.Font = New-Object System.Drawing.Font('Consolas', 8.5)
    $log.SetBounds(18, 356, 526, 140)
    $form.Controls.Add($log)
    $script:LogBox = $log

    $btnInstall = New-Object System.Windows.Forms.Button
    $btnInstall.Text = 'Install'
    $btnInstall.SetBounds(268, 510, 84, 30)
    $form.Controls.Add($btnInstall)
    $form.AcceptButton = $btnInstall

    $btnUninstall = New-Object System.Windows.Forms.Button
    $btnUninstall.Text = 'Uninstall all'
    $btnUninstall.SetBounds(356, 510, 96, 30)
    $form.Controls.Add($btnUninstall)

    $btnClose = New-Object System.Windows.Forms.Button
    $btnClose.Text = 'Close'
    $btnClose.SetBounds(460, 510, 84, 30)
    $btnClose.Add_Click({ $form.Close() })
    $form.Controls.Add($btnClose)
    $form.CancelButton = $btnClose

    $refreshList = {
        $script:GuiInstances = @(Get-Instances | Sort-Object Drive)
        $lstInst.Items.Clear()
        foreach ($i in $script:GuiInstances) {
            [void]$lstInst.Items.Add(('{0}  {1}  ({2})' -f $i.Drive, $i.Bucket, $i.User))
        }
        if (-not $script:GuiInstances.Count) { [void]$lstInst.Items.Add('(none)') }
        $btnRemove.Enabled = [bool]$script:GuiInstances.Count
        $btnUninstall.Enabled = Test-Installed
    }

    # Drive letters: the free ones, plus the current one of the storage of the selected
    # activation file (reinstalling it replaces that drive)
    $refreshDrives = {
        $bucket = $null
        try { if ($txtKey.Text) { $bucket = (Read-Activation $txtKey.Text).storage } } catch {}
        $mine = $script:GuiInstances | Where-Object { $bucket -and $_.Bucket -eq $bucket } | Select-Object -First 1
        $current = [string]$cmbDrive.SelectedItem
        $letters = @(Get-FreeDriveLetters $user.Sid $script:GuiInstances)
        if ($mine) { $letters = @($mine.Drive) + $letters }
        $cmbDrive.Items.Clear()
        foreach ($l in $letters) { [void]$cmbDrive.Items.Add($l) }
        $default = if ($mine) { $mine.Drive }
                   elseif ($current -and $letters -contains $current) { $current }
                   elseif ($Drive) { $Drive.ToUpper() }
                   else { $letters | Where-Object { $_ -ge 'G:' } | Select-Object -First 1 }
        if ($default -and $cmbDrive.Items.Contains($default)) { $cmbDrive.SelectedItem = $default }
        elseif ($cmbDrive.Items.Count) { $cmbDrive.SelectedIndex = 0 }
        $lblDriveHint.Text = if ($mine) { "'$bucket' is already installed on $($mine.Drive): it will be replaced." }
                             else { 'Only free letters are listed.' }
    }

    $setBusy = {
        param([bool]$Busy)
        foreach ($c in $btnInstall, $btnUninstall, $btnClose, $btnBrowse, $txtKey, $cmbDrive, $lstInst, $btnRemove) { $c.Enabled = -not $Busy }
        $form.UseWaitCursor = $Busy
        if (-not $Busy) { & $refreshList; & $refreshDrives }
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
                Show-Message "cloudHPCstorage is ready!`r`n`r`nYour storage is the drive $letter in File Explorer > This PC.`r`nIt is connected automatically at every logon.`r`n`r`nTo add another storage, select its activation file and click Install again."
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

    $btnRemove.Add_Click({
        $idx = $lstInst.SelectedIndex
        if ($idx -lt 0 -or $idx -ge $script:GuiInstances.Count) { Show-Message 'Select a storage in the list.' 'Warning'; return }
        $inst = $script:GuiInstances[$idx]
        $answer = [System.Windows.Forms.MessageBox]::Show("Remove the drive $($inst.Drive) (storage '$($inst.Bucket)') from this PC?",
            'cloudHPCstorage', 'YesNo', 'Question')
        if ($answer -ne 'Yes') { return }
        & $setBusy $true
        try {
            Invoke-RemoveStorage $inst.Bucket
            Show-Message "The drive $($inst.Drive) has been removed."
        } catch {
            Write-Log "ERROR: $($_.Exception.Message)"
            Show-Message $_.Exception.Message 'Error'
        } finally {
            & $setBusy $false
        }
    })

    $btnUninstall.Add_Click({
        $answer = [System.Windows.Forms.MessageBox]::Show('Remove cloudHPCstorage and ALL its drives from this PC?', 'cloudHPCstorage', 'YesNo', 'Question')
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

    & $refreshList
    $found = if ($ActivationFile) { $ActivationFile } else { Find-ActivationFile $BaseDir }
    if ($found) { $txtKey.Text = $found }
    & $refreshDrives
    $txtKey.Add_TextChanged({ & $refreshDrives })

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
    if ($Storage)        { $argList += @('-Storage', $Storage) }
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
    $what = if ($Storage) { "the storage '$Storage'" } else { 'cloudHPCstorage and ALL its drives' }
    if (-not $Silent) {
        $answer = [System.Windows.Forms.MessageBox]::Show("Remove $what from this PC?", 'cloudHPCstorage', 'YesNo', 'Question')
        if ($answer -ne 'Yes') { exit 0 }
    }
    try {
        if ($Storage) { Invoke-RemoveStorage $Storage.ToLower() } else { Invoke-Uninstall }
        Show-Message "Removed $what."
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
