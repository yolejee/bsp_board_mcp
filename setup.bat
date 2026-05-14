@echo off
REM Double-click entry point. Forwards to setup.ps1 with execution policy bypass
REM so unsigned scripts run without modifying machine settings.
setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%setup.ps1" %*
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
    echo Setup finished successfully.
) else (
    echo Setup failed with exit code %RC%.
)
pause
exit /b %RC%
