"""
Agent Task Model for Email-to-Task Processing
Defines the structure for tasks extracted from emails
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
from config.config_loader import get_config_loader


class TaskPriority(Enum):
    """Task priority levels"""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    @classmethod
    def from_email_markers(cls, subject: str, body: str) -> 'TaskPriority':
        """Determine priority from email content markers"""
        content = f"{subject} {body}".lower()
        config = get_config_loader()
        
        # Use configuration for priority keywords
        if any(marker in content for marker in config.get_priority_keywords('urgent')):
            return cls.URGENT
        elif any(marker in content for marker in config.get_priority_keywords('high')):
            return cls.HIGH
        elif any(marker in content for marker in config.get_priority_keywords('low')):
            return cls.LOW
        else:
            return cls.MEDIUM


class TaskType(Enum):
    """Types of tasks that can be extracted from emails"""
    CODE_REVIEW = "code_review"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    INVESTIGATION = "investigation"
    GENERAL = "general"
    
    @classmethod
    def detect_from_content(cls, subject: str, body: str) -> 'TaskType':
        """Detect task type from email content"""
        content = f"{subject} {body}".lower()
        config = get_config_loader()
        
        # Use configuration for task type keywords
        task_types = [
            (cls.CODE_REVIEW, 'code_review'),
            (cls.BUG_REPORT, 'bug_report'),
            (cls.FEATURE_REQUEST, 'feature_request'),
            (cls.DOCUMENTATION, 'documentation'),
            (cls.DEPLOYMENT, 'deployment'),
            (cls.INVESTIGATION, 'investigation')
        ]
        
        for task_type, config_key in task_types:
            keywords = config.get_task_type_keywords(config_key)
            if any(keyword in content for keyword in keywords):
                return task_type
        
        return cls.GENERAL


@dataclass
class EmailMetadata:
    """Metadata from the original email"""
    message_id: str
    sender: str
    recipients: List[str]
    subject: str
    timestamp: datetime
    cc: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class TaskRequirements:
    """Extracted requirements and constraints for the task"""
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)


@dataclass
class AgentAssignment:
    """Agent assignment for the task"""
    primary_agent: str
    supporting_agents: List[str] = field(default_factory=list)
    reason: str = ""
    
    @classmethod
    def from_task_type(cls, task_type: TaskType, content: str = "") -> 'AgentAssignment':
        """Determine agent assignment based on task type"""
        config = get_config_loader()
        
        # Get assignment from configuration
        assignment_config = config.get_task_assignment(task_type.value)
        
        if assignment_config:
            return cls(
                primary_agent=assignment_config.get('primary', 'general_01'),
                supporting_agents=assignment_config.get('supporting', []),
                reason=assignment_config.get('reason', f"Assignment for {task_type.value}")
            )
        
        # Fallback to general agent if not configured
        return cls(
            primary_agent="general_01",
            supporting_agents=[],
            reason="Default assignment - no specific configuration found"
        )


@dataclass
class AgentTask:
    """
    Structured task extracted from an email for agent processing
    """
    # Core identifiers
    task_id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Task details
    title: str = ""
    description: str = ""
    task_type: TaskType = TaskType.GENERAL
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Email source
    email_metadata: Optional[EmailMetadata] = None
    
    # Requirements and constraints
    requirements: TaskRequirements = field(default_factory=TaskRequirements)
    
    # Agent assignment
    agent_assignment: Optional[AgentAssignment] = None
    
    # Processing metadata
    status: str = "pending"
    processed: bool = False
    processing_notes: List[str] = field(default_factory=list)
    
    # Additional context
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for JSON serialization"""
        return {
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "email_metadata": {
                "message_id": self.email_metadata.message_id,
                "sender": self.email_metadata.sender,
                "recipients": self.email_metadata.recipients,
                "subject": self.email_metadata.subject,
                "timestamp": self.email_metadata.timestamp.isoformat()
            } if self.email_metadata else None,
            "requirements": {
                "deadline": self.requirements.deadline.isoformat() if self.requirements.deadline else None,
                "dependencies": self.requirements.dependencies,
                "success_criteria": self.requirements.success_criteria,
                "constraints": self.requirements.constraints,
                "deliverables": self.requirements.deliverables
            },
            "agent_assignment": {
                "primary_agent": self.agent_assignment.primary_agent,
                "supporting_agents": self.agent_assignment.supporting_agents,
                "reason": self.agent_assignment.reason
            } if self.agent_assignment else None,
            "status": self.status,
            "processed": self.processed,
            "processing_notes": self.processing_notes,
            "context": self.context,
            "tags": self.tags
        }
    
    def get_task_prompt(self) -> str:
        """Generate a prompt for the assigned agent"""
        prompt_parts = [
            f"Task: {self.title}",
            f"Type: {self.task_type.value}",
            f"Priority: {self.priority.value}",
            f"\nDescription:\n{self.description}"
        ]
        
        if self.requirements.deadline:
            prompt_parts.append(f"\nDeadline: {self.requirements.deadline}")
            
        if self.requirements.success_criteria:
            prompt_parts.append(f"\nSuccess Criteria:\n" + "\n".join(f"- {c}" for c in self.requirements.success_criteria))
            
        if self.requirements.deliverables:
            prompt_parts.append(f"\nDeliverables:\n" + "\n".join(f"- {d}" for d in self.requirements.deliverables))
            
        if self.email_metadata:
            prompt_parts.append(f"\nRequested by: {self.email_metadata.sender}")
            
        return "\n".join(prompt_parts)