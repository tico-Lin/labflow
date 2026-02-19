"""
XRD matching adapter using COD/MP references and pymatgen XRD calculator.
"""

from __future__ import annotations

import io
import os
from typing import Any, Dict, List, Optional, Tuple

from ..base import ToolAdapter, ToolContext, ToolParameter, ToolResult, ToolSpec


class XrdMatchAdapter(ToolAdapter):
    spec = ToolSpec(
        id="xrd_match",
        name="XRD Standard Match",
        version="1.0",
        description="Match measured XRD peaks to a reference pattern.",
        input_types=["xrd", "csv", "txt"],
        parameters=[
            ToolParameter("reference_cif_text", "string", False, None, "Reference CIF text"),
            ToolParameter("reference_cif_path", "string", False, None, "Reference CIF path"),
            ToolParameter("cod_id", "string", False, None, "Crystallography Open Database ID"),
            ToolParameter("mp_id", "string", False, None, "Materials Project ID"),
            ToolParameter("mp_api_key", "string", False, None, "Materials Project API key"),
            ToolParameter("two_theta_col", "string", False, "2theta", "Measured 2theta column"),
            ToolParameter("intensity_col", "string", False, "intensity", "Measured intensity column"),
            ToolParameter("peak_count", "integer", False, 20, "Number of peaks to match"),
            ToolParameter("tolerance", "number", False, 0.2, "Peak match tolerance (deg)"),
            ToolParameter("wavelength", "string", False, "CuKa", "XRD wavelength"),
        ],
        outputs=["match_score", "reference_formula", "matched_peaks"],
    )

    def run(self, context: ToolContext) -> ToolResult:
        if not context.file_bytes:
            return ToolResult(status="failed", error="Missing file bytes")

        params = context.parameters or {}
        reference = self._load_reference_structure(params)
        if isinstance(reference, ToolResult):
            return reference
        structure = reference

        try:
            import numpy as np
            import pandas as pd
        except ImportError as exc:
            return ToolResult(status="failed", error=f"numpy/pandas not available: {exc}")

        two_theta_col = params.get("two_theta_col", "2theta")
        intensity_col = params.get("intensity_col", "intensity")
        peak_count = int(params.get("peak_count", 20))
        tolerance = float(params.get("tolerance", 0.2))

        try:
            text = context.file_bytes.decode("utf-8", errors="replace")
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
        except Exception as exc:
            return ToolResult(status="failed", error=f"Failed to parse XRD data: {exc}")

        col_map = {c.lower(): c for c in df.columns}
        two_theta_col = col_map.get(str(two_theta_col).lower(), two_theta_col)
        intensity_col = col_map.get(str(intensity_col).lower(), intensity_col)

        if two_theta_col not in df.columns or intensity_col not in df.columns:
            return ToolResult(status="failed", error="Required columns not found")

        two_theta = df[two_theta_col].to_numpy(dtype=float)
        intensity = df[intensity_col].to_numpy(dtype=float)

        if len(two_theta) == 0:
            return ToolResult(status="failed", error="No peaks provided")

        top_indices = np.argsort(intensity)[-peak_count:]
        measured_peaks = list(zip(two_theta[top_indices], intensity[top_indices]))
        measured_peaks.sort(key=lambda x: x[0])

        try:
            from pymatgen.analysis.diffraction.xrd import XRDCalculator
        except ImportError as exc:
            return ToolResult(status="failed", error=f"pymatgen not available: {exc}")

        wavelength = params.get("wavelength", "CuKa")
        calculator = XRDCalculator(wavelength=wavelength)
        pattern = calculator.get_pattern(structure)
        reference_peaks = list(zip(pattern.x, pattern.y))

        matches, match_score = self._match_peaks(measured_peaks, reference_peaks, tolerance)

        output = {
            "match_score": match_score,
            "matched_peaks": matches,
            "reference_formula": structure.composition.reduced_formula,
            "reference_peaks": [
                {"two_theta": float(tth), "intensity": float(intensity)}
                for tth, intensity in reference_peaks
            ],
        }

        annotations = [
            {
                "analysis": "xrd_match",
                "match_score": match_score,
                "reference_formula": output["reference_formula"],
                "matched_peaks": matches,
            }
        ]
        conclusion = f"XRD match score: {match_score:.3f}"

        return ToolResult(status="completed", output=output, annotations=annotations, conclusion=conclusion)

    def _load_reference_structure(self, params: Dict[str, Any]) -> ToolResult | Any:
        reference_cif_text = params.get("reference_cif_text")
        reference_cif_path = params.get("reference_cif_path")
        cod_id = params.get("cod_id")
        mp_id = params.get("mp_id")
        mp_api_key = params.get("mp_api_key") or os.getenv("MP_API_KEY")

        if not any([reference_cif_text, reference_cif_path, cod_id, mp_id]):
            return ToolResult(status="failed", error="Reference CIF or COD/MP ID is required")

        try:
            from pymatgen.core import Structure
        except ImportError as exc:
            return ToolResult(status="failed", error=f"pymatgen not available: {exc}")

        if reference_cif_text:
            try:
                return Structure.from_str(reference_cif_text, fmt="cif")
            except Exception as exc:
                return ToolResult(status="failed", error=f"Invalid reference CIF: {exc}")

        if reference_cif_path:
            if not os.path.exists(reference_cif_path):
                return ToolResult(status="failed", error="reference_cif_path not found")
            try:
                with open(reference_cif_path, "r", encoding="utf-8") as handle:
                    return Structure.from_str(handle.read(), fmt="cif")
            except Exception as exc:
                return ToolResult(status="failed", error=f"Invalid reference CIF: {exc}")

        if cod_id:
            try:
                import requests
            except ImportError as exc:
                return ToolResult(status="failed", error=f"requests not available: {exc}")
            url = f"https://www.crystallography.net/cod/{cod_id}.cif"
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return Structure.from_str(response.text, fmt="cif")
            except Exception as exc:
                return ToolResult(status="failed", error=f"Failed to fetch COD CIF: {exc}")

        if mp_id:
            if not mp_api_key:
                return ToolResult(status="failed", error="mp_api_key is required for MP queries")
            try:
                from mp_api.client import MPRester
            except ImportError as exc:
                return ToolResult(status="failed", error=f"mp-api not available: {exc}")
            try:
                with MPRester(mp_api_key) as mpr:
                    if hasattr(mpr, "get_structure_by_material_id"):
                        return mpr.get_structure_by_material_id(mp_id)
                    if hasattr(mpr, "materials") and hasattr(mpr.materials, "get_structure_by_material_id"):
                        return mpr.materials.get_structure_by_material_id(mp_id)
            except Exception as exc:
                return ToolResult(status="failed", error=f"Failed to fetch MP structure: {exc}")

        return ToolResult(status="failed", error="Unable to load reference structure")

    def _match_peaks(
        self,
        measured_peaks: List[Tuple[float, float]],
        reference_peaks: List[Tuple[float, float]],
        tolerance: float,
    ) -> Tuple[List[Dict[str, Any]], float]:
        matches: List[Dict[str, Any]] = []
        if not measured_peaks or not reference_peaks:
            return matches, 0.0

        reference_two_theta = [p[0] for p in reference_peaks]
        for tth, intensity in measured_peaks:
            nearest = min(reference_two_theta, key=lambda r: abs(r - tth))
            diff = abs(nearest - tth)
            if diff <= tolerance:
                matches.append(
                    {
                        "measured_two_theta": float(tth),
                        "reference_two_theta": float(nearest),
                        "difference": float(diff),
                        "intensity": float(intensity),
                    }
                )

        score = len(matches) / len(measured_peaks) if measured_peaks else 0.0
        return matches, score
