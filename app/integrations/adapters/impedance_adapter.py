"""
Impedance analysis adapter using impedance.py.
"""

from __future__ import annotations

import io
import importlib
from typing import Dict, Any

import numpy as np
import pandas as pd

from ..base import ToolAdapter, ToolContext, ToolParameter, ToolResult, ToolSpec


class ImpedanceAdapter(ToolAdapter):
    spec = ToolSpec(
        id="impedance",
        name="Impedance Fit",
        version="1.0",
        description="Fit a Randles circuit model to EIS data.",
        input_types=["eis", "csv", "txt"],
        parameters=[
            ToolParameter("freq_col", "string", False, "frequency", "Frequency column name"),
            ToolParameter("zreal_col", "string", False, "zreal", "Real impedance column name"),
            ToolParameter("zimag_col", "string", False, "zimag", "Imag impedance column name"),
            ToolParameter("initial_guess", "array", False, None, "Initial guess for Randles parameters"),
        ],
        outputs=["parameters", "fit_error", "data_points"],
    )

    def run(self, context: ToolContext) -> ToolResult:
        if not context.file_bytes:
            return ToolResult(status="failed", error="Missing file bytes")

        try:
            circuits = importlib.import_module("impedance.models.circuits")
            Randles = circuits.Randles
        except Exception as exc:
            return ToolResult(status="failed", error=f"impedance library not available: {exc}")

        try:
            text = context.file_bytes.decode("utf-8", errors="replace")
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
        except Exception as exc:
            return ToolResult(status="failed", error=f"Failed to parse EIS data: {exc}")

        params = context.parameters or {}
        freq_col = params.get("freq_col", "frequency")
        zreal_col = params.get("zreal_col", "zreal")
        zimag_col = params.get("zimag_col", "zimag")

        col_map = {c.lower(): c for c in df.columns}
        freq_col = col_map.get(freq_col.lower(), freq_col)
        zreal_col = col_map.get(zreal_col.lower(), zreal_col)
        zimag_col = col_map.get(zimag_col.lower(), zimag_col)

        if freq_col not in df.columns or zreal_col not in df.columns or zimag_col not in df.columns:
            return ToolResult(
                status="failed",
                error="Required columns not found. Need frequency/zreal/zimag columns.",
            )

        freq = df[freq_col].to_numpy(dtype=float)
        zreal = df[zreal_col].to_numpy(dtype=float)
        zimag = df[zimag_col].to_numpy(dtype=float)
        z = zreal + 1j * zimag

        initial_guess = params.get("initial_guess")
        if not initial_guess:
            initial_guess = [
                float(np.median(zreal)),
                float(np.median(zreal)),
                1e-5,
                1.0,
                1.0,
            ]

        try:
            circuit = Randles(initial_guess=initial_guess)
            circuit.fit(freq, z)
        except Exception as exc:
            return ToolResult(status="failed", error=f"Impedance fit failed: {exc}")

        output = {
            "parameters": circuit.parameters_.tolist(),
            "parameter_names": list(circuit.get_param_names()),
            "fit_error": float(getattr(circuit, "chi_squared_", 0.0)),
            "data_points": int(len(freq)),
        }
        annotations = [
            {
                "analysis": "impedance_fit",
                "parameter_names": output["parameter_names"],
                "parameters": output["parameters"],
            }
        ]
        conclusion = "Impedance Randles fit completed"

        return ToolResult(status="completed", output=output, annotations=annotations, conclusion=conclusion)
