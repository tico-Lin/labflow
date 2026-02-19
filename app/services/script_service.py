"""
Script Service

Handles CRUD operations and business logic for scripts and executions.
"""

from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
import json
import logging

from sqlalchemy import select, desc, and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import Script, ScriptExecution, User
from app.cache import CacheManager


logger = logging.getLogger(__name__)


class ScriptServiceError(Exception):
    """Base exception for script service"""
    pass


class ScriptNotFoundError(ScriptServiceError):
    """Script not found exception"""
    pass


class ExecutionNotFoundError(ScriptServiceError):
    """Execution not found exception"""
    pass


class InvalidScriptError(ScriptServiceError):
    """Invalid script configuration exception"""
    pass


class ScriptService:
    """Service for managing scripts and executions"""
    
    def __init__(self, db: Session):
        """Initialize service with database session"""
        self.db = db
        self.cache_ttl = 3600  # 1 hour default cache TTL
        self.cache = CacheManager()
    
    # ========================================================================
    # Script CRUD Operations
    # ========================================================================
    
    def create_script(
        self,
        name: str,
        content: str,
        parameters: Dict[str, Any],
        category: str,
        created_by_id: UUID,
        version: str = "1.0.0",
    ) -> Script:
        """
        Create a new script
        
        Parameters:
          name: Script name
          content: Script content (Python/Shell/etc)
          parameters: Script parameter definitions
          category: Script category (transform, calculate, validate, etc)
          created_by_id: User ID who created the script
          version: Script version
        
        Returns:
          Created Script object
        
        Raises:
          InvalidScriptError: If script configuration is invalid
          SQLAlchemyError: If database operation fails
        """
        try:
            # Validate script content
            self._validate_script_content(content)
            
            # Create new script
            script = Script(
                id=uuid4(),
                name=name,
                content=content,
                parameters=json.dumps(parameters),
                category=category,
                version=version,
                created_by_id=created_by_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            
            self.db.add(script)
            self.db.commit()
            self.db.refresh(script)
            
            logger.info(f"Created script: {script.id} (name={name}, version={version})")
            
            # Invalidate cache
            self._invalidate_script_cache()
            
            return script
        
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating script: {e}")
            raise ScriptServiceError(f"Failed to create script: {e}")
    
    def get_script(self, script_id: UUID) -> Optional[Script]:
        """
        Get a script by ID
        
        Uses cache to improve performance.
        """
        cache_key = f"script:{script_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            stmt = select(Script).where(Script.id == script_id)
            script = self.db.execute(stmt).scalar_one_or_none()
            
            if script:
                self.cache.set(cache_key, script, self.cache_ttl)
            
            return script
        
        except SQLAlchemyError as e:
            logger.error(f"Database error getting script: {e}")
            return None
    
    def get_script_by_name(self, name: str) -> Optional[Script]:
        """Get the latest version of a script by name"""
        try:
            stmt = (
                select(Script)
                .where(Script.name == name)
                .order_by(desc(Script.created_at))
                .limit(1)
            )
            script = self.db.execute(stmt).scalar_one_or_none()
            return script
        
        except SQLAlchemyError as e:
            logger.error(f"Database error getting script by name: {e}")
            return None
    
    def list_scripts(
        self,
        skip: int = 0,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Script]:
        """
        List scripts with pagination and filtering
        
        Parameters:
          skip: Number of records to skip
          limit: Maximum records to return
          category: Filter by category (optional)
        
        Returns:
          List of Script objects
        """
        try:
            query = select(Script)
            
            if category:
                query = query.where(Script.category == category)
            
            # Group by name and get latest version of each
            query = query.order_by(desc(Script.created_at))
            query = query.offset(skip).limit(limit)
            
            scripts = self.db.execute(query).scalars().all()
            return scripts
        
        except SQLAlchemyError as e:
            logger.error(f"Database error listing scripts: {e}")
            return []
    
    def list_script_versions(self, name: str) -> List[Script]:
        """
        List all versions of a script
        
        Parameters:
          name: Script name
        
        Returns:
          List of Script versions ordered by creation date descending
        """
        try:
            stmt = (
                select(Script)
                .where(Script.name == name)
                .order_by(desc(Script.created_at))
            )
            scripts = self.db.execute(stmt).scalars().all()
            return scripts
        
        except SQLAlchemyError as e:
            logger.error(f"Database error listing script versions: {e}")
            return []
    
    def update_script(
        self,
        script_id: UUID,
        name: Optional[str] = None,
        content: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Optional[Script]:
        """
        Update a script
        
        Creates a new version if content changes.
        
        Parameters:
          script_id: Script ID to update
          name: New name (optional)
          content: New content (optional)
          parameters: New parameters (optional)
          category: New category (optional)
          version: New version string (optional)
        
        Returns:
          Updated Script object or None if not found
        """
        try:
            script = self.get_script(script_id)
            if not script:
                raise ScriptNotFoundError(f"Script not found: {script_id}")
            
            # If content changed, we could create a new version
            # For now, just update the existing one
            
            if content:
                self._validate_script_content(content)
                script.content = content
            
            if name:
                script.name = name
            
            if parameters:
                script.parameters = json.dumps(parameters)
            
            if category:
                script.category = category
            
            if version:
                script.version = version
            
            script.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(script)
            
            logger.info(f"Updated script: {script_id}")
            
            # Invalidate cache
            self._invalidate_script_cache()
            
            return script
        
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating script: {e}")
            raise ScriptServiceError(f"Failed to update script: {e}")
    
    def delete_script(self, script_id: UUID) -> bool:
        """
        Delete a script
        
        Returns:
          True if deleted, False if not found
        """
        try:
            script = self.get_script(script_id)
            if not script:
                return False
            
            self.db.delete(script)
            self.db.commit()
            
            logger.info(f"Deleted script: {script_id}")
            
            # Invalidate cache
            self._invalidate_script_cache()
            
            return True
        
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting script: {e}")
            return False
    
    # ========================================================================
    # Script Execution Operations
    # ========================================================================
    
    def execute_script(
        self,
        script_id: UUID,
        input_params: Dict[str, Any],
        timeout: int = 300,
    ) -> ScriptExecution:
        """
        Execute a script
        
        Parameters:
          script_id: Script to execute
          input_params: Input parameters for execution
          timeout: Execution timeout in seconds
        
        Returns:
          ScriptExecution object with results
        
        Raises:
          ScriptNotFoundError: If script not found
          ScriptServiceError: If execution fails
        """
        try:
            # Get the script
            script = self.get_script(script_id)
            if not script:
                raise ScriptNotFoundError(f"Script not found: {script_id}")
            
            # Create execution record
            execution = ScriptExecution(
                id=uuid4(),
                script_id=script_id,
                status="running",
                input_params=json.dumps(input_params),
                result=None,
                error=None,
                started_at=datetime.now(timezone.utc),
                completed_at=None,
                execution_time_ms=0,
            )
            
            self.db.add(execution)
            self.db.commit()
            
            try:
                # Execute script (placeholder - would use subprocess/exec)
                result = self._execute_script_content(
                    script.content,
                    input_params,
                    timeout,
                )
                
                # Update execution record
                execution.status = "completed"
                execution.result = json.dumps(result)
                execution.completed_at = datetime.now(timezone.utc)
                
                # Calculate execution time
                if execution.completed_at and execution.started_at:
                    execution.execution_time_ms = self._safe_duration_ms(
                        execution.started_at,
                        execution.completed_at,
                    )
                
                logger.info(
                    f"Script execution completed: {execution.id} "
                    f"(script={script_id}, status={execution.status})"
                )
            
            except Exception as e:
                # Update execution with error
                execution.status = "failed"
                execution.error = str(e)
                execution.completed_at = datetime.now(timezone.utc)
                
                if execution.completed_at and execution.started_at:
                    execution.execution_time_ms = self._safe_duration_ms(
                        execution.started_at,
                        execution.completed_at,
                    )
                
                logger.error(f"Script execution failed: {execution.id} - {e}")
            
            self.db.commit()
            self.db.refresh(execution)
            
            # Invalidate execution cache
            self._invalidate_execution_cache(script_id)
            
            return execution
        
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error executing script: {e}")
            raise ScriptServiceError(f"Failed to execute script: {e}")
    
    def get_execution(self, execution_id: UUID) -> Optional[ScriptExecution]:
        """
        Get a script execution by ID
        
        Uses cache to improve performance.
        """
        cache_key = f"script_execution:{execution_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            stmt = select(ScriptExecution).where(ScriptExecution.id == execution_id)
            execution = self.db.execute(stmt).scalar_one_or_none()
            
            if execution:
                self.cache.set(cache_key, execution, self.cache_ttl)
            
            return execution
        
        except SQLAlchemyError as e:
            logger.error(f"Database error getting execution: {e}")
            return None
    
    def list_executions(
        self,
        script_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> List[ScriptExecution]:
        """
        List script executions with filters
        
        Parameters:
          script_id: Filter by script ID (optional)
          skip: Number of records to skip
          limit: Maximum records to return
          status: Filter by execution status (optional)
        
        Returns:
          List of ScriptExecution objects
        """
        try:
            query = select(ScriptExecution)
            
            filters = []
            if script_id:
                filters.append(ScriptExecution.script_id == script_id)
            if status:
                filters.append(ScriptExecution.status == status)
            
            if filters:
                query = query.where(and_(*filters))
            
            query = query.order_by(desc(ScriptExecution.started_at))
            query = query.offset(skip).limit(limit)
            
            executions = self.db.execute(query).scalars().all()
            return executions
        
        except SQLAlchemyError as e:
            logger.error(f"Database error listing executions: {e}")
            return []
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def _validate_script_content(self, content: str) -> None:
        """
        Validate script content
        
        Checks:
          1. Content is not empty
          2. Content doesn't exceed size limit (1MB)
          3. Basic syntax check (if applicable)
        
        Raises:
          InvalidScriptError: If validation fails
        """
        if not content or not content.strip():
            raise InvalidScriptError("Script content cannot be empty")
        
        if len(content) > 1024 * 1024:  # 1MB limit
            raise InvalidScriptError("Script content exceeds 1MB limit")
    
    def _execute_script_content(
        self,
        content: str,
        input_params: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """
        Execute script content
        
        Placeholder implementation. Real version would:
          - Use subprocess for shell scripts
          - Use exec/eval for Python scripts with sandboxing
          - Handle timeouts properly
          - Capture output and errors
        """
        # Placeholder: return success
        return {
            "status": "success",
            "message": "Script execution not yet fully implemented",
            "input_params": input_params,
        }

    def _safe_duration_ms(self, start_time: datetime, end_time: datetime) -> int:
        if start_time is None or end_time is None:
            return 0
        if (start_time.tzinfo is None) != (end_time.tzinfo is None):
            start_time = start_time.replace(tzinfo=None)
            end_time = end_time.replace(tzinfo=None)
        return int((end_time - start_time).total_seconds() * 1000)
    
    # ========================================================================
    # Cache Management
    # ========================================================================
    
    def _invalidate_script_cache(self) -> None:
        """Invalidate script cache"""
        self.cache.delete_pattern("script:*")
        self.cache.delete_pattern("scripts:*")
    
    def _invalidate_execution_cache(self, script_id: UUID) -> None:
        """Invalidate execution cache for a script"""
        self.cache.delete_pattern(f"script_execution:*")
        self.cache.delete_pattern(f"script_executions:{script_id}:*")
