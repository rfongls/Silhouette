@echo off
setlocal ENABLEDELAYEDEXPANSION

set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"
if exist "..\server.py" (
    pushd ".."
)

echo Running from: %CD%
set PYTHONPATH=%CD%
set ENGINE_V2=1
set PYTHONUNBUFFERED=1
set SIL_OPENURL=http://127.0.0.1:8000/ui/landing

start "" cmd /c python tools\open_browser.py "%SIL_OPENURL%"
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

if exist "..\server.py" (
    popd
)
popd
endlocal
