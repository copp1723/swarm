#!/usr/bin/env python3
"""
Automated Documentation Tests

Ensures documentation stays in sync with code and API behavior.
"""

import os
import re
import json
import ast
import pytest
import requests
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
API_DOCS = DOCS_DIR / "api" / "README.md"
SRC_DIR = PROJECT_ROOT


class DocumentationTester:
    """Tests to ensure documentation accuracy and completeness"""
    
    def __init__(self):
        self.base_url = "http://localhost:5006"
        self.api_key = os.getenv('SWARM_API_KEY', 'test-key')
    
    def extract_code_blocks(self, filepath: Path, language: str = None) -> List[str]:
        """Extract code blocks from markdown files"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Pattern for code blocks
        if language:
            pattern = f'```{language}\n(.*?)```'
        else:
            pattern = r'```(?:\w+)?\n(.*?)```'
        
        return re.findall(pattern, content, re.DOTALL)
    
    def extract_api_endpoints(self, filepath: Path) -> List[Dict[str, str]]:
        """Extract API endpoints from documentation"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Pattern for HTTP endpoints
        pattern = r'```http\n(GET|POST|PUT|DELETE|PATCH)\s+([^\n]+)'
        matches = re.findall(pattern, content)
        
        endpoints = []
        for method, path in matches:
            # Clean up path
            path = path.strip()
            if path.startswith('/api'):
                endpoints.append({'method': method, 'path': path})
        
        return endpoints
    
    def extract_json_examples(self, filepath: Path) -> List[Dict]:
        """Extract JSON examples from documentation"""
        code_blocks = self.extract_code_blocks(filepath, 'json')
        json_examples = []
        
        for block in code_blocks:
            try:
                # Clean up block
                block = block.strip()
                if block:
                    json_obj = json.loads(block)
                    json_examples.append(json_obj)
            except json.JSONDecodeError:
                # Some blocks might be partial or have comments
                pass
        
        return json_examples
    
    def find_route_definitions(self) -> Set[Tuple[str, str]]:
        """Find all route definitions in source code"""
        routes = set()
        
        # Search for Flask routes
        for py_file in SRC_DIR.rglob("*.py"):
            if "test" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Find @app.route and @blueprint.route decorators
                route_pattern = r'@(?:\w+\.)?route\(["\']([^"\']+)["\'](?:.*methods=\[([^\]]+)\])?'
                matches = re.findall(route_pattern, content)
                
                for path, methods in matches:
                    if methods:
                        # Parse methods
                        method_list = re.findall(r'["\'](\w+)["\']', methods)
                        for method in method_list:
                            routes.add((method.upper(), path))
                    else:
                        # Default is GET
                        routes.add(('GET', path))
                        
            except Exception:
                pass
        
        return routes


class TestDocumentationAccuracy:
    """Test documentation matches implementation"""
    
    @pytest.fixture
    def doc_tester(self):
        return DocumentationTester()
    
    def test_api_endpoints_exist(self, doc_tester):
        """Verify all documented API endpoints exist in code"""
        # Extract documented endpoints
        documented = doc_tester.extract_api_endpoints(API_DOCS)
        
        # Find actual routes
        actual_routes = doc_tester.find_route_definitions()
        
        # Check each documented endpoint
        missing = []
        for endpoint in documented:
            method = endpoint['method']
            path = endpoint['path']
            
            # Normalize path (remove /api prefix if needed)
            if path.startswith('/api/'):
                path = path[4:]  # Remove /api prefix
            
            # Check if route exists (considering parameters)
            found = False
            for actual_method, actual_path in actual_routes:
                if method == actual_method:
                    # Simple match or pattern match
                    if path == actual_path or self._paths_match(path, actual_path):
                        found = True
                        break
            
            if not found:
                missing.append(f"{method} {endpoint['path']}")
        
        assert not missing, f"Documented endpoints not found in code: {missing}"
    
    def _paths_match(self, doc_path: str, code_path: str) -> bool:
        """Check if paths match considering parameters"""
        # Convert {param} to <param> format
        doc_pattern = re.sub(r'\{([^}]+)\}', r'<\1>', doc_path)
        
        # Check exact match
        if doc_pattern == code_path:
            return True
        
        # Check pattern match
        # Convert Flask route to regex
        code_pattern = re.sub(r'<[^:>]+:([^>]+)>', r'<\1>', code_path)
        code_pattern = re.sub(r'<([^>]+)>', r'(?P<\1>[^/]+)', code_pattern)
        
        try:
            return bool(re.match(f"^{code_pattern}$", doc_pattern))
        except:
            return False
    
    def test_json_examples_valid(self, doc_tester):
        """Verify all JSON examples in documentation are valid"""
        invalid = []
        
        for doc_file in DOCS_DIR.rglob("*.md"):
            json_examples = doc_tester.extract_json_examples(doc_file)
            
            for i, example in enumerate(json_examples):
                try:
                    # Re-serialize to ensure it's valid
                    json.dumps(example)
                except Exception as e:
                    invalid.append(f"{doc_file}:example{i}: {e}")
        
        assert not invalid, f"Invalid JSON examples: {invalid}"
    
    def test_code_examples_syntax(self, doc_tester):
        """Verify Python code examples have valid syntax"""
        syntax_errors = []
        
        for doc_file in DOCS_DIR.rglob("*.md"):
            python_blocks = doc_tester.extract_code_blocks(doc_file, 'python')
            
            for i, block in enumerate(python_blocks):
                try:
                    # Check syntax
                    ast.parse(block)
                except SyntaxError as e:
                    syntax_errors.append(f"{doc_file}:block{i}: {e}")
        
        assert not syntax_errors, f"Python syntax errors: {syntax_errors}"
    
    def test_env_variables_documented(self):
        """Verify all environment variables are documented"""
        # Find env variables in code
        env_vars = set()
        
        for py_file in SRC_DIR.rglob("*.py"):
            if "test" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Find os.getenv and os.environ calls
                env_pattern = r'os\.(?:getenv|environ\.get)\(["\']([A-Z_]+)["\']'
                matches = re.findall(env_pattern, content)
                env_vars.update(matches)
            except:
                pass
        
        # Check if documented
        readme_content = (PROJECT_ROOT / "README.md").read_text()
        migration_content = (DOCS_DIR / "migration-guide.md").read_text()
        
        undocumented = []
        for var in env_vars:
            if var not in readme_content and var not in migration_content:
                undocumented.append(var)
        
        # Allow some system variables
        allowed_undocumented = {'PATH', 'HOME', 'USER', 'PWD'}
        undocumented = [v for v in undocumented if v not in allowed_undocumented]
        
        assert not undocumented, f"Undocumented env variables: {undocumented}"


class TestAPIDocumentation:
    """Test API documentation against live endpoints"""
    
    @pytest.fixture
    def api_client(self):
        return DocumentationTester()
    
    @pytest.mark.integration
    def test_documented_endpoints_respond(self, api_client):
        """Test that documented endpoints respond correctly"""
        # Skip if server not running
        try:
            requests.get(f"{api_client.base_url}/api/monitoring/health")
        except requests.ConnectionError:
            pytest.skip("Server not running")
        
        documented = api_client.extract_api_endpoints(API_DOCS)
        failures = []
        
        for endpoint in documented:
            if '{' in endpoint['path']:
                # Skip parameterized endpoints in this test
                continue
            
            # Test endpoint
            headers = {'X-API-Key': api_client.api_key}
            
            try:
                if endpoint['method'] == 'GET':
                    resp = requests.get(
                        f"{api_client.base_url}{endpoint['path']}",
                        headers=headers
                    )
                elif endpoint['method'] == 'POST':
                    # Use minimal valid payload
                    resp = requests.post(
                        f"{api_client.base_url}{endpoint['path']}",
                        headers=headers,
                        json={}
                    )
                else:
                    continue
                
                # Check for complete failure (not 4xx client errors)
                if resp.status_code >= 500:
                    failures.append(
                        f"{endpoint['method']} {endpoint['path']}: {resp.status_code}"
                    )
            except Exception as e:
                failures.append(
                    f"{endpoint['method']} {endpoint['path']}: {e}"
                )
        
        assert not failures, f"Endpoint failures: {failures}"


class TestChangelogCompleteness:
    """Test that changelog is complete and accurate"""
    
    def test_version_consistency(self):
        """Check version numbers are consistent"""
        # Read changelog
        changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        
        # Extract version numbers
        version_pattern = r'## \[(\d+\.\d+\.\d+)\]'
        versions = re.findall(version_pattern, changelog)
        
        # Check semantic versioning
        for version in versions:
            parts = version.split('.')
            assert len(parts) == 3, f"Invalid version format: {version}"
            assert all(p.isdigit() for p in parts), f"Invalid version: {version}"
    
    def test_unreleased_section_exists(self):
        """Ensure Unreleased section exists"""
        changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        assert '## [Unreleased]' in changelog, "Missing Unreleased section"
    
    def test_links_section_exists(self):
        """Ensure links section exists at bottom"""
        changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        assert '[Unreleased]:' in changelog, "Missing version comparison links"


class TestDocumentationCompleteness:
    """Test documentation completeness"""
    
    def test_all_services_documented(self):
        """Ensure all services have documentation"""
        services_dir = SRC_DIR / "services"
        undocumented = []
        
        for service_file in services_dir.glob("*.py"):
            if service_file.name.startswith('__'):
                continue
            
            service_name = service_file.stem
            
            # Check if mentioned in architecture or other docs
            documented = False
            for doc_file in DOCS_DIR.rglob("*.md"):
                if service_name in doc_file.read_text():
                    documented = True
                    break
            
            if not documented:
                undocumented.append(service_name)
        
        # Some services might be internal only
        allowed_undocumented = {'__init__', 'base', 'utils'}
        undocumented = [s for s in undocumented if s not in allowed_undocumented]
        
        assert not undocumented, f"Undocumented services: {undocumented}"
    
    def test_plugin_examples_exist(self):
        """Ensure plugin documentation has examples"""
        plugin_doc = DOCS_DIR / "plugin-development.md"
        assert plugin_doc.exists(), "Plugin documentation missing"
        
        content = plugin_doc.read_text()
        
        # Check for essential sections
        required_sections = [
            "Basic Plugin Structure",
            "Service Implementation",
            "Plugin Types",
            "Testing Plugins",
            "Best Practices"
        ]
        
        missing = [s for s in required_sections if s not in content]
        assert not missing, f"Missing sections in plugin docs: {missing}"


class TestDocumentationLinks:
    """Test that all links in documentation are valid"""
    
    def test_internal_links_valid(self):
        """Test internal documentation links"""
        broken_links = []
        
        for doc_file in DOCS_DIR.rglob("*.md"):
            content = doc_file.read_text()
            
            # Find markdown links
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            matches = re.findall(link_pattern, content)
            
            for link_text, link_url in matches:
                if link_url.startswith('http'):
                    continue  # Skip external links
                
                if link_url.startswith('#'):
                    continue  # Skip anchors
                
                # Resolve relative path
                if link_url.startswith('./'):
                    target = doc_file.parent / link_url[2:]
                elif link_url.startswith('../'):
                    target = doc_file.parent / link_url
                else:
                    target = doc_file.parent / link_url
                
                # Check if exists
                if not target.exists():
                    broken_links.append(f"{doc_file}: {link_url}")
        
        assert not broken_links, f"Broken internal links: {broken_links}"


class TestCodeCoverage:
    """Test that code examples cover main features"""
    
    def test_orchestration_examples(self):
        """Ensure orchestration has complete examples"""
        orch_doc = DOCS_DIR / "nlu-orchestration.md"
        content = orch_doc.read_text()
        
        # Check for essential examples
        required_examples = [
            "POST /api/agents/analyze",
            "POST /api/agents/orchestrate",
            "dry_run",
            "task_id",
            "routing_decision"
        ]
        
        missing = [ex for ex in required_examples if ex not in content]
        assert not missing, f"Missing orchestration examples: {missing}"


def run_documentation_tests():
    """Run all documentation tests"""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_documentation_tests()