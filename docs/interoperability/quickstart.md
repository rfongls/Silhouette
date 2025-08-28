# Interoperability Quickstart

Validate clinical payloads end-to-end using bundled validators and profiles.

```python
from skills.interoperability import InteropSkill

skill = InteropSkill()
result = skill.validate(payload, "hl7")
print(result)
```

See [validators](../../validators/) for supported formats and
[overview](./overview.md) for flow diagrams.
