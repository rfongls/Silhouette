from silhouette_core.tools import safe_calc


def main(command: str) -> str:
    """Evaluate a basic arithmetic expression."""
    if " " in command:
        expr = command.split(" ", 1)[1]
    else:
        return "No expression provided."
    out = safe_calc(expr)
    if out.startswith("[tool:calc] error"):
        return f"Error evaluating expression: {out.split(': ',1)[1]}"
    return f"Result: {out}"
