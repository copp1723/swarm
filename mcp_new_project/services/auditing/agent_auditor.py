"""
Agent Auditor - Tracks and logs all agent actions for explainability
"""
import logging
import json
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import uuid
import threading

from utils.logging_config import get_logger

logger = get_logger(__name__)


class AuditLevel(Enum):
    """Levels of audit detail"""
    MINIMAL = "minimal"      # Basic action tracking
    STANDARD = "standard"    # Standard tracking with inputs/outputs
    DETAILED = "detailed"    # Full tracking including intermediate steps
    DEBUG = "debug"          # Everything including internal state


@dataclass
class AuditRecord:
    """Represents a single audit record"""
    record_id: str
    timestamp: datetime
    task_id: str
    agent_id: str
    agent_name: str
    action_type: str
    action_name: str
    level: AuditLevel
    duration_ms: float
    success: bool
    
    # Input/Output tracking
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    
    # Context and reasoning
    context: Dict[str, Any]
    reasoning: Optional[str]
    
    # Error handling
    error_message: Optional[str]
    error_traceback: Optional[str]
    
    # Chain of thought
    intermediate_steps: List[Dict[str, Any]]
    tools_used: List[Dict[str, Any]]
    
    # Performance metrics
    tokens_used: Optional[int]
    model_calls: int
    memory_used_mb: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class AgentAuditor:
    """Central auditing system for all agent actions"""
    
    def __init__(self, storage_backend=None, default_level: AuditLevel = AuditLevel.STANDARD):
        self.storage_backend = storage_backend
        self.default_level = default_level
        self.logger = get_logger(__name__)
        self._local_storage = threading.local()
        self._audit_hooks: List[Callable] = []
        
    def set_audit_level(self, level: AuditLevel) -> None:
        """Set the default audit level"""
        self.default_level = level
        self.logger.info(f"Audit level set to: {level.value}")
    
    def add_audit_hook(self, hook: Callable[[AuditRecord], None]) -> None:
        """Add a hook that gets called for each audit record"""
        self._audit_hooks.append(hook)
    
    def create_audit_record(self, 
                          task_id: str,
                          agent_id: str,
                          agent_name: str,
                          action_type: str,
                          action_name: str,
                          level: Optional[AuditLevel] = None) -> AuditRecord:
        """Create a new audit record"""
        return AuditRecord(
            record_id=f"audit_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(),
            task_id=task_id,
            agent_id=agent_id,
            agent_name=agent_name,
            action_type=action_type,
            action_name=action_name,
            level=level or self.default_level,
            duration_ms=0,
            success=False,
            inputs={},
            outputs={},
            context={},
            reasoning=None,
            error_message=None,
            error_traceback=None,
            intermediate_steps=[],
            tools_used=[],
            tokens_used=None,
            model_calls=0,
            memory_used_mb=None
        )
    
    def audit_agent_action(self, 
                          task_id: str,
                          agent_id: str,
                          agent_name: str,
                          action_type: str,
                          action_name: str,
                          level: Optional[AuditLevel] = None):
        """Decorator to audit an agent action"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Create audit record
                audit_record = self.create_audit_record(
                    task_id=task_id,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type=action_type,
                    action_name=action_name,
                    level=level
                )
                
                # Store in thread local for nested tracking
                self._local_storage.current_audit = audit_record
                
                # Capture inputs
                audit_record.inputs = {
                    'args': str(args)[:1000],  # Truncate for storage
                    'kwargs': str(kwargs)[:1000]
                }
                
                start_time = time.time()
                
                try:
                    # Execute the function
                    result = await func(*args, **kwargs)
                    
                    # Mark success
                    audit_record.success = True
                    
                    # Capture outputs
                    audit_record.outputs = {
                        'result': str(result)[:5000] if result else None,
                        'type': type(result).__name__
                    }
                    
                    return result
                    
                except Exception as e:
                    # Capture error details
                    audit_record.success = False
                    audit_record.error_message = str(e)
                    audit_record.error_traceback = traceback.format_exc()
                    
                    # Re-raise the exception
                    raise
                    
                finally:
                    # Calculate duration
                    audit_record.duration_ms = (time.time() - start_time) * 1000
                    
                    # Store the record
                    await self.store_audit_record(audit_record)
                    
                    # Clear thread local
                    self._local_storage.current_audit = None
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Similar logic for sync functions
                audit_record = self.create_audit_record(
                    task_id=task_id,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    action_type=action_type,
                    action_name=action_name,
                    level=level
                )
                
                self._local_storage.current_audit = audit_record
                audit_record.inputs = {
                    'args': str(args)[:1000],
                    'kwargs': str(kwargs)[:1000]
                }
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    audit_record.success = True
                    audit_record.outputs = {
                        'result': str(result)[:5000] if result else None,
                        'type': type(result).__name__
                    }
                    return result
                    
                except Exception as e:
                    audit_record.success = False
                    audit_record.error_message = str(e)
                    audit_record.error_traceback = traceback.format_exc()
                    raise
                    
                finally:
                    audit_record.duration_ms = (time.time() - start_time) * 1000
                    # Use sync storage method
                    self.store_audit_record_sync(audit_record)
                    self._local_storage.current_audit = None
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
                
        return decorator
    
    def add_reasoning(self, reasoning: str) -> None:
        """Add reasoning to current audit record"""
        if hasattr(self._local_storage, 'current_audit') and self._local_storage.current_audit:
            self._local_storage.current_audit.reasoning = reasoning
    
    def add_intermediate_step(self, step_name: str, step_data: Dict[str, Any]) -> None:
        """Add an intermediate step to current audit record"""
        if hasattr(self._local_storage, 'current_audit') and self._local_storage.current_audit:
            self._local_storage.current_audit.intermediate_steps.append({
                'step_name': step_name,
                'timestamp': datetime.now().isoformat(),
                'data': step_data
            })
    
    def add_tool_usage(self, tool_name: str, tool_input: Any, tool_output: Any) -> None:
        """Record tool usage in current audit record"""
        if hasattr(self._local_storage, 'current_audit') and self._local_storage.current_audit:
            self._local_storage.current_audit.tools_used.append({
                'tool_name': tool_name,
                'timestamp': datetime.now().isoformat(),
                'input': str(tool_input)[:1000],
                'output': str(tool_output)[:1000]
            })
    
    def add_context(self, key: str, value: Any) -> None:
        """Add context information to current audit record"""
        if hasattr(self._local_storage, 'current_audit') and self._local_storage.current_audit:
            self._local_storage.current_audit.context[key] = value
    
    def increment_model_calls(self, tokens: Optional[int] = None) -> None:
        """Increment model call counter and optionally add tokens"""
        if hasattr(self._local_storage, 'current_audit') and self._local_storage.current_audit:
            self._local_storage.current_audit.model_calls += 1
            if tokens:
                current_tokens = self._local_storage.current_audit.tokens_used or 0
                self._local_storage.current_audit.tokens_used = current_tokens + tokens
    
    async def store_audit_record(self, record: AuditRecord) -> None:
        """Store an audit record asynchronously"""
        try:
            # Call audit hooks
            for hook in self._audit_hooks:
                try:
                    hook(record)
                except Exception as e:
                    self.logger.error(f"Audit hook failed: {e}")
            
            # Store in backend if available
            if self.storage_backend:
                await self.storage_backend.store_record(record)
            else:
                # Log to file as fallback
                self.logger.info(f"Audit: {record.action_name} by {record.agent_name} - {'SUCCESS' if record.success else 'FAILED'}")
                if self.default_level == AuditLevel.DEBUG:
                    self.logger.debug(record.to_json())
                    
        except Exception as e:
            self.logger.error(f"Failed to store audit record: {e}")
    
    def store_audit_record_sync(self, record: AuditRecord) -> None:
        """Store an audit record synchronously"""
        try:
            # Call audit hooks
            for hook in self._audit_hooks:
                try:
                    hook(record)
                except Exception as e:
                    self.logger.error(f"Audit hook failed: {e}")
            
            # Store in backend if available
            if self.storage_backend and hasattr(self.storage_backend, 'store_record_sync'):
                self.storage_backend.store_record_sync(record)
            else:
                # Log to file as fallback
                self.logger.info(f"Audit: {record.action_name} by {record.agent_name} - {'SUCCESS' if record.success else 'FAILED'}")
                if self.default_level == AuditLevel.DEBUG:
                    self.logger.debug(record.to_json())
                    
        except Exception as e:
            self.logger.error(f"Failed to store audit record: {e}")
    
    async def get_audit_trail(self, task_id: str) -> List[AuditRecord]:
        """Get full audit trail for a task"""
        if self.storage_backend:
            return await self.storage_backend.get_records_by_task(task_id)
        return []
    
    async def get_agent_actions(self, agent_id: str, limit: int = 100) -> List[AuditRecord]:
        """Get recent actions for a specific agent"""
        if self.storage_backend:
            return await self.storage_backend.get_records_by_agent(agent_id, limit)
        return []
    
    def create_explainability_report(self, task_id: str) -> Dict[str, Any]:
        """Create an explainability report for a task"""
        # This will be implemented by the ExplainabilityEngine
        pass


# Global auditor instance
agent_auditor = AgentAuditor()