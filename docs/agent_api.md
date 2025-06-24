# 📡 Silhouette Agent API

Agents communicate using JSON messages. Each message contains a `type` and optional `payload` field.

Example:

```json
{
  "type": "invoke",
  "payload": {"module": "Weather", "args": [], "kwargs": {}}
}
```

Responses follow a similar structure:

```json
{
  "type": "result",
  "payload": {"value": "sunny"}
}
```

Actual transport (WebSockets, HTTP, etc.) is left to the host environment.
