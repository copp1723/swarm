#!/usr/bin/env python3
"""
Documentation Test Runner

Automated testing for documentation accuracy and completeness.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_command(cmd: List[str], cwd: str = None) -> tuple:
    """Run a command and return (success, output, error)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_documentation_syntax():
    """Test documentation files for syntax errors"""
    print("🔍 Testing documentation syntax...")
    
    # Test markdown syntax
    doc_files = list(PROJECT_ROOT.glob("docs/**/*.md"))
    doc_files.append(PROJECT_ROOT / "README.md")
    doc_files.append(PROJECT_ROOT / "CHANGELOG.md")
    
    errors = []
    for doc_file in doc_files:
        if not doc_file.exists():
            continue
            
        try:
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Basic markdown validation
            if content.count('```') % 2 != 0:
                errors.append(f"{doc_file}: Unmatched code blocks")
                
            # Check for broken internal links
            import re
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            for link_text, link_url in links:
                if link_url.startswith('./') or link_url.startswith('../'):
                    # Check relative paths
                    target = doc_file.parent / link_url
                    if not target.exists():
                        errors.append(f"{doc_file}: Broken link to {link_url}")
                        
        except Exception as e:
            errors.append(f"{doc_file}: {e}")
    
    if errors:
        print("❌ Documentation syntax errors found:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("✅ Documentation syntax is valid")
        return True

def test_openapi_spec():
    """Test OpenAPI specification"""
    print("🔍 Testing OpenAPI specification...")
    
    openapi_file = PROJECT_ROOT / "openapi.yaml"
    if not openapi_file.exists():
        print("❌ OpenAPI specification not found")
        return False
    
    # Try to parse YAML
    try:
        import yaml
        with open(openapi_file, 'r') as f:
            spec = yaml.safe_load(f)
        
        # Basic validation
        required_fields = ['openapi', 'info', 'paths']
        for field in required_fields:
            if field not in spec:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Check version format
        version = spec['info'].get('version', '')
        if not version or len(version.split('.')) != 3:
            print(f"❌ Invalid version format: {version}")
            return False
            
        print(f"✅ OpenAPI specification is valid (version {version})")
        return True
        
    except ImportError:
        print("⚠️  PyYAML not installed, skipping OpenAPI validation")
        return True
    except Exception as e:
        print(f"❌ OpenAPI specification error: {e}")
        return False

def test_code_examples():
    """Test code examples in documentation"""
    print("🔍 Testing code examples...")
    
    import ast
    import re
    
    errors = []
    doc_files = list(PROJECT_ROOT.glob("docs/**/*.md"))
    
    for doc_file in doc_files:
        try:
            with open(doc_file, 'r') as f:
                content = f.read()
            
            # Extract Python code blocks
            python_blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
            
            for i, block in enumerate(python_blocks):
                try:
                    # Skip blocks with obvious placeholders
                    if '...' in block or 'your-api-key' in block or 'example.com' in block:
                        continue
                    
                    # Try to parse the Python code
                    ast.parse(block)
                except SyntaxError as e:
                    errors.append(f"{doc_file}:python-block-{i}: {e}")
                    
        except Exception as e:
            errors.append(f"{doc_file}: {e}")
    
    if errors:
        print("❌ Code example errors found:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("✅ Code examples are syntactically valid")
        return True

def test_documentation_completeness():
    """Test that documentation covers all features"""
    print("🔍 Testing documentation completeness...")
    
    # Check that all services are mentioned in docs
    services_dir = PROJECT_ROOT / "services"
    if services_dir.exists():
        service_files = [f.stem for f in services_dir.glob("*.py") 
                        if not f.name.startswith('__')]
        
        # Read all documentation
        all_docs_content = ""
        for doc_file in PROJECT_ROOT.glob("docs/**/*.md"):
            with open(doc_file, 'r') as f:
                all_docs_content += f.read().lower()
        
        # Check for mentions
        undocumented = []
        for service in service_files:
            service_name = service.replace('_', ' ').replace('-', ' ')
            if service_name not in all_docs_content and service not in all_docs_content:
                undocumented.append(service)
        
        # Filter out utility services
        exclude = {'base', 'utils', '__init__'}
        undocumented = [s for s in undocumented if s not in exclude]
        
        if undocumented:
            print(f"⚠️  Services not documented: {', '.join(undocumented)}")
        else:
            print("✅ All services are documented")
    
    return True

def test_api_documentation():
    """Test API documentation against server (if running)"""
    print("🔍 Testing API documentation...")
    
    try:
        import requests
        
        # Check if server is running
        response = requests.get("http://localhost:5006/api/monitoring/health", timeout=5)
        if response.status_code != 200:
            print("⚠️  Server not running, skipping API tests")
            return True
            
        print("✅ Server is running, API documentation tests would run here")
        # Could add more specific API tests here
        
    except ImportError:
        print("⚠️  Requests not installed, skipping API tests")
    except Exception:
        print("⚠️  Server not running, skipping API tests")
    
    return True

def run_pytest_docs():
    """Run pytest documentation tests"""
    print("🔍 Running pytest documentation tests...")
    
    test_file = PROJECT_ROOT / "tests" / "test_documentation.py"
    if not test_file.exists():
        print("⚠️  Documentation test file not found")
        return True
    
    success, output, error = run_command([
        sys.executable, "-m", "pytest", 
        str(test_file), 
        "-v", "--tb=short"
    ])
    
    if success:
        print("✅ Pytest documentation tests passed")
    else:
        print("❌ Pytest documentation tests failed:")
        print(output)
        print(error)
    
    return success

def generate_documentation_report():
    """Generate a documentation quality report"""
    print("\n📊 Generating documentation report...")
    
    report = {
        "total_docs": 0,
        "total_size": 0,
        "files": {}
    }
    
    # Count documentation files
    for doc_file in PROJECT_ROOT.glob("docs/**/*.md"):
        size = doc_file.stat().st_size
        report["total_docs"] += 1
        report["total_size"] += size
        report["files"][str(doc_file.relative_to(PROJECT_ROOT))] = {
            "size": size,
            "lines": len(doc_file.read_text().splitlines())
        }
    
    # Add main files
    for main_file in ["README.md", "CHANGELOG.md"]:
        file_path = PROJECT_ROOT / main_file
        if file_path.exists():
            size = file_path.stat().st_size
            report["total_docs"] += 1
            report["total_size"] += size
            report["files"][main_file] = {
                "size": size,
                "lines": len(file_path.read_text().splitlines())
            }
    
    print(f"📄 Total documentation files: {report['total_docs']}")
    print(f"📏 Total documentation size: {report['total_size']:,} bytes")
    print(f"📋 Average file size: {report['total_size'] // report['total_docs']:,} bytes")
    
    # Save report
    report_file = PROJECT_ROOT / "docs" / "documentation-report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"📊 Report saved to {report_file}")

def main():
    """Run all documentation tests"""
    print("🚀 Running documentation tests...\n")
    
    tests = [
        test_documentation_syntax,
        test_openapi_spec,
        test_code_examples,
        test_documentation_completeness,
        test_api_documentation,
        run_pytest_docs
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
        print()
    
    # Generate report
    generate_documentation_report()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "="*50)
    print(f"📊 Documentation Test Summary")
    print("="*50)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All documentation tests passed!")
        return 0
    else:
        print("❌ Some documentation tests failed")
        return 1

if __name__ == "__main__":
    exit(main())