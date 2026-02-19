"""
Mendeleev adapter for element properties and dopant radius hints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..base import ToolAdapter, ToolContext, ToolParameter, ToolResult, ToolSpec


DEFAULT_PROPERTIES = [
    "atomic_number",
    "atomic_weight",
    "electronegativity",
    "atomic_radius",
    "covalent_radius",
    "vdw_radius",
]


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if callable(value):
        return None
    if isinstance(value, dict):
        return {str(k): _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(v) for v in value]
    as_float = _as_float(value)
    if as_float is not None:
        return as_float
    return str(value)


def _get_property(element: Any, name: str) -> Any:
    if not hasattr(element, name):
        return None
    value = getattr(element, name)
    return _serialize_value(value)


def _radius_hint(base_radius: Optional[float], dopant_radius: Optional[float]) -> Optional[Dict[str, Any]]:
    if base_radius is None or dopant_radius is None:
        return None
    diff = abs(dopant_radius - base_radius)
    pct = None
    if base_radius != 0:
        pct = diff / base_radius * 100.0
    hint = "unknown"
    if pct is not None:
        if pct <= 5:
            hint = "low mismatch"
        elif pct <= 15:
            hint = "moderate mismatch"
        else:
            hint = "high mismatch"
    return {
        "radius_difference": diff,
        "radius_difference_pct": pct,
        "hint": hint,
    }


class MendeleevAdapter(ToolAdapter):
    spec = ToolSpec(
        id="mendeleev_props",
        name="Element Properties",
        version="1.0",
        description="Query element properties and dopant radius mismatch.",
        input_types=["any"],
        parameters=[
            ToolParameter("element", "string", True, None, "Base element symbol (e.g., Fe)"),
            ToolParameter("dopant", "string", False, None, "Dopant element symbol"),
            ToolParameter("radius_type", "string", False, "atomic_radius", "Radius attribute name"),
            ToolParameter("properties", "array", False, None, "Optional list of properties to return"),
        ],
        outputs=["properties", "dopant_hint"],
    )

    def run(self, context: ToolContext) -> ToolResult:
        params = context.parameters or {}
        element_symbol = params.get("element")
        if not element_symbol:
            return ToolResult(status="failed", error="element is required")

        try:
            from mendeleev import element as get_element
        except ImportError as exc:
            return ToolResult(status="failed", error=f"mendeleev not available: {exc}")

        dopant_symbol = params.get("dopant")
        radius_type = params.get("radius_type", "atomic_radius")

        try:
            base_element = get_element(element_symbol)
        except Exception as exc:
            return ToolResult(status="failed", error=f"Unknown element: {exc}")

        prop_names = params.get("properties") or DEFAULT_PROPERTIES
        properties: Dict[str, Any] = {name: _get_property(base_element, name) for name in prop_names}

        dopant_hint = None
        if dopant_symbol:
            try:
                dopant_element = get_element(dopant_symbol)
            except Exception as exc:
                return ToolResult(status="failed", error=f"Unknown dopant element: {exc}")

            base_radius = _as_float(_get_property(base_element, radius_type))
            dopant_radius = _as_float(_get_property(dopant_element, radius_type))
            dopant_hint = _radius_hint(base_radius, dopant_radius)
            if dopant_hint:
                dopant_hint["radius_type"] = radius_type
                dopant_hint["base_element"] = element_symbol
                dopant_hint["dopant_element"] = dopant_symbol

        output = {
            "element": element_symbol,
            "properties": properties,
            "dopant_hint": dopant_hint,
        }

        annotations = [
            {
                "analysis": "element_properties",
                "element": element_symbol,
                "properties": properties,
                "dopant_hint": dopant_hint,
            }
        ]
        conclusion = f"Element properties retrieved for {element_symbol}"

        return ToolResult(status="completed", output=output, annotations=annotations, conclusion=conclusion)
