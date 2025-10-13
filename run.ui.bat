@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"
if exist "..\server.py" pushd ".."

REM --- Feature flags & env defaults ---
set "ENGINE_V2=1"
set "INSIGHTS_DB_URL=sqlite:///data/insights.db"
set "AGENT_DATA_ROOT=%CD%\data\agent"
set "PYTHONUNBUFFERED=1"
set "PYTHONPATH=%CD%"

if not exist "data" mkdir "data"
if not exist "data\agent" mkdir "data\agent"

REM --- Resolve Python interpreter (prefer local venv) ---
set "PYEXE="
if exist ".venv\Scripts\python.exe" set "PYEXE=%CD%\.venv\Scripts\python.exe"
if "%PYEXE%"=="" where py >nul 2>&1 && for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)"') do set "PYEXE=%%P"
if "%PYEXE%"=="" set "PYEXE=python"

REM --- Launch browser helper in parallel using the same interpreter ---
set "SIL_OPENURL=http://127.0.0.1:8000/ui"
start "" "%PYEXE%" tools\open_browser.py "%SIL_OPENURL%"

REM --- Run the server in this window ---
"%PYEXE%" -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

if exist "..\server.py" popd
popd
endlocal
exit /b 0
