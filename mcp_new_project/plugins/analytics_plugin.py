"""
Example Analytics Plugin
Demonstrates how to create a dynamically loadable service plugin
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
import logging

from core.plugins import ServicePlugin
from core.dependency_injection import Scope
from core.interfaces import IService
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AnalyticsService(IService):
    """Example analytics service that tracks system metrics"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.metrics = {
            'api_calls': 0,
            'agent_activations': 0,
            'task_completions': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the analytics service"""
        self.logger.info("Analytics service initializing...")
        self._initialized = True
        self.logger.info("Analytics service initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the analytics service"""
        self.logger.info("Analytics service shutting down...")
        # Save final metrics
        uptime = (datetime.now() - self.metrics['start_time']).total_seconds()
        self.logger.info(f"Analytics service ran for {uptime:.2f} seconds")
        self.logger.info(f"Final metrics: {self.metrics}")
    
    def track_event(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """Track an analytics event"""
        if event_type == 'api_call':
            self.metrics['api_calls'] += 1
        elif event_type == 'agent_activation':
            self.metrics['agent_activations'] += 1
        elif event_type == 'task_completion':
            self.metrics['task_completions'] += 1
        elif event_type == 'error':
            self.metrics['errors'] += 1
        
        self.logger.debug(f"Tracked event: {event_type} with data: {data}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        uptime = (datetime.now() - self.metrics['start_time']).total_seconds()
        return {
            **self.metrics,
            'uptime_seconds': uptime,
            'events_per_minute': (sum([
                self.metrics['api_calls'],
                self.metrics['agent_activations'],
                self.metrics['task_completions'],
                self.metrics['errors']
            ]) / uptime * 60) if uptime > 0 else 0
        }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health metrics for monitoring"""
        total_events = sum([
            self.metrics['api_calls'],
            self.metrics['agent_activations'],
            self.metrics['task_completions']
        ])
        
        error_rate = (self.metrics['errors'] / total_events * 100) if total_events > 0 else 0
        
        return {
            'healthy': error_rate < 5,  # Less than 5% error rate
            'error_rate': error_rate,
            'total_events': total_events,
            'status': 'healthy' if error_rate < 5 else 'degraded'
        }


class AnalyticsPlugin(ServicePlugin):
    """Plugin that provides analytics functionality"""
    
    def get_plugin_info(self) -> Dict[str, str]:
        """Return plugin metadata"""
        return {
            'name': 'Analytics Service Plugin',
            'version': '1.0.0',
            'description': 'Provides system analytics and metrics tracking',
            'author': 'SWARM Team',
            'type': 'service',
            'category': 'monitoring'
        }
    
    def register_services(self, container) -> None:
        """Register analytics service with the DI container"""
        logger.info("Registering Analytics Service...")
        
        # Create and register the analytics service
        analytics_service = AnalyticsService()
        
        # Register as singleton
        container.register_singleton('analytics_service', analytics_service)
        
        # Also register factory for creating new instances if needed
        container.register_factory(
            'analytics_service_factory',
            lambda: AnalyticsService(),
            scope=Scope.TRANSIENT
        )
        
        # Hook into existing services if available
        try:
            # Try to get event bus and subscribe to events
            event_bus = container.get_service('event_bus')
            if event_bus:
                # Subscribe to system events
                event_bus.subscribe('api.request', lambda event: analytics_service.track_event('api_call', event))
                event_bus.subscribe('agent.activated', lambda event: analytics_service.track_event('agent_activation', event))
                event_bus.subscribe('task.completed', lambda event: analytics_service.track_event('task_completion', event))
                event_bus.subscribe('system.error', lambda event: analytics_service.track_event('error', event))
                logger.info("Analytics service subscribed to system events")
        except Exception as e:
            logger.warning(f"Could not subscribe to events: {e}")
        
        logger.info("Analytics Service registered successfully")
    
    def unregister_services(self, container) -> None:
        """Clean up when plugin is unloaded"""
        logger.info("Unregistering Analytics Service...")
        
        # Get the service and shut it down
        analytics_service = container.get_service('analytics_service')
        if analytics_service:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(analytics_service.shutdown())
        
        # Remove from container
        # Note: Container doesn't have unregister method yet, 
        # but this is where you would clean up
        
        logger.info("Analytics Service unregistered")