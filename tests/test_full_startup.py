#!/usr/bin/env python3
"""
Test script for full SWARM app startup
Validates that all async issues are resolved
"""

import os
import sys

# Change to the correct directory
os.chdir('/Users/copp1723/Desktop/swarm/mcp_new_project')
sys.path.insert(0, '/Users/copp1723/Desktop/swarm/mcp_new_project')

print("🚀 Testing SWARM Full App Startup")
print("=" * 50)

try:
    print("✅ 1. Loading environment...")
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='config/.env')
    
    print("✅ 2. Setting up logging...")
    from utils.logging_config import setup_logging, get_logger
    setup_logging(app_name="swarm_test")
    logger = get_logger(__name__)
    
    print("✅ 3. Initializing Flask app...")
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    print("✅ 4. Testing async service initialization...")
    from services.memory_aware_chat_service import get_memory_aware_chat_service
    chat_service = get_memory_aware_chat_service()
    
    # Test async initialization
    import asyncio
    async def test_async_init():
        await chat_service.initialize()
        print("   - MemoryAwareChatService async init: ✅")
        await chat_service.shutdown()
        print("   - MemoryAwareChatService shutdown: ✅")
    
    asyncio.run(test_async_init())
    
    print("✅ 5. Testing service container...")
    from core.service_registry import initialize_services
    container = initialize_services()
    print(f"   - Services registered: {len(container._services) if hasattr(container, '_services') else 'unknown'}")
    
    print("✅ 6. Testing database...")
    from models.core import db
    from utils.db_init import initialize_databases
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        initialize_databases(app)
        print("   - Database initialized: ✅")
    
    print("\n✅ 7. Testing async-aware service initialization...")
    from core.dependency_injection import get_container
    container = get_container()
    
    # Test the async initialization logic from app.py
    if hasattr(container, '_async_init_services'):
        print(f"   - Found {len(container._async_init_services)} services requiring async init")
        for service_name in container._async_init_services:
            print(f"   - Testing async init for: {service_name}")
            service = container.get_service(service_name)
            if service and hasattr(service, 'initialize'):
                async def init_service():
                    await service.initialize()
                asyncio.run(init_service())
                print(f"   - {service_name} async initialized: ✅")
    else:
        print("   - No async-init services found in container")
    
    print("\n🎉 SUCCESS: All components initialized without async issues!")
    print("The full app should now start properly with: python app.py")
    
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
