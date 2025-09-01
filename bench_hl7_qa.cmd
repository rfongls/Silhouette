@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem === ARGS (all optional) ===
set "INPUT=%~1"
if not defined INPUT set "INPUT=tests\fixtures\hl7"
set "RULES=%~2"
if not defined RULES set "RULES=tests\hl7\rules\rules.yaml"
set "REPORT=%~3"
if not defined REPORT set "REPORT=artifacts\hl7\qa.csv"
set "LOG=%~4"
if not defined LOG set "LOG=artifacts\hl7\qa_run.log"

rem === Ensure folders ===
for %%I in ("%REPORT%") do if not exist "%%~dpI" mkdir "%%~dpI"
for %%I in ("%LOG%")    do if not exist "%%~dpI" mkdir "%%~dpI"

rem === Start time (centiseconds) ===
set "t0=%time: =0%"
for /f "tokens=1-4 delims=:.," %%a in ("%t0%") do (
  set /a h0=1%%a-100, m0=1%%b-100, s0=1%%c-100, c0=1%%d-100
)
set /a T0=((h0*60+m0)*60+s0)*100+c0

rem === Run (quiet output -> log), UTF-8 safe ===
> "%LOG%" 2>&1 py -X utf8 tools\hl7_qa.py "%INPUT%" --rules "%RULES%" --max-print 0 --report "%REPORT%"
set "EXITCODE=%ERRORLEVEL%"

rem === End time (centiseconds) ===
set "t1=%time: =0%"
for /f "tokens=1-4 delims=:.," %%a in ("%t1%") do (
  set /a h1=1%%a-100, m1=1%%b-100, s1=1%%c-100, c1=1%%d-100
)
set /a T1=((h1*60+m1)*60+s1)*100+c1
if !T1! LSS !T0! set /a T1+=24*3600*100

set /a ELAPSED_CS=T1-T0
set /a SEC=ELAPSED_CS/100
set /a CEN=ELAPSED_CS%%100
set "CEN=0%CEN%" & set "CEN=%CEN:~-2%"

rem === Count CSV rows (minus header) ===
if exist "%REPORT%" (
  for /f %%A in ('type "%REPORT%" ^| find /c /v ""') do set LINES=%%A
) else (
  set LINES=1
)
set /a ROWS=LINES-1

rem === msgs/sec with 2 decimals ===
if !ELAPSED_CS! GTR 0 (
  set /a RATE100=(ROWS*10000 + ELAPSED_CS/2)/ELAPSED_CS
  set /a RATE_W=RATE100/100
  set /a RATE_F=RATE100%%100
  set "RATE_F=0!RATE_F!" & set "RATE_F=!RATE_F:~-2!"
) else (
  set RATE_W=0 & set RATE_F=00
)

echo.
echo Tool exit code: %EXITCODE%
echo !ROWS! messages in !SEC!.!CEN!s  ==>  !RATE_W!.!RATE_F! msg/s
echo Report: "%REPORT%"
echo Log:    "%LOG%"

endlocal
