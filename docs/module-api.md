# MODULE_API.md

Silhouette Core supports dynamic modules composed of two parts:

1. A JSON file describing module metadata and inputs
2. A Python file implementing the logic

---

## 🔧 JSON Structure (Example: `math.json`)

```json
{
  "name": "MathModule",
  "description": "Performs basic arithmetic operations",
  "inputs": ["operation", "a", "b"],
  "entrypoint": "math.run"
}
```

- `name`: Human-friendly module name
- `description`: Used for introspection and help
- `inputs`: Expected keys in the user payload
- `entrypoint`: Python path to callable function

---

## 🧪 Python Implementation (`math.py`)

```python
def run(data):
    op = data.get("operation")
    a = data.get("a")
    b = data.get("b")
    if op == "add":
        return a + b
    elif op == "subtract":
        return a - b
    else:
        return "Unsupported operation"
```

---

## 🧬 Guidelines

- Always define a `run()` method or handler function
- Validate inputs gracefully
- Keep logic stateless unless needed

---

## 🔄 Hot Reload Support

To reload modules at runtime:

```text
> :reload
```

To list loaded modules:

```text
> :modules
```

Ensure your `.json` and `.py` file pairs share the same base name and are located under `modules/`.
