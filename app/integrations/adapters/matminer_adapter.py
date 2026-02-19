"""
Matminer adapter for composition features and dopant hints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..base import ToolAdapter, ToolContext, ToolParameter, ToolResult, ToolSpec


def _try_radius_hint(base_element: str, dopant_element: str, radius_type: str) -> Optional[Dict[str, Any]]:
    try:
        from mendeleev import element as get_element
    except ImportError:
        return None

    try:
        base = get_element(base_element)
        dopant = get_element(dopant_element)
    except Exception:
        return None

    base_radius = getattr(base, radius_type, None)
    dopant_radius = getattr(dopant, radius_type, None)
    if base_radius is None or dopant_radius is None:
        return None

    diff = abs(float(dopant_radius) - float(base_radius))
    pct = diff / float(base_radius) * 100.0 if float(base_radius) != 0 else None
    hint = "unknown"
    if pct is not None:
        if pct <= 5:
            hint = "low mismatch"
        elif pct <= 15:
            hint = "moderate mismatch"
        else:
            hint = "high mismatch"
    return {
        "base_element": base_element,
        "dopant_element": dopant_element,
        "radius_type": radius_type,
        "radius_difference": diff,
        "radius_difference_pct": pct,
        "hint": hint,
    }


class MatminerAdapter(ToolAdapter):
    spec = ToolSpec(
        id="matminer_features",
        name="Matminer Features",
        version="1.0",
        description="Generate composition features and optional dopant hints.",
        input_types=["metadata", "cif", "txt"],
        parameters=[
            ToolParameter("composition", "string", True, None, "Composition string (e.g., LiFePO4)"),
            ToolParameter("feature_set", "string", False, "magpie", "Matminer preset"),
            ToolParameter("base_element", "string", False, None, "Base element for dopant hint"),
            ToolParameter("dopant_element", "string", False, None, "Dopant element for hint"),
            ToolParameter("radius_type", "string", False, "atomic_radius", "Radius attribute name"),
        ],
        outputs=["features", "dopant_hint"],
    )

    def run(self, context: ToolContext) -> ToolResult:
        params = context.parameters or {}
        composition_str = params.get("composition")
        if not composition_str:
            return ToolResult(status="failed", error="composition is required")

        try:
            from pymatgen.core import Composition
        except ImportError as exc:
            return ToolResult(status="failed", error=f"pymatgen not available: {exc}")

        try:
            from matminer.featurizers.composition import ElementProperty
        except ImportError as exc:
            return ToolResult(status="failed", error=f"matminer not available: {exc}")

        feature_set = params.get("feature_set", "magpie")

        try:
            composition = Composition(composition_str)
            featurizer = ElementProperty.from_preset(feature_set)
        except Exception as exc:
            return ToolResult(status="failed", error=f"Failed to initialize features: {exc}")

        try:
            feature_values = featurizer.featurize(composition)
            feature_labels = featurizer.feature_labels()
        except Exception as exc:
            return ToolResult(status="failed", error=f"Failed to featurize composition: {exc}")

        features = {label: float(value) for label, value in zip(feature_labels, feature_values)}

        base_element = params.get("base_element")
        dopant_element = params.get("dopant_element")
        radius_type = params.get("radius_type", "atomic_radius")
        dopant_hint = None
        if base_element and dopant_element:
            dopant_hint = _try_radius_hint(base_element, dopant_element, radius_type)

        output = {
            "composition": composition_str,
            "features": features,
            "dopant_hint": dopant_hint,
        }
        annotations = [
            {
                "analysis": "matminer_features",
                "composition": composition_str,
                "feature_set": feature_set,
                "dopant_hint": dopant_hint,
            }
        ]
        conclusion = f"Matminer features generated for {composition_str}"

        return ToolResult(status="completed", output=output, annotations=annotations, conclusion=conclusion)
