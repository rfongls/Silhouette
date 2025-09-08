@echo off
setlocal ENABLEDELAYEDEXPANSION
pushd %~dp0\..

REM Create virtual environment if missing
if not exist .venv\Scripts\activate.bat (
  echo [1/3] Creating .venv ...
  python -m venv .venv || goto :end
)

call .venv\Scripts\activate.bat

echo [2/3] Installing requirements ...
pip install -r requirements.txt >nul || goto :end

echo [3/3] Launching UI ...
call scripts\run_ui.bat

:end
popd
endlocal
