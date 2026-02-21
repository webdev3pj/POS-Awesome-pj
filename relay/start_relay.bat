@echo off
setlocal

cd /d "%~dp0"

echo ==============================================
echo POS Relay One-Click Installer + Starter
echo ==============================================

set "PYTHON_CMD="

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3.11 -V >nul 2>nul && set "PYTHON_CMD=py -3.11"
  if "%PYTHON_CMD%"=="" py -3.10 -V >nul 2>nul && set "PYTHON_CMD=py -3.10"
  if "%PYTHON_CMD%"=="" py -3 -V >nul 2>nul && set "PYTHON_CMD=py -3"
)

if "%PYTHON_CMD%"=="" (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 set "PYTHON_CMD=python"
)

if "%PYTHON_CMD%"=="" (
  echo Python not found. Attempting automatic install with winget...
  where winget >nul 2>nul
  if %ERRORLEVEL%==0 (
    winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
  )

  where py >nul 2>nul
  if %ERRORLEVEL%==0 (
    py -3.11 -V >nul 2>nul && set "PYTHON_CMD=py -3.11"
    if "%PYTHON_CMD%"=="" py -3 -V >nul 2>nul && set "PYTHON_CMD=py -3"
  )

  if "%PYTHON_CMD%"=="" (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 set "PYTHON_CMD=python"
  )
)

if "%PYTHON_CMD%"=="" (
  echo ERROR: Could not find or install Python automatically.
  echo Please install Python 3.10+ and run this file again.
  pause
  exit /b 1
)

echo Using Python command: %PYTHON_CMD%

if not exist ".venv" (
  echo Creating virtual environment...
  %PYTHON_CMD% -m venv .venv
  if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

echo Installing/updating dependencies...
python -m pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
  echo ERROR: pip upgrade failed.
  pause
  exit /b 1
)

pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
  echo ERROR: dependency installation failed.
  pause
  exit /b 1
)

echo Running relay self-test...
python -m relay.selftest
if %ERRORLEVEL% neq 0 (
  echo ERROR: self-test failed. Fix issues and rerun.
  pause
  exit /b 1
)

echo Opening relay dashboard in browser...
start "" http://127.0.0.1:8787

echo Starting POS Relay on configured host/port...
python -m relay.app

endlocal

