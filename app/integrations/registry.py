"""
Registry for integration adapters.
"""

from typing import Dict, List

from .base import ToolAdapter, ToolSpec


_ADAPTERS: Dict[str, ToolAdapter] = {}


def register_adapter(adapter: ToolAdapter) -> None:
    tool_id = adapter.spec.id
    if tool_id in _ADAPTERS:
        existing = _ADAPTERS[tool_id]
        if type(existing) is type(adapter):
            return
        raise ValueError(f"Adapter already registered: {tool_id}")
    _ADAPTERS[tool_id] = adapter


def get_adapter(tool_id: str) -> ToolAdapter:
    adapter = _ADAPTERS.get(tool_id)
    if not adapter:
        raise KeyError(f"Unknown tool_id: {tool_id}")
    return adapter


def list_specs() -> List[ToolSpec]:
    return [adapter.spec for adapter in _ADAPTERS.values()]
