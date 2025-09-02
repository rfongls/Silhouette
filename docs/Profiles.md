# Profiles (`profiles/`)

Policy YAMLs controlling behavior, safety, and routing.

## Structure
Example `profiles/core/policy.yaml`:
```yaml
name: core
allowed_tools:
  - echo
  - calc

tone:
  style: neutral

deny_rules_ref: docs/alignment_kernel/persona.dsl

latency_budget_ms: 3000
max_new_tokens: 256
required_skills:
  - http_get_json@v1

research_mode:
  require_citations: true
  note: "For non-obvious claims, retrieve first and include [n]-style citations."
```
Key fields:
- `allowed_tools` – built-in tools permitted for the agent
- `tone.style` – default response style
- `deny_rules_ref` – path to persona DSL defining `deny_on` patterns
- `latency_budget_ms` / `max_new_tokens` – runtime guidance
- `required_skills` – skills that must exist at startup
- `research_mode` – citation policy and notes
