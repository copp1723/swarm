#!/usr/bin/env python3
"""
Log cleanup and rotation script
Cleans up old logs and keeps only recent ones
"""

import os
import sys
import gzip
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
LOG_DIR = Path(__file__).parent.parent / "logs"
MAX_LOG_SIZE_MB = 50  # Maximum size before rotation
KEEP_DAYS = 7  # Keep logs for this many days
COMPRESS_AFTER_DAYS = 1  # Compress logs older than this


def get_file_age_days(file_path):
    """Get file age in days"""
    stat = os.stat(file_path)
    age = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
    return age.days


def compress_file(file_path):
    """Compress a file using gzip"""
    with open(file_path, 'rb') as f_in:
        with gzip.open(f"{file_path}.gz", 'wb') as f_out:
            f_out.writelines(f_in)
    os.remove(file_path)
    print(f"Compressed: {file_path}")


def clean_logs():
    """Clean and rotate log files"""
    if not LOG_DIR.exists():
        print(f"Log directory not found: {LOG_DIR}")
        return
    
    total_cleaned = 0
    files_compressed = 0
    files_deleted = 0
    
    for log_file in LOG_DIR.glob("*.log"):
        file_size_mb = log_file.stat().st_size / (1024 * 1024)
        file_age_days = get_file_age_days(log_file)
        
        # Delete very old logs
        if file_age_days > KEEP_DAYS:
            print(f"Deleting old log: {log_file.name} ({file_age_days} days old)")
            log_file.unlink()
            files_deleted += 1
            continue
        
        # Compress older logs
        if file_age_days > COMPRESS_AFTER_DAYS and not log_file.name.endswith('.gz'):
            compress_file(log_file)
            files_compressed += 1
            continue
        
        # Rotate large logs
        if file_size_mb > MAX_LOG_SIZE_MB:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_name = log_file.stem + f"_{timestamp}" + log_file.suffix
            rotated_path = log_file.parent / rotated_name
            
            log_file.rename(rotated_path)
            print(f"Rotated large log: {log_file.name} -> {rotated_name}")
            
            # Create new empty log file
            log_file.touch()
            
            # Compress the rotated file
            compress_file(rotated_path)
            files_compressed += 1
    
    # Clean up old compressed logs
    for gz_file in LOG_DIR.glob("*.log.gz"):
        if get_file_age_days(gz_file) > KEEP_DAYS:
            print(f"Deleting old compressed log: {gz_file.name}")
            gz_file.unlink()
            files_deleted += 1
    
    print("\nLog cleanup summary:")
    print(f"- Files compressed: {files_compressed}")
    print(f"- Files deleted: {files_deleted}")
    print(f"- Total files processed: {files_compressed + files_deleted}")


if __name__ == "__main__":
    print("Starting log cleanup...")
    clean_logs()
    print("Log cleanup completed!")