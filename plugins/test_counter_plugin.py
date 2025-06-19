"""
Test Counter Plugin
A simple plugin that counts events
"""
from core.plugins import ServicePlugin
from core.interfaces import IService
from datetime import datetime

class CounterService(IService):
    def __init__(self):
        self.count = 0
        self.last_increment = None
    
    async def initialize(self):
        print("Counter service initialized")
    
    async def shutdown(self):
        print(f"Counter service shutting down. Final count: {self.count}")
    
    def increment(self):
        self.count += 1
        self.last_increment = datetime.now()
        return self.count
    
    def get_count(self):
        return {
            "count": self.count,
            "last_increment": self.last_increment.isoformat() if self.last_increment else None
        }

class CounterPlugin(ServicePlugin):
    def get_plugin_info(self):
        return {
            "name": "Counter Plugin",
            "version": "1.0.0",
            "description": "Simple counter service for testing",
            "type": "service"
        }
    
    def register_services(self, container):
        container.register_singleton("counter_service", CounterService())
        print("Counter service registered")
