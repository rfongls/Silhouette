# Stage 1 Codex Handoff

This document contains the seed examples for the reasoning module along with the prompt used to expand the dataset. It also describes how to run the Codex controller and validate the outputs.

## Seed Entries (stage1_sample.jsonl)
```jsonl
{"prompt": "Explain the Pythagorean theorem", "completion": "The Pythagorean theorem states that for any right triangle, the square of the hypotenuse equals the sum of the squares of the other two sides."}
{"prompt": "List the first five prime numbers", "completion": "2, 3, 5, 7, 11"}
{"prompt": "Convert 37 degrees Celsius to Fahrenheit", "completion": "98.6"}
{"prompt": "What is the factorial of 5?", "completion": "120"}
{"prompt": "Simplify the expression (x^2 - 9)/(x - 3)", "completion": "x + 3"}
```

## Expansion Prompt
Use the following prompt with OpenAI or your local Codex controller to generate entries #6 through #500:

```
Continue the JSONL dataset with numbered reasoning problems and short factual answers. Keep responses concise and deterministic.
```

## CLI Example
```bash
python -m silhouette_core.codex_controller --input training_data/reasoner/stage1_sample.jsonl --output training_data/reasoner/stage1_full.jsonl --count 500
```

## Post-processing
1. Remove any duplicate prompts.
2. Ensure JSONL formatting is valid.
3. Run the tests:
   ```bash
   pytest tests
   ```
