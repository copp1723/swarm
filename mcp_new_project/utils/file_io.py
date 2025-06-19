"""File I/O utilities with safe operations and error handling"""
import os
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


def safe_read_json(file_path: str, default_value: Any = None) -> Any:
    """
    Safely read and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file
        default_value: Value to return if file doesn't exist or parsing fails
        
    Returns:
        Parsed JSON data or default_value
        
    Example:
        config = safe_read_json('config.json', default_value={})
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"JSON file not found: {file_path}, returning default value")
        return default_value
    except PermissionError:
        logger.error(f"Permission denied reading JSON file: {file_path}")
        return default_value
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        return default_value
    except Exception as e:
        logger.error(f"Unexpected error reading JSON file {file_path}: {e}")
        return default_value


def safe_write_json(file_path: str, data: Any, indent: int = 2) -> bool:
    """
    Safely write data to a JSON file with atomic write operation.
    
    Args:
        file_path: Path to write the JSON file
        data: Data to serialize to JSON
        indent: JSON indentation level
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        ensure_directory_exists(os.path.dirname(file_path))
        
        # Serialize to JSON first to catch any serialization errors
        json_data = json.dumps(data, indent=indent, ensure_ascii=False)
        
        # Use atomic write
        return atomic_write(file_path, json_data)
    except TypeError as e:
        logger.error(f"Data not JSON serializable: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error writing JSON file {file_path}: {e}")
        return False


def safe_read_yaml(file_path: str, default_value: Any = None) -> Any:
    """
    Safely read and parse a YAML file.
    
    Args:
        file_path: Path to the YAML file
        default_value: Value to return if file doesn't exist or parsing fails
        
    Returns:
        Parsed YAML data or default_value
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"YAML file not found: {file_path}, returning default value")
        return default_value
    except PermissionError:
        logger.error(f"Permission denied reading YAML file: {file_path}")
        return default_value
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in file {file_path}: {e}")
        return default_value
    except Exception as e:
        logger.error(f"Unexpected error reading YAML file {file_path}: {e}")
        return default_value


def safe_write_yaml(file_path: str, data: Any) -> bool:
    """
    Safely write data to a YAML file.
    
    Args:
        file_path: Path to write the YAML file
        data: Data to serialize to YAML
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        ensure_directory_exists(os.path.dirname(file_path))
        
        # Serialize to YAML first to catch any serialization errors
        yaml_data = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        
        # Use atomic write
        return atomic_write(file_path, yaml_data)
    except yaml.YAMLError as e:
        logger.error(f"Error serializing data to YAML: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error writing YAML file {file_path}: {e}")
        return False


def atomic_write(file_path: str, content: str) -> bool:
    """
    Perform atomic file write to prevent partial writes.
    Writes to temp file first, then renames.
    
    Args:
        file_path: Target file path
        content: Content to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the directory and create a temp file in the same directory
        # This ensures we can do an atomic rename
        dir_path = os.path.dirname(os.path.abspath(file_path))
        ensure_directory_exists(dir_path)
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                       dir=dir_path, delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Atomic rename
        shutil.move(tmp_file_path, file_path)
        logger.debug(f"Successfully wrote file: {file_path}")
        return True
        
    except PermissionError:
        logger.error(f"Permission denied writing file: {file_path}")
        # Clean up temp file if it exists
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        return False
    except Exception as e:
        logger.error(f"Error during atomic write to {file_path}: {e}")
        # Clean up temp file if it exists
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        return False


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Create directory and all parent directories if they don't exist.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        True if directory exists or was created, False on error
    """
    if not directory_path:
        return True  # Empty path is considered success
        
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        logger.error(f"Permission denied creating directory: {directory_path}")
        return False
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False


@contextmanager
def safe_file_operation(file_path: str, mode: str = 'r', encoding: str = 'utf-8'):
    """
    Context manager for safe file operations with automatic error handling.
    
    Args:
        file_path: Path to the file
        mode: File open mode
        encoding: File encoding
        
    Yields:
        File handle
        
    Example:
        with safe_file_operation('data.txt', 'w') as f:
            if f:
                f.write('content')
    """
    file_handle = None
    try:
        # Ensure directory exists for write modes
        if any(m in mode for m in ['w', 'a', 'x']):
            ensure_directory_exists(os.path.dirname(file_path))
        
        file_handle = open(file_path, mode, encoding=encoding)
        yield file_handle
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        yield None
    except PermissionError:
        logger.error(f"Permission denied accessing file: {file_path}")
        yield None
    except Exception as e:
        logger.error(f"Error opening file {file_path}: {e}")
        yield None
    finally:
        if file_handle:
            try:
                file_handle.close()
            except Exception as e:
                logger.error(f"Error closing file {file_path}: {e}")


def read_file_lines(file_path: str, skip_empty: bool = False) -> List[str]:
    """
    Read file and return lines as a list.
    
    Args:
        file_path: Path to the file
        skip_empty: Whether to skip empty lines
        
    Returns:
        List of lines or empty list on error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if skip_empty:
                lines = [line.strip() for line in lines if line.strip()]
            else:
                lines = [line.rstrip('\n') for line in lines]
            return lines
    except Exception as e:
        logger.error(f"Error reading lines from {file_path}: {e}")
        return []


def append_to_file(file_path: str, content: str, add_newline: bool = True) -> bool:
    """
    Safely append content to a file.
    
    Args:
        file_path: Path to the file
        content: Content to append
        add_newline: Whether to add a newline after content
        
    Returns:
        True if successful, False otherwise
    """
    try:
        ensure_directory_exists(os.path.dirname(file_path))
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)
            if add_newline and not content.endswith('\n'):
                f.write('\n')
        return True
    except Exception as e:
        logger.error(f"Error appending to file {file_path}: {e}")
        return False


def file_exists(file_path: str) -> bool:
    """
    Check if a file exists and is accessible.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file exists and is accessible
    """
    try:
        return os.path.isfile(file_path) and os.access(file_path, os.R_OK)
    except Exception:
        return False


def get_file_size(file_path: str) -> Optional[int]:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes or None on error
    """
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        return None


def copy_file(source: str, destination: str, create_dirs: bool = True) -> bool:
    """
    Safely copy a file.
    
    Args:
        source: Source file path
        destination: Destination file path
        create_dirs: Whether to create destination directories
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if create_dirs:
            ensure_directory_exists(os.path.dirname(destination))
        shutil.copy2(source, destination)
        logger.debug(f"Successfully copied {source} to {destination}")
        return True
    except Exception as e:
        logger.error(f"Error copying file from {source} to {destination}: {e}")
        return False


def move_file(source: str, destination: str, create_dirs: bool = True) -> bool:
    """
    Safely move a file.
    
    Args:
        source: Source file path
        destination: Destination file path
        create_dirs: Whether to create destination directories
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if create_dirs:
            ensure_directory_exists(os.path.dirname(destination))
        shutil.move(source, destination)
        logger.debug(f"Successfully moved {source} to {destination}")
        return True
    except Exception as e:
        logger.error(f"Error moving file from {source} to {destination}: {e}")
        return False


def delete_file(file_path: str, ignore_missing: bool = True) -> bool:
    """
    Safely delete a file.
    
    Args:
        file_path: Path to the file to delete
        ignore_missing: Whether to ignore if file doesn't exist
        
    Returns:
        True if successful or file doesn't exist (when ignore_missing=True)
    """
    try:
        os.unlink(file_path)
        logger.debug(f"Successfully deleted file: {file_path}")
        return True
    except FileNotFoundError:
        if ignore_missing:
            return True
        logger.error(f"File not found when trying to delete: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return False