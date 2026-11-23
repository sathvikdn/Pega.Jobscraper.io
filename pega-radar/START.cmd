@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"
rem Opens the Pega Radar website in your browser. Close this window to stop it.
%PY% -B radar.py serve
if errorlevel 1 (
  echo.
  echo Pega Radar could not start. Run "%PY% -B radar.py doctor" in this folder to see why.
  pause
)
endlocal
