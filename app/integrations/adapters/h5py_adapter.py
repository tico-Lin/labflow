"""
HDF5 storage adapter for curve/array data.
"""

from __future__ import annotations

import io
import os
from typing import Any, Dict, List

from ..base import ToolAdapter, ToolContext, ToolParameter, ToolResult, ToolSpec
from app.storage import Hdf5Storage


class Hdf5StorageAdapter(ToolAdapter):
    spec = ToolSpec(
        id="hdf5_storage",
        name="HDF5 Storage",
        version="1.0",
        description="Store curve or array data into HDF5 with SQL metadata.",
        input_types=["csv", "txt"],
        parameters=[
            ToolParameter("dataset_name", "string", False, None, "Dataset name (defaults to file stem)"),
            ToolParameter("kind", "string", False, "curve", "Data kind (cv/eis/spectrum/curve)"),
            ToolParameter("x_col", "string", False, "x", "X column name"),
            ToolParameter("y_col", "string", False, "y", "Y column name"),
            ToolParameter("y_cols", "array", False, None, "Optional list of Y columns"),
            ToolParameter("metadata", "object", False, None, "Extra metadata to store"),
        ],
        outputs=["hdf5_path", "datasets"],
    )

    def run(self, context: ToolContext) -> ToolResult:
        if not context.file_bytes:
            return ToolResult(status="failed", error="Missing file bytes")

        try:
            import pandas as pd
        except ImportError as exc:
            return ToolResult(status="failed", error=f"pandas not available: {exc}")

        params = context.parameters or {}
        x_col = params.get("x_col", "x")
        y_col = params.get("y_col", "y")
        y_cols = params.get("y_cols")
        kind = params.get("kind", "curve")
        metadata = params.get("metadata") or {}

        try:
            text = context.file_bytes.decode("utf-8", errors="replace")
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
        except Exception as exc:
            return ToolResult(status="failed", error=f"Failed to parse CSV: {exc}")

        col_map = {c.lower(): c for c in df.columns}
        x_col = col_map.get(str(x_col).lower(), x_col)

        if y_cols:
            if isinstance(y_cols, str):
                y_cols = [c.strip() for c in y_cols.split(",") if c.strip()]
            y_cols = [col_map.get(str(c).lower(), c) for c in y_cols]
        else:
            y_cols = [col_map.get(str(y_col).lower(), y_col)]

        if x_col not in df.columns or any(c not in df.columns for c in y_cols):
            return ToolResult(status="failed", error="Required columns not found in input data")

        arrays: Dict[str, Any] = {
            "x": df[x_col].to_numpy(),
        }
        for idx, col in enumerate(y_cols):
            key = "y" if idx == 0 else f"y{idx+1}"
            arrays[key] = df[col].to_numpy()

        dataset_name = params.get("dataset_name")
        if not dataset_name:
            stem = os.path.splitext(context.filename or "dataset")[0]
            dataset_name = stem or "dataset"

        storage = Hdf5Storage()
        metadata.update(
            {
                "kind": kind,
                "source_filename": context.filename,
                "x_col": x_col,
                "y_cols": y_cols,
            }
        )

        try:
            hdf5_path = storage.save_arrays(dataset_name, arrays, metadata)
        except Exception as exc:
            return ToolResult(status="failed", error=f"Failed to store HDF5: {exc}")

        output = {
            "hdf5_path": hdf5_path,
            "datasets": list(arrays.keys()),
            "kind": kind,
        }
        annotations = [
            {
                "analysis": "hdf5_store",
                "hdf5_path": hdf5_path,
                "datasets": list(arrays.keys()),
                "kind": kind,
            }
        ]
        conclusion = "HDF5 storage completed"

        return ToolResult(status="completed", output=output, annotations=annotations, conclusion=conclusion)
