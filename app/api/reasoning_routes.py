"""
Reasoning chain API routes.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app import security
from app import database
from app import models
from app.services.reasoning_service import ReasoningService
from app.storage import LocalStorage


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reasoning", tags=["reasoning"])
storage = LocalStorage()


def _serialize_chain(chain: models.ReasoningChain, include_nodes: bool = False) -> Dict[str, Any]:
    payload = {
        "id": str(chain.id),
        "name": chain.name,
        "description": chain.description,
        "is_template": chain.is_template,
        "created_at": chain.created_at.isoformat() if chain.created_at else None,
        "updated_at": chain.updated_at.isoformat() if chain.updated_at else None,
    }
    if include_nodes:
        payload["nodes"] = chain.nodes
    return payload


def _normalize_json_payload(value: Any) -> Any:
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        import json
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}


def _normalize_error_payload(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        import json
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _serialize_execution_summary(execution: models.ReasoningExecution) -> Dict[str, Any]:
    return {
        "execution_id": str(execution.id),
        "chain_id": str(execution.chain_id),
        "status": execution.status,
        "user_id": execution.user_id,
        "model_name": execution.model_name,
        "tool_name": execution.tool_name,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
    }


def _serialize_execution_detail(execution: models.ReasoningExecution) -> Dict[str, Any]:
    return {
        **_serialize_execution_summary(execution),
        "input_data": _normalize_json_payload(execution.input_data),
        "results": _normalize_json_payload(execution.results),
        "error": _normalize_error_payload(execution.error_log),
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "execution_time_ms": execution.execution_time_ms,
    }


@router.post(
    "/chains",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.ReasoningChainResponse,
)
def create_reasoning_chain(
    chain_data: schemas.ReasoningChainCreate,
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user_optional),
):
    """Create a reasoning chain."""
    # Check if offline user tries to create chain
    if security.is_offline_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="離線模式下不允許建立推理鏈。請登錄後執行此操作。"
        )
    try:
        service = ReasoningService(db, storage=storage)
        chain = service.create_chain(
            name=chain_data.name,
            description=chain_data.description or "",
            nodes=[node.model_dump() for node in chain_data.nodes],
            created_by_id=current_user["id"],
            is_template=chain_data.is_template,
        )
        logger.info("Created reasoning chain: %s", chain.id)
        return _serialize_chain(chain)
    except Exception as exc:
        logger.error("Failed to create reasoning chain: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/chains", response_model=List[schemas.ReasoningChainResponse])
def list_reasoning_chains(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user_optional),
):
    """List reasoning chains."""
    try:
        service = ReasoningService(db, storage=storage)
        chains = service.list_chains(skip=skip, limit=limit)
        return [_serialize_chain(chain) for chain in chains]
    except Exception as exc:
        logger.error("Failed to list reasoning chains: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/chains/{chain_id}", response_model=schemas.ReasoningChainResponse)
def get_reasoning_chain(
    chain_id: str,
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user_optional),
):
    """Get a reasoning chain."""
    try:
        service = ReasoningService(db, storage=storage)
        chain = service.get_chain(UUID(chain_id))
        if not chain:
            raise HTTPException(status_code=404, detail="Chain not found")
        return _serialize_chain(chain, include_nodes=True)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get reasoning chain: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/chains/{chain_id}", response_model=schemas.ReasoningChainResponse)
def update_reasoning_chain(
    chain_id: str,
    update_data: schemas.ReasoningChainUpdate,
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user_optional),
):
    """Update a reasoning chain."""
    # Check if offline user tries to update chain
    if security.is_offline_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="離線模式下不允許修改推理鏈。請登錄後執行此操作。"
        )
    try:
        service = ReasoningService(db, storage=storage)
        nodes: Optional[List[Dict[str, Any]]] = None
        if update_data.nodes is not None:
            nodes = [node.model_dump() for node in update_data.nodes]
        chain = service.update_chain(
            chain_id=UUID(chain_id),
            name=update_data.name,
            description=update_data.description,
            nodes=nodes,
        )
        if not chain:
            raise HTTPException(status_code=404, detail="Chain not found")
        logger.info("Updated reasoning chain: %s", chain_id)
        return _serialize_chain(chain)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update reasoning chain: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/chains/{chain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reasoning_chain(
    chain_id: str,
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user_optional),
):
    """Delete a reasoning chain."""
    # Check if offline user tries to delete chain
    if security.is_offline_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="離線模式下不允許刪除推理鏈。請登錄後執行此操作。"
        )
    try:
        service = ReasoningService(db, storage=storage)
        service.delete_chain(UUID(chain_id))
        logger.info("Deleted reasoning chain: %s", chain_id)
    except Exception as exc:
        logger.error("Failed to delete reasoning chain: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/chains/{chain_id}/execute",
    response_model=schemas.ReasoningExecutionSummary,
)
def execute_reasoning_chain(
    chain_id: str,
    payload: schemas.ReasoningExecuteRequest = Body(default_factory=schemas.ReasoningExecuteRequest),
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user_optional),
):
    """Execute a reasoning chain."""
    # Check if offline user tries to execute chain
    if security.is_offline_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="離線模式下不允許執行推理鏈。請登錄後執行此操作。"
        )
    try:
        service = ReasoningService(db, storage=storage)
        execution = service.execute_chain(
            UUID(chain_id),
            payload.input_data or {},
            user_id=current_user["id"],
            model_name=payload.model_name,
            tool_name=payload.tool_name,
        )
        logger.info("Executed reasoning chain: %s", chain_id)
        return _serialize_execution_summary(execution)
    except Exception as exc:
        logger.error("Failed to execute reasoning chain: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/executions/{execution_id}",
    response_model=schemas.ReasoningExecutionDetail,
)
def get_execution_result(
    execution_id: str,
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user),
):
    """Get execution result."""
    try:
        service = ReasoningService(db, storage=storage)
        execution = service.get_execution(UUID(execution_id))
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return _serialize_execution_detail(execution)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get execution result: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/chains/{chain_id}/history",
    response_model=schemas.ReasoningChainHistory,
)
def get_reasoning_chain_history(
    chain_id: str,
    days: int = 30,
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user),
):
    """Get execution history for a chain."""
    try:
        service = ReasoningService(db, storage=storage)
        history = service.get_execution_history(UUID(chain_id), days=days)
        if not history:
            raise HTTPException(status_code=404, detail="Chain history not found")
        return history
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get chain history: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/chains/{chain_id}/executions",
    response_model=List[schemas.ReasoningExecutionSummary],
)
def list_chain_executions(
    chain_id: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(database.get_db),
    current_user = Depends(security.get_current_user),
):
    """List executions for a specific chain."""
    try:
        service = ReasoningService(db, storage=storage)
        executions = service.list_executions(UUID(chain_id), skip=skip, limit=limit)
        return [_serialize_execution_summary(execution) for execution in executions]
    except Exception as exc:
        logger.error("Failed to list chain executions: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
