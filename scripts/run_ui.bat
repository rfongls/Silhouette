@echo off
setlocal ENABLEDELAYEDEXPANSION
pushd %~dp0\..

set HOST=127.0.0.1
set PORT=8000
set URL=http://%HOST%:%PORT%/ui/landing
set SENTINEL=%TEMP%\silhouette_ui_browser_opened

if not defined ENGINE_V2 set ENGINE_V2=1

REM Optional: activate venv if present
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat

echo Starting Silhouette UI server on http://%HOST%:%PORT%/ ...
start "Silhouette UI (server)" cmd /k python -m uvicorn server:app --host %HOST% --port %PORT% --reload
set OPEN_BROWSER=1
if exist "%SENTINEL%" set OPEN_BROWSER=0
if "%OPEN_BROWSER%"=="1" (
  timeout /t 2 >nul
  start "" %URL%
  >"%SENTINEL%" echo opened
)

popd
endlocal
