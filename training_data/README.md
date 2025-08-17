# Training Data (Core Seed)

Small, domain-agnostic seed set to exercise:
- Plain Q&A
- Tool-use prompts (`use:echo`, `use:calc`)
- Alignment refusals (deny_on patterns)

## Format (JSONL)
Each line is a JSON object:
```json
{"instruction":"...", "input":"...", "output":"...", "tools_used":["calc"]}
```

* `instruction`: required (string)
* `input`: required (string; may be empty)
* `output`: required (string)
* `tools_used`: optional (array of tool names used to produce the output)

## Provenance

Synthetic authoring for internal testing.

## License

CC BY 4.0 for the text content in this folder.

## PII

None intended; keep it that way. If you add data, ensure no sensitive info.

