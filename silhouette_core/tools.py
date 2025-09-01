import ast
import importlib
import operator as op
import pathlib
from collections.abc import Callable
from typing import Any

import yaml


class ToolRegistry:
    """
    Tiny tool API to prove 'agent can act'.
    Provides a minimal registry with an echo tool and a safe arithmetic
    calculator implemented via Python's AST module.
    """
    def __init__(self):
        self._tools: dict[str, Callable[[str], Any]] = {}
        self.register("echo", lambda s: s)
        self.register("calc", safe_calc)

    def register(self, name: str, fn: Callable[[str], Any]):
        self._tools[name] = fn

    def invoke(self, name: str, arg: str) -> Any:
        if name not in self._tools:
            return f"[tool:{name}] not found"
        try:
            return self._tools[name](arg)
        except Exception as e:
            return f"[tool:{name}] error: {e}"

    def load_skills_from_registry(self, path: str = "silhouette_core/skills/registry.yaml") -> None:
        p = pathlib.Path(path)
        if not p.exists():
            return
        reg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for skill in reg.get("skills", []):
            if not skill.get("enabled", True):
                continue
            name = skill.get("name")
            entry = skill.get("entry", "tool")
            version = skill.get("version")
            mod_path = skill.get("module")
            if not mod_path:
                if version:
                    mod_path = f"silhouette_core.skills.{name}.{version}.wrapper"
                else:
                    mod_path = f"silhouette_core.skills.{name}.wrapper"

            if not (mod_path and name):
                continue
            try:
                mod = importlib.import_module(mod_path)
                fn = getattr(mod, entry)
                public_name = f"{name}@{version}" if version else name
                self.register(public_name, fn)

            except Exception:
                continue


# ---------- Safe calculator implementation ----------
_ALLOWED_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow,
    ast.UAdd: op.pos, ast.USub: op.neg,
}


def _eval_ast(node):
    if isinstance(node, ast.Constant) and isinstance(
        getattr(node, "value", None), int | float | complex
    ):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_ast(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    raise ValueError("operator not allowed")


def safe_calc(expr: str) -> str:
    expr = expr.strip()
    if len(expr) > 200:
        return "[tool:calc] error: expression too long"
    try:
        tree = ast.parse(expr, mode="eval")
        val = _eval_ast(tree.body)
        return str(val)
    except Exception as e:
        return f"[tool:calc] error: {e}"
