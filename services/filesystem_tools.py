"""
Direct filesystem tools for agents when MCP servers are not available
"""
import os
import glob
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from utils.file_io import safe_read_json, safe_write_json, safe_file_operation, ensure_directory_exists
from utils.error_catalog import ErrorCodes, format_error_response

logger = logging.getLogger(__name__)

class FilesystemTools:
    """Direct filesystem access tools for agents"""
    
    def __init__(self, base_path: str = "/Users/copp1723/Desktop"):
        self.base_path = Path(base_path)
        logger.info(f"FilesystemTools initialized with base path: {self.base_path}")
    
    def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """List contents of a directory"""
        try:
            full_path = self._resolve_path(path)
            if not full_path.exists():
                return {"error": f"Path does not exist: {path}"}
            
            if not full_path.is_dir():
                return {"error": f"Path is not a directory: {path}"}
            
            items = []
            for item in full_path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "path": str(item.relative_to(self.base_path))
                })
            
            return {
                "success": True,
                "path": str(full_path.relative_to(self.base_path)),
                "items": items,
                "total_items": len(items)
            }
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return {"error": str(e)}
    
    def read_file(self, path: str, max_size: int = 10000) -> Dict[str, Any]:
        """Read contents of a file"""
        try:
            full_path = self._resolve_path(path)
            if not full_path.exists():
                return format_error_response(
                    ErrorCodes.FILE_NOT_FOUND,
                    filename=path
                )
            
            if not full_path.is_file():
                return format_error_response(
                    ErrorCodes.INVALID_PARAMETER,
                    parameter='path',
                    reason='Path is not a file'
                )
            
            if full_path.stat().st_size > max_size:
                return format_error_response(
                    ErrorCodes.FILE_TOO_LARGE,
                    max_size=f"{max_size} bytes"
                )
            
            with safe_file_operation(str(full_path), 'r') as f:
                if f:
                    content = f.read()
                else:
                    return format_error_response(
                        ErrorCodes.FILE_NOT_FOUND,
                        filename=path
                    )
            
            return {
                "success": True,
                "path": str(full_path.relative_to(self.base_path)),
                "content": content,
                "size": len(content)
            }
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return format_error_response(
                ErrorCodes.STORAGE_ERROR,
                operation='read',
                details={'error': str(e)}
            )
    
    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file"""
        try:
            full_path = self._resolve_path(path)
            
            # Create directory if it doesn't exist
            if not ensure_directory_exists(str(full_path.parent)):
                return format_error_response(
                    ErrorCodes.STORAGE_ERROR,
                    operation='create_directory',
                    details={'path': str(full_path.parent)}
                )
            
            with safe_file_operation(str(full_path), 'w') as f:
                if f:
                    f.write(content)
                else:
                    return format_error_response(
                        ErrorCodes.STORAGE_ERROR,
                        operation='write',
                        details={'path': path}
                    )
            
            return {
                "success": True,
                "path": str(full_path.relative_to(self.base_path)),
                "bytes_written": len(content.encode('utf-8'))
            }
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            return format_error_response(
                ErrorCodes.STORAGE_ERROR,
                operation='write',
                details={'error': str(e)}
            )
    
    def search_files(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        """Search for files matching a pattern"""
        try:
            full_path = self._resolve_path(path)
            if not full_path.exists():
                return {"error": f"Path does not exist: {path}"}
            
            matches = []
            search_path = full_path / "**" / pattern
            for match in glob.glob(str(search_path), recursive=True):
                match_path = Path(match)
                matches.append({
                    "name": match_path.name,
                    "path": str(match_path.relative_to(self.base_path)),
                    "type": "directory" if match_path.is_dir() else "file",
                    "size": match_path.stat().st_size if match_path.is_file() else None
                })
            
            return {
                "success": True,
                "pattern": pattern,
                "search_path": str(full_path.relative_to(self.base_path)),
                "matches": matches,
                "total_matches": len(matches)
            }
        except Exception as e:
            logger.error(f"Error searching files with pattern {pattern}: {e}")
            return {"error": str(e)}
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed information about a file or directory"""
        try:
            full_path = self._resolve_path(path)
            if not full_path.exists():
                return {"error": f"Path does not exist: {path}"}
            
            stat = full_path.stat()
            
            return {
                "success": True,
                "path": str(full_path.relative_to(self.base_path)),
                "name": full_path.name,
                "type": "directory" if full_path.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:]
            }
        except Exception as e:
            logger.error(f"Error getting file info for {path}: {e}")
            return {"error": str(e)}
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path to an absolute path within base_path"""
        if os.path.isabs(path):
            # If absolute path, ensure it's within base_path
            abs_path = Path(path)
            try:
                abs_path.relative_to(self.base_path)
                return abs_path
            except ValueError:
                # Path is outside base_path, treat as relative
                return self.base_path / Path(path).name
        else:
            return self.base_path / path

# Global instance
filesystem_tools = FilesystemTools()