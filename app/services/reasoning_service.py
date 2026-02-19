"""
Reasoning Chain Service

Handles CRUD operations and business logic for reasoning chains and executions.
"""

from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import select, desc, and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import (
    ReasoningChain,
    ReasoningExecution,
    User,
)
from app.cache import CacheManager
from app.reasoning_engine import ReasoningEngine, NodeConfig
from app.storage import LocalStorage
from app.reasoning_engine.node_types import NodeStatus


logger = logging.getLogger(__name__)


class ReasoningServiceError(Exception):
    """Base exception for reasoning service"""
    pass


class ChainNotFoundError(ReasoningServiceError):
    """Chain not found exception"""
    pass


class ExecutionNotFoundError(ReasoningServiceError):
    """Execution not found exception"""
    pass


class InvalidChainError(ReasoningServiceError):
    """Invalid chain configuration exception"""
    pass


class ReasoningService:
    """Service for managing reasoning chains and executions"""
    
    def __init__(self, db: Session, storage: Optional[LocalStorage] = None):
        """Initialize service with database session"""
        self.db = db
        self.storage = storage
        self.engine = ReasoningEngine(db_session=db, storage=storage, persist_execution=False)
        self.cache_ttl = 3600  # 1 hour default cache TTL
        self.cache = CacheManager()
    
    # ========================================================================
    # Reasoning Chain CRUD Operations
    # ========================================================================
    
    def create_chain(
        self,
        name: str,
        description: str,
        nodes: List[Dict[str, Any]],
        created_by_id: int,
        is_template: bool = False,
    ) -> ReasoningChain:
        """
        Create a new reasoning chain
        
        Parameters:
          name: Chain name
          description: Chain description
          nodes: List of node configurations
          created_by_id: User ID who created the chain
          is_template: Whether this is a template chain
        
        Returns:
          Created ReasoningChain object
        
        Raises:
          InvalidChainError: If chain configuration is invalid
          SQLAlchemyError: If database operation fails
        """
        try:
            # Validate chain structure
            self._validate_chain_structure(nodes)
            
            # Create new chain (SQLAlchemy will automatically serialize JSON)
            chain = ReasoningChain(
                id=uuid4(),
                name=name,
                description=description,
                nodes=nodes,  # Pass list directly, SQLAlchemy handles JSON serialization
                is_template=is_template,
                created_by_id=created_by_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            
            self.db.add(chain)
            self.db.commit()
            self.db.refresh(chain)
            
            logger.info(f"Created reasoning chain: {chain.id} (name={name})")
            
            # Invalidate cache
            self._invalidate_chain_cache()
            
            return chain
        
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating chain: {e}")
            raise ReasoningServiceError(f"Failed to create chain: {e}")
    
    def get_chain(self, chain_id: UUID) -> Optional[ReasoningChain]:
        """
        Get a reasoning chain by ID
        
        Uses cache to improve performance.
        """
        # Try cache first
        cache_key = f"chain:{chain_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            stmt = select(ReasoningChain).where(ReasoningChain.id == chain_id)
            chain = self.db.execute(stmt).scalar_one_or_none()
            
            if chain:
                # Cache the result
                self.cache.set(cache_key, chain, self.cache_ttl)
            
            return chain
        
        except SQLAlchemyError as e:
            logger.error(f"Database error getting chain: {e}")
            return None
    
    def list_chains(
        self,
        skip: int = 0,
        limit: int = 10,
        template_only: bool = False,
    ) -> List[ReasoningChain]:
        """
        List reasoning chains with pagination
        
        Parameters:
          skip: Number of records to skip
          limit: Maximum records to return
          template_only: Only return template chains
        
        Returns:
          List of ReasoningChain objects
        """
        try:
            query = select(ReasoningChain)
            
            if template_only:
                query = query.where(ReasoningChain.is_template == True)
            
            query = query.order_by(desc(ReasoningChain.created_at))
            query = query.offset(skip).limit(limit)
            
            chains = self.db.execute(query).scalars().all()
            return chains
        
        except SQLAlchemyError as e:
            logger.error(f"Database error listing chains: {e}")
            return []
    
    def update_chain(
        self,
        chain_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[ReasoningChain]:
        """
        Update a reasoning chain
        
        Parameters:
          chain_id: Chain ID to update
          name: New name (optional)
          description: New description (optional)
          nodes: New node configuration (optional)
        
        Returns:
          Updated ReasoningChain object or None if not found
        """
        try:
            chain = self.get_chain(chain_id)
            if not chain:
                raise ChainNotFoundError(f"Chain not found: {chain_id}")
            
            # Validate new nodes if provided
            if nodes:
                self._validate_chain_structure(nodes)
                chain.nodes = nodes  # SQLAlchemy handles JSON serialization
            
            if name:
                chain.name = name
            
            if description:
                chain.description = description
            
            chain.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(chain)
            
            logger.info(f"Updated reasoning chain: {chain_id}")
            
            # Invalidate cache
            self._invalidate_chain_cache()
            
            return chain
        
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating chain: {e}")
            raise ReasoningServiceError(f"Failed to update chain: {e}")
    
    def delete_chain(self, chain_id: UUID) -> bool:
        """
        Delete a reasoning chain
        
        Returns:
          True if deleted, False if not found
        """
        try:
            chain = self.get_chain(chain_id)
            if not chain:
                return False
            
            self.db.delete(chain)
            self.db.commit()
            
            logger.info(f"Deleted reasoning chain: {chain_id}")
            
            # Invalidate cache
            self._invalidate_chain_cache()
            
            return True
        
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting chain: {e}")
            return False
    
    # ========================================================================
    # Reasoning Execution Operations
    # ========================================================================
    
    def execute_chain(
        self,
        chain_id: UUID,
        input_data: Dict[str, Any],
        user_id: int,
        model_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        timeout: int = 300,
    ) -> ReasoningExecution:
        """
        Execute a reasoning chain
        
        Parameters:
          chain_id: Chain to execute
          input_data: Input data for execution
          user_id: User executing the chain
          timeout: Execution timeout in seconds
        
        Returns:
          ReasoningExecution object with results
        
        Raises:
          ChainNotFoundError: If chain not found
          ReasoningServiceError: If execution fails
        """
        try:
            # Get the chain
            chain = self.get_chain(chain_id)
            if not chain:
                raise ChainNotFoundError(f"Chain not found: {chain_id}")

            normalized_input = self._normalize_json_value(input_data) or {}
            
            # Create execution record
            execution = ReasoningExecution(
                id=uuid4(),
                chain_id=chain_id,
                status="running",
                user_id=user_id,
                model_name=model_name,
                tool_name=tool_name,
                input_data=normalized_input,
                results={},
                error_log=None,
                started_at=datetime.now(timezone.utc),
                completed_at=None,
                execution_time_ms=0,
            )
            
            self.db.add(execution)
            self.db.commit()
            
            try:
                # Parse chain nodes
                nodes = self._normalize_nodes(chain.nodes)
                
                # Execute chain using reasoning engine
                result = self.engine.execute_chain(
                    nodes=nodes,
                    input_data=normalized_input,
                    timeout=timeout,
                )
                
                # Update execution record
                execution.status = result.get("status", "completed")
                execution.results = self._normalize_json_value(result.get("results", {}))
                errors = result.get("errors")
                if errors:
                    execution.error_log = self._stringify_errors(errors)
                execution.completed_at = datetime.now(timezone.utc)
                
                # Calculate execution time
                if execution.completed_at and execution.started_at:
                    execution.execution_time_ms = self._safe_duration_ms(
                        execution.started_at,
                        execution.completed_at,
                    )
                
                logger.info(
                    f"Chain execution completed: {execution.id} "
                    f"(chain={chain_id}, status={execution.status})"
                )
            
            except Exception as e:
                # Update execution with error
                execution.status = "failed"
                execution.error_log = self._stringify_errors({"error": str(e)})
                execution.completed_at = datetime.now(timezone.utc)
                
                if execution.completed_at and execution.started_at:
                    execution.execution_time_ms = self._safe_duration_ms(
                        execution.started_at,
                        execution.completed_at,
                    )
                
                logger.error(f"Chain execution failed: {execution.id} - {e}")
            
            self.db.commit()
            self.db.refresh(execution)
            
            # Invalidate execution cache
            self._invalidate_execution_cache(chain_id)
            
            return execution
        
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error executing chain: {e}")
            raise ReasoningServiceError(f"Failed to execute chain: {e}")

    def _safe_duration_ms(self, start_time: datetime, end_time: datetime) -> int:
        if start_time is None or end_time is None:
            return 0
        if (start_time.tzinfo is None) != (end_time.tzinfo is None):
            start_time = start_time.replace(tzinfo=None)
            end_time = end_time.replace(tzinfo=None)
        return int((end_time - start_time).total_seconds() * 1000)

    def _normalize_nodes(self, nodes: Any) -> List[Dict[str, Any]]:
        if nodes is None:
            return []
        if isinstance(nodes, list):
            return nodes
        if isinstance(nodes, str):
            import json
            return json.loads(nodes)
        raise InvalidChainError("Invalid chain nodes format")

    def _normalize_json_value(self, value: Any) -> Any:
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

    def _stringify_errors(self, errors: Any) -> str:
        if isinstance(errors, str):
            return errors
        try:
            import json
            return json.dumps(errors, ensure_ascii=True)
        except Exception:
            return str(errors)
    
    def get_execution(self, execution_id: UUID) -> Optional[ReasoningExecution]:
        """
        Get a reasoning execution by ID
        
        Uses cache to improve performance.
        """
        cache_key = f"execution:{execution_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            stmt = select(ReasoningExecution).where(ReasoningExecution.id == execution_id)
            execution = self.db.execute(stmt).scalar_one_or_none()
            
            if execution:
                self.cache.set(cache_key, execution, self.cache_ttl)
            
            return execution
        
        except SQLAlchemyError as e:
            logger.error(f"Database error getting execution: {e}")
            return None
    
    def list_executions(
        self,
        chain_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> List[ReasoningExecution]:
        """
        List reasoning executions with filters
        
        Parameters:
          chain_id: Filter by chain ID (optional)
          skip: Number of records to skip
          limit: Maximum records to return
          status: Filter by execution status (optional)
        
        Returns:
          List of ReasoningExecution objects
        """
        try:
            query = select(ReasoningExecution)
            
            filters = []
            if chain_id:
                filters.append(ReasoningExecution.chain_id == chain_id)
            if status:
                filters.append(ReasoningExecution.status == status)
            
            if filters:
                query = query.where(and_(*filters))
            
            query = query.order_by(desc(ReasoningExecution.started_at))
            query = query.offset(skip).limit(limit)
            
            executions = self.db.execute(query).scalars().all()
            return executions
        
        except SQLAlchemyError as e:
            logger.error(f"Database error listing executions: {e}")
            return []
    
    def get_execution_history(
        self,
        chain_id: UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get execution history for a chain
        
        Parameters:
          chain_id: Chain ID
          days: Look back period in days
        
        Returns:
          Summary of execution history
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = select(ReasoningExecution).where(
                and_(
                    ReasoningExecution.chain_id == chain_id,
                    ReasoningExecution.started_at >= cutoff_date,
                )
            )
            
            executions = self.db.execute(query).scalars().all()
            
            # Calculate statistics
            total = len(executions)
            completed = sum(1 for e in executions if e.status == "completed")
            failed = sum(1 for e in executions if e.status == "failed")
            avg_time = (
                sum(e.execution_time_ms for e in executions) / total
                if total > 0
                else 0
            )
            
            return {
                "chain_id": str(chain_id),
                "period_days": days,
                "total_executions": total,
                "completed": completed,
                "failed": failed,
                "success_rate": (completed / total * 100) if total > 0 else 0,
                "avg_execution_time_ms": avg_time,
            }
        
        except SQLAlchemyError as e:
            logger.error(f"Database error getting execution history: {e}")
            return {}
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def _validate_chain_structure(self, nodes: List[Dict[str, Any]]) -> None:
        """
        Validate chain structure
        
        Checks:
          1. At least one node
          2. Unique node IDs
          3. Valid node types
          4. Valid input references
          5. No cycles
        
        Raises:
          InvalidChainError: If validation fails
        """
        if not nodes:
            raise InvalidChainError("Chain must have at least one node")
        
        # Check unique node IDs
        node_ids = [n.get("node_id") for n in nodes]
        if len(node_ids) != len(set(node_ids)):
            raise InvalidChainError("Duplicate node IDs found")
        
        # Check valid node types
        valid_types = {
            "data_input",
            "transform",
            "calculate",
            "condition",
            "output",
        }
        for node in nodes:
            node_type = node.get("node_type")
            normalized_type = node_type.value if hasattr(node_type, "value") else str(node_type).lower()
            if normalized_type not in valid_types:
                raise InvalidChainError(f"Invalid node type: {node_type}")
        
        # Try DAG validation with engine
        try:
            self.engine._validate_dag(nodes)
        except Exception as e:
            raise InvalidChainError(f"DAG validation failed: {e}")
    
    # ========================================================================
    # Cache Management
    # ========================================================================
    
    def _invalidate_chain_cache(self) -> None:
        """Invalidate chain cache"""
        # Clear pattern-based cache keys
        self.cache.delete_pattern("chain:*")
        self.cache.delete_pattern("chains:*")
    
    def _invalidate_execution_cache(self, chain_id: UUID) -> None:
        """Invalidate execution cache for a chain"""
        self.cache.delete_pattern(f"execution:*")
        self.cache.delete_pattern(f"executions:{chain_id}:*")
