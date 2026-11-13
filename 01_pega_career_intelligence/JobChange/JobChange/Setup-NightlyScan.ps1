
# Setup-NightlyScan.ps1 — Register a Windows Scheduled Task
# Runs the Pega job scan every night at midnight.
#
# Usage:  .\Setup-NightlyScan.ps1
#         .\Setup-NightlyScan.ps1 -Time "01:00"   # 1 AM instead
#         .\Setup-NightlyScan.ps1 -Remove          # uninstall

param(
    [string]$Time = "00:00",
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$TaskName = 'PegaCareerDeskNightlyScan'
$ScriptDir = $PSScriptRoot
$PythonExe = Join-Path $ScriptDir '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $PythonExe)) {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}

$ScanScript = Join-Path $ScriptDir 'nightly_scan.py'

if ($Remove) {
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task: $TaskName"
    } catch {
        Write-Host "Task not found or already removed."
    }
    return
}

Write-Host "Setting up nightly Pega scan..."
Write-Host "  Python:  $PythonExe"
Write-Host "  Script:  $ScanScript"
Write-Host "  Time:    $Time daily"
Write-Host ""

# Build the task
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-B `"$ScanScript`"" `
    -WorkingDirectory $ScriptDir

$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -WakeToRun

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

# Register (replace if exists)
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
} catch {}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Nightly Pega job scan: LinkedIn + career portals + job boards. Results preloaded for morning review."

Write-Host ""
Write-Host "Scheduled task '$TaskName' created successfully!"
Write-Host "  Runs every night at $Time"
Write-Host "  Logs saved to: $ScriptDir\_logs\"
Write-Host ""
Write-Host "To remove:  .\Setup-NightlyScan.ps1 -Remove"
Write-Host "To change time:  .\Setup-NightlyScan.ps1 -Time '01:00'"
Write-Host "To run manually:  python -B nightly_scan.py"
