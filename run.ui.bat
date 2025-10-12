@echo off
setlocal EnableExtensions

REM --- Ensure we run from repo root ---
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"
if exist "..\server.py" pushd ".."

REM --- Feature flags & environment defaults ---
set ENGINE_V2=1
set INSIGHTS_DB_URL=sqlite:///data/insights.db
set AGENT_DATA_ROOT=%CD%\data\agent
set PYTHONUNBUFFERED=1
set PYTHONPATH=%CD%

if not exist data mkdir data
if not exist data\agent mkdir data\agent

REM --- Pick a runner: prefer 'uv' if available; else fall back to python -m uvicorn ---
where /q uv
if %ERRORLEVEL%==0 (
  set "RUN_SERVER=uv run uvicorn server:app --host 127.0.0.1 --port 8000 --reload"
) else (
  REM try python, py, or python3
  where /q py
  if %ERRORLEVEL%==0 (
    set "PYCMD=py -m"
  ) else (
    where /q python3
    if %ERRORLEVEL%==0 ( set "PYCMD=python3 -m" ) else ( set "PYCMD=python -m" )
  )
  set "RUN_SERVER=%PYCMD% uvicorn server:app --host 127.0.0.1 --port 8000 --reload"
)

REM --- Launch server in a new window (non-blocking) ---
start "Silhouette UI Server" cmd /c "%RUN_SERVER%"

REM --- Wait for /healthz to respond (PS 5/7 compatible) ---
set "PROBE=try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/healthz' -Method Head; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }"
for /l %%i in (1,1,30) do (
  powershell -NoProfile -Command "%PROBE%" && goto :OPEN
  >nul 2>&1 ping -n 2 127.0.0.1
)

:OPEN
REM --- Open the UI in the default browser (no PowerShell needed) ---
start "" "http://127.0.0.1:8000/ui"

REM --- Restore directory stack and exit ---
if exist "..\server.py" popd
popd
endlocal
exit /b 0
