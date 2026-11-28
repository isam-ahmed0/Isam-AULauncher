#requires -Version 5.1
<#
CrewLauncher installer / updater for Windows.

  powershell -ExecutionPolicy Bypass -File setup.ps1 [install] [-Silent] [-Online]
  powershell -ExecutionPolicy Bypass -File setup.ps1 update [-Silent]
  powershell -ExecutionPolicy Bypass -File setup.ps1 uninstall [-Silent]
  powershell -ExecutionPolicy Bypass -File setup.ps1 is-installed

  -Online   download the small stub installer instead of the ~79 MB offline one
  -Silent   run the NSIS installer/uninstaller without UI

Windows keeps the self-contained PyInstaller build; WebView2 is provided by Edge.
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet('install', 'update', 'uninstall', 'is-installed', 'help')]
    [string]$Command = 'install',
    [switch]$Silent,
    [switch]$Online
)

$ErrorActionPreference = 'Stop'
$Repo         = 'isam-ahmed0/Isam-AULauncher'
$Api          = "https://api.github.com/repos/$Repo/releases/latest"
$AppName      = 'CrewLauncher'
$RegKey       = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
$AppKey       = "HKCU:\Software\$AppName"
$AssetOffline = 'CrewLauncher-Setup-Offline.exe'
$AssetOnline  = 'CrewLauncher-Setup.exe'

function Log { param([string]$Message) Write-Host "==> $Message" }
function Fail { param([string]$Message) Write-Error $Message; exit 1 }

function Get-Release {
    try {
        return Invoke-RestMethod -Uri $Api -Headers @{ 'User-Agent' = 'CrewLauncher-Setup' } -UseBasicParsing
    } catch {
        Fail "Could not reach GitHub: $($_.Exception.Message)"
    }
}

function Get-InstallDir {
    if (Test-Path $AppKey) {
        $value = (Get-ItemProperty -Path $AppKey -Name 'Install_Location' -ErrorAction SilentlyContinue).Install_Location
        if ($value -and (Test-Path $value)) { return $value }
    }
    if (Test-Path $RegKey) {
        $value = (Get-ItemProperty -Path $RegKey -Name 'InstallLocation' -ErrorAction SilentlyContinue).InstallLocation
        if ($value -and (Test-Path $value)) { return $value }
    }
    return $null
}

function Test-Installed {
    $dir = Get-InstallDir
    return [bool]($dir -and (Test-Path (Join-Path $dir 'CrewLauncher.exe')))
}

function Get-InstalledVersion {
    if (Test-Path $RegKey) {
        return (Get-ItemProperty -Path $RegKey -Name 'DisplayVersion' -ErrorAction SilentlyContinue).DisplayVersion
    }
    return $null
}

function Normalize([string]$v) {
    if (-not $v) { return '' }
    # Tags may have a leading 'v'; NSIS DisplayVersion does not.
    return (($v -replace '^v', '') -replace '[^0-9A-Za-z]', '').ToLowerInvariant()
}

function Install-Release {
    $release = Get-Release
    $asset = if ($Online) { $AssetOnline } else { $AssetOffline }
    $entry = $release.assets | Where-Object { $_.name -eq $asset } | Select-Object -First 1
    if (-not $entry) { Fail "Release $($release.tag_name) has no $asset asset." }

    $tmp = Join-Path $env:TEMP "CrewLauncher-$asset"
    Log "downloading $asset ($([math]::Round($entry.size / 1MB, 1)) MB)"
    try {
        Invoke-WebRequest -Uri $entry.browser_download_url -OutFile $tmp -UseBasicParsing
    } catch {
        Fail "Download failed: $($_.Exception.Message)"
    }

    Log "installing $($release.tag_name)"
    $nsisArgs = if ($Silent) { '/S' } else { @() }
    try {
        $proc = Start-Process -FilePath $tmp -ArgumentList $nsisArgs -Wait -PassThru
        if ($proc.ExitCode -ne 0) { Fail "Installer exited with code $($proc.ExitCode)." }
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
    Log 'CrewLauncher installed.'
}

function Uninstall-Release {
    if (-not (Test-Installed)) { Log 'CrewLauncher is not installed.'; return }
    $dir = Get-InstallDir
    $exe = Join-Path $dir 'Uninstall.exe'
    if (-not (Test-Path $exe)) {
        $cmd = (Get-ItemProperty -Path $RegKey -Name 'UninstallString' -ErrorAction SilentlyContinue).UninstallString
        if (-not $cmd) { Fail "Uninstaller not found in $dir." }
        $exe = ($cmd -replace '^"|"$', '')
    }
    Log 'uninstalling CrewLauncher'
    $nsisArgs = if ($Silent) { '/S' } else { @() }
    $proc = Start-Process -FilePath $exe -ArgumentList $nsisArgs -Wait -PassThru
    if ($proc.ExitCode -ne 0) { Fail "Uninstaller exited with code $($proc.ExitCode)." }
    Log 'CrewLauncher uninstalled.'
}

switch ($Command) {
    'help' { Get-Help -Full $PSCommandPath; exit 0 }
    'is-installed' {
        if (Test-Installed) { Log "installed ($(Get-InstalledVersion))"; exit 0 }
        Log 'not installed'; exit 1
    }
    'uninstall' { Uninstall-Release; exit 0 }
    'update' {
        if (-not (Test-Installed)) { Log 'not installed; installing'; Install-Release; exit 0 }
        $release = Get-Release
        $current = Normalize (Get-InstalledVersion)
        $latest = Normalize $release.tag_name
        if ($current -eq $latest) { Log "already up to date ($(Get-InstalledVersion))"; exit 0 }
        Log "updating $current -> $($release.tag_name)"
        Install-Release
        exit 0
    }
    default {
        if (Test-Installed) {
            Log "CrewLauncher $(Get-InstalledVersion) is already installed (use 'update')."
            exit 0
        }
        Install-Release
        exit 0
    }
}
