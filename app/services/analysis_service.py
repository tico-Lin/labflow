"""
Analysis service for running integration adapters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json

from sqlalchemy.orm import Session

from app.integrations import get_adapter, list_specs
from app.integrations.base import ToolContext, ToolResult
from app.integrations.utils import write_temp_file
from app.models import Annotation, Conclusion, File
from app.storage import LocalStorage


class AnalysisServiceError(Exception):
    pass


class AnalysisService:
    def __init__(self, db: Session, storage: Optional[LocalStorage] = None):
        self.db = db
        self.storage = storage or LocalStorage()

    def list_tools(self) -> List[Dict[str, Any]]:
        specs = list_specs()
        return [
            {
                "id": spec.id,
                "name": spec.name,
                "version": spec.version,
                "description": spec.description,
                "input_types": spec.input_types,
                "parameters": [p.__dict__ for p in spec.parameters],
                "outputs": spec.outputs,
            }
            for spec in specs
        ]

    def run_tool(
        self,
        tool_id: str,
        file_id: int,
        parameters: Optional[Dict[str, Any]] = None,
        store_output: bool = True,
    ) -> Dict[str, Any]:
        file_record = self.db.query(File).filter(File.id == file_id).first()
        if not file_record:
            raise AnalysisServiceError(f"File not found: {file_id}")

        file_bytes = self.storage.load(file_record.storage_key)
        file_path = write_temp_file(file_bytes, file_record.filename)

        adapter = get_adapter(tool_id)
        context = ToolContext(
            file_id=file_record.id,
            filename=file_record.filename,
            file_bytes=file_bytes,
            file_path=file_path,
            parameters=parameters or {},
        )
        result = adapter.run(context)

        stored = {
            "conclusion_id": None,
            "annotation_ids": [],
        }

        if store_output and result.status == "completed":
            stored = self._store_outputs(file_record.id, tool_id, result)

        return {
            "status": result.status,
            "output": result.output,
            "metrics": result.metrics,
            "warnings": result.warnings,
            "error": result.error,
            "stored": stored,
        }

    def _store_outputs(self, file_id: int, tool_id: str, result: ToolResult) -> Dict[str, Any]:
        stored = {
            "conclusion_id": None,
            "annotation_ids": [],
        }

        if result.conclusion:
            conclusion = Conclusion(file_id=file_id, content=result.conclusion)
            self.db.add(conclusion)
            self.db.commit()
            self.db.refresh(conclusion)
            stored["conclusion_id"] = conclusion.id

        for annotation_data in result.annotations:
            payload = dict(annotation_data)
            payload.setdefault("tool_id", tool_id)
            payload = self._normalize_json_payload(payload)
            annotation = Annotation(
                file_id=file_id,
                data=payload,
                source="auto",
            )
            self.db.add(annotation)
            self.db.commit()
            self.db.refresh(annotation)
            stored["annotation_ids"].append(annotation.id)

        return stored

    def _normalize_json_payload(self, payload: Any) -> Any:
        try:
            return json.loads(json.dumps(payload, default=self._json_default))
        except TypeError:
            return {"value": str(payload)}

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                return str(value)
        return str(value)
