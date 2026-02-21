@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Starting POS Relay on configured host/port...
python -m relay.app

endlocal

