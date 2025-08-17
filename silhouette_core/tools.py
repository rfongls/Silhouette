from typing import Callable, Dict, Any

class ToolRegistry:
    """
    Tiny tool API to prove 'agent can act'.
    NOTE: 'calc' uses eval() for demo purposes; replace with a safe evaluator in Phase 2.
    """
    def __init__(self):
        self._tools: Dict[str, Callable[[str], Any]] = {}
        self.register("echo", lambda s: s)
        self.register("calc", lambda s: eval(s, {"__builtins__": {}}, {}))  # demo only

    def register(self, name: str, fn: Callable[[str], Any]):
        self._tools[name] = fn

    def invoke(self, name: str, arg: str) -> Any:
        if name not in self._tools:
            return f"[tool:{name}] not found"
        try:
            return self._tools[name](arg)
        except Exception as e:
            return f"[tool:{name}] error: {e}"
