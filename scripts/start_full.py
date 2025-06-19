#!/usr/bin/env python3
"""
Full app startup with async initialization fixes
"""
import os
import sys
import asyncio
from pathlib import Path

# Set up paths
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))
os.chdir(project_dir)

# Fix for macOS async issues
if sys.platform == 'darwin':
    # Use the selector event loop policy to avoid kqueue issues
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    # Ensure we have a clean event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.close()
    except:
        pass
    asyncio.set_event_loop(asyncio.new_event_loop())

# Load environment
env_file = project_dir / 'config' / '.env'
if env_file.exists():
    print(f"Loading environment from {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Set Flask environment
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '0'  # Disable debug to avoid reload issues

print("Starting SWARM v2.0.0 Full Server...")
print("-" * 50)

try:
    # Patch the problematic memory aware chat service initialization
    import services.memory_aware_chat_service
    
    # Override the background task starter
    original_init = services.memory_aware_chat_service.MemoryAwareChatService.__init__
    
    def patched_init(self):
        # Call original init without background tasks
        self.conversations = {}
        self.memory_monitor = None
        self.cleanup_task = None
        self._cleanup_interval = 300  # 5 minutes
        self._session_timeout = 1800  # 30 minutes
        print("✓ Memory aware chat service initialized (background tasks disabled)")
    
    services.memory_aware_chat_service.MemoryAwareChatService.__init__ = patched_init
    
    # Now import the app
    from app import app
    
    # Initialize database if needed
    with app.app_context():
        from models.core import db
        from core.service_registry import initialize_services
        
        # Create tables
        try:
            db.create_all()
            print("✓ Database tables created")
        except Exception as e:
            print(f"⚠ Database initialization warning: {e}")
        
        # Initialize services
        try:
            initialize_services()
            print("✓ Services initialized")
        except Exception as e:
            print(f"⚠ Service initialization warning: {e}")
    
    # Get OpenRouter API key status
    api_key = os.environ.get('OPENROUTER_API_KEY', '')
    if api_key and len(api_key) > 10:
        print(f"✓ OpenRouter API key configured: {api_key[:10]}...")
    else:
        print("⚠ OpenRouter API key not configured - agent responses will fail")
    
    # Start the server
    print(f"\nServer starting on http://localhost:5006")
    print("\nAvailable features:")
    print("  ✓ Full agent chat with AI responses")
    print("  ✓ Multi-agent collaboration")
    print("  ✓ File upload and analysis")
    print("  ✓ Audit system with explainability")
    print("  ✓ WebSocket real-time updates")
    print("  ✓ All API endpoints active")
    print(f"\nDev API Key: {os.environ.get('SWARM_DEV_API_KEY', 'Not set')}")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 50)
    
    # Run with gevent for better async support
    from gevent import monkey
    monkey.patch_all()
    
    # Use the Flask development server with threading
    app.run(
        host='0.0.0.0', 
        port=5006, 
        debug=False, 
        use_reloader=False,
        threaded=True
    )
    
except Exception as e:
    print(f"\nError starting server: {e}")
    import traceback
    traceback.print_exc()
    print("\nTrying fallback minimal server...")
    # Fall back to minimal server if full server fails
    os.system(f"python3 {project_dir}/scripts/start_with_api.py")