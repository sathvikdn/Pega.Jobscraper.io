$ErrorActionPreference = 'Stop'
$careerSource = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$careerDestination = (Resolve-Path -LiteralPath 'C:\Users\sathv\Desktop\JobChange').Path
if ($careerSource -eq $careerDestination) { throw 'Run this installer from the workspace copy.' }
$careerNames = @('app.py','job_matching.py','job_details.py','portal_scan.py','parallel_scan.py','campaign.py','directory_data.py','opportunity_data.py','quality.py','storage.py','verification.py','pega_job_hunter.py','pega_job_portal.py','requirements.txt','README.md','Start-CareerDesk.ps1','Setup-CareerDesk.ps1','START_CAREER_DESK.cmd','test_portal.py','test_scanner.py','test_directory.py','test_campaign.py','test_expanded_portal.py','test_team_depth.py','test_checkpoint.py','test_ui.cjs','investigation_data.py','ecosystem_discovery.py','test_investigation.py','test_investigation_api.py','test_experience_audit.py','test_ui_investigation.cjs')
$careerRelativeFiles = [System.Collections.Generic.List[string]]::new()
foreach ($careerName in $careerNames) { $careerRelativeFiles.Add($careerName) }
foreach ($careerFolder in @('static','templates','research')) {
    foreach ($careerFile in (Get-ChildItem -LiteralPath (Join-Path $careerSource $careerFolder) -File -Recurse)) {
        if ($careerFile.Extension -in @('.js','.css','.html','.json')) {
            if ($careerFolder -eq 'research' -and $careerFile.Name -eq 'preloaded_search.json' -and (Test-Path -LiteralPath (Join-Path $careerDestination 'research\preloaded_search.json'))) { continue }
            $careerRelativeFiles.Add($careerFile.FullName.Substring($careerSource.Length + 1))
        }
    }
}
foreach ($careerRelative in $careerRelativeFiles) {
    $careerSourceFile = [IO.Path]::GetFullPath((Join-Path $careerSource $careerRelative))
    $careerDestFile = [IO.Path]::GetFullPath((Join-Path $careerDestination $careerRelative))
    if (-not $careerSourceFile.StartsWith($careerSource + '\') -or -not $careerDestFile.StartsWith($careerDestination + '\')) { throw 'File escaped the intended portal directories.' }
    if (-not (Test-Path -LiteralPath $careerSourceFile -PathType Leaf)) { throw "Missing source: $careerRelative" }
}
$careerLiveState = $null
try { $careerLiveState = Invoke-RestMethod -Uri 'http://127.0.0.1:5050/api/status' -TimeoutSec 3 } catch { }
if ($careerLiveState.running) { throw 'Pause the running search and allow its checkpoint to finish before installing.' }
$careerListeners = @(Get-NetTCPConnection -LocalPort 5050 -State Listen -ErrorAction SilentlyContinue)
foreach ($careerOwner in ($careerListeners.OwningProcess | Select-Object -Unique)) {
    $careerProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $careerOwner"
    if ($careerProcess.CommandLine -notlike "*$careerDestination\app.py*" -or $careerProcess.CommandLine -notmatch '--port\s+5050') { throw "Port 5050 belongs to a different process ($careerOwner). No files copied." }
    Stop-Process -Id $careerOwner
}
$careerDataBefore = @{}
$careerDataPath = Join-Path $careerDestination 'data'
if (Test-Path -LiteralPath $careerDataPath) {
    foreach ($careerFile in (Get-ChildItem -LiteralPath $careerDataPath -File -Recurse)) {
        $careerDataBefore[$careerFile.FullName] = (Get-FileHash -LiteralPath $careerFile.FullName).Hash
    }
}
$careerBackup = Join-Path $careerDestination ('_backup_before_expansion_' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $careerBackup | Out-Null
foreach ($careerRelative in $careerRelativeFiles) {
    $careerExisting = Join-Path $careerDestination $careerRelative
    $careerBackupFile = Join-Path $careerBackup $careerRelative
    if (Test-Path -LiteralPath $careerExisting) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $careerBackupFile) -Force | Out-Null
        Copy-Item -LiteralPath $careerExisting -Destination $careerBackupFile -Force
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $careerExisting) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $careerSource $careerRelative) -Destination $careerExisting -Force
    if ((Get-FileHash -LiteralPath (Join-Path $careerSource $careerRelative)).Hash -ne (Get-FileHash -LiteralPath $careerExisting).Hash) { throw "Copy verification failed: $careerRelative" }
}
foreach ($careerDataFile in $careerDataBefore.Keys) {
    if ((Get-FileHash -LiteralPath $careerDataFile).Hash -ne $careerDataBefore[$careerDataFile]) { throw "User state changed during installation: $careerDataFile" }
}
Write-Output "Installed and hash-verified $($careerRelativeFiles.Count) code/research files."
Write-Output "Backup: $careerBackup"
Write-Output "Preserved $($careerDataBefore.Count) user-state files, job history, all personal documents and original reference HTML."
