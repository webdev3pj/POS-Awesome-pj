@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_shop_pc_relay_cert.ps1"
set "EXITCODE=%ERRORLEVEL%"
echo.
if "%EXITCODE%"=="0" (
  echo Shop PC relay setup completed successfully.
) else (
  echo Shop PC relay setup finished with code %EXITCODE%.
)
echo.
pause
exit /b %EXITCODE%
