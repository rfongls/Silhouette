@echo off
setlocal
pushd %~dp0
REM If located in scripts\, move to repo root
if exist "..\server.py" pushd ..
title Silhouette — Engine V2 (UI + Agent)

REM --- Feature flags / config -------------------------------------------------
set ENGINE_V2=1

if not defined INSIGHTS_DB_URL (
  set INSIGHTS_DB_URL=sqlite:///data/insights.db
)

if not defined AGENT_DATA_ROOT (
  set AGENT_DATA_ROOT=.\data\agent
)

echo ENGINE_V2=%ENGINE_V2%
echo INSIGHTS_DB_URL=%INSIGHTS_DB_URL%
echo AGENT_DATA_ROOT=%AGENT_DATA_ROOT%
echo.

uvicorn server:app --reload --host 127.0.0.1 --port 8000

popd
endlocal
