# CONSTRAINTS.md

This guide explains how Silhouette Core can run under constrained system environments and adapt to available resources.

---

## 🧠 Memory & Resource Tiers

| Tier        | Description                           | Limits                         |
|-------------|---------------------------------------|--------------------------------|
| Minimal     | CLI-only, no API, low-memory logs     | <= 1 GB RAM, CPU < 2 cores     |
| Moderate    | FastAPI + memory core + DSL           | 2–4 GB RAM, 2–4 cores          |
| Full Node   | All modules active, scalable workers  | 8+ GB RAM, multi-core server   |

---

## ⚙️ System Detection

Use Python's `psutil` or `os` to detect:

- Available memory
- CPU count
- Disk I/O throughput

Adaptively disable modules:
```python
if low_memory():
    disable_module("tone_parser")
```

---

## 📦 Deployment Adjustments

- Memory files flushed regularly
- Logs rotated or compressed
- Tone engine becomes optional

---

## 🌐 CLI vs API Modes

| Mode | Benefits                    | When to Use             |
|------|-----------------------------|--------------------------|
| CLI  | Resilient, offline, minimal | Edge and fallback usage |
| API  | Scalable, accessible        | Web or integrated use   |
