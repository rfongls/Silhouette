# RECOVERY.md

This guide explains how to recover or rebuild Silhouette Core after system failure, data loss, or degraded environments.

---

## 🧱 Core Recovery Strategy

Silhouette Core is designed with fallback-first architecture:

- ✅ Logs contain all user interactions (`logs/`)
- ✅ Memory uses append-only JSONL (`logs/memory.jsonl`)
- ✅ Modules are JSON+Python pairs (in `modules/`)
- ✅ Alignment DSL is loaded dynamically and reloadable (`:reload`)

---

## 🔁 Recovery from Logs Only

1. **Find the latest log in `logs/`**

```bash
ls -lt logs/
```

2. **Replay key actions manually via CLI**

```bash
python cli/main.py
> :reload
> :modules
```

3. **Restore memory manually (optional)**

```bash
cp logs/memory_backup.jsonl logs/memory.jsonl
```

---

## 🧠 Rebuilding Memory

If memory is lost, extract historical entries from logs:

```bash
grep -i 'memory' logs/session-*.txt > recovered.txt
# Manually review and append to memory.jsonl
```

---

## 🔧 Regenerating Modules

If `modules/` is corrupted:

- Reference your Git repo or backups
- JSON files describe the DSL API contract
- Python files must implement `run(data: dict)` or equivalent

---

## 🔗 Recreating CI/Testing

If CI configs are lost:

1. Recreate `.github/workflows/ci.yml`
2. Reinstall dependencies and run:

```bash
ruff .
pytest -q
```

---

## 💡 Offline Recovery Summary

| Component | Recovery Source |
|----------|------------------|
| CLI & Modules | `main.py`, `module_loader.py`, `modules/` |
| Memory | `logs/memory.jsonl`, transcripts |
| API Server | `interface_server.py` |
| Test Suite | `tests/` |
