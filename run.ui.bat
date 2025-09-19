@echo off
setlocal ENABLEDELAYEDEXPANSION
pushd %~dp0
REM If this file lives in scripts\, go up one level to the repo root
if exist "..\server.py" pushd ..
echo Running from: %CD%
set PYTHONPATH=%CD%
python run_dynamic.py --app server:app --host 127.0.0.1 --port 8000 --reload
popd
endlocal

