#!/usr/bin/env python3
"""
Production runner for MCP Executive Interface
Uses Gunicorn with gevent workers + Celery workers for optimal performance
"""
import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from multiprocessing import Process

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def run_celery_worker():
    """Run Celery worker process"""
    cmd = [
        "celery",
        "-A", "config.celery_config:celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=2",
        "--queues=agent_queue,analysis_queue",
        "--hostname=worker@%h"
    ]
    
    print("🔄 Starting Celery worker...")
    try:
        subprocess.run(cmd, cwd=project_dir)
    except KeyboardInterrupt:
        print("\n🛑 Celery worker stopped")
    except FileNotFoundError:
        print("❌ Celery not found. Install with: pip install celery")


def run_celery_beat():
    """Run Celery beat scheduler (if needed)"""
    cmd = [
        "celery",
        "-A", "config.celery_config:celery_app",
        "beat",
        "--loglevel=info"
    ]
    
    print("⏰ Starting Celery beat scheduler...")
    try:
        subprocess.run(cmd, cwd=project_dir)
    except KeyboardInterrupt:
        print("\n🛑 Celery beat stopped")
    except FileNotFoundError:
        print("❌ Celery not found. Install with: pip install celery")


def run_flower_monitor():
    """Run Flower monitoring interface"""
    cmd = [
        "celery",
        "-A", "config.celery_config:celery_app",
        "flower",
        "--port=5555",
        "--address=0.0.0.0"
    ]
    
    print("🌸 Starting Flower monitoring on port 5555...")
    try:
        subprocess.run(cmd, cwd=project_dir)
    except KeyboardInterrupt:
        print("\n🛑 Flower monitoring stopped")
    except FileNotFoundError:
        print("❌ Flower not found. Install with: pip install flower")


def run_production():
    """Run the application with Gunicorn + gevent workers"""
    import subprocess
    
    # Configuration
    workers = 4
    bind = f"0.0.0.0:{os.environ.get('PORT', 5006)}"
    app_module = "app:app"
    
    # Build Gunicorn command with SocketIO support
    cmd = [
        "gunicorn",
        "--workers", str(workers),
        "--worker-class", "gevent",  # Use gevent for SocketIO
        "--bind", bind,
        "--timeout", "120",
        "--keep-alive", "2",
        "--max-requests", "1000",
        "--max-requests-jitter", "100",
        "--preload",
        app_module
    ]
    
    print(f"🚀 Starting production server with {workers} workers...")
    print(f"📡 Listening on http://{bind}")
    print(f"⚡ Using gevent workers for WebSocket support")
    print(f"🔄 Task queues enabled with Celery backend")
    
    # Run the command
    try:
        subprocess.run(cmd, cwd=project_dir)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except FileNotFoundError:
        print("❌ Gunicorn not found. Install with: pip install gunicorn gevent")
        sys.exit(1)


def run_full_stack():
    """Run the complete application stack with all services"""
    processes = []
    
    try:
        # Start Celery worker
        worker_process = Process(target=run_celery_worker)
        worker_process.start()
        processes.append(worker_process)
        
        # Start Flower monitoring (optional)
        flower_process = Process(target=run_flower_monitor)
        flower_process.start()
        processes.append(flower_process)
        
        # Wait a moment for workers to start
        time.sleep(2)
        
        # Start main web application
        print("🚀 Starting main web application...")
        run_production()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down all services...")
    finally:
        # Clean shutdown of all processes
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()


def run_development():
    """Run the application in development mode"""
    from app import app, socketio
    port = int(os.environ.get('PORT', 5006))
    print(f"🔧 Starting development server on port {port}...")
    print("🔌 WebSocket support enabled")
    print("🔄 Task queues available (requires Redis)")
    socketio.run(app, host='0.0.0.0', port=port, debug=True)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'development'
    
    if mode == 'production':
        run_production()
    elif mode == 'worker':
        run_celery_worker()
    elif mode == 'flower':
        run_flower_monitor()
    elif mode == 'full-stack':
        run_full_stack()
    else:
        run_development()