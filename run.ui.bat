@echo off
setlocal

REM --- Ensure paths are relative to the repo root ---
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"
if exist "..\server.py" (
    pushd ".."
)

REM --- Feature flags & environment defaults ---
set ENGINE_V2=1
set INSIGHTS_DB_URL=sqlite:///data/insights.db
set AGENT_DATA_ROOT=%CD%\data\agent
set PYTHONUNBUFFERED=1
set PYTHONPATH=%CD%

if not exist data mkdir data
if not exist data\agent mkdir data\agent

REM --- Start the server in a new window so we can launch the browser from here ---
start "Silhouette UI Server" cmd /c "uv run uvicorn server:app --host 127.0.0.1 --port 8000 --reload"

REM --- Give the server a moment to start, then open the Engine landing page ---
powershell -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000/ui/engine'"

if exist "..\server.py" (
    popd
)
popd
endlocal
