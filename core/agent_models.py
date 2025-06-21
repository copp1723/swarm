"""
Agent Data Models
Extracted from multi_agent_executor for better organization
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class AgentMessage:
    """Represents a message from one agent to another"""
    from_agent: str
    to_agent: str
    message: str
    timestamp: datetime
    task_id: str
    message_id: str
    response: Optional[str] = None
    response_timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "task_id": self.task_id,
            "message_id": self.message_id,
            "response": self.response,
            "response_timestamp": self.response_timestamp.isoformat() if self.response_timestamp else None
        }


@dataclass
class TaskStatus:
    """Represents the status of a multi-agent task"""
    task_id: str
    status: str  # "pending", "running", "completed", "error"
    progress: int = 0
    current_phase: str = ""
    agents_working: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    conversations: List[Dict] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    agent_messages: List[AgentMessage] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "current_phase": self.current_phase,
            "agents_working": self.agents_working,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "conversations": self.conversations,
            "results": self.results,
            "error_message": self.error_message,
            "agent_messages": [msg.to_dict() for msg in self.agent_messages]
        }
    
    def update_progress(self, progress: int, phase: Optional[str] = None) -> None:
        """Update task progress and optionally the phase"""
        self.progress = min(100, max(0, progress))
        if phase:
            self.current_phase = phase
    
    def add_agent_message(self, message: AgentMessage) -> None:
        """Add an agent-to-agent message"""
        self.agent_messages.append(message)
    
    def complete(self, results: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as completed"""
        self.status = "completed"
        self.progress = 100
        self.end_time = datetime.now()
        if results:
            self.results.update(results)
    
    def fail(self, error_message: str) -> None:
        """Mark task as failed"""
        self.status = "error"
        self.error_message = error_message
        self.end_time = datetime.now()