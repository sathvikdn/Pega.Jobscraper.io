param([int]$Port = 5050, [switch]$Force)
$ErrorActionPreference = 'Stop'
$careerPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $careerPython)) {
    $careerPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
}
if (-not (Test-Path -LiteralPath $careerPython)) {
    $careerPython = (Get-Command python -ErrorAction Stop).Source
}
# Windows allows a second process to bind a port that is already being listened on,
# so Flask reports "Running on ..." while a stale instance keeps serving every request.
# Detect that here, because a silently ignored server looks identical to a broken portal.
$holders = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique)
if ($holders.Count -gt 0) {
    $stale = @(Get-Process -Id $holders -ErrorAction SilentlyContinue)
    foreach ($proc in $stale) {
        Write-Host ("Port {0} is already held by {1} (PID {2}, started {3})." -f $Port, $proc.ProcessName, $proc.Id, $proc.StartTime)
    }
    if (-not $Force) {
        throw "Port $Port is already in use. Re-run with -Force to stop the listener(s) above, or pick another -Port."
    }
    foreach ($proc in $stale) {
        Write-Host "Stopping stale listener PID $($proc.Id)."
        Stop-Process -Id $proc.Id -Force
    }
    Start-Sleep -Seconds 2
}
Push-Location -LiteralPath $PSScriptRoot
try {
    Write-Host "Career desk: http://127.0.0.1:$Port"
    Write-Host 'Keep this terminal open. Press Ctrl+C to stop.'
    & $careerPython app.py --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Portal failed to start. Run Setup-CareerDesk.ps1 if dependencies are missing, or choose another -Port.' }
} finally { Pop-Location }
