# FHIR Ops Runbook

Operational notes for running (and validating) the HL7→FHIR pipeline locally.

> See [Agent Setup](../../ops/agent_setup.md) for one-click environment setup. Windows users may use the optional Silhouette Launcher GUI.

---

## Quick start (TL;DR)

```bat
cd C:\path\to\repo\Silhouette
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install --upgrade pip
pip install -e .[validate]

:: clean any stale outputs
del /Q out\fhir\ndjson\*.ndjson

:: translate (use MapSpec under maps/, not legacy profiles/)
silhouette fhir translate --in "tests\data\hl7\adt_a01.hl7" --map "maps\adt_uscore.yaml" --out out --message-mode

:: validate (local)
silhouette fhir validate --in-dir out\fhir\ndjson
```

Expected:

```
Preparing to validate N file(s).
Validation summary: N passed, 0 failed.
```

---

## 1) Environment setup

### Create & activate a virtual environment

* **CMD (Windows)**

  ```bat
  cd C:\path\to\repo\Silhouette
  python -m venv .venv
  .\.venv\Scripts\activate.bat
  ```
* **PowerShell**

  ```powershell
  cd C:\path\to\repo\Silhouette
  .\.venv\Scripts\Activate.ps1
  # If policy blocks activation:
  # Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
  ```
* **macOS/Linux**

  ```bash
  cd /path/to/repo/Silhouette
  python3 -m venv .venv
  source .venv/bin/activate
  ```

Verify you’re inside the venv:

```bat
where python
where pip
where silhouette
```

Paths should resolve under `...\Silhouette\.venv\Scripts\...`.

### Install package (editable) + validator extras

```bat
pip install --upgrade pip
pip install -e .[validate]
```

This pulls in `jsonschema`, `pydantic` (v2), `fhir.resources` (v7+), etc.

Sanity:

```bat
silhouette --version
silhouette fhir validate -h
python -c "import jsonschema, pydantic, fhir.resources, requests, yaml; print('deps OK')"
```

### Reinstall after changes

Most code edits are picked up automatically with `-e .`. Reinstall if you changed **entry points** or **dependencies**:

```bat
pip install -e .[validate]
```

### Hard reset the venv (when in doubt)

```bat
deactivate  2> NUL
rmdir /S /Q .venv
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install --upgrade pip
pip install -e .[validate]
```

---

## 2) Configuration

* Default settings live in `config/` – copy and adjust for your environment.
* Set `FHIR_TOKEN` for authenticated servers; leave unset for public sandboxes.
* Package cache: ensure `.fhir/packages` is writable so HAPI can reuse IGs.

> **Map files:** The pipeline expects **MapSpec** format under `maps/*.yaml`
> (keys: `messageTypes`, `resourcePlan: [ {resource, profile?, rules: [...] } ]`).
> Do **not** pass legacy `profiles/*` maps to `--map`.

---

## 3) Translate → Validate workflow

### Clear old outputs (avoid stale files)

```bat
del /Q out\fhir\ndjson\*.ndjson
```

### Translate

```bat
silhouette fhir translate --in "tests\data\hl7\adt_a01.hl7" --map "maps\adt_uscore.yaml" --out out --message-mode
```

* Use a MapSpec from `maps/…yaml`, not `profiles/…`.
* `--message-mode` creates a FHIR message bundle flavor; optional.

### Validate (local)

```bat
silhouette fhir validate --in-dir out\fhir\ndjson
```

* **PowerShell glob tip:** If you use `--in 'out\fhir\ndjson\*.ndjson'`, **quote** the glob so PowerShell doesn’t expand `*` early.
* `--fail-fast` will stop on the first invalid resource.

### Validate (HAPI, optional)

Run HAPI locally:

```bat
docker run -p 8080:8080 hapiproject/hapi:latest
```

Then:

```bat
silhouette fhir validate --in-dir out\fhir\ndjson --hapi --server http://localhost:8080/fhir
```

---

## 4) Posting modes

* **Dry run** (`--dry-run`): generate artifacts and metrics without hitting a server.
* **Post**: provide `--server <URL>` and optional `--token` to upsert resources.
* Conditional upserts are preserved for Patient/Encounter when identifiers exist.

---

## 5) Validator usage

* **Local** (preferred during dev):

  ```bat
  silhouette fhir validate --in-dir out\fhir\ndjson
  ```

  PowerShell alternative with glob:

  ```powershell
  silhouette fhir validate --in 'out\fhir\ndjson\*.ndjson'
  ```
* **Server**: add `--hapi` and (optionally) call `$validate` before posting:

  ```bat
  silhouette fhir validate --in-dir out\fhir\ndjson --hapi --server http://localhost:8080/fhir
  ```
* HAPI versions and IGs are pinned in `config/fhir_target.yaml`.

---

## 6) tx-miss triage

`tx-miss` counts unresolved terminology or mapping gaps.

1. Inspect `out/qa/metrics.csv` for non-zero `txMisses`.
2. Review logs for the specific segments and update terminology tables or maps.

---

## 7) Dead-letter handling

Failed validations or posts write request/response pairs under `out/deadletter/`.

* `<messageId>_request.json` – the bundle that failed.
* `<messageId>_response.json` – server or validator error details.

After fixes, rerun the pipeline; successful posts remove previous dead letters.

---

## 8) Troubleshooting (fast answers)

| Symptom / Error                                                          | What it means                                                           | Fix                                                                                        |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `ModuleNotFoundError: requests / jsonschema / pydantic / fhir.resources` | Missing deps in venv                                                    | `pip install -e .[validate]`                                                               |
| `ModuleNotFoundError: validators` (import inside CLI)                    | Package not installed to current venv                                   | Activate venv; `pip install -e .[validate]`                                                |
| `unexpected extra arguments (... .ndjson)`                               | PowerShell expanded `*` before Click parsed                             | Quote the glob in PS (`'out\fhir\ndjson\*.ndjson'`) or use `--in-dir`                      |
| Translate only writes `Device` and `Provenance`                          | You passed a **legacy** map (profiles\*) or rules didn’t match message | Use a MapSpec under `maps/*.yaml` that includes your message type and rules                |
| `Encounter.class … Input should be a valid dict`                         | Your installed models expect `class` as an object                     | Ensure map writes to `class` (Coding object) or regenerate outputs; stale files will keep failing |
| `Provenance.agent[0].who: Field required`                                | Missing actor for Provenance                                            | Re-translate (pipeline adds a fallback Device actor) or patch NDJSON in place              |

**NDJSON in-place patcher (optional)**

```python
# fix_fhir_ndjson_shapes.py
import sys, json
from pathlib import Path
def fix_file(p, ref="Device/silhouette-translator"):
    out, n = [], 0
    for s in p.read_text(encoding="utf-8").splitlines():
        if not s.strip(): continue
        o = json.loads(s)
        if o.get("resourceType")=="Encounter" and isinstance(o.get("class"), list):
            o["class"]=o["class"][0]; n+=1
        if o.get("resourceType")=="Provenance":
            agents=o.get("agent")
            if not isinstance(agents,list) or not agents:
                o["agent"]=[{"who":{"reference":ref}}]; n+=1
            elif "who" not in agents[0]:
                agents[0]["who"]={"reference":ref}; n+=1
        out.append(json.dumps(o,separators=(",",":")))
    p.write_text("\n".join(out)+"\n", encoding="utf-8"); return n
def main():
    d=Path(sys.argv[1]); total=0
    for f in d.glob("*.ndjson"): total+=fix_file(f)
    print(f"Patched items: {total}")
if __name__=="__main__": main()
```

Run:

```bat
python fix_fhir_ndjson_shapes.py out\fhir\ndjson
silhouette fhir validate --in-dir out\fhir\ndjson
```

---

## 9) PowerShell notes

* Use **single quotes** around globs:

  ```powershell
  silhouette fhir validate --in 'out\fhir\ndjson\*.ndjson'
  ```
* Line breaks use backticks:

  ```powershell
  silhouette fhir translate `
    --in "tests\data\hl7\adt_a01.hl7" `
    --map "maps\adt_uscore.yaml" `
    --out out `
    --message-mode
  ```

---

## 10) “All green” checklist

* `silhouette --version` prints a version (e.g., `0.25.0`)
* `pip install -e .[validate]` completes without error
* Old NDJSON cleared (`del /Q out\fhir\ndjson\*.ndjson`) before re-translate
* Translate uses a **MapSpec** in `maps/*.yaml`
* Validate ends with `Validation summary: N passed, 0 failed`
* Optional: HAPI `$validate` also succeeds if server is running

---
