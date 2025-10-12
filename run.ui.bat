@echo off
setlocal EnableExtensions

REM --- Ensure we run from repo root ---
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"
if exist "..\server.py" pushd ".."

REM --- Feature flags & env defaults ---
set ENGINE_V2=1
set INSIGHTS_DB_URL=sqlite:///data/insights.db
set AGENT_DATA_ROOT=%CD%\data\agent
set PYTHONUNBUFFERED=1
set PYTHONPATH=%CD%

if not exist "data" mkdir "data"
if not exist "data\agent" mkdir "data\agent"

REM --- Pick a runner: prefer 'uv', else python -m uvicorn via py/python3/python ---
where /q uv
if %ERRORLEVEL%==0 (
  set "RUN_SERVER=uv run uvicorn server:app --host 127.0.0.1 --port 8000 --reload"
) else (
  where /q py
  if %ERRORLEVEL%==0 (
    set "RUN_SERVER=py -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload"
  ) else (
    where /q python3
    if %ERRORLEVEL%==0 (
      set "RUN_SERVER=python3 -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload"
    ) else (
      set "RUN_SERVER=python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload"
    )
  )
)

REM --- Launch server in a new window (non-blocking) ---
start "Silhouette UI Server" cmd /c "%RUN_SERVER%"

REM --- Probe readiness (no PowerShell):
REM     1) If curl exists (Win10+), do a HEAD to /healthz
REM     2) Else, use netstat to check LISTENING on :8000
set "USE_CURL=0"
where /q curl && set "USE_CURL=1"

REM Wait up to ~30 seconds
for /l %%i in (1,1,30) do (
  if "%USE_CURL%"=="1" (
    curl -s -o nul -I http://127.0.0.1:8000/healthz && goto :OPEN
  ) else (
    for /f "tokens=1,2,3,4,* delims= " %%A in ('netstat -an ^| find ":8000" ^| find "LISTENING"') do (
      goto :OPEN
    )
  )
  ping -n 2 127.0.0.1 >nul
)

:OPEN
start "" "http://127.0.0.1:8000/ui"

if exist "..\server.py" popd
popd
endlocal
exit /b 0
