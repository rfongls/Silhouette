# HL7 QA — Running & Commands

Validate HL7 v2 messages against site-tunable **profiles** in `tests/hl7/rules/rules.yaml`.

## Engines

* **fast** — raw ER7 parsing (no object model): HL7Spy-like speed (default via profiles; great for batch QA)
* **hl7apy** — full object model: use when you need strict grammar/group reasoning or tree navigation

> **MSH indexing:** tool accounts for HL7’s special MSH rules (MSH-1 is the separator). `MSH-7` now maps correctly to the Date/Time of Message, not MSH-8.

## Output & formats

* **Default report path (no `--report` needed):**
  `<repo root>\tests\artifacts\hl7\<input_stem>_<engine>.csv`
  Override with `--report-dir` or env `HL7_QA_REPORT_DIR`. Explicit `--report` still wins.
* **CSV layout (default = *per-issue*):**
  `index,msg_ctrl_id,msg_type,version,field,value_received,validation_value,issue_type,issue`
  (one row per error/warning ⇒ easy filtering)
* **Legacy CSV layout (*per-message* aggregate):**
  pass `--report-mode per-message`
* **JSONL:** pass a `.jsonl` path via `--report` (includes a structured `issues[]` array)

> Add `tests/artifacts/` to `.gitignore`.

## Prereqs

* Python 3.10+
* Install deps
  **Windows (CMD):**

  ```bat
  py -m pip install -U pip
  py -m pip install -r requirements.txt
  ```

  **macOS/Linux (bash):**

  ```bash
  python3 -m pip install -U pip
  python3 -m pip install -r requirements.txt
  ```

---

## Runbook (Windows)

> All examples assume running from **repo root**:
> `C:\Users\<you>\Documents\GitHub\test\Silhouette>`

### A) FAST engine (batch QA; fastest)

**CMD (single line):**

```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast
```

* Writes: `tests\artifacts\hl7\sample_set_x_fast.csv`
* Default **per-issue** rows; add `--report-mode per-message` for aggregate.

**PowerShell (multiline):**

```powershell
py -X utf8 tools/hl7_qa.py "tests/fixtures/hl7/sample_set_x.hl7" `
  --rules "tests/hl7/rules/rules.yaml" `
  --engine fast
```

> Tip: PowerShell line-continuation uses the backtick `` ` `` and must be the **last** char on the line.

### B) HL7apy engine (structured; slower; parallel helps)

**Recommended (Windows, \~2–10k msgs):**

```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine hl7apy --hl7apy-validation none --workers auto --chunk 500
```

* Writes: `tests\artifacts\hl7\sample_set_x_hl7apy.csv`
* `--workers auto` uses multiple processes; `--chunk 500` reduces overhead.

**Minimal single-process (small files / debugging):**

```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine hl7apy --hl7apy-validation none --workers 1 --chunk 200
```

### C) From the **tests/** folder instead

If your prompt is:

```
C:\...\Silhouette\tests>
```

use paths relative to `tests/`:

**FAST**

```cmd
py -X utf8 ..\tools\hl7_qa.py "fixtures\hl7\sample_set_x.hl7" --rules "hl7\rules\rules.yaml" --engine fast
```

**HL7apy**

```cmd
py -X utf8 ..\tools\hl7_qa.py "fixtures\hl7\sample_set_x.hl7" --rules "hl7\rules\rules.yaml" --engine hl7apy --hl7apy-validation none --workers auto --chunk 500
```

> Output still lands in `tests\artifacts\hl7\...` by default.

---

## Parallel execution (critical for hl7apy)

* A **worker** is a separate Python **process** (real parallelism for CPU-bound parsing).
* `--workers auto` picks a sensible count; or pass an int (e.g., `--workers 4`).
* `--chunk N` = messages per task per worker. Larger chunks → fewer handoffs → often faster.

**Windows guidelines**

* **Small (<\~800 msgs):** `--workers 1`
* **Medium (\~2k–10k):** `--workers auto --chunk 500`
* **Very large:** prefer WSL/Linux; start with `--workers auto --chunk 1000`

---

## What the key flags do

* `--engine {fast|hl7apy}`: pick parser backend (profiles may set a default; CLI overrides)
* `--hl7apy-validation {none|tolerant|strict}`: grammar strictness for hl7apy (we default to `none`)
* `--workers`, `--chunk`: parallelism (process count and batch size)
* `--report-mode {per-issue|per-message}`: row granularity (default per-issue)
* `--report-dir DIR` / `HL7_QA_REPORT_DIR`: set default output folder when `--report` omitted
* `--report PATH`: explicit `.csv` or `.jsonl` file
* `--max-errors-per-msg N`: cap issues captured per message (raise this for full dumps, e.g., `1000`)
* `--only ORU_R01,ADT_A01`: filter by message type(s)
* `--start S --limit L`: process a window of messages
* `--progress-every N`, `--progress-time T`: periodic progress logging

---

## Parity checks (FAST vs hl7apy) — **matches new CSV**

**PowerShell (ignores row order):**

```powershell
$fast = Import-Csv tests\artifacts\hl7\sample_set_x_fast.csv
$hl7  = Import-Csv tests\artifacts\hl7\sample_set_x_hl7apy.csv

# Compare by: index + field + issue_type + issue (core signal)
$cols = 'index','field','issue_type','issue'
$fastS = $fast | Sort-Object $cols
$hl7S  = $hl7  | Sort-Object $cols
$diff = Compare-Object $fastS $hl7S -Property $cols

if ($diff) { $diff | Format-Table -Auto }
else { '✅ Reports are identical at issue-level (by index, field, type, message).' }
```

**Quick line counts (CMD/PowerShell):**

```cmd
find /c /v "" "tests\artifacts\hl7\sample_set_x_fast.csv"
find /c /v "" "tests\artifacts\hl7\sample_set_x_hl7apy.csv"
```

---

## Useful variants

**Subset (fast iteration)**

```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --start 1000 --limit 500 --max-errors-per-msg 1000
```

**Filter types (e.g., ORU\_R01 + ADT\_A01)**

```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --only ORU_R01,ADT_A01
```

**JSONL output**

```cmd
py -X utf8 tools\hl7_qa.py "tests\fixtures\hl7\sample_set_x.hl7" --rules "tests\hl7\rules\rules.yaml" --engine fast --report "tests\artifacts\hl7\sample_set_x.jsonl"
```

---

## Notes & pitfalls

* **Default output** now always lands in `tests\artifacts\hl7\` when `--report` is omitted (independent of current working directory).
* **PowerShell vs CMD:** backticks are PowerShell-only; in CMD use single-line commands.
* **MSH indexing:** MSH-1 is the separator; tool correctly maps `MSH-7` to the timestamp.
* If you see few rows, raise `--max-errors-per-msg` (e.g., `1000`) to capture every issue per message.

---

If you want, I can also paste this straight into `docs/hl7_testing.md` and link it from `docs/README.md` in a quick follow-up.
