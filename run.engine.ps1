$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
if (Test-Path "../server.py") { Set-Location .. }

$env:ENGINE_V2 = "1"
if (-not $env:INSIGHTS_DB_URL) { $env:INSIGHTS_DB_URL = "sqlite:///data/insights.db" }
if (-not $env:AGENT_DATA_ROOT) { $env:AGENT_DATA_ROOT = ".\data\agent" }

Write-Host "ENGINE_V2       =" $env:ENGINE_V2
Write-Host "INSIGHTS_DB_URL =" $env:INSIGHTS_DB_URL
Write-Host "AGENT_DATA_ROOT =" $env:AGENT_DATA_ROOT
Write-Host ""

uvicorn server:app --reload --host 127.0.0.1 --port 8000
