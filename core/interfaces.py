"""
Service Interfaces and Abstract Base Classes
Defines contracts for all services in the system
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Callable, AsyncIterator
from datetime import datetime
from dataclasses import dataclass
import asyncio


# Base service interface
class IService(ABC):
    """Base interface for all services"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup and shutdown the service"""
        pass


# Repository interfaces
class IRepository(ABC):
    """Base repository interface"""
    
    @abstractmethod
    async def get_by_id(self, id: Any) -> Optional[Any]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[Any]:
        """Get all entities"""
        pass
    
    @abstractmethod
    async def create(self, entity: Any) -> Any:
        """Create new entity"""
        pass
    
    @abstractmethod
    async def update(self, id: Any, entity: Any) -> Optional[Any]:
        """Update existing entity"""
        pass
    
    @abstractmethod
    async def delete(self, id: Any) -> bool:
        """Delete entity"""
        pass


# Agent interfaces
@dataclass
class AgentMessage:
    """Message to/from an agent"""
    content: str
    role: str = "user"  # user, assistant, system
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AgentResponse:
    """Response from an agent"""
    content: str
    agent_id: str
    metadata: Dict[str, Any] = None
    tools_used: List[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tools_used is None:
            self.tools_used = []


class IAgent(ABC):
    """Interface for AI agents"""
    
    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique agent identifier"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """List of agent capabilities"""
        pass
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> AgentResponse:
        """Process a message and return response"""
        pass
    
    @abstractmethod
    async def process_stream(self, message: AgentMessage) -> AsyncIterator[str]:
        """Process a message and stream response"""
        pass


class IAgentManager(ABC):
    """Interface for managing multiple agents"""
    
    @abstractmethod
    def register_agent(self, agent: IAgent) -> None:
        """Register an agent"""
        pass
    
    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[IAgent]:
        """Get agent by ID"""
        pass
    
    @abstractmethod
    def list_agents(self) -> List[str]:
        """List all registered agent IDs"""
        pass
    
    @abstractmethod
    async def route_message(self, agent_id: str, message: AgentMessage) -> AgentResponse:
        """Route message to specific agent"""
        pass


# MCP (Model Context Protocol) interfaces
class IMCPServer(ABC):
    """Interface for MCP servers"""
    
    @property
    @abstractmethod
    def server_id(self) -> str:
        """Server identifier"""
        pass
    
    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if server is running"""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the server"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the server"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the server"""
        pass
    
    @abstractmethod
    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        pass


class IMCPManager(ABC):
    """Interface for managing MCP servers"""
    
    @abstractmethod
    def register_server(self, server: IMCPServer) -> None:
        """Register an MCP server"""
        pass
    
    @abstractmethod
    def get_server(self, server_id: str) -> Optional[IMCPServer]:
        """Get server by ID"""
        pass
    
    @abstractmethod
    def list_servers(self) -> List[str]:
        """List all server IDs"""
        pass
    
    @abstractmethod
    async def start_all_servers(self) -> Dict[str, bool]:
        """Start all registered servers"""
        pass
    
    @abstractmethod
    async def stop_all_servers(self) -> Dict[str, bool]:
        """Stop all registered servers"""
        pass


# Task and workflow interfaces
@dataclass
class TaskDefinition:
    """Definition of a task"""
    task_id: str
    title: str
    description: str
    task_type: str
    priority: str = "medium"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    status: str  # pending, running, completed, failed
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ITaskExecutor(ABC):
    """Interface for task execution"""
    
    @abstractmethod
    async def execute_task(self, task: TaskDefinition) -> TaskResult:
        """Execute a single task"""
        pass
    
    @abstractmethod
    async def execute_tasks(self, tasks: List[TaskDefinition]) -> List[TaskResult]:
        """Execute multiple tasks"""
        pass


class IWorkflowEngine(ABC):
    """Interface for workflow execution"""
    
    @abstractmethod
    async def execute_workflow(self, workflow_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow"""
        pass
    
    @abstractmethod
    def register_workflow(self, workflow_id: str, workflow_definition: Dict[str, Any]) -> None:
        """Register a workflow definition"""
        pass
    
    @abstractmethod
    def list_workflows(self) -> List[str]:
        """List registered workflow IDs"""
        pass


# Notification interfaces
@dataclass
class Notification:
    """Notification message"""
    title: str
    message: str
    level: str = "info"  # debug, info, warning, error, critical
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


class INotificationService(ABC):
    """Interface for sending notifications"""
    
    @abstractmethod
    async def send_notification(self, notification: Notification) -> bool:
        """Send a notification"""
        pass
    
    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email notification"""
        pass
    
    @abstractmethod
    async def send_webhook(self, url: str, payload: Dict[str, Any]) -> bool:
        """Send a webhook notification"""
        pass


# Storage interfaces
class IStorageService(ABC):
    """Interface for file storage"""
    
    @abstractmethod
    async def save_file(self, path: str, content: bytes) -> str:
        """Save a file and return its identifier"""
        pass
    
    @abstractmethod
    async def get_file(self, file_id: str) -> Optional[bytes]:
        """Get file content by ID"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file"""
        pass
    
    @abstractmethod
    async def list_files(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files with optional prefix filter"""
        pass


# Configuration interfaces
class IConfigurationService(ABC):
    """Interface for configuration management"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        pass
    
    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section"""
        pass
    
    @abstractmethod
    def reload(self) -> None:
        """Reload configuration from source"""
        pass


# Monitoring interfaces
@dataclass
class Metric:
    """Performance metric"""
    name: str
    value: float
    unit: str = ""
    tags: Dict[str, str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.tags is None:
            self.tags = {}


class IMonitoringService(ABC):
    """Interface for monitoring and metrics"""
    
    @abstractmethod
    async def record_metric(self, metric: Metric) -> None:
        """Record a metric"""
        pass
    
    @abstractmethod
    async def get_metrics(self, name: str, start_time: datetime, end_time: datetime) -> List[Metric]:
        """Get metrics for a time range"""
        pass
    
    @abstractmethod
    async def record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record an event"""
        pass


# Cache interfaces
class ICacheService(ABC):
    """Interface for caching"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL in seconds"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries"""
        pass


# Event bus interfaces
@dataclass
class Event:
    """Event message"""
    event_type: str
    data: Dict[str, Any]
    source: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


EventHandler = Callable[[Event], None]


class IEventBus(ABC):
    """Interface for event bus"""
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type"""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from an event type"""
        pass
    
    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publish an event"""
        pass