"""
Azimuthal integration adapter using pyFAI.
"""

from __future__ import annotations

from typing import Dict, Any

import importlib

from ..base import ToolAdapter, ToolContext, ToolParameter, ToolResult, ToolSpec
from ..utils import write_temp_file


class PyFAIAdapter(ToolAdapter):
    spec = ToolSpec(
        id="pyfai",
        name="Azimuthal Integration",
        version="1.0",
        description="Integrate 2D diffraction images into 1D profiles.",
        input_types=["image", "tiff", "png"],
        parameters=[
            ToolParameter("poni_file", "string", False, None, "Path to PONI calibration file"),
            ToolParameter("npt", "integer", False, 1000, "Number of output points"),
            ToolParameter("unit", "string", False, "2th_deg", "Output unit"),
        ],
        outputs=["radial", "intensity"],
    )

    def run(self, context: ToolContext) -> ToolResult:
        if not context.file_bytes:
            return ToolResult(status="failed", error="Missing file bytes")

        try:
            skimage_io = importlib.import_module("skimage.io")
            imread = skimage_io.imread
        except Exception as exc:
            return ToolResult(status="failed", error=f"scikit-image not available: {exc}")

        try:
            pyFAI = importlib.import_module("pyFAI")
        except Exception as exc:
            return ToolResult(status="failed", error=f"pyFAI not available: {exc}")

        params = context.parameters or {}
        poni_file = params.get("poni_file")
        npt = int(params.get("npt", 1000))
        unit = params.get("unit", "2th_deg")

        if not poni_file:
            return ToolResult(status="failed", error="poni_file is required for pyFAI integration")

        file_path = context.file_path
        if not file_path:
            file_path = write_temp_file(context.file_bytes, context.filename)

        try:
            image = imread(file_path)
            integrator = pyFAI.load(poni_file)
            radial, intensity = integrator.integrate1d(image, npt, unit=unit)
        except Exception as exc:
            return ToolResult(status="failed", error=f"pyFAI integration failed: {exc}")

        output = {
            "radial": radial.tolist(),
            "intensity": intensity.tolist(),
            "npt": npt,
            "unit": unit,
        }
        annotations = [
            {
                "analysis": "azimuthal_integration",
                "npt": npt,
                "unit": unit,
            }
        ]
        conclusion = "Azimuthal integration completed"

        return ToolResult(status="completed", output=output, annotations=annotations, conclusion=conclusion)
