#!/usr/bin/env python3
"""Runtime verification script for SWARM project"""

import sys
import os
import subprocess
import json

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_mark(passed):
    return f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"

def print_section(title):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def check_command(cmd, description):
    """Check if a command is available"""
    try:
        subprocess.run(cmd, capture_output=True, shell=True, check=True)
        print(f"{check_mark(True)} {description}")
        return True
    except:
        print(f"{check_mark(False)} {description}")
        return False

print_section("SWARM PROJECT RUNTIME VERIFICATION")

# Track issues
issues = []

# 1. Check Python version
print_section("1. PYTHON ENVIRONMENT")
python_version = sys.version_info
print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
if python_version.major >= 3 and python_version.minor >= 7:
    print(f"{check_mark(True)} Python version is sufficient (3.7+)")
else:
    print(f"{check_mark(False)} Python version too old (requires 3.7+)")
    issues.append("Python version")

# 2. Check critical files
print_section("2. CRITICAL FILES")

critical_files = {
    "app.py": "Main Flask application",
    "config/agents.json": "Agent configurations",
    "config/workflows.json": "Workflow configurations",
    "static/index.html": "Main UI file",
    "static/css/ui-enhancements.css": "UI enhancement styles",
    "static/js/ui-enhancements/agent-enhancements.js": "UI enhancement scripts",
    "utils/file_io.py": "File I/O utilities",
    "utils/error_catalog.py": "Error handling utilities",
    "utils/batch_operations.py": "Batch operation utilities",
    "utils/async_error_handler.py": "Async error handling",
    "services/multi_agent_executor.py": "Multi-agent orchestration",
    "services/error_handler.py": "Error handling service"
}

for file_path, description in critical_files.items():
    if os.path.exists(file_path):
        print(f"{check_mark(True)} {file_path} - {description}")
    else:
        print(f"{check_mark(False)} {file_path} - {description}")
        issues.append(f"Missing: {file_path}")

# 3. Check configuration validity
print_section("3. CONFIGURATION VALIDATION")

# Check agents.json
try:
    with open('config/agents.json', 'r') as f:
        agents = json.load(f)
    agent_count = len(agents)
    print(f"{check_mark(True)} agents.json is valid JSON ({agent_count} agents configured)")
    
    # Check for expected agents
    expected_agents = ['product_01', 'coder_01', 'bug_01']
    missing_agents = [a for a in expected_agents if a not in agents]
    if missing_agents:
        print(f"{check_mark(False)} Missing expected agents: {', '.join(missing_agents)}")
        issues.append("Missing agents")
    else:
        print(f"{check_mark(True)} All expected agents present")
except Exception as e:
    print(f"{check_mark(False)} Error reading agents.json: {e}")
    issues.append("Invalid agents.json")

# Check workflows.json
try:
    with open('config/workflows.json', 'r') as f:
        workflows = json.load(f)
    print(f"{check_mark(True)} workflows.json is valid JSON ({len(workflows)} workflows)")
except Exception as e:
    print(f"{check_mark(False)} Error reading workflows.json: {e}")
    issues.append("Invalid workflows.json")

# 4. Check UI Integration
print_section("4. UI INTEGRATION")

try:
    with open('static/index.html', 'r') as f:
        index_content = f.read()
    
    ui_checks = [
        ("ui-enhancements.css", "UI enhancement CSS"),
        ("agent-enhancements.js", "UI enhancement JavaScript"),
        ("css/main.css", "Main CSS"),
        ("js/app.js", "Main JavaScript")
    ]
    
    for filename, description in ui_checks:
        if filename in index_content:
            print(f"{check_mark(True)} {description} is included")
        else:
            print(f"{check_mark(False)} {description} is NOT included")
            issues.append(f"Missing include: {filename}")
            
    # Check for duplicates
    css_count = index_content.count("ui-enhancements.css")
    js_count = index_content.count("agent-enhancements.js")
    
    if css_count > 1:
        print(f"{check_mark(False)} Duplicate CSS includes ({css_count} times)")
        issues.append("Duplicate CSS includes")
    if js_count > 1:
        print(f"{check_mark(False)} Duplicate JS includes ({js_count} times)")
        issues.append("Duplicate JS includes")
        
except Exception as e:
    print(f"{check_mark(False)} Error checking index.html: {e}")
    issues.append("Cannot read index.html")

# 5. Check Python imports
print_section("5. PYTHON IMPORTS")

import_tests = [
    ("from utils.file_io import safe_read_json", "File I/O utilities"),
    ("from utils.error_catalog import ErrorCodes", "Error catalog"),
    ("from utils.batch_operations import BatchProcessor", "Batch operations"),
    ("from utils.async_error_handler import AsyncRouteHandler", "Async error handler"),
    ("from models.core import db", "Database models"),
    ("from flask import Flask", "Flask framework"),
]

for import_statement, description in import_tests:
    try:
        exec(import_statement)
        print(f"{check_mark(True)} {description}")
    except ImportError as e:
        print(f"{check_mark(False)} {description}: {e}")
        if "jsonschema" in str(e):
            print(f"  {YELLOW}→ Optional dependency: pip install jsonschema{RESET}")
        else:
            issues.append(f"Import error: {description}")

# 6. Check services
print_section("6. SERVICE DEPENDENCIES")

# Check for Redis (optional for Celery)
redis_available = check_command("redis-cli ping 2>/dev/null", "Redis server (optional for background tasks)")

# Check for PostgreSQL (optional)
postgres_available = check_command("pg_isready 2>/dev/null", "PostgreSQL (optional, using SQLite by default)")

# 7. Environment check
print_section("7. ENVIRONMENT VARIABLES")

env_vars = {
    "FLASK_SECRET_KEY": ("optional", "Using default if not set"),
    "DATABASE_URL": ("optional", "Using SQLite if not set"),
    "OPENAI_API_KEY": ("recommended", "Required for AI features"),
}

for var, (status, note) in env_vars.items():
    if os.environ.get(var):
        print(f"{check_mark(True)} {var} is set")
    else:
        if status == "optional":
            print(f"{YELLOW}⚠{RESET}  {var} not set ({note})")
        else:
            print(f"{check_mark(False)} {var} not set ({note})")
            if status == "required":
                issues.append(f"Missing env var: {var}")

# 8. Port availability
print_section("8. PORT AVAILABILITY")

import socket
port = int(os.environ.get('PORT', 5006))
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(('', port))
    sock.close()
    print(f"{check_mark(True)} Port {port} is available")
except:
    print(f"{check_mark(False)} Port {port} is in use")
    issues.append(f"Port {port} unavailable")

# Summary
print_section("VERIFICATION SUMMARY")

if not issues:
    print(f"{GREEN}✅ ALL CHECKS PASSED!{RESET}")
    print("\nThe project appears to be properly configured.")
    print("\nTo start the application:")
    print(f"  {BLUE}python app.py{RESET}")
    print("\nThen open:")
    print(f"  {BLUE}http://localhost:{port}{RESET}")
    print("\nTo test UI enhancements:")
    print(f"  {BLUE}http://localhost:{port}/test-ui-enhancements.html{RESET}")
else:
    print(f"{RED}❌ ISSUES FOUND:{RESET}")
    for issue in issues:
        print(f"  - {issue}")
    print(f"\n{YELLOW}Some issues may not prevent the app from running.{RESET}")
    print("Critical issues should be addressed first.")

print("\n" + "="*60)
print("Optional enhancements:")
print("  - Install jsonschema for config validation: pip install jsonschema")
print("  - Install Redis for background tasks: brew install redis (macOS)")
print("  - Set OPENAI_API_KEY for AI features")
print("="*60)