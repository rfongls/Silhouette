@echo off
setlocal
cd /d %~dp0\..

:: Optional venv if not present
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat

:: Seeds & scope
mkdir data\security\seeds\cve 2>nul
mkdir data\security\seeds\kev 2>nul
mkdir docs\cyber 2>nul
> data\security\seeds\cve\cve_seed.json echo {"CVE-0001":{"summary":"Demo CVE","severity":5}}
> data\security\seeds\kev\kev_seed.json echo {"cves":["CVE-0001"]}
(echo example.com&echo *.example.com&echo sub.example.com) > docs\cyber\scope_example.txt

:: Smoke runs via wrappers (no Click)
echo auth> auth.pdf
python -c "import json; from skills.cyber_pentest_gate.v1.wrapper import tool as T; print(T(json.dumps({'target':'sub.example.com','scope_file':'docs/cyber/scope_example.txt','auth_doc':'auth.pdf','out_dir':'out/security/manual'})))"
python -c "import json; from skills.cyber_recon_scan.v1.wrapper import tool as T; print(T(json.dumps({'target':'sub.example.com','scope_file':'docs/cyber/scope_example.txt','profile':'version','out_dir':'out/security/manual'})))"
type nul > sample.pcap
python -c "import json; from skills.cyber_netforensics.v1.wrapper import tool as T; print(T(json.dumps({'pcap':'sample.pcap','out_dir':'out/security/manual'})))"
python -c "import json; from skills.cyber_ir_playbook.v1.wrapper import tool as T; print(T(json.dumps({'incident':'ransomware','out_dir':'out/security/manual'})))"

echo.
echo Active artifacts:
dir /b out\security\manual\active
endlocal
