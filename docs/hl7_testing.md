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

## Execution Runbook (Windows CMD & PowerShell)

This section documents how to run the HL7 validator using the FAST and HL7apy engines, including Windows CMD and PowerShell variants, parallel workers guidance, and parity checks.

### Prereqs
- Run from the repo root (where `tools/`, `tests/`, `artifacts/` live).
- Windows: `py` launcher installed. If `py` isn’t found, replace `py` with `python`.
- Reports are written to `artifacts/hl7/`.

---

### A) FAST engine (recommended for batch QA)

**CMD (single line):**
```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --progress-every 200 --progress-time 10 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_fast.csv"
```

**PowerShell (multiline):**

```powershell
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine fast `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_fast.csv"
```

> PowerShell tip: the backtick `` ` `` must be the **last character** on the line (no trailing spaces).

---

### B) HL7apy engine (structured parse; slower; use for deep debugging)

**CMD (single line):**

```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine hl7apy --hl7apy-validation none --workers 1 --chunk 200 --progress-every 200 --progress-time 10 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_hl7apy.csv"
```

**PowerShell (multiline):**

```powershell
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine hl7apy --hl7apy-validation none `
  --workers 1 --chunk 200 `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_hl7apy.csv"
```

---

### C) Parallel execution: workers & chunk size (critical)

* A **worker** is a separate Python **process**. Multiple workers parse different batches **in parallel**; results are merged at the end (true parallelism for CPU-bound tasks).
* `--workers auto` chooses a sensible number based on your CPU; you can also pass an integer, e.g. `--workers 4`.
* `--chunk N` sets how many messages a worker takes per task. Larger chunks reduce coordination overhead (usually faster).

**Guidelines (Windows):**

* **Small inputs (<~800 msgs):** `--workers 1` (avoid process-spawn overhead)
* **Medium (~2k–10k msgs):** `--workers auto --chunk 500` (good default)
* **Very large:** prefer WSL/Linux for best scaling; start with `--workers auto --chunk 1000`

**Faster hl7apy preset (Windows, ~2.4k msgs):**

```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine hl7apy --hl7apy-validation none --workers auto --chunk 500 --progress-every 200 --progress-time 10 --max-errors-per-msg 10 --max-print 0 --report "artifacts\hl7\sample_set_x_hl7apy.csv"
```

```powershell
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine hl7apy --hl7apy-validation none `
  --workers auto --chunk 500 `
  --progress-every 200 --progress-time 10 `
  --max-errors-per-msg 10 --max-print 0 `
  --report "artifacts/hl7/sample_set_x_hl7apy.csv"
```

---

### D) Parity checks (FAST vs. HL7apy)

**PowerShell — exact diff of CSV rows:**

```powershell
$fast = Import-Csv artifacts\hl7\sample_set_x_fast.csv
$hl7  = Import-Csv artifacts\hl7\sample_set_x_hl7apy.csv
$cols = 'msg_index','rule_id','field','severity','message'
$fastS = $fast | Sort-Object msg_index, rule_id, field, severity, message
$hl7S  = $hl7  | Sort-Object msg_index, rule_id, field, severity, message
$diff = Compare-Object $fastS $hl7S -Property $cols
if ($diff) { $diff | Format-Table -Auto } else { '✅ Reports are identical.' }
```

**Quick line-count sanity (PowerShell & CMD):**

```powershell
(Get-Content artifacts\hl7\sample_set_x_fast.csv).Count
(Get-Content artifacts\hl7\sample_set_x_hl7apy.csv).Count
```

```cmd
find /c /v "" "artifacts\hl7\sample_set_x_fast.csv"
find /c /v "" "artifacts\hl7\sample_set_x_hl7apy.csv"
```

---

### E) Recommended defaults & pitfalls

* Default to **`--engine fast`** for production QA.
* Use **`--engine hl7apy --hl7apy-validation none`** only when you need full structure; on Windows prefer `--workers 1` for small files.
* Keep `--max-errors-per-msg` modest and `--max-print 0` for speed.
* **Pitfalls:**
  * Running PowerShell commands in **CMD**: backticks are treated as literal characters → “unrecognized arguments: \`”. In CMD, use the single-line versions.
  * Trailing spaces after a PowerShell backtick break line continuation.
  * If `py` isn’t found, use `python`.

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

