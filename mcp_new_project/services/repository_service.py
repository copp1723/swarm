import os
import logging
from typing import Dict, Any, List

class RepositoryService:
    """Centralized repository analysis and file handling for multi-agent tasks"""
    
    def __init__(self, base_path: str = "/Users/copp1723/Desktop/working_projects"):
        self.base_path = base_path
        self.logger = logging.getLogger(__name__)
    
    def analyze_repository(self, path: str, include_content: bool = False) -> Dict[str, Any]:
        """Comprehensive repository analysis"""
        full_path = self._resolve_path(path)
        
        analysis = {
            "directory": full_path,
            "total_files": 0,
            "languages": set(),
            "file_categories": {
                "code": [],
                "config": [],
                "documentation": [],
                "package": []
            },
            "priority_files": [],
            "directory_structure": {"directories": []},
            "git_info": {},
            "package_info": {},
            "analysis_summary": ""
        }
        
        for root, dirs, files in os.walk(full_path):
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv', 'env'}]
            rel_root = os.path.relpath(root, full_path)
            if rel_root != '.':
                analysis["directory_structure"]["directories"].append(rel_root)
            
            for file in files:
                if file.startswith('.'):
                    continue
                analysis["total_files"] += 1
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, full_path)

                # File classification
                if file.endswith(('.py', '.js', '.ts', '.go', '.java', '.c', '.cpp')):
                    file_ext = file.split('.')[-1]
                    analysis["languages"].add(self._language_from_extension(file_ext))
                    analysis["file_categories"]["code"].append({"relative_path": rel_path})
                    if file in ['app.py', 'main.py', 'server.py', 'index.js']:
                        analysis["priority_files"].append(rel_path)
                elif file.endswith('.md'):
                    analysis["file_categories"]["documentation"].append({"relative_path": rel_path})
                    if file.lower() in ['readme.md', 'documentation.md']:
                        analysis["priority_files"].append(rel_path)
                elif file in ['package.json', 'requirements.txt', 'Pipfile', 'go.mod', 'pom.xml', 'Cargo.toml']:
                    analysis["file_categories"]["package"].append({"relative_path": rel_path})
                    analysis["priority_files"].append(rel_path)
                elif file in ['.env', 'config.json', 'settings.py', 'application.properties', 'docker-compose.yml']:
                    analysis["file_categories"]["config"].append({"relative_path": rel_path})
                    analysis["priority_files"].append(rel_path)
                    
        analysis["languages"] = list(analysis["languages"])
        analysis["analysis_summary"] = f"Analyzed {analysis['total_files']} files with {len(analysis['file_categories']['code'])} code files in {len(analysis['directory_structure']['directories'])} directories."
        return analysis
    
    def extract_file_contents(self, path: str, file_paths: List[str], max_content_length: int = 7500) -> Dict[str, str]:
        """Get contents of specific repository files"""
        full_path = self._resolve_path(path)
        contents = {}
        
        for rel_path in file_paths:
            abs_path = os.path.join(full_path, rel_path)
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(max_content_length)  # Limit to avoid token overflow
                    contents[rel_path] = content
            except Exception as e:
                contents[rel_path] = f"[ERROR] {str(e)}"
                
        return contents
    
    def _resolve_path(self, path: str) -> str:
        """Ensure absolute path handling"""
        if not os.path.isabs(path):
            return os.path.join(self.base_path, path)
        return path
    
    def _language_from_extension(self, ext: str) -> str:
        """Map file extension to language"""
        return {
            'py': 'Python',
            'js': 'JavaScript',
            'ts': 'TypeScript',
            'go': 'Go',
            'java': 'Java',
            'c': 'C',
            'cpp': 'C++',
            'h': 'C++'
        }.get(ext, ext.upper())