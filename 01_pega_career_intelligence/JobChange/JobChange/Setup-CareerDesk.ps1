$ErrorActionPreference = 'Stop'
$careerPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $careerPython)) {
    $careerPython = (Get-Command python -ErrorAction Stop).Source
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $careerPython -m pip install --target .deps --upgrade -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    Write-Host 'Ready. Run .\Start-CareerDesk.ps1'
} finally { Pop-Location }
