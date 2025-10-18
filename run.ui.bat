@echo off
setlocal ENABLEDELAYEDEXPANSION
REM Silhouette Core UI runner (consolidated)
REM Usage: run.ui.bat [port]

REM Force-disable legacy standalone router so only the isolated module is active
set SILH_STANDALONE_ENABLE=0

if "%SILH_STANDALONE_ENABLE%"=="" set SILH_STANDALONE_ENABLE=1
set PORT=%1
if "%PORT%"=="" set PORT=8000

echo Starting Silhouette UI on http://127.0.0.1:%PORT%/ ...
python -m uvicorn server:app --host 127.0.0.1 --port %PORT% --reload

endlocal
exit /B %ERRORLEVEL%
