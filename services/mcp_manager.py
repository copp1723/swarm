import json
import asyncio
import subprocess
import os
import shutil
import platform
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
from services.config_manager import ConfigManager
import threading
from concurrent.futures import ThreadPoolExecutor, Future
import queue

logger = logging.getLogger(__name__)

@dataclass
class MCPMessage:
    """MCP protocol message structure"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class MCPServer:
    """Enhanced MCP server with proper async loop handling"""
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process = None
        self.tools = []
        self.resources = []
        self.status = "stopped"
        self.message_id_counter = 0
        self.error_message = None
        self.last_heartbeat = None
        self._loop = None  # Store the loop this server runs in
        self._reader = None
        self._writer = None
        self._read_task = None
        self._response_futures = {}  # Store futures for pending responses
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"mcp-{name}")

    def get_next_id(self) -> str:
        """Generate next message ID"""
        self.message_id_counter += 1
        return f"{self.name}_{self.message_id_counter}"

    async def validate_prerequisites(self) -> bool:
        """Validate that server prerequisites are met with detailed checks"""
        try:
            command = self.config.get("command", "")
            if not shutil.which(command):
                self.error_message = f"Command '{command}' not found in PATH"
                logger.warning(f"MCP Server {self.name}: {self.error_message}")
                
                # Check if this server is disabled via environment variable
                if os.getenv('DISABLE_MCP_FILESYSTEM', '').lower() == 'true' and 'filesystem' in self.name.lower():
                    logger.info(f"MCP Server {self.name} disabled by environment variable")
                    return False
                    
                # For production environments, allow graceful degradation
                if os.getenv('FLASK_ENV') == 'production':
                    logger.warning(f"Production environment: allowing graceful degradation for {self.name}")
                    return False
                
                return False
            return True
        except Exception as e:
            self.error_message = f"Validation failed: {e}"
            logger.error(f"MCP Server {self.name}: {self.error_message}")
            return False

    async def start(self):
        """Start the MCP server process with enhanced error handling"""
        try:
            if not await self.validate_prerequisites():
                self.status = "error"
                return
            
            command = self.config.get("command", "")
            args = self.config.get("args", [])
            env = {**os.environ, **self.config.get("env", {})}
            cwd = self.config.get("cwd", None)
            
            # Store the current event loop
            self._loop = asyncio.get_running_loop()
            
            logger.info(f"Starting MCP server {self.name}: {command} {' '.join(args)}")
            self.process = await asyncio.create_subprocess_exec(
                command, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd
            )
            
            # Store reader/writer references
            self._reader = self.process.stdout
            self._writer = self.process.stdin
            
            # Start background reader task
            self._read_task = asyncio.create_task(self._read_responses())
            
            await asyncio.sleep(1)
            
            if self.process.returncode is not None:
                stderr = await self.process.stderr.read()
                self.error_message = f"Process exited immediately: {stderr.decode()}"
                self.status = "error"
                logger.error(f"MCP Server {self.name}: {self.error_message}")
                return

            await self.initialize()
            self.status = "running"
            self.last_heartbeat = self._loop.time()
            logger.info(f"Successfully started MCP server: {self.name}")

        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Failed to start MCP server {self.name}: {e}")
            self.status = "error"
            raise

    async def _read_responses(self):
        """Background task to read responses from the server"""
        while self._reader and not self._reader.at_eof():
            try:
                line = await self._reader.readline()
                if not line:
                    break
                    
                try:
                    response_data = json.loads(line.decode().strip())
                    response_id = response_data.get("id")
                    
                    if response_id and response_id in self._response_futures:
                        # Complete the future with the response
                        future = self._response_futures.pop(response_id)
                        if not future.cancelled():
                            response = MCPMessage(
                                jsonrpc=response_data.get("jsonrpc", "2.0"),
                                id=response_id,
                                result=response_data.get("result"),
                                error=response_data.get("error")
                            )
                            future.set_result(response)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error for server {self.name}: {e}")
                except Exception as e:
                    logger.error(f"Error processing response for server {self.name}: {e}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading from server {self.name}: {e}")
                break

    async def initialize(self):
        """Initialize MCP connection with timeout and better error handling"""
        try:
            init_msg = MCPMessage(
                id=self.get_next_id(),
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}},
                    "clientInfo": {"name": "mcp-executive-interface", "version": "1.0.0"}
                }
            )
            response = await asyncio.wait_for(self.send_message(init_msg), timeout=10.0)
            if response and not response.error:
                await self.list_tools()
                await self.list_resources()
                logger.info(f"MCP server {self.name} initialized successfully with {len(self.tools)} tools")
            else:
                error_msg = response.error if response else "No response"
                raise Exception(f"Initialize failed: {error_msg}")
        except asyncio.TimeoutError:
            raise Exception("Initialize request timed out")
        except Exception as e:
            logger.error(f"Failed to initialize MCP server {self.name}: {e}")
            raise

    async def send_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Send message and wait for response using futures"""
        if not self.process or not self._writer:
            raise Exception("MCP server not running")
            
        # Ensure we're in the correct event loop
        if asyncio.get_running_loop() != self._loop:
            # We're in a different loop, need to schedule in the correct one
            return await self._send_message_cross_loop(message)
            
        try:
            # Create a future for this response
            response_future = self._loop.create_future()
            self._response_futures[message.id] = response_future
            
            # Send the message
            msg_dict = {
                "jsonrpc": message.jsonrpc,
                "id": message.id,
                "method": message.method,
                "params": message.params
            }
            msg_json = json.dumps(msg_dict) + "\n"
            self._writer.write(msg_json.encode())
            await self._writer.drain()
            
            # Wait for the response
            return await asyncio.wait_for(response_future, timeout=30.0)
            
        except asyncio.TimeoutError:
            self._response_futures.pop(message.id, None)
            logger.error(f"Message timeout for server {self.name}")
            return None
        except Exception as e:
            self._response_futures.pop(message.id, None)
            logger.error(f"Error sending message to {self.name}: {e}")
            return None

    async def _send_message_cross_loop(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Send message from a different event loop"""
        future = Future()
        
        async def _send():
            try:
                result = await self.send_message(message)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
        
        # Schedule the coroutine in the server's loop
        asyncio.run_coroutine_threadsafe(_send(), self._loop)
        
        # Wait for the result
        return future.result(timeout=35.0)

    async def list_tools(self):
        """Get list of available tools with error handling"""
        try:
            msg = MCPMessage(id=self.get_next_id(), method="tools/list", params={})
            response = await self.send_message(msg)
            if response and response.result:
                self.tools = response.result.get("tools", [])
                logger.info(f"Server {self.name} has {len(self.tools)} tools: {[t.get('name') for t in self.tools]}")
        except Exception as e:
            logger.error(f"Failed to list tools for {self.name}: {e}")

    async def list_resources(self):
        """Get list of available resources with error handling"""
        try:
            msg = MCPMessage(id=self.get_next_id(), method="resources/list", params={})
            response = await self.send_message(msg)
            if response and response.result:
                self.resources = response.result.get("resources", [])
                logger.info(f"Server {self.name} has {len(self.resources)} resources")
        except Exception as e:
            logger.error(f"Failed to list resources for {self.name}: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool with cross-loop support"""
        msg = MCPMessage(
            id=self.get_next_id(),
            method="tools/call",
            params={"name": tool_name, "arguments": arguments}
        )
        
        # Check if we're in the same loop
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, we'll need to run in the server's loop
            return await self._call_tool_sync(tool_name, arguments)
            
        if current_loop != self._loop:
            # Different loop, use cross-loop communication
            future = Future()
            
            async def _call():
                try:
                    response = await self.send_message(msg)
                    if response:
                        if response.error:
                            future.set_exception(Exception(f"Tool call error: {response.error}"))
                        else:
                            future.set_result(response.result)
                    else:
                        future.set_exception(Exception("No response from server"))
                except Exception as e:
                    future.set_exception(e)
            
            asyncio.run_coroutine_threadsafe(_call(), self._loop)
            return future.result(timeout=35.0)
        else:
            # Same loop, call directly
            response = await self.send_message(msg)
            if response:
                if response.error:
                    raise Exception(f"Tool call error: {response.error}")
                return response.result
            else:
                raise Exception("No response from server")

    def _call_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Synchronous wrapper for tool calls from non-async contexts"""
        future = Future()
        
        async def _call():
            try:
                result = await self.call_tool(tool_name, arguments)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
        
        asyncio.run_coroutine_threadsafe(_call(), self._loop)
        return future.result(timeout=35.0)

    async def health_check(self) -> bool:
        """Perform health check on the server"""
        try:
            if not self.process:
                return False
            if self.process.returncode is not None:
                self.status = "stopped"
                return False
            ping_msg = MCPMessage(id=self.get_next_id(), method="ping", params={})
            response = await asyncio.wait_for(self.send_message(ping_msg), timeout=5.0)
            if response:
                self.last_heartbeat = self._loop.time()
                return True
            return False
        except Exception:
            return False

    async def stop(self):
        """Stop the MCP server gracefully"""
        if self._read_task:
            self._read_task.cancel()
            
        if self.process:
            try:
                if self.status == "running":
                    try:
                        shutdown_msg = MCPMessage(id=self.get_next_id(), method="shutdown", params={})
                        await asyncio.wait_for(self.send_message(shutdown_msg), timeout=2.0)
                    except:
                        pass
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            finally:
                self.process = None
                self.status = "stopped"
                self._executor.shutdown(wait=False)
                logger.info(f"Stopped MCP server: {self.name}")

class EnhancedMCPManager:
    """Enhanced MCP Manager with proper async loop isolation"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.config_manager = ConfigManager()
        self._health_check_task = None
        self._mcp_loop = None
        self._mcp_thread = None
        self._started = False

    def _start_event_loop(self):
        """Start the dedicated MCP event loop in a separate thread"""
        self._mcp_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._mcp_loop)
        self._mcp_loop.run_forever()

    def _ensure_loop_running(self):
        """Ensure the MCP event loop is running"""
        if not self._mcp_thread or not self._mcp_thread.is_alive():
            self._mcp_thread = threading.Thread(target=self._start_event_loop, daemon=True)
            self._mcp_thread.start()
            # Give the loop time to start
            import time
            time.sleep(0.1)

    def load_config(self) -> bool:
        """Load MCP configuration using ConfigManager"""
        return self.config_manager.load_config()

    async def start_all_servers(self):
        """Start all configured MCP servers"""
        # This method might be called from the main event loop
        # We need to ensure operations happen in the MCP loop
        self._ensure_loop_running()
        
        if not self.config_manager.config:
            if not self.load_config():
                logger.error("Failed to load MCP configuration")
                return
        
        # Schedule the actual start in the MCP loop
        future = asyncio.run_coroutine_threadsafe(
            self._start_all_servers_internal(),
            self._mcp_loop
        )
        
        # Wait for completion
        future.result()
        self._started = True

    async def _start_all_servers_internal(self):
        """Internal method to start servers in the MCP loop"""
        tasks = []
        for server_name, server_config in self.config_manager.config.get("mcpServers", {}).items():
            if server_config.get("enabled", True):
                task = asyncio.create_task(self.start_server(server_name, server_config))
                tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"Started {successful}/{len(tasks)} MCP servers successfully")
            await self.start_health_monitoring()

    async def start_server(self, name: str, config: Dict[str, Any]):
        """Start a single MCP server"""
        try:
            logger.info(f"Starting MCP server: {name}")
            server = MCPServer(name, config)
            await server.start()
            self.servers[name] = server
            is_healthy = await server.health_check()
            if not is_healthy:
                logger.warning(f"Server {name} started but failed health check")
                server.status = "unhealthy"
            else:
                logger.info(f"Successfully started MCP server: {name}")
        except Exception as e:
            logger.error(f"Failed to start MCP server {name}: {e}")
            server = MCPServer(name, config)
            server.status = "error"
            server.error_message = str(e)
            self.servers[name] = server

    async def start_health_monitoring(self):
        """Start background health monitoring for all servers"""
        if self._health_check_task:
            self._health_check_task.cancel()
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())

    async def _health_monitor_loop(self):
        """Background health monitoring loop"""
        while True:
            try:
                await asyncio.sleep(30)
                for name, server in self.servers.items():
                    if server.status == "running":
                        is_healthy = await server.health_check()
                        if not is_healthy:
                            logger.warning(f"Server {name} failed health check")
                            server.status = "unhealthy"
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    async def stop_all_servers(self):
        """Stop all running MCP servers"""
        if self._health_check_task:
            self._health_check_task.cancel()
        
        if self._mcp_loop and self._started:
            future = asyncio.run_coroutine_threadsafe(
                self._stop_all_servers_internal(),
                self._mcp_loop
            )
            future.result()

    async def _stop_all_servers_internal(self):
        """Internal method to stop servers"""
        tasks = []
        for name in list(self.servers.keys()):
            task = asyncio.create_task(self.stop_server(name))
            tasks.append(task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_server(self, name: str):
        """Stop a single MCP server"""
        if name in self.servers:
            try:
                server = self.servers[name]
                await server.stop()
                logger.info(f"Stopped MCP server: {name}")
            except Exception as e:
                logger.error(f"Error stopping server {name}: {e}")

    def get_server_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all servers"""
        server_status = {}
        for name, server in self.servers.items():
            server_status[name] = {
                "name": name,
                "status": server.status,
                "tools": len(server.tools),
                "resources": len(server.resources),
                "config": server.config,
                "error_message": server.error_message,
                "last_heartbeat": server.last_heartbeat,
                "tool_names": [t.get('name', 'unnamed') for t in server.tools]
            }
        return {
            "servers": server_status, 
            "total": len(self.servers),
            "running": len([s for s in self.servers.values() if s.status == "running"]),
            "errors": len([s for s in self.servers.values() if s.status == "error"])
        }

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from running servers"""
        tools = []
        for server_name, server in self.servers.items():
            if server.status == "running":
                for tool in server.tools:
                    tools.append({
                        "id": f"{server_name}_{tool['name']}",
                        "name": tool.get('description', tool['name']),
                        "description": tool.get('description', f"Tool from {server_name}"),
                        "server": server_name,
                        "category": "mcp",
                        "enabled": True,
                        "icon": "fas fa-plug",
                        "type": "mcp",
                        "inputSchema": tool.get('inputSchema', {}),
                        "tool_name": tool['name']
                    })
        return tools

    async def call_tool(self, tool_id: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool from any event loop"""
        try:
            parts = tool_id.split("_", 1)
            server_name = parts[0]
            tool_name = parts[1]
            
            if server_name not in self.servers:
                raise Exception(f"Server not found: {server_name}")
                
            server = self.servers[server_name]
            if server.status != "running":
                raise Exception(f"Server {server_name} is not running")
                
            # The server's call_tool method handles cross-loop calls
            result = await server.call_tool(tool_name, arguments)
            logger.info(f"Successfully called tool {tool_id}")
            return result
            
        except Exception as e:
            logger.error(f"Tool call failed for {tool_id}: {e}")
            raise

# Global enhanced instance
mcp_manager = EnhancedMCPManager()