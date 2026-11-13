@echo off
REM ============================================================
REM  Pega Job Hunter - Daily Scheduler Setup
REM  Creates a Windows Task Scheduler task to run every day at 9 AM
REM ============================================================

echo.
echo ========================================
echo  Pega Job Hunter - Scheduler Setup
echo ========================================
echo.

SET SCRIPT_PATH=%~dp0pega_job_hunter.py
SET PYTHON_PATH=python

REM Check Python is available
%PYTHON_PATH% --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python or update PATH.
    pause
    exit /b 1
)

echo Script: %SCRIPT_PATH%
echo.
echo This will create a scheduled task that runs daily at 9:00 AM.
echo.
set /p CONFIRM="Proceed? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

REM Create the scheduled task
schtasks /create /tn "PegaJobHunter" /tr "cmd /c \"%PYTHON_PATH%\" \"%SCRIPT_PATH%\" --open" /sc daily /st 09:00 /rl HIGHEST /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo  SUCCESS! Task "PegaJobHunter" created.
    echo  Schedule: Daily at 9:00 AM
    echo  Action:   Full scan + auto-open report
    echo ========================================
    echo.
    echo To modify:
    echo   schtasks /change /tn "PegaJobHunter" /st 08:00
    echo.
    echo To run now:
    echo   schtasks /run /tn "PegaJobHunter"
    echo.
    echo To delete:
    echo   schtasks /delete /tn "PegaJobHunter" /f
    echo.
) else (
    echo.
    echo [ERROR] Failed to create task. Try running as Administrator.
    echo.
)

pause
