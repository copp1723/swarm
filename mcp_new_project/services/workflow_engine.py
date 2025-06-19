"""
Workflow Template Engine for Chain-of-Agents execution
Supports detailed step-by-step workflows with dependencies and parallel execution
"""
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from collections import defaultdict
import asyncio
from utils.file_io import safe_read_json

logger = logging.getLogger(__name__)

@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    agent: str
    task: str
    output_format: str
    dependencies: List[str]
    timeout_minutes: int
    priority: str = "normal"
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "task": self.task,
            "output_format": self.output_format,
            "dependencies": self.dependencies,
            "timeout_minutes": self.timeout_minutes,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

@dataclass
class WorkflowExecution:
    """Tracks the execution of a workflow"""
    workflow_id: str
    execution_id: str
    steps: List[WorkflowStep]
    current_stage: int = 0
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    summary: Optional[str] = None
    
    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute (dependencies met)"""
        ready = []
        completed_agents = {step.agent for step in self.steps if step.status == "completed"}
        
        for step in self.steps:
            if step.status == "pending":
                # Check if all dependencies are completed
                if all(dep in completed_agents for dep in step.dependencies):
                    ready.append(step)
        
        return ready
    
    def get_execution_stages(self) -> List[List[WorkflowStep]]:
        """Group steps into execution stages based on dependencies"""
        stages = []
        remaining_steps = self.steps.copy()
        completed = set()
        
        while remaining_steps:
            stage = []
            for step in remaining_steps[:]:
                if all(dep in completed for dep in step.dependencies):
                    stage.append(step)
                    remaining_steps.remove(step)
            
            if not stage:
                # Circular dependency or error
                logger.error("Circular dependency detected in workflow")
                break
                
            stages.append(stage)
            completed.update(step.agent for step in stage)
        
        return stages

class WorkflowTemplateEngine:
    """Manages and executes workflow templates"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'workflows_v2.json'
        )
        self.templates = self._load_templates()
        self.executions: Dict[str, WorkflowExecution] = {}
        
    def _load_templates(self) -> Dict[str, Any]:
        """Load workflow templates from configuration"""
        config = safe_read_json(self.config_path, default_value={'templates': []})
        return {t['id']: t for t in config.get('templates', [])}
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available workflow templates"""
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "steps": len(t.get("steps", [])),
                "agents": list(set(step["agent"] for step in t.get("steps", [])))
            }
            for t in self.templates.values()
        ]
    
    def create_execution(self, template_id: str, execution_id: str = None) -> Optional[WorkflowExecution]:
        """Create a new workflow execution from a template"""
        template = self.templates.get(template_id)
        if not template:
            logger.error(f"Template {template_id} not found")
            return None
        
        execution_id = execution_id or f"exec_{datetime.now().timestamp()}_{template_id}"
        
        # Create workflow steps from template
        steps = []
        for step_config in template.get("steps", []):
            step = WorkflowStep(
                agent=step_config["agent"],
                task=step_config["task"],
                output_format=step_config.get("output_format", "markdown"),
                dependencies=step_config.get("dependencies", []),
                timeout_minutes=step_config.get("timeout_minutes", 10),
                priority=step_config.get("priority", "normal")
            )
            steps.append(step)
        
        execution = WorkflowExecution(
            workflow_id=template_id,
            execution_id=execution_id,
            steps=steps
        )
        
        self.executions[execution_id] = execution
        return execution
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get a workflow execution by ID"""
        return self.executions.get(execution_id)
    
    def update_step_status(self, execution_id: str, agent: str, 
                          status: str, result: Optional[str] = None) -> bool:
        """Update the status of a workflow step"""
        execution = self.executions.get(execution_id)
        if not execution:
            return False
        
        for step in execution.steps:
            if step.agent == agent:
                step.status = status
                if status == "running":
                    step.started_at = datetime.now()
                elif status in ["completed", "failed"]:
                    step.completed_at = datetime.now()
                if result:
                    step.result = result
                
                # Update execution status
                if all(s.status == "completed" for s in execution.steps):
                    execution.status = "completed"
                    execution.completed_at = datetime.now()
                elif any(s.status == "failed" for s in execution.steps):
                    execution.status = "failed"
                elif any(s.status == "running" for s in execution.steps):
                    execution.status = "running"
                    if not execution.started_at:
                        execution.started_at = datetime.now()
                
                return True
        
        return False
    
    def get_execution_visualization(self, execution_id: str) -> Dict[str, Any]:
        """Get visualization data for workflow execution"""
        execution = self.executions.get(execution_id)
        if not execution:
            return {}
        
        # Create stages for visualization
        stages = execution.get_execution_stages()
        
        visualization = {
            "execution_id": execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status,
            "stages": []
        }
        
        for i, stage in enumerate(stages):
            stage_data = {
                "stage_number": i + 1,
                "steps": [step.to_dict() for step in stage]
            }
            visualization["stages"].append(stage_data)
        
        return visualization
    
    def reorder_steps(self, execution_id: str, new_order: List[str]) -> bool:
        """Reorder workflow steps (if allowed by template)"""
        execution = self.executions.get(execution_id)
        if not execution:
            return False
        
        template = self.templates.get(execution.workflow_id)
        if not template or not template.get("allow_reordering", False):
            logger.warning("Step reordering not allowed for this workflow")
            return False
        
        # Validate new order maintains dependencies
        agent_to_index = {agent: i for i, agent in enumerate(new_order)}
        
        for step in execution.steps:
            if step.agent not in agent_to_index:
                return False
            
            step_index = agent_to_index[step.agent]
            for dep in step.dependencies:
                if dep not in agent_to_index or agent_to_index[dep] >= step_index:
                    logger.error(f"Invalid order: {step.agent} depends on {dep}")
                    return False
        
        # Reorder steps
        ordered_steps = []
        for agent in new_order:
            for step in execution.steps:
                if step.agent == agent:
                    ordered_steps.append(step)
                    break
        
        execution.steps = ordered_steps
        return True
    
    def export_execution_report(self, execution_id: str) -> Dict[str, Any]:
        """Export a comprehensive execution report"""
        execution = self.executions.get(execution_id)
        if not execution:
            return {}
        
        template = self.templates.get(execution.workflow_id, {})
        
        report = {
            "execution_id": execution_id,
            "workflow": {
                "id": execution.workflow_id,
                "name": template.get("name", "Unknown"),
                "description": template.get("description", "")
            },
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_minutes": None,
            "steps": [step.to_dict() for step in execution.steps],
            "summary": execution.summary
        }
        
        if execution.started_at and execution.completed_at:
            duration = (execution.completed_at - execution.started_at).total_seconds() / 60
            report["duration_minutes"] = round(duration, 2)
        
        return report

# Global instance
_engine_instance = None

def get_workflow_engine() -> WorkflowTemplateEngine:
    """Get or create the global workflow engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = WorkflowTemplateEngine()
    return _engine_instance