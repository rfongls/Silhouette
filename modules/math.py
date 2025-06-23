def main(command: str) -> str:
    """Evaluate a basic arithmetic expression."""
    if " " in command:
        expr = command.split(" ", 1)[1]
    else:
        return "No expression provided."
    try:
        result = eval(expr, {"__builtins__": {}})
        return f"Result: {result}"
    except Exception as e:
        return f"Error evaluating expression: {e}"
