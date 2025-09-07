@echo off
setlocal enabledelayedexpansion
REM -----------------------------------------------------------------------------
REM Silhouette UI — One-click launcher (Windows)
REM Creates .venv if missing, installs UI deps, starts Uvicorn, opens browser.
REM -----------------------------------------------------------------------------

REM Move to repo root (this file lives in scripts/)
pushd "%~dp0\.."

REM Prefer py launcher when available
where py >nul 2>nul
if %errorlevel%==0 (
  set PYEXE=py -3
) else (
  set PYEXE=python
)

echo.
echo [1/4] Ensuring virtual env: .venv
if not exist .venv (
  %PYEXE% -m venv .venv
  if %errorlevel% neq 0 (
    echo Failed to create virtualenv. Ensure Python 3.10+ is installed.
    pause
    exit /b 1
  )
)

echo.
echo [2/4] Upgrading pip
call .venv\Scripts\python -m pip install -U pip
if %errorlevel% neq 0 goto :pipfail

echo.
echo [3/4] Installing UI dependencies (fastapi, uvicorn, jinja2, anyio, python-multipart)
call .venv\Scripts\python -m pip install "fastapi>=0.110" "uvicorn[standard]>=0.23" "jinja2>=3.1" "anyio>=4.0" "python-multipart>=0.0.9"
if %errorlevel% neq 0 goto :pipfail

echo.
echo [4/4] Starting server at http://localhost:8000/
start "" "http://localhost:8000/ui/home"
call .venv\Scripts\python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
goto :eof

:pipfail
echo Pip installation failed. Check your network and try again.
pause
exit /b 1
