"""Auto-generates each tool's JSON schema from its function signature/docstring, so the
system prompt in loop.py never needs a hand-written schema per tool. Adding a tool means
writing the function and decorating it -- nothing else."""

import inspect
from typing import Callable

TOOLS = {}


def register(name: str = None, description: str = None):
    def decorator(fn: Callable):
        tool_name = name or fn.__name__
        sig = inspect.signature(fn)
        schema = {}
        for pname, param in sig.parameters.items():
            annotation = param.annotation
            type_name = (
                getattr(annotation, "__name__", "any")
                if annotation is not inspect.Parameter.empty
                else "any"
            )
            schema[pname] = type_name
        TOOLS[tool_name] = {
            "fn": fn,
            "description": description or (fn.__doc__ or "").strip().split("\n")[0],
            "schema": schema,
        }
        return fn
    return decorator


def get_tools() -> dict:
    return TOOLS
