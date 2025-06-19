from flask import Blueprint
import logging
from utils.validation import validate_request_data
from utils.service_container import get_service
from utils.async_wrapper import async_manager
from utils.response_handler import response_handler, ErrorCategory

mcp_bp = Blueprint('mcp', __name__, url_prefix='/api/mcp')
logger = logging.getLogger(__name__)

@mcp_bp.route('/servers', methods=['GET'])
@response_handler.handle_route_errors(ErrorCategory.MCP_ERROR)
def get_servers():
    """Get list of configured MCP servers and their status"""
    mcp_manager = get_service('mcp_manager')
    servers = mcp_manager.get_server_status()
    return {
        'servers': servers,
        'total': len(servers)
    }

@mcp_bp.route('/servers/<server_id>/start', methods=['POST'])
@response_handler.handle_route_errors(ErrorCategory.MCP_ERROR)
def start_server(server_id: str):
    """Start a specific MCP server"""
    mcp_manager = get_service('mcp_manager')
    
    # Load the config to get the specific server config
    if not mcp_manager.config_manager.config:
        mcp_manager.load_config()
    
    # Get the specific server config
    server_config = mcp_manager.config_manager.config.get("mcpServers", {}).get(server_id)
    if not server_config:
        return response_handler.error(
            f'Server {server_id} not found in configuration',
            404,
            'SERVER_NOT_FOUND'
        )
    
    # Check if already running
    if server_id in mcp_manager.servers and mcp_manager.servers[server_id].status == "running":
        return {
            'message': f'Server {server_id} is already running',
            'server_id': server_id
        }
    
    # Start the server with proper config
    # We need to run this in the MCP event loop
    if not mcp_manager._started:
        async_manager.run_sync(mcp_manager.start_all_servers())
    
    # Now start the specific server if not already running
    try:
        from asyncio import run_coroutine_threadsafe
        future = run_coroutine_threadsafe(
            mcp_manager.start_server(server_id, server_config),
            mcp_manager._mcp_loop
        )
        result = future.result(timeout=30)  # Wait up to 30 seconds
        
        # Check if server is now running
        if server_id in mcp_manager.servers and mcp_manager.servers[server_id].status == "running":
            return {
                'message': f'Server {server_id} started successfully',
                'server_id': server_id
            }
        else:
            return response_handler.error(
                f'Failed to start server {server_id}',
                500,
                'SERVER_START_FAILED'
            )
    except Exception as e:
        logger.error(f"Error starting server {server_id}: {e}")
        return response_handler.error(
            f'Failed to start server {server_id}: {str(e)}',
            500,
            'SERVER_START_FAILED'
        )

@mcp_bp.route('/servers/<server_id>/stop', methods=['POST'])
@response_handler.handle_route_errors(ErrorCategory.MCP_ERROR)
def stop_server(server_id: str):
    """Stop a specific MCP server"""
    mcp_manager = get_service('mcp_manager')
    success = async_manager.run_sync(mcp_manager.stop_server(server_id))
    
    if success:
        return {'message': f'Server {server_id} stopped successfully'}
    else:
        return response_handler.error(f'Failed to stop server {server_id}', 500)

@mcp_bp.route('/servers/<server_id>/resources', methods=['GET'])
@response_handler.handle_route_errors(ErrorCategory.MCP_ERROR)
def get_server_resources(server_id: str):
    """Get available resources from a specific MCP server"""
    mcp_manager = get_service('mcp_manager')
    resources = mcp_manager.get_server_resources(server_id)
    return {
        'server_id': server_id,
        'resources': resources
    }

@mcp_bp.route('/servers/<server_id>/call', methods=['POST'])
@response_handler.handle_route_errors(ErrorCategory.MCP_ERROR)
@validate_request_data(required_fields=['tool'])
def call_server_tool(server_id: str, validated_data):
    """Call a tool on a specific MCP server"""
    mcp_manager = get_service('mcp_manager')
    tool_name = validated_data.get('tool')
    arguments = validated_data.get('arguments', {})
        
    result = async_manager.run_sync(
        mcp_manager.call_tool(server_id, tool_name, arguments)
    )
    
    return {'result': result}