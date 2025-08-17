# Training Data (Core Seed)

Small, domain-agnostic seed set to exercise:
- Plain Q&A
- Tool-use prompts (`use:echo`, `use:calc`)
- Alignment refusals (deny_on patterns)

`teacher_outputs.jsonl` provides a line-aligned set of teacher responses for
knowledge distillation experiments.

## Format (JSONL)
Each line is a JSON object:
```json
{"instruction":"...", "input":"...", "output":"...", "tools_used":["calc"]}
```

* `instruction`: required (string)
* `input`: required (string; may be empty)
* `output` or `teacher_output`: required (string)
* `tools_used`: optional (array of tool names used to produce the output)

## Provenance

Synthetic authoring for internal testing.

## License

CC BY 4.0 for the text content in this folder.

## PII

None intended; keep it that way. If you add data, ensure no sensitive info.

