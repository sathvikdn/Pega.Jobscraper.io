<#
Registers the daily Pega Radar scan in Windows Task Scheduler.

    powershell -ExecutionPolicy Bypass -File setup_schedule.ps1                      # every day at 07:30
    powershell -ExecutionPolicy Bypass -File setup_schedule.ps1 -Time 06:45
    powershell -ExecutionPolicy Bypass -File setup_schedule.ps1 -SecondTime 19:00    # a second daily scan
    powershell -ExecutionPolicy Bypass -File setup_schedule.ps1 -Remove

The task runs "python -B radar.py scan" in this folder as the signed-in user, only
while that user is signed in, for at most 2 hours. A scan missed because the PC was
off starts at the next opportunity, and a new scan never starts while one is running.
#>
param(
    [string]$Time = '07:30',
    [string]$SecondTime = '',
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$TaskName = 'PegaRadarDailyScan'
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Remove) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed the scheduled task $TaskName."
    } else {
        Write-Host "No scheduled task named $TaskName exists."
    }
    exit 0
}

function ConvertTo-TriggerTime([string]$Value) {
    try {
        return [datetime]::ParseExact($Value, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
    } catch {
        throw "'$Value' is not a time. Use 24-hour HH:mm, for example 07:30."
    }
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
    $Executable = $Python.Source
    $Arguments = '-B radar.py scan'
} else {
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $Launcher) {
        throw 'Python was not found. Install Python 3.10 or newer from python.org and tick "Add python.exe to PATH".'
    }
    $Executable = $Launcher.Source
    $Arguments = '-3 -B radar.py scan'
}

$Triggers = @(New-ScheduledTaskTrigger -Daily -At (ConvertTo-TriggerTime $Time))
if ($SecondTime) {
    $Triggers += New-ScheduledTaskTrigger -Daily -At (ConvertTo-TriggerTime $SecondTime)
}
$Action = New-ScheduledTaskAction -Execute $Executable -Argument $Arguments -WorkingDirectory $ProjectDir
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Triggers -Settings $Settings `
    -Principal $Principal -Description 'Pega Radar: daily search for Pega roles in India.' -Force | Out-Null

$When = $Time
if ($SecondTime) { $When = "$Time and $SecondTime" }
Write-Host "Scheduled $TaskName every day at $When."
Write-Host "It runs: $Executable $Arguments"
Write-Host "In:      $ProjectDir"
Write-Host 'Open START.cmd any time to see the results. Remove the schedule with: setup_schedule.ps1 -Remove'
