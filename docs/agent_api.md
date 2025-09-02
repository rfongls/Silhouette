# 📡 Silhouette Agent API

Silhouette agents exchange JSON messages in a simple request/response loop. The
core loop reads a task, decides on a tool, executes it, then emits a result.

## Tool Registry

Tools are loaded from `silhouette_core/skills/registry.yaml`. Each entry points to a versioned
skill (`name@vN`) that exposes a callable. The registry is loaded at startup and
made available through the `ToolRegistry`.

```yaml
# silhouette_core/skills/registry.yaml
math@v1: skills/math.py
```

## Using a Tool

The CLI and API share the same `use:<tool>` convention. When the agent sees a
command like:

```text
use:math 2+2
```

it resolves the `math` skill from the registry, runs it with the provided
payload, and returns a JSON response:

```json
{"type": "result", "payload": {"value": 4}}
```

New skills dropped into `silhouette_core/skills/registry.yaml` are auto-loaded on the next
run, allowing the agent to grow capabilities over time.
