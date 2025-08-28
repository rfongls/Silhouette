# HL7 QA — Running & Commands

Validate HL7 v2 messages against site-tunable **profiles** in `tests/hl7/rules/rules.yaml`.

**Engines**
- **fast** — raw ER7 parsing (no object model): HL7Spy-like speed (default via `engine: fast` in profiles)
- **hl7apy** — full object model: use when you need strict grammar/group checks

Artifacts: reports go to `artifacts/hl7/` — add `artifacts/` to `.gitignore`.

## Prereqs
- Python 3.10+
- Install:
  - Windows:
    ```bat
    py -m pip install -U pip
    py -m pip install -r requirements.txt
    ```
  - macOS/Linux:
    ```bash
    python3 -m pip install -U pip
    python3 -m pip install -r requirements.txt
    ```
- Create output folder:
  - Windows: `mkdir artifacts\hl7 2>nul`
  - macOS/Linux: `mkdir -p artifacts/hl7`

---

## Windows (cmd)

**Fast engine (recommended)**
```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine fast ^
  --progress-every 200 --progress-time 10 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_fast.csv"
```

**HL7apy engine (object model)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine hl7apy --hl7apy-validation none ^
  --workers auto --chunk 200 ^
  --progress-every 200 --progress-time 10 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_hl7apy.csv"
```

---

## Windows (PowerShell)

**Fast**

```powershell
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine fast `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_fast.csv"
```

**HL7apy**

```powershell
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine hl7apy --hl7apy-validation none `
  --workers auto --chunk 200 `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_hl7apy.csv"
```

---

## macOS/Linux (bash/zsh)

**Fast**

```bash
python3 tools/hl7_qa.py tests/fixtures/hl7/sample_set_x.hl7 \
  --rules tests/hl7/rules/rules.yaml \
  --engine fast \
  --progress-every 200 --progress-time 10 \
  --max-errors-per-msg 10 --max-print 0 \
  --report artifacts/hl7/sample_set_x_fast.csv
```

**HL7apy**

```bash
python3 tools/hl7_qa.py tests/fixtures/hl7/sample_set_x.hl7 \
  --rules tests/hl7/rules/rules.yaml \
  --engine hl7apy --hl7apy-validation none \
  --workers auto --chunk 200 \
  --progress-every 200 --progress-time 10 \
  --max-errors-per-msg 10 --max-print 0 \
  --report artifacts/hl7/sample_set_x_hl7apy.csv
```

---

## Useful variants

**Subset (fast iteration)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine fast ^
  --start 1000 --limit 500 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x_1k-1.5k.csv"
```

**Filter types (e.g., ORU_R01 & ADT_A01)**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine fast ^
  --only ORU_R01,ADT_A01 ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\oru_adt_check.csv"
```

**JSONL output**

```bat
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" ^
  --rules "tests\hl7\rules\rules.yaml" ^
  --engine fast ^
  --max-errors-per-msg 10 --max-print 0 ^
  --report "artifacts\hl7\sample_set_x.jsonl"
```

---

## Notes

* Profiles may specify `engine: fast|hl7apy`; CLI `--engine` overrides per run.
* Timestamp policy is controlled in `timestamps.mode` (`length_only` by default).
* Add `artifacts/` to `.gitignore` to keep reports out of VCS.
