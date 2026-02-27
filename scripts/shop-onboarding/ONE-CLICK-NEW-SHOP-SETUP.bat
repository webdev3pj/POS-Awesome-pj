@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0shop_onboarding_config.json" (
  copy /Y "%~dp0shop_onboarding_config.example.json" "%~dp0shop_onboarding_config.json" >nul
  echo Created shop_onboarding_config.json from example.
  echo Edit this file with your target POS profile names, then run this launcher again.
  start "" notepad "%~dp0shop_onboarding_config.json"
  pause
  exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0one_click_new_shop_setup.ps1" -ConfigPath "%~dp0shop_onboarding_config.json"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo.
  echo Setup failed with exit code %RC%.
)
pause
exit /b %RC%

