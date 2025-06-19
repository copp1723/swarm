"""
Resilient HTTP Client with Tenacity
Provides HTTP client with automatic retry and notification on failures
"""

import logging
from typing import Dict, Any, Optional, Union
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from utils.tenacity_retry import retry_api_call, retry_webhook_delivery
from utils.notification_service import get_notification_service

logger = logging.getLogger(__name__)


class ResilientHTTPClient:
    """
    HTTP client with built-in retry logic and failure notifications.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize resilient HTTP client.
        
        Args:
            base_url: Base URL for requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            headers: Default headers
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = headers or {}
        self._client = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self.default_headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.default_headers
            )
        return self._client
    
    @retry_api_call(max_attempts=5)
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make GET request with retry logic.
        
        Args:
            url: Request URL
            params: Query parameters
            headers: Request headers
            **kwargs: Additional httpx arguments
            
        Returns:
            HTTP response
        """
        response = await self.client.get(
            url,
            params=params,
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response
    
    @retry_api_call(max_attempts=5)
    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make POST request with retry logic.
        
        Args:
            url: Request URL
            json: JSON payload
            data: Form data or raw bytes
            headers: Request headers
            **kwargs: Additional httpx arguments
            
        Returns:
            HTTP response
        """
        response = await self.client.post(
            url,
            json=json,
            data=data,
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response
    
    @retry_api_call(max_attempts=3)
    async def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make PUT request with retry logic.
        
        Args:
            url: Request URL
            json: JSON payload
            data: Form data or raw bytes
            headers: Request headers
            **kwargs: Additional httpx arguments
            
        Returns:
            HTTP response
        """
        response = await self.client.put(
            url,
            json=json,
            data=data,
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response
    
    @retry_api_call(max_attempts=3)
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make DELETE request with retry logic.
        
        Args:
            url: Request URL
            headers: Request headers
            **kwargs: Additional httpx arguments
            
        Returns:
            HTTP response
        """
        response = await self.client.delete(
            url,
            headers=headers,
            **kwargs
        )
        response.raise_for_status()
        return response
    
    @retry_webhook_delivery(max_attempts=5)
    async def deliver_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        signature: Optional[str] = None
    ) -> httpx.Response:
        """
        Deliver webhook with enhanced retry logic.
        
        Args:
            url: Webhook endpoint URL
            payload: Webhook payload
            headers: Request headers
            signature: Webhook signature for verification
            
        Returns:
            HTTP response
        """
        webhook_headers = headers or {}
        
        # Add signature if provided
        if signature:
            webhook_headers['X-Webhook-Signature'] = signature
            
        # Add standard webhook headers
        webhook_headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'MCP-Multi-Agent-Platform/1.0'
        })
        
        response = await self.client.post(
            url,
            json=payload,
            headers=webhook_headers,
            timeout=60.0  # Longer timeout for webhooks
        )
        
        # Check response
        if response.status_code >= 500:
            # Server error - will retry
            response.raise_for_status()
        elif response.status_code >= 400:
            # Client error - log but don't retry
            logger.error(f"Webhook client error: {response.status_code} - {response.text}")
            # Send notification for 4xx errors
            notification_service = get_notification_service()
            await notification_service.send_webhook_failure_alert(
                webhook_url=url,
                attempts=1,
                error=f"Client error: {response.status_code}"
            )
            
        return response
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Specialized clients

class SupermemoryClient(ResilientHTTPClient):
    """
    Resilient client for Supermemory API.
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.supermemory.com"):
        """Initialize Supermemory client with API key."""
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        super().__init__(
            base_url=base_url,
            timeout=30.0,
            max_retries=5,
            headers=headers
        )
    
    async def add_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add memory with resilient retry."""
        try:
            response = await self.post('/v1/memories', json=memory_data)
            if response:
                return response.json()
            else:
                return {"success": False, "error": "No response from API"}
        except Exception as e:
            logger.error(f"Error adding memory to Supermemory: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_memories(self, query: str, **params) -> Dict[str, Any]:
        """Search memories with resilient retry."""
        try:
            response = await self.get(
                '/v1/memories/search',
                params={'q': query, **params}
            )
            if response:
                return response.json()
            else:
                return {"success": False, "error": "No response from API", "results": []}
        except Exception as e:
            logger.error(f"Error searching memories in Supermemory: {e}")
            return {"success": False, "error": str(e), "results": []}


class ZenMCPClient(ResilientHTTPClient):
    """
    Resilient client for Zen MCP Server.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize Zen MCP client."""
        super().__init__(
            base_url=base_url,
            timeout=120.0,  # Longer timeout for AI operations
            max_retries=3
        )
    
    async def create_chat(self, messages: list, model: str = "gpt-4") -> Dict[str, Any]:
        """Create chat completion with resilient retry."""
        response = await self.post(
            '/chat/completions',
            json={
                'messages': messages,
                'model': model
            }
        )
        return response.json()


# Convenience functions

async def make_resilient_request(
    method: str,
    url: str,
    max_retries: int = 3,
    **kwargs
) -> httpx.Response:
    """
    Make a one-off resilient HTTP request.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        max_retries: Maximum retry attempts
        **kwargs: Additional request arguments
        
    Returns:
        HTTP response
    """
    async with ResilientHTTPClient(max_retries=max_retries) as client:
        method_func = getattr(client, method.lower())
        return await method_func(url, **kwargs)


async def deliver_webhook_resilient(
    url: str,
    payload: Dict[str, Any],
    signature: Optional[str] = None,
    max_retries: int = 5
) -> bool:
    """
    Deliver webhook with resilient retry and notification.
    
    Args:
        url: Webhook endpoint
        payload: Webhook payload
        signature: Optional signature
        max_retries: Maximum retry attempts
        
    Returns:
        Success status
    """
    try:
        async with ResilientHTTPClient(max_retries=max_retries) as client:
            response = await client.deliver_webhook(
                url=url,
                payload=payload,
                signature=signature
            )
            return response.status_code < 400
            
    except Exception as e:
        logger.error(f"Failed to deliver webhook to {url}: {e}")
        return False