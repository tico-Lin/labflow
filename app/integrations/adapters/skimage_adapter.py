"""
Image analysis adapter using scikit-image.
"""

from __future__ import annotations

from typing import Dict, Any

import importlib
import numpy as np

from ..base import ToolAdapter, ToolContext, ToolParameter, ToolResult, ToolSpec
from ..utils import write_temp_file


class SkimageAdapter(ToolAdapter):
    spec = ToolSpec(
        id="skimage",
        name="Image Filters",
        version="1.0",
        description="Run basic image filters (canny, gaussian) and return metrics.",
        input_types=["image", "png", "jpg", "tiff"],
        parameters=[
            ToolParameter("operation", "string", True, None, "canny or gaussian"),
            ToolParameter("sigma", "number", False, 1.0, "Sigma for filters"),
        ],
        outputs=["metrics"],
    )

    def run(self, context: ToolContext) -> ToolResult:
        if not context.file_bytes:
            return ToolResult(status="failed", error="Missing file bytes")

        try:
            feature = importlib.import_module("skimage.feature")
            filters = importlib.import_module("skimage.filters")
            skimage_io = importlib.import_module("skimage.io")
            imread = skimage_io.imread
        except Exception as exc:
            return ToolResult(status="failed", error=f"scikit-image not available: {exc}")

        params = context.parameters or {}
        operation = params.get("operation")
        if not operation:
            return ToolResult(status="failed", error="operation is required")

        sigma = float(params.get("sigma", 1.0))

        file_path = context.file_path
        if not file_path:
            file_path = write_temp_file(context.file_bytes, context.filename)

        try:
            image = imread(file_path, as_gray=True)
        except Exception as exc:
            return ToolResult(status="failed", error=f"Failed to read image: {exc}")

        image = image.astype(float)
        metrics: Dict[str, Any] = {
            "shape": list(image.shape),
            "mean": float(np.mean(image)),
            "std": float(np.std(image)),
        }

        if operation == "canny":
            edges = feature.canny(image, sigma=sigma)
            metrics["edge_ratio"] = float(np.mean(edges))
        elif operation == "gaussian":
            blurred = filters.gaussian(image, sigma=sigma)
            metrics["blur_mean"] = float(np.mean(blurred))
        else:
            return ToolResult(status="failed", error=f"Unknown operation: {operation}")

        annotations = [
            {
                "analysis": "image_filter",
                "operation": operation,
                "sigma": sigma,
            }
        ]
        conclusion = f"Image filter '{operation}' completed"

        return ToolResult(status="completed", output={"metrics": metrics}, annotations=annotations, conclusion=conclusion)
