import asyncio
import logging
import uuid
import os
import re
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from services.api_client import OpenRouterClient
from services.repository_service import RepositoryService
from services.mcp_manager import mcp_manager
from services.chat_history_service import chat_history_service
from utils.async_wrapper import async_manager

logger = logging.getLogger(__name__)
client = OpenRouterClient()

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
    task_id: str
    status: str  # "pending", "running", "completed", "error"
    progress: int = 0
    current_phase: str = ""
    agents_working: List[str] = None
    start_time: datetime = None
    end_time: datetime = None
    conversations: List[Dict] = None
    results: Dict[str, Any] = None
    error_message: str = ""
    agent_messages: List[AgentMessage] = None  # Track agent-to-agent communications

    def __post_init__(self):
        if self.agents_working is None:
            self.agents_working = []
        if self.conversations is None:
            self.conversations = []
        if self.results is None:
            self.results = {}
        if self.agent_messages is None:
            self.agent_messages = []
        if self.start_time is None:
            self.start_time = datetime.now()

    def to_dict(self):
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
            "agent_messages": [msg.to_dict() for msg in self.agent_messages] if self.agent_messages else []
        }

class TaskStorage:
    """Abstract base class for task storage"""

    def store_task(self, task_id: str, task_status: TaskStatus):
        raise NotImplementedError

    def get_task(self, task_id: str) -> Optional[TaskStatus]:
        raise NotImplementedError

    def update_task(self, task_id: str, **updates):
        raise NotImplementedError

    def store_message(self, task_id: str, message: Dict):
        raise NotImplementedError

class InMemoryTaskStorage(TaskStorage):
    """In-memory storage for tasks"""

    def __init__(self):
        self._tasks = {}

    def store_task(self, task_id: str, task_status: TaskStatus):
        self._tasks[task_id] = task_status

    def get_task(self, task_id: str) -> Optional[TaskStatus]:
        return self._tasks.get(task_id)

    def update_task(self, task_id: str, **updates):
        if task_id in self._tasks:
            for key, value in updates.items():
                if hasattr(self._tasks[task_id], key):
                    setattr(self._tasks[task_id], key, value)

    def store_message(self, task_id: str, message: Dict):
        if task_id in self._tasks:
            self._tasks[task_id].conversations.append(message)

class MultiAgentExecutor:
    """
    Consolidated Multi-Agent Executor that provides structured, concrete file analysis
    with robust error handling and validation.
    """

    def __init__(self, storage: TaskStorage = None, base_directory: str = None):
        self.storage = storage or InMemoryTaskStorage()
        self.base_directory = base_directory or "/Users/copp1723/Desktop"
        self.repo_service = RepositoryService(self.base_directory)
        self._running_tasks = {}
        self._agent_name_to_id_map = {}  # Map agent names to IDs for communication
        self._agent_chats = {}  # Initialize agent chats dictionary

        # Get auditor from service registry (lazy import to avoid circular dependency)
        self.auditor = None

        logger.info(f"MultiAgentExecutor initialized with base directory: {self.base_directory}")

    def _get_auditor(self):
        """Get auditor lazily to avoid circular import"""
        if self.auditor is None:
            try:
                from core.service_registry import get_service
                self.auditor = get_service('agent_auditor')
            except Exception as e:
                logger.warning(f"Could not get auditor service: {e}")
        return self.auditor

    def _build_agent_name_mapping(self, agent_configs: List[Dict]):
        """Build mapping from agent names to agent IDs for communication routing"""
        self._agent_name_to_id_map.clear()
        for config in agent_configs:
            agent_name = config.get('agent_name', config.get('agent_id'))
            agent_id = config.get('agent_id', agent_name)
            self._agent_name_to_id_map[agent_name.lower()] = agent_id
            # Also add variations
            self._agent_name_to_id_map[agent_name.replace(' ', '').lower()] = agent_id
            if agent_id != agent_name:
                self._agent_name_to_id_map[agent_id.lower()] = agent_id

    def _parse_agent_request(self, response: str, current_agent: str) -> Optional[Tuple[str, str]]:
        """Parse agent response for requests to other agents using @agent_name: message format"""
        lines = response.split('\n')

        for line in lines:
            line = line.strip()
            # Look for @agent_name: message pattern
            if line.startswith('@') and ':' in line:
                try:
                    # Extract target agent and message
                    at_part, message = line.split(':', 1)
                    target_agent_name = at_part[1:].strip()  # Remove @ symbol
                    message = message.strip()

                    # Find the actual agent ID from the name
                    target_agent_id = None
                    for name_variant, agent_id in self._agent_name_to_id_map.items():
                        if target_agent_name.lower() in name_variant or name_variant in target_agent_name.lower():
                            target_agent_id = agent_id
                            break

                    if target_agent_id and target_agent_id != current_agent and message:
                        return target_agent_id, message

                except Exception as e:
                    logger.warning(f"Error parsing agent request '{line}': {e}")
                    continue

        return None

    async def _handle_agent_to_agent_request(self, from_agent: str, to_agent: str,
                                             message: str, task_id: str, model: str) -> str:
        """Handle a request from one agent to another"""
        try:
            # Create message ID
            message_id = f"msg_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

            # Create agent message record
            agent_message = AgentMessage(
                from_agent=from_agent,
                to_agent=to_agent,
                message=message,
                timestamp=datetime.now(),
                task_id=task_id,
                message_id=message_id
            )

            # Store the message in task storage
            task = self.storage.get_task(task_id)
            if task:
                task.agent_messages.append(agent_message)

            # Get target agent's context
            if to_agent not in self._agent_chats:
                # Initialize with system message for the target agent
                from routes.agents import AGENT_PROFILES
                agent_config = next((profile for profile in AGENT_PROFILES.values()
                                   if profile['agent_id'] == to_agent), None)
                if agent_config:
                    self._agent_chats[to_agent] = [
                        {"role": "system", "content": agent_config.get("default_prompt", "You are an AI assistant.")}
                    ]
                else:
                    self._agent_chats[to_agent] = [
                        {"role": "system", "content": "You are an AI assistant helping with a collaborative task."}
                    ]

            # Add the request to target agent's context
            request_context = f"""[AGENT COMMUNICATION]
From: {from_agent}
Request: {message}

Please respond to this request from your colleague {from_agent}. Be helpful and specific in your response."""

            self._agent_chats[to_agent].append({"role": "user", "content": request_context})

            # Get response from target agent
            response = await self._get_agent_response(to_agent, model)

            # Update agent message with response
            agent_message.response = response
            agent_message.response_timestamp = datetime.now()

            # Add response to target agent's context
            self._agent_chats[to_agent].append({"role": "assistant", "content": response})

            # Also add to individual agent chat history for UI
            if to_agent not in self._agent_chats:
                self._agent_chats[to_agent] = []

            # Log the communication
            logger.info(f"Agent communication: {from_agent} -> {to_agent}: '{message[:50]}...'")
            logger.info(f"Agent response: {to_agent} -> {from_agent}: '{response[:50]}...'")

            # Send WebSocket notification for real-time updates
            await self._send_agent_communication_update(task_id, agent_message)

            return response

        except Exception as e:
            logger.error(f"Error handling agent-to-agent request: {e}")
            return f"Error: Could not get response from {to_agent}: {str(e)}"

    async def _send_agent_communication_update(self, task_id: str, agent_message: AgentMessage):
        """Send WebSocket update for agent-to-agent communication"""
        try:
            # Import here to avoid circular imports
            from utils.websocket import task_notifier

            # Send structured agent communication update
            task_notifier.send_agent_communication_update(task_id, agent_message.to_dict())

        except Exception as e:
            logger.warning(f"Failed to send WebSocket update for agent communication: {e}")

    def execute_task(self, task_description: str, agent_configs: List[Dict],
                     working_directory: str, conversation_id: int = 1,
                     enable_real_time: bool = True, sequential: bool = False, enhance_prompt: bool = True) -> Dict[str, Any]:
        """
        Execute a multi-agent task with concrete file analysis.

        Args:
            task_description: The task to execute
            agent_configs: List of agent configurations with agent_id, agent_name, model
            working_directory: Directory to analyze
            conversation_id: Conversation identifier
            enable_real_time: Enable real-time updates
        """
        # Validate inputs
        if not task_description or not agent_configs:
            return {"error": "Task description and agent configurations are required", "success": False}

        if not working_directory:
            return {"error": "Working directory is required", "success": False}

        # Resolve full path
        full_path = self._resolve_working_directory(working_directory)
        if not full_path:
            return {"error": f"Working directory not found: {working_directory}", "success": False}

        # Create task
        task_id = f"task_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

        # Build agent name mapping for communication
        self._build_agent_name_mapping(agent_configs)

        agent_names = [config.get('agent_name', config.get('agent_id')) for config in agent_configs]

        task_status = TaskStatus(
            task_id=task_id,
            status="running",
            progress=0,
            current_phase="Initializing Analysis",
            agents_working=agent_names,
            start_time=datetime.now(),
            conversations=[],
            results={
                "working_directory": full_path,
                "agents": agent_configs,
                "task_description": task_description,
                "sequential": sequential
            }
        )

        self.storage.store_task(task_id, task_status)
        self._running_tasks[task_id] = True

        # Enhance task description if enabled
        if enhance_prompt:
            enhanced_description = async_manager.run_sync(self._enhance_prompt(task_description, agent_configs[0].get('model', 'openai/gpt-4')))
            task_status.results["enhanced_task_description"] = enhanced_description
            task_status.results["original_task_description"] = task_description
        else:
            enhanced_description = task_description

        # Execute in background using thread to handle asyncio
        import threading
        def run_task():
            async_manager.run_sync(
                self._execute_structured_task(
                    task_id, enhanced_description, agent_configs, full_path, enable_real_time, sequential
                )
            )

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        return {
            "success": True,
            "task_id": task_id,
            "message": f"Multi-agent task execution started in {full_path}",
            "agents": agent_names,
            "working_directory": full_path
        }

    def start_agent_chat(self, agent_id: str, initial_message: str, model: str = None, enhance_prompt: bool = True) -> Dict[str, Any]:
        """Initialize or continue a chat with a specific agent."""
        from routes.agents import AGENT_PROFILES
        agent_config = next((profile for profile in AGENT_PROFILES.values() if profile['agent_id'] == agent_id), None)
        if not agent_config:
            return {"success": False, "error": f"Agent {agent_id} not found"}

        # Get chat history from database
        history = chat_history_service.get_history(agent_id)

        # Build messages list with system prompt
        messages = []
        if not history or history[0].get('role') != 'system':
            system_message = agent_config.get("default_prompt", "You are an AI assistant.")

            # Add MCP tools to system message
            available_tools = mcp_manager.get_all_tools()
            if available_tools:
                tool_list = "\n".join([f"- {tool['name']}: {tool['description']}" for tool in available_tools])
                tool_message = f"\n\nYou have access to these MCP tools:\n{tool_list}\n\nUse these tools to access the filesystem when needed."
                system_message += tool_message

            messages.append({"role": "system", "content": system_message})
            chat_history_service.add_message(agent_id, "system", system_message)

        # Add history
        messages.extend(history)

        # Enhance user prompt if enabled
        if enhance_prompt:
            enhanced_message = async_manager.run_sync(self._enhance_prompt(initial_message, model or agent_config['preferred_models'][0]))
        else:
            enhanced_message = initial_message

        # Check if we should add filesystem context before agent responds
        if self._should_use_filesystem_tools("", initial_message):
            filesystem_context = async_manager.run_sync(self._get_filesystem_context())
            enhanced_message = f"{enhanced_message}\n\n**Current Filesystem Context:**\n{filesystem_context}"

        messages.append({"role": "user", "content": enhanced_message})
        chat_history_service.add_message(agent_id, "user", enhanced_message)

        # Get response using centralized async manager
        response = async_manager.run_sync(self._get_agent_response_from_messages(messages, model or agent_config['preferred_models'][0]))

        chat_history_service.add_message(agent_id, "assistant", response)

        return {
            "success": True,
            "agent_id": agent_id,
            "response": response,
            "chat_history": messages + [{"role": "assistant", "content": response}],
            "enhanced": enhance_prompt and enhanced_message != initial_message,
            "original_message": initial_message if enhance_prompt else None
        }

    async def _enhance_prompt(self, user_input: str, model: str) -> str:
        """Enhance user prompt for clarity and detail while maintaining original intent."""
        enhancement_prompt = f"""Improve this query to be clear and specific. Keep it concise:

{user_input}

Improved (keep brief):"""

        messages = [
            {"role": "system", "content": "You are an expert at making prompts clear and concise. Improve clarity without adding unnecessary detail."},
            {"role": "user", "content": enhancement_prompt}
        ]

        try:
            response = await asyncio.to_thread(client.call_api, messages, model)
            if response and 'choices' in response and response['choices']:
                enhanced = response['choices'][0]['message']['content'].strip()
                logger.info(f"Prompt enhanced from: '{user_input}' to: '{enhanced}'")
                return enhanced
            return user_input  # Fallback to original
        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            return user_input  # Fallback to original

    async def _get_agent_response_from_messages(self, messages: List[Dict], model: str) -> str:
        """Get response from messages list"""
        try:
            response = await asyncio.to_thread(client.call_api, messages, model)
            if response and 'choices' in response and response['choices']:
                agent_response = response['choices'][0]['message']['content']

                # Check if agent mentions needing filesystem access and automatically use tools
                if messages and len(messages) > 0:
                    last_user_message = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), '')
                    if self._should_use_filesystem_tools(agent_response, last_user_message):
                        filesystem_info = await self._get_filesystem_context()
                        agent_response = f"{agent_response}\n\n**Filesystem Context:**\n{filesystem_info}"

                return agent_response
            return "Error: No response from agent"
        except Exception as e:
            logger.error(f"Error getting response: {e}")
            return f"Error: {str(e)}"

    async def _get_agent_response(self, agent_id: str, model: str) -> str:
        """Get response from an agent using the specified model with MCP tool access."""
        try:
            # Get chat history from database
            history = chat_history_service.get_history(agent_id)
            messages = history.copy() if history else []

            # Add system message if needed
            if not messages or messages[0].get('role') != 'system':
                from routes.agents import AGENT_PROFILES
                agent_config = next((profile for profile in AGENT_PROFILES.values() if profile['agent_id'] == agent_id), None)
                if agent_config:
                    messages.insert(0, {"role": "system", "content": agent_config.get("default_prompt", "You are an AI assistant.")})

            # Get available MCP tools
            available_tools = mcp_manager.get_all_tools()

            # Add tool calling capability to the conversation
            messages = self._agent_chats[agent_id].copy()

            # Add system message about available tools
            if available_tools:
                tool_list = "\n".join([f"- {tool['name']}: {tool['description']}" for tool in available_tools])
                tool_message = f"\n\nYou have access to these MCP tools:\n{tool_list}\n\nUse these tools to access the filesystem when needed."
                if messages and messages[0]['role'] == 'system':
                    messages[0]['content'] += tool_message

            response = await asyncio.to_thread(client.call_api, messages, model)
            if response and 'choices' in response and response['choices']:
                agent_response = response['choices'][0]['message']['content']

                # Check if agent mentions needing filesystem access and automatically use tools
                if self._should_use_filesystem_tools(agent_response, messages[-1]['content']):
                    filesystem_info = await self._get_filesystem_context()
                    agent_response = f"{agent_response}\n\n**Filesystem Context:**\n{filesystem_info}"

                return agent_response
            return "Error: No response from agent"
        except Exception as e:
            logger.error(f"Error getting response from {agent_id}: {e}")
            return f"Error: {str(e)}"

    def _should_use_filesystem_tools(self, response: str, user_message: str) -> bool:
        """Determine if filesystem tools should be used based on agent response and user message."""
        filesystem_keywords = [
            'list files', 'read file', 'check directory', 'analyze files',
            'swarm folder', 'swram folder', 'desktop', 'file contents', 'directory structure',
            'can you see', 'access', 'upload', 'folder', 'directory'
        ]

        combined_text = (response + " " + user_message).lower()
        return any(keyword in combined_text for keyword in filesystem_keywords)

    async def _get_filesystem_context(self) -> str:
        """Get filesystem context using MCP tools."""
        try:
            # Get available tools and use correct tool IDs
            available_tools = mcp_manager.get_all_tools()
            list_dir_tool = None
            for tool in available_tools:
                if 'list_directory' in tool.get('name', '') or 'list_directory' in tool.get('id', ''):
                    list_dir_tool = tool['id']
                    break

            if not list_dir_tool:
                # Fallback to direct filesystem access
                import os
                desktop_files = os.listdir('/Users/copp1723/Desktop')
                swarm_exists = 'swarm' in desktop_files
                context = f"**Desktop contents:** {', '.join(desktop_files)}"
                if swarm_exists:
                    try:
                        swarm_files = os.listdir('/Users/copp1723/Desktop/swarm')
                        context += f"\n\n**Swarm folder contents:** {', '.join(swarm_files)}"
                    except:
                        context += "\n\n**Note:** Swarm folder exists but contents not accessible"
                return context[:1500]

            # Use MCP tool
            desktop_result = await mcp_manager.call_tool(list_dir_tool, {
                "path": "/Users/copp1723/Desktop"
            })

            context = f"**Desktop contents:** {desktop_result}"

            # Try to list swarm directory
            try:
                swarm_result = await mcp_manager.call_tool(list_dir_tool, {
                    "path": "/Users/copp1723/Desktop/swarm"
                })
                context += f"\n\n**Swarm folder contents:** {swarm_result}"
            except Exception as swarm_error:
                context += "\n\n**Note:** Swarm folder not found or inaccessible"

            return context[:1500]

        except Exception as e:
            logger.error(f"Failed to get filesystem context via MCP: {e}")
            # Direct filesystem access fallback
            try:
                import os
                desktop_files = os.listdir('/Users/copp1723/Desktop')
                context = f"**Desktop contents (direct access):** {', '.join(desktop_files[:20])}"
                if 'swarm' in desktop_files:
                    try:
                        swarm_files = os.listdir('/Users/copp1723/Desktop/swarm')
                        context += f"\n\n**Swarm folder contents:** {', '.join(swarm_files[:20])}"
                    except:
                        context += "\n\n**Note:** Swarm folder exists but not accessible"
                return context
            except Exception as fallback_error:
                return f"Filesystem access error: {str(e)}. Fallback failed: {str(fallback_error)}"

    def get_agent_chat_history(self, agent_id: str) -> List[Dict]:
        """Retrieve chat history for a specific agent."""
        return self._agent_chats.get(agent_id, [])

    def clear_agent_chat_history(self, agent_id: str) -> None:
        """Clear chat history for a specific agent."""
        if agent_id in self._agent_chats:
            self._agent_chats[agent_id] = []
            logger.info(f"Cleared chat history for agent {agent_id}")

    def _get_agent_id_by_name(self, agent_name: str) -> Optional[str]:
        """Get agent ID from agent name."""
        from routes.agents import AGENT_PROFILES
        for agent_id, profile in AGENT_PROFILES.items():
            if profile.get('name') == agent_name:
                return agent_id
        return None

    def execute_collaborative_task(self, task_description: str, tagged_agents: List[str], working_directory: str, sequential: bool = False, enhance_prompt: bool = True) -> Dict[str, Any]:
        """Execute a task with tagged agents for collaboration."""
        from routes.agents import AGENT_PROFILES
        agent_configs = []
        for agent_id in tagged_agents:
            config = next((profile for profile in AGENT_PROFILES.values() if profile['agent_id'] == agent_id), None)
            if config:
                agent_configs.append({
                    "agent_id": agent_id,
                    "agent_name": config['name'],
                    "model": config['preferred_models'][0]
                })

        if not agent_configs:
            return {"success": False, "error": "No valid agents tagged for collaboration"}

        return self.execute_task(task_description, agent_configs, working_directory, sequential=sequential, enhance_prompt=enhance_prompt)

    def _resolve_working_directory(self, working_directory: str) -> Optional[str]:
        """Resolve and validate the working directory path."""
        try:
            if os.path.isabs(working_directory):
                full_path = working_directory
            else:
                full_path = os.path.join(self.base_directory, working_directory)

            # Normalize path and verify it exists
            full_path = os.path.abspath(full_path)
            if os.path.exists(full_path) and os.path.isdir(full_path):
                return full_path
            else:
                logger.error(f"Directory does not exist: {full_path}")
                return None
        except Exception as e:
            logger.error(f"Error resolving directory {working_directory}: {e}")
            return None

    async def _execute_structured_task(self, task_id: str, task_description: str,
                                         agent_configs: List[Dict], working_directory: str,
                                         enable_real_time: bool, sequential: bool = False) -> None:
        """Execute the task with structured analysis and concrete output."""
        try:
            # Phase 1: Repository Analysis
            await self._update_task_progress(task_id, 10, "Analyzing Repository Structure")
            repo_analysis = await self._analyze_repository_structure(working_directory)

            # Phase 2: Agent Collaboration
            await self._update_task_progress(task_id, 30, f"Starting Agent Collaboration {'(Sequential)' if sequential else '(Parallel)'}")

            previous_responses = []  # Store previous agent responses for sequential processing

            for i, agent_config in enumerate(agent_configs):
                agent_name = agent_config.get('agent_name', agent_config.get('agent_id'))
                model = agent_config.get('model', 'openai/gpt-4')

                phase_name = f"Agent {agent_name} Analysis"
                progress = 30 + (50 * i // len(agent_configs))
                await self._update_task_progress(task_id, progress, phase_name)

                # Execute agent analysis with structured prompts
                if sequential and previous_responses:
                    # For sequential processing, include previous agent responses
                    agent_response = await self._execute_sequential_agent_analysis(
                        agent_name, model, task_description, repo_analysis, working_directory, previous_responses, task_id
                    )

                    # Check for agent-to-agent communication requests in sequential mode
                    agent_id = agent_config.get('agent_id', agent_name)
                    agent_request = self._parse_agent_request(agent_response, agent_id)

                    if agent_request:
                        target_agent_id, request_message = agent_request
                        logger.info(f"Agent {agent_id} (sequential) is requesting help from {target_agent_id}")

                        # Handle the agent-to-agent request
                        response_from_colleague = await self._handle_agent_to_agent_request(
                            agent_id, target_agent_id, request_message, task_id, model
                        )

                        # Append the response to the original agent's output
                        agent_response += f"\n\n**Response from {target_agent_id}:**\n{response_from_colleague}"
                else:
                    agent_response = await self._execute_agent_analysis(
                        agent_name, model, task_description, repo_analysis, working_directory, task_id
                    )

                # Check for agent-to-agent communication requests
                agent_id = agent_config.get('agent_id', agent_name)
                agent_request = self._parse_agent_request(agent_response, agent_id)

                if agent_request:
                    target_agent_id, request_message = agent_request
                    logger.info(f"Agent {agent_id} is requesting help from {target_agent_id}")

                    # Handle the agent-to-agent request
                    response_from_colleague = await self._handle_agent_to_agent_request(
                        agent_id, target_agent_id, request_message, task_id, model
                    )

                    # Append the response to the original agent's output
                    agent_response += f"\n\n**Response from {target_agent_id}:**\n{response_from_colleague}"

                # Validate and store response
                if self._validate_concrete_analysis(agent_response):
                    await self._add_conversation_entry(task_id, agent_name, agent_response)
                    if sequential:
                        previous_responses.append({
                            "agent": agent_name,
                            "response": agent_response
                        })
                else:
                    # Retry with stricter prompt if validation fails
                    logger.warning(f"Agent {agent_name} response lacks concrete analysis, retrying...")
                    retry_response = await self._retry_with_strict_prompt(
                        agent_name, model, task_description, repo_analysis, working_directory
                    )
                    await self._add_conversation_entry(task_id, agent_name, retry_response)
                    if sequential:
                        previous_responses.append({
                            "agent": agent_name,
                            "response": retry_response
                        })

            # Phase 3: Consolidation Summary by General Assistant
            await self._update_task_progress(task_id, 85, "Consolidating Findings")
            executive_summary = await self._generate_executive_summary(
                task_id, task_description, agent_configs, working_directory
            )

            if executive_summary:
                await self._add_conversation_entry(task_id, "General Assistant", executive_summary)

            # Phase 4: Generate Summary
            await self._update_task_progress(task_id, 95, "Generating Final Summary")
            summary = await self._generate_task_summary(task_id, agent_configs)

            # Complete task
            await self._complete_task(task_id, summary)

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            await self._error_task(task_id, str(e))
        finally:
            self._running_tasks.pop(task_id, None)

    async def _get_sample_files_for_agent(self, working_directory: str) -> str:
        """Get a sample of files in the working directory to help agents understand what's available."""
        try:
            # Try to use MCP filesystem tools first
            available_tools = mcp_manager.get_all_tools()
            list_dir_tool = None
            read_file_tool = None

            for tool in available_tools:
                if 'list_directory' in tool.get('name', '').lower():
                    list_dir_tool = tool.get('name')
                elif 'read_file' in tool.get('name', '').lower():
                    read_file_tool = tool.get('name')

            if list_dir_tool:
                # Use MCP to list directory
                result = await mcp_manager.call_tool(list_dir_tool, {
                    "path": working_directory
                })

                # Extract file names from the result
                if isinstance(result, dict) and 'content' in result:
                    content = result['content']
                    if isinstance(content, list) and content:
                        # Extract text content
                        text_content = content[0].get('text', '') if content[0].get('type') == 'text' else str(content)
                        return f"Directory listing from MCP:\n{text_content[:500]}..."
                elif isinstance(result, str):
                    return f"Directory listing from MCP:\n{result[:500]}..."
                else:
                    return f"MCP result: {str(result)[:500]}..."

            # Fallback to direct filesystem access
            import os
            if os.path.exists(working_directory):
                files = os.listdir(working_directory)
                sample = files[:10]  # First 10 files
                return f"Files found (first 10): {', '.join(sample)}"
            else:
                return f"Directory {working_directory} not accessible via direct filesystem"

        except Exception as e:
            logger.error(f"Error getting sample files: {e}")
            return f"Error accessing directory: {str(e)}"

    async def _analyze_repository_structure(self, working_directory: str) -> Dict[str, Any]:
        """Analyze the repository structure using the RepositoryService."""
        try:
            analysis = self.repo_service.analyze_repository(working_directory, include_content=False)
            logger.info(f"Repository analysis complete: {analysis['total_files']} files found")
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing repository structure: {e}")
            return {"error": str(e), "total_files": 0}

    async def _execute_sequential_agent_analysis(self, agent_name: str, model: str, task_description: str,
                                                  repo_analysis: Dict, working_directory: str,
                                                  previous_responses: List[Dict], task_id: str) -> str:
        """Execute analysis for a specific agent with context from previous agents."""
        # Create structured prompt that includes previous agent outputs
        previous_context = "\n\n".join([
            f"### Previous Analysis by {resp['agent']}:\n{resp['response'][:1000]}..."
            if len(resp['response']) > 1000 else f"### Previous Analysis by {resp['agent']}:\n{resp['response']}"
            for resp in previous_responses
        ])

        structured_prompt = f"""You are {agent_name}, an expert software engineer. You must provide a structured analysis report with concrete file references and specific code examples.

TASK: {task_description}

AGENT COMMUNICATION: You can request help from other agents using the format: @AgentName: your question or request
Available agents: {', '.join(self._agent_name_to_id_map.keys())}
Example: @Developer: Can you review this code structure?
Example: @Security: What vulnerabilities do you see in this authentication flow?

PREVIOUS AGENT ANALYSES:
{previous_context}

REPOSITORY CONTEXT:
- Working Directory: {working_directory}
- Total Files: {repo_analysis.get('total_files', 0)}
- Code Files: {', '.join([f['relative_path'] for f in repo_analysis.get('file_categories', {}).get('code', [])][:10])}
- Priority Files: {', '.join(repo_analysis.get('priority_files', []))}
- Filesystem Access: You have full access to the local filesystem at /Users/copp1723/Desktop. Use this to read, analyze, or modify files as needed for the task.

IMPORTANT: Build upon the previous agents' analyses. Reference their findings and extend or refine their work.

REQUIRED OUTPUT FORMAT:
### {agent_name} Analysis Report

**Building on Previous Work:**
- [Reference specific findings from previous agents]
- [How your analysis extends or refines their work]

**Files Analyzed:** [List specific files you examined]

**Key Findings:**
- [Specific finding with file reference]
- [Another specific finding with line numbers if applicable]

**Code Issues Found:**
- **File:** `filename.ext`
  - **Line X:** [Specific issue description]
  - **Recommendation:** [Concrete action to take]

**Concrete Actions Taken:**
- [List specific actions like "Analyzed X files", "Identified Y issues"]

**Next Steps:**
1. [Specific actionable step]
2. [Another specific step]

You MUST reference actual files and provide concrete analysis. Generic responses will be rejected.
"""

        try:
            messages = [
                {"role": "system", "content": f"You are {agent_name}. Provide concrete, file-specific analysis only. Build on previous agent work. You have filesystem access at /Users/copp1723/Desktop."},
                {"role": "user", "content": structured_prompt}
            ]

            response = await asyncio.to_thread(client.call_api, messages, model)
            if response and 'choices' in response and response['choices']:
                return response['choices'][0]['message']['content']
            else:
                return f"Error: No response from {agent_name}"

        except Exception as e:
            logger.error(f"Error in sequential agent {agent_name} analysis: {e}")
            return f"Error in {agent_name} analysis: {str(e)}"

    async def _execute_agent_analysis(self, agent_name: str, model: str, task_description: str,
                                      repo_analysis: Dict, working_directory: str, task_id: str) -> str:
        """Execute structured analysis for a specific agent."""
        # Get a sample of actual files to help the agent
        sample_files = await self._get_sample_files_for_agent(working_directory)

        # Create direct, action-oriented prompt
        structured_prompt = f"""IMMEDIATE TASK: {task_description}

DIRECTORY TO ANALYZE: {working_directory}

ACTION STEPS:
1. RUN: list_directory on {working_directory}
2. READ: Key files like package.json, README, main files
3. SEARCH: For errors, conflicts, missing imports

WHAT TO REPORT (with examples):
✓ Syntax errors: "app.js line 45: Missing closing bracket"
✓ Import errors: "main.py line 10: 'requests' not imported"
✓ Merge conflicts: "index.html line 89: Unresolved <<<<<<< HEAD"
✓ Missing deps: "package.json missing: express (used in app.js)"

AGENT HELP: Use @AgentName to ask others
Available: {', '.join(self._agent_name_to_id_map.keys())}

IMPORTANT: Only report what you ACTUALLY find in files. No guessing.
If MCP tools fail, say: "Cannot access {working_directory} - MCP error"
"""

        try:
            messages = [
                {"role": "system", "content": f"""You are {agent_name}. USE THE MCP TOOLS:
- list_directory: See what files exist
- read_file: Read file contents
- search_files: Find specific patterns

RULES:
1. ALWAYS use tools first, talk second
2. Report line numbers and exact code
3. NO generic advice - only specific findings
4. If tools fail, say "MCP tools not working"

Current directory: {working_directory}"""},
                {"role": "user", "content": structured_prompt}
            ]

            response = await asyncio.to_thread(client.call_api, messages, model)
            if response and 'choices' in response and response['choices']:
                return response['choices'][0]['message']['content']
            else:
                return f"Error: No response from {agent_name}"

        except Exception as e:
            logger.error(f"Error in agent {agent_name} analysis: {e}")
            return f"Error in {agent_name} analysis: {str(e)}"

    def _validate_concrete_analysis(self, response: str) -> bool:
        """Validate that the response contains concrete file analysis."""
        if not response:
            return False

        # Check for concrete indicators
        concrete_indicators = [
            r'`[^`]+\.(py|js|ts|java|cpp|c|go|rs|json|yaml|yml|md)`',  # File references
            r'Line \d+',  # Line number references
            r'function \w+',  # Function references
            r'class \w+',  # Class references
            r'Analyzed \d+',  # Quantified analysis
        ]

        matches = sum(1 for pattern in concrete_indicators if re.search(pattern, response, re.IGNORECASE))

        # Require at least 2 concrete indicators
        return matches >= 2

    async def _retry_with_strict_prompt(self, agent_name: str, model: str, task_description: str,
                                        repo_analysis: Dict, working_directory: str) -> str:
        """Retry analysis with an even stricter prompt that demands specificity."""

        strict_prompt = f"""CRITICAL: Your previous response was too generic. You MUST provide specific file analysis.

MANDATORY REQUIREMENTS:
1. Reference at least 3 specific files by name
2. Include actual line numbers or code snippets
3. Provide quantified analysis (e.g., "Found 5 issues", "Analyzed 12 files")
4. Give concrete recommendations with file paths

TASK: {task_description}
DIRECTORY: {working_directory}
FILESYSTEM ACCESS: You have full access to /Users/copp1723/Desktop. Use this to analyze or modify files.

Format your response with these EXACT sections:
### CONCRETE FILE ANALYSIS
- **Examined Files:** [List exact file paths]
- **Code Issues:** [File:Line - Specific problem]
- **Metrics:** [Numbers: X files, Y issues, Z recommendations]

If you provide another generic response, you have failed this task.
"""

        try:
            messages = [
                {"role": "system", "content": f"You are {agent_name}. BE SPECIFIC. Reference actual files and code. Filesystem access at /Users/copp1723/Desktop."},
                {"role": "user", "content": strict_prompt}
            ]

            response = await asyncio.to_thread(client.call_api, messages, model)
            if response and 'choices' in response and response['choices']:
                return response['choices'][0]['message']['content']
            else:
                return f"ERROR: {agent_name} failed to provide concrete analysis after retry"

        except Exception as e:
            logger.error(f"Error in strict retry for {agent_name}: {e}")
            return f"ERROR: {agent_name} retry failed: {str(e)}"

    async def _generate_executive_summary(self, task_id: str, task_description: str,
                                          agent_configs: List[Dict], working_directory: str) -> Optional[str]:
        """Generate an executive summary by having the General Assistant consolidate all findings."""
        try:
            task = self.storage.get_task(task_id)
            if not task or not task.conversations:
                return None

            # Collect all agent findings except any previous General Assistant entries
            agent_findings = []
            for conv in task.conversations:
                if conv.get('agent_id') != 'General Assistant':
                    agent_findings.append({
                        'agent': conv.get('agent_id'),
                        'findings': conv.get('content', '')
                    })

            if not agent_findings:
                return None

            # Create consolidated findings text
            findings_text = "\n\n".join([
                f"### {finding['agent']} Findings:\n{finding['findings']}"
                for finding in agent_findings
            ])

            # Create executive summary prompt
            summary_prompt = f"""You are the General Assistant tasked with creating an executive summary of a collaborative code review.

ORIGINAL TASK: {task_description}
WORKING DIRECTORY: {working_directory}
AGENTS INVOLVED: {[config.get('agent_name', config.get('agent_id')) for config in agent_configs]}

AGENT FINDINGS:
{findings_text}

Your task is to consolidate these findings into a comprehensive executive summary. Format your response as follows:

# Executive Summary: Code Review Analysis

## Overview
[Brief overview of the analysis scope and what was reviewed]

## Key Findings
### Critical Issues
- [List the most critical issues found by any agent, with file references]
- [Another critical issue]

### Security Concerns
- [Security vulnerabilities identified]
- [Security recommendations]

### Code Quality Issues
- [Code quality problems found]
- [Technical debt identified]

### Testing & QA Gaps
- [Testing issues identified]
- [Quality assurance concerns]

## Recommendations
### Immediate Actions Required
1. [Most urgent action with specific file/line references]
2. [Second most urgent action]
3. [Third priority action]

### Short-term Improvements (1-2 weeks)
1. [Improvement with timeline]
2. [Another improvement]

### Long-term Strategic Items (1-3 months)
1. [Strategic improvement]
2. [Architecture or process improvement]

## Risk Assessment
- **High Risk**: [Items that could cause immediate problems]
- **Medium Risk**: [Items that should be addressed soon]
- **Low Risk**: [Items for future consideration]

## Next Steps
1. [Immediate next step with owner/timeline]
2. [Second next step]
3. [Third next step]

## Files Requiring Attention
- [List of specific files that need work, based on agent findings]

## Summary
[2-3 sentence overall assessment of the codebase health and priority actions]

Consolidate and prioritize the findings from all agents. Remove duplicates, synthesize related issues, and provide clear actionable guidance."""

            # Get General Assistant model (prefer a capable model for summary)
            summary_model = "openai/gpt-4o"  # Use a reliable model for executive summary

            messages = [
                {"role": "system", "content": "You are an experienced Technical Lead creating an executive summary. Synthesize findings from multiple specialists into clear, actionable recommendations for leadership."},
                {"role": "user", "content": summary_prompt}
            ]

            response = await asyncio.to_thread(client.call_api, messages, summary_model)
            if response and 'choices' in response and response['choices']:
                summary_content = response['choices'][0]['message']['content']
                logger.info(f"Executive summary generated for task {task_id}")
                return summary_content
            else:
                logger.error(f"Failed to generate executive summary for task {task_id}")
                return None

        except Exception as e:
            logger.error(f"Error generating executive summary for task {task_id}: {e}")
            return None

    async def _update_task_progress(self, task_id: str, progress: int, phase: str):
        """Update task progress and phase."""
        self.storage.update_task(task_id, progress=progress, current_phase=phase)

    async def _add_conversation_entry(self, task_id: str, agent_name: str, content: str):
        """Add a conversation entry to the task."""
        message = {
            "agent_id": agent_name,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "role": "agent"
        }
        self.storage.store_message(task_id, message)

        # Also add to individual agent's chat history
        agent_id = self._get_agent_id_by_name(agent_name)
        if agent_id:
            # Initialize chat history if not exists
            if agent_id not in self._agent_chats:
                self._agent_chats[agent_id] = []

            # Add collaboration context
            collab_message = f"[Collaboration Task #{task_id}]\n{content}"
            self._agent_chats[agent_id].append({"role": "assistant", "content": collab_message})

    async def _generate_task_summary(self, task_id: str, agent_configs: List[Dict]) -> Dict[str, Any]:
        """Generate a comprehensive summary of the task execution."""
        task = self.storage.get_task(task_id)
        if not task:
            return {"error": "Task not found"}

        summary = {
            "task_id": task_id,
            "execution_time": (datetime.now() - task.start_time).total_seconds(),
            "agents_involved": len(agent_configs),
            "total_conversations": len(task.conversations),
            "working_directory": task.results.get("working_directory"),
            "status": "completed"
        }

        return summary

    async def _complete_task(self, task_id: str, summary: Dict[str, Any]):
        """Mark task as completed with summary."""
        self.storage.update_task(
            task_id,
            status="completed",
            progress=100,
            current_phase="Completed",
            end_time=datetime.now(),
            results=summary
        )
        logger.info(f"Task {task_id} completed successfully")

    async def _error_task(self, task_id: str, error_message: str):
        """Mark task as failed with error message."""
        self.storage.update_task(
            task_id,
            status="error",
            current_phase="Error",
            end_time=datetime.now(),
            error_message=error_message
        )
        logger.error(f"Task {task_id} failed: {error_message}")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task."""
        task = self.storage.get_task(task_id)
        if not task:
            return None
        # Task is already a dict from storage
        return task

    def get_task_conversation(self, task_id: str, offset: int = 0) -> Optional[Dict[str, Any]]:
        """Gets the conversation for a task, including agent-to-agent communications."""
        task = self.storage.get_task(task_id)
        if not task:
            return None

        # Include both regular conversations and agent communications
        all_communications = []

        # Add regular conversations
        for conv in task.conversations[offset:]:
            all_communications.append({
                'type': 'conversation',
                'timestamp': conv.get('timestamp'),
                'agent_id': conv.get('agent_id'),
                'content': conv.get('content'),
                'role': conv.get('role')
            })

        # Add agent-to-agent communications
        for agent_msg in task.agent_messages:
            all_communications.append({
                'type': 'agent_communication',
                'timestamp': agent_msg.timestamp.isoformat(),
                'from_agent': agent_msg.from_agent,
                'to_agent': agent_msg.to_agent,
                'message': agent_msg.message,
                'response': agent_msg.response,
                'response_timestamp': agent_msg.response_timestamp.isoformat() if agent_msg.response_timestamp else None,
                'message_id': agent_msg.message_id
            })

        # Sort by timestamp
        all_communications.sort(key=lambda x: x.get('timestamp', ''))

        return {
            "conversations": task.conversations[offset:],
            "agent_communications": [msg.to_dict() for msg in task.agent_messages],
            "all_communications": all_communications,
            "offset": offset,
            "total": len(task.conversations)
        }

    def list_active_tasks(self) -> List[str]:
        """List all currently active task IDs."""
        return list(self._running_tasks.keys())