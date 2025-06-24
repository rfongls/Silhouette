# Silhouette Core CLI Usage

Interactive commands and flags:

- `:help`  
  Show help message.

- `:replay`  
  Parse `logs/session_*.txt` into `memory.jsonl`.

- `:selfcheck [--strict]`  
  Verify required files (`persona.dsl`, `memory.jsonl`).  
  `--strict` exits with error on issues.

- `:backup`  
  Export full system state via `export_state()`.

- `:exit` / `:quit`  
  Exit the CLI.

**Global flags (when launching):**

```bash
python -m cli.main [--no-repl]
```

- `--no-repl`: skip interactive mode and exit immediately.

**Offline / Safe Mode**

- If `SILHOUETTE_OFFLINE=1` or missing files, CLI starts in SAFE MODE:
  - Prints `[SAFE MODE] Offline detected: throttling modules, no network calls.`
  - Decorated network calls enforce min-interval delays.
