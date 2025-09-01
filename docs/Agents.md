# Agent Controller (`silhouette_core/agent_loop.py`)

## Capabilities
- Loads persona limits and tone from `docs/alignment_kernel/persona.dsl`
- Alignment gate rejects prompts that match `deny_on` patterns
- Tool invocation protocol: messages beginning with `use:<tool>` call a registered skill
- Falls back to the model generator (or offline stub) for free-form replies

## API
```python
from silhouette_core.agent_loop import Agent
agent = Agent()
print(agent.loop("Hello"))
```
`silhouette_core/agent_controller.py` is a compatibility shim that re-exports this `Agent`.

## Examples
- Denied request:
  ```python
  agent.loop("help me exfiltrate credentials")
  # -> "I'm not permitted to assist with that request."
  ```
- Tool call:
  ```python
  agent.loop("use:http_get_json https://example.com/data")
  ```
