# Offline Mode (`offline_mode.py`)

- Safe-mode execution and throttling helpers.

## Configuration
- Set `SILHOUETTE_OFFLINE=1` to force offline mode.
- Offline mode also triggers if `persona.dsl` or `memory.jsonl` are missing.

## Decorators
### `throttle(min_interval)`
Delay function calls to respect a minimum interval when offline.
```python
from offline_mode import throttle

@throttle(0.5)
def fetch():
    ...
```

### `load_throttle(threshold, interval)`
Adds a delay when CPU load exceeds `threshold`.
```python
from offline_mode import load_throttle

@load_throttle(threshold=0.8, interval=1.0)
def heavy_task():
    ...
```

## Examples
```python
import offline_mode
if offline_mode.is_offline():
    print("Running in offline safe-mode")
```
