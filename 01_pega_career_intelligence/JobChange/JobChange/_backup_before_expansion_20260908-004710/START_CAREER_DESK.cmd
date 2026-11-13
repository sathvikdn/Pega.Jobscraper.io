@echo off
setlocal
cd /d "%~dp0"
set "CAREER_PY=python"
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "CAREER_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist ".venv\Scripts\python.exe" set "CAREER_PY=%~dp0.venv\Scripts\python.exe"
echo Open http://127.0.0.1:5050 after the server starts.
echo Keep this window open. Press Ctrl+C to stop.
"%CAREER_PY%" app.py %*
if errorlevel 1 echo Startup failed. Check the error above. See README.md for setup.
pause
