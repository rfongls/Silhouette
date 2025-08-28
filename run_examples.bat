@echo off
setlocal
if not exist artifacts\hl7 mkdir artifacts\hl7

REM Fast engine
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine fast ^
  --progress-every 200 --progress-time 10 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_fast.csv"

REM HL7apy engine
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine hl7apy --hl7apy-validation none ^
  --workers auto --chunk 200 ^
  --progress-every 200 --progress-time 10 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_hl7apy.csv"

REM Subset run
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine fast ^
  --start 1000 --limit 500 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_1k-1.5k.csv"
