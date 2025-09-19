@echo off
setlocal ENABLEDELAYEDEXPANSION
REM --- Go to repo root (this BAT is assumed in scripts\ or directly in root) ---
pushd %~dp0
REM If this file lives in scripts\, go up one:
if /I "%CD%"=="%~dp0" if exist "..\server.py" pushd ..

echo Running from: %CD%
set PYTHONPATH=%CD%
REM Optional: show the exact app and log paths being used
python -c "import pathlib; print('Repo root:', pathlib.Path().resolve())"

REM Start the fully-instrumented app
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

popd
endlocal
