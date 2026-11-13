param([int]$Port = 5050)
$ErrorActionPreference = 'Stop'
$careerPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $careerPython)) {
    $careerPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
}
if (-not (Test-Path -LiteralPath $careerPython)) {
    $careerPython = (Get-Command python -ErrorAction Stop).Source
}
Push-Location -LiteralPath $PSScriptRoot
try {
    Write-Host "Career desk: http://127.0.0.1:$Port"
    Write-Host 'Keep this terminal open. Press Ctrl+C to stop.'
    & $careerPython app.py --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Portal failed to start. Run Setup-CareerDesk.ps1 if dependencies are missing, or choose another -Port.' }
} finally { Pop-Location }
