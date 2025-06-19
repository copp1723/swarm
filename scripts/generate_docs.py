#!/usr/bin/env python3
"""
Documentation Generation Scripts

Generate and update various documentation formats from the OpenAPI specification
and source code.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).parent.parent

def generate_swagger_ui():
    """Generate Swagger UI for API documentation"""
    print("🔧 Generating Swagger UI...")
    
    # Read OpenAPI spec
    openapi_file = PROJECT_ROOT / "openapi.yaml"
    if not openapi_file.exists():
        print("❌ OpenAPI specification not found")
        return False
    
    with open(openapi_file, 'r') as f:
        spec = yaml.safe_load(f)
    
    # Create static docs directory
    docs_dir = PROJECT_ROOT / "static" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML with embedded Swagger UI
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{spec["info"]["title"]} - API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: '/static/docs/openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                tryItOutEnabled: true,
                supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
                docExpansion: 'list',
                jsonEditor: true,
                defaultModelRendering: 'example',
                showExtensions: true,
                showCommonExtensions: true
            }});
        }};
    </script>
</body>
</html>'''
    
    # Write HTML file
    html_file = docs_dir / "index.html"
    with open(html_file, 'w') as f:
        f.write(html_content)
    
    # Write OpenAPI spec as JSON for Swagger UI
    json_file = docs_dir / "openapi.json"
    with open(json_file, 'w') as f:
        json.dump(spec, f, indent=2)
    
    print(f"✅ Swagger UI generated at {html_file}")
    print(f"   Access at: http://localhost:5006/static/docs/")
    return True

def generate_postman_collection():
    """Generate Postman collection from OpenAPI spec"""
    print("🔧 Generating Postman collection...")
    
    openapi_file = PROJECT_ROOT / "openapi.yaml"
    if not openapi_file.exists():
        print("❌ OpenAPI specification not found")
        return False
    
    with open(openapi_file, 'r') as f:
        spec = yaml.safe_load(f)
    
    # Basic Postman collection structure
    collection = {
        "info": {
            "name": spec["info"]["title"],
            "description": spec["info"]["description"],
            "version": spec["info"]["version"],
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "auth": {
            "type": "apikey",
            "apikey": [
                {
                    "key": "key",
                    "value": "X-API-Key",
                    "type": "string"
                },
                {
                    "key": "value",
                    "value": "{{api_key}}",
                    "type": "string"
                }
            ]
        },
        "variable": [
            {
                "key": "base_url",
                "value": "http://localhost:5006/api",
                "type": "string"
            },
            {
                "key": "api_key",
                "value": "your-api-key-here",
                "type": "string"
            }
        ],
        "item": []
    }
    
    # Convert paths to Postman requests
    for path, methods in spec["paths"].items():
        folder = {
            "name": path.split('/')[1].title() if '/' in path else "Root",
            "item": []
        }
        
        for method, operation in methods.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                continue
            
            request_item = {
                "name": operation.get("summary", f"{method.upper()} {path}"),
                "request": {
                    "method": method.upper(),
                    "header": [
                        {
                            "key": "Content-Type",
                            "value": "application/json",
                            "type": "text"
                        }
                    ],
                    "url": {
                        "raw": "{{base_url}}" + path,
                        "host": ["{{base_url}}"],
                        "path": path.strip('/').split('/')
                    },
                    "description": operation.get("description", "")
                }
            }
            
            # Add request body if needed
            if method.lower() in ['post', 'put', 'patch'] and "requestBody" in operation:
                request_item["request"]["body"] = {
                    "mode": "raw",
                    "raw": "{}",
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                }
            
            folder["item"].append(request_item)
        
        if folder["item"]:
            collection["item"].append(folder)
    
    # Write collection
    collection_file = PROJECT_ROOT / "docs" / "postman_collection.json"
    with open(collection_file, 'w') as f:
        json.dump(collection, f, indent=2)
    
    print(f"✅ Postman collection generated at {collection_file}")
    return True

def generate_api_changelog():
    """Generate API-specific changelog from OpenAPI spec"""
    print("🔧 Generating API changelog...")
    
    openapi_file = PROJECT_ROOT / "openapi.yaml"
    if not openapi_file.exists():
        print("❌ OpenAPI specification not found")
        return False
    
    with open(openapi_file, 'r') as f:
        spec = yaml.safe_load(f)
    
    # Extract version info from OpenAPI
    current_version = spec["info"]["version"]
    
    # Count endpoints by version
    version_stats = {}
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                continue
            
            # Look for version info in operation
            since_version = operation.get("x-available-since", "1.0.0")
            
            if since_version not in version_stats:
                version_stats[since_version] = {"endpoints": 0, "paths": set()}
            
            version_stats[since_version]["endpoints"] += 1
            version_stats[since_version]["paths"].add(f"{method.upper()} {path}")
    
    # Generate changelog content
    changelog_content = f"""# API Changelog

## Version {current_version}

### Endpoint Summary
"""
    
    for version in sorted(version_stats.keys(), reverse=True):
        stats = version_stats[version]
        changelog_content += f"\n#### Version {version}\n"
        changelog_content += f"- **{stats['endpoints']} endpoints** added\n"
        changelog_content += "- Endpoints:\n"
        
        for path in sorted(stats['paths']):
            changelog_content += f"  - `{path}`\n"
    
    # Add deprecation info
    deprecated_endpoints = []
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if operation.get("deprecated", False):
                deprecated_endpoints.append(f"{method.upper()} {path}")
    
    if deprecated_endpoints:
        changelog_content += "\n### Deprecated Endpoints\n"
        for endpoint in deprecated_endpoints:
            changelog_content += f"- `{endpoint}`\n"
    
    # Write API changelog
    api_changelog_file = PROJECT_ROOT / "docs" / "api" / "CHANGELOG.md"
    with open(api_changelog_file, 'w') as f:
        f.write(changelog_content)
    
    print(f"✅ API changelog generated at {api_changelog_file}")
    return True

def update_readme_badges():
    """Update README badges with current info"""
    print("🔧 Updating README badges...")
    
    readme_file = PROJECT_ROOT / "README.md"
    if not readme_file.exists():
        print("❌ README.md not found")
        return False
    
    content = readme_file.read_text()
    
    # Update version badge from OpenAPI spec
    openapi_file = PROJECT_ROOT / "openapi.yaml"
    if openapi_file.exists():
        with open(openapi_file, 'r') as f:
            spec = yaml.safe_load(f)
        
        current_version = spec["info"]["version"]
        
        # Replace version badge
        import re
        version_pattern = r'!\[Version\]\(https://img\.shields\.io/badge/version-[^-]+-blue\.svg\)'
        new_badge = f'![Version](https://img.shields.io/badge/version-{current_version}-blue.svg)'
        
        if re.search(version_pattern, content):
            content = re.sub(version_pattern, new_badge, content)
        else:
            # Add version badge if not present
            badge_section = content.find('![Python]')
            if badge_section != -1:
                content = content[:badge_section] + new_badge + '\n' + content[badge_section:]
    
    # Count endpoints for API badge
    total_endpoints = sum(
        len([m for m in methods.keys() if m.lower() in ['get', 'post', 'put', 'delete', 'patch']])
        for methods in spec["paths"].values()
    )
    
    api_badge = f'![API Endpoints](https://img.shields.io/badge/endpoints-{total_endpoints}-green.svg)'
    
    # Add API endpoints badge
    if 'endpoints' not in content:
        badge_section = content.find('![License]')
        if badge_section != -1:
            content = content[:badge_section] + api_badge + '\n' + content[badge_section:]
    
    # Write updated README
    with open(readme_file, 'w') as f:
        f.write(content)
    
    print(f"✅ README badges updated (version {current_version}, {total_endpoints} endpoints)")
    return True

def generate_sdk_examples():
    """Generate SDK usage examples from OpenAPI spec"""
    print("🔧 Generating SDK examples...")
    
    openapi_file = PROJECT_ROOT / "openapi.yaml"
    if not openapi_file.exists():
        print("❌ OpenAPI specification not found")
        return False
    
    with open(openapi_file, 'r') as f:
        spec = yaml.safe_load(f)
    
    # Generate Python client examples
    python_examples = '''# Python SDK Examples

```python
import requests

class MCPClient:
    def __init__(self, base_url="http://localhost:5006/api", api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
    
    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
'''
    
    # Add method for each main endpoint
    main_endpoints = [
        ('GET', '/agents/list', 'list_agents'),
        ('POST', '/agents/chat/{agent_id}', 'chat_with_agent'),
        ('POST', '/agents/analyze', 'analyze_task'),
        ('POST', '/agents/orchestrate', 'orchestrate_task'),
        ('GET', '/monitoring/health', 'get_health')
    ]
    
    for method, path, func_name in main_endpoints:
        if path in spec["paths"] and method.lower() in spec["paths"][path]:
            operation = spec["paths"][path][method.lower()]
            
            # Generate method
            params = []
            if '{' in path:
                # Extract path parameters
                import re
                path_params = re.findall(r'\{([^}]+)\}', path)
                params.extend(path_params)
            
            if method.upper() in ['POST', 'PUT', 'PATCH']:
                params.append('data=None')
            
            python_examples += f'''
    def {func_name}(self, {', '.join(params)}):
        """
        {operation.get('summary', f'{method} {path}')}
        
        {operation.get('description', '')}
        """'''
            
            if method.upper() in ['POST', 'PUT', 'PATCH']:
                python_examples += f'''
        return self._request('{method}', '{path}', json=data)'''
            else:
                python_examples += f'''
        return self._request('{method}', '{path}')'''
    
    # Add usage examples
    python_examples += '''

# Usage Examples

# Initialize client
client = MCPClient(api_key="your-api-key")

# List available agents
agents = client.list_agents()
print(f"Available agents: {[agent['name'] for agent in agents['agents']]}")

# Chat with an agent
response = client.chat_with_agent(
    agent_id="developer_01",
    data={"message": "Create a REST API endpoint"}
)
print(f"Agent response: {response['response']}")

# Analyze a task with NLU
analysis = client.analyze_task(data={
    "task": "Fix the bug in the login function"
})
print(f"Detected intent: {analysis['analysis']['intent']['primary']}")

# Orchestrate task execution
result = client.orchestrate_task(data={
    "task": "Create a secure authentication system",
    "dry_run": True
})
print(f"Execution plan: {result['plan']['execution_steps']}")
```'''
    
    # Write SDK examples
    sdk_file = PROJECT_ROOT / "docs" / "sdk-examples.md"
    with open(sdk_file, 'w') as f:
        f.write(python_examples)
    
    print(f"✅ SDK examples generated at {sdk_file}")
    return True

def main():
    """Run all documentation generation tasks"""
    print("🚀 Running documentation generation...\n")
    
    tasks = [
        generate_swagger_ui,
        generate_postman_collection,
        generate_api_changelog,
        update_readme_badges,
        generate_sdk_examples
    ]
    
    results = []
    for task in tasks:
        try:
            result = task()
            results.append(result)
        except Exception as e:
            print(f"❌ Task {task.__name__} failed: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("="*50)
    print(f"📊 Documentation Generation Summary")
    print("="*50)
    print(f"Tasks completed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All documentation generated successfully!")
        return 0
    else:
        print("❌ Some tasks failed")
        return 1

if __name__ == "__main__":
    exit(main())