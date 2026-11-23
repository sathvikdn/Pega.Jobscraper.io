@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"
rem Searches every source once. Exit code 2 means a source needs attention; results are still saved.
%PY% -B radar.py scan
echo.
echo Scan finished with exit code %errorlevel%. Open START.cmd to see the results.
pause
endlocal
