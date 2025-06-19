"""
Maintenance Tasks
Handles periodic maintenance and cleanup operations
"""

import logging
import asyncio
import os
from typing import Dict, Any
from datetime import datetime, timedelta
from celery import current_task, current_app
from config.celery_config import celery_app
from services.token_replay_cache import get_token_replay_cache

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name='tasks.maintenance_tasks.cleanup_expired_tokens')
def cleanup_expired_tokens() -> Dict[str, Any]:
    """Synchronous wrapper for async cleanup_expired_tokens."""
    return run_async(_cleanup_expired_tokens_async())


async def _cleanup_expired_tokens_async() -> Dict[str, Any]:
    """
    Periodic task to clean up expired tokens from replay cache.
    Runs every hour via Celery Beat.
    
    Returns:
        Cleanup statistics
    """
    try:
        logger.info("Starting token cleanup task")
        
        token_cache = get_token_replay_cache()
        
        # Get cache stats before cleanup
        stats_before = await token_cache.get_cache_stats()
        
        # For in-memory cache, cleanup happens automatically
        # For Redis, we rely on TTL expiration
        # This task mainly serves for monitoring and reporting
        
        # Get cache stats after
        stats_after = await token_cache.get_cache_stats()
        
        result = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'cache_type': stats_after.get('type'),
            'tokens_before': stats_before.get('replay_tokens', stats_before.get('total_tokens', 0)),
            'tokens_after': stats_after.get('replay_tokens', stats_after.get('active_tokens', 0)),
            'tokens_cleaned': max(0, 
                stats_before.get('replay_tokens', stats_before.get('total_tokens', 0)) - 
                stats_after.get('replay_tokens', stats_after.get('active_tokens', 0))
            )
        }
        
        logger.info(f"Token cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in token cleanup task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='tasks.maintenance_tasks.monitor_cache_health')
def monitor_cache_health() -> Dict[str, Any]:
    """Synchronous wrapper for async monitor_cache_health."""
    return run_async(_monitor_cache_health_async())


async def _monitor_cache_health_async() -> Dict[str, Any]:
    """
    Monitor the health of the replay cache.
    
    Returns:
        Cache health metrics
    """
    try:
        token_cache = get_token_replay_cache()
        stats = await token_cache.get_cache_stats()
        
        # Determine health status
        health_status = 'healthy'
        warnings = []
        
        if stats.get('type') == 'redis':
            # Check Redis-specific metrics
            if stats.get('connected_clients', 0) == 0:
                health_status = 'unhealthy'
                warnings.append('No Redis clients connected')
            
            # Parse memory usage
            memory_str = stats.get('memory_used', '0')
            if 'GB' in memory_str:
                memory_gb = float(memory_str.replace('GB', '').strip())
                if memory_gb > 1:  # Warning if over 1GB
                    warnings.append(f'High memory usage: {memory_str}')
                    health_status = 'warning' if health_status == 'healthy' else health_status
        
        elif stats.get('type') == 'in-memory':
            # Check in-memory metrics
            total_tokens = stats.get('total_tokens', 0)
            if total_tokens > 100000:  # Warning if over 100k tokens
                warnings.append(f'High token count: {total_tokens}')
                health_status = 'warning' if health_status == 'healthy' else health_status
        
        return {
            'success': True,
            'health_status': health_status,
            'cache_stats': stats,
            'warnings': warnings,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error monitoring cache health: {e}")
        return {
            'success': False,
            'health_status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='tasks.maintenance_tasks.cleanup_old_task_results')
def cleanup_old_task_results(days_to_keep: int = 7) -> Dict[str, Any]:
    """
    Clean up old Celery task results.
    
    Args:
        days_to_keep: Number of days of results to retain
        
    Returns:
        Cleanup statistics
    """
    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        logger.info(f"Cleaning up task results older than {cutoff_date}")
        
        # Get result backend from Celery
        from config.celery_config import celery_app
        backend = celery_app.backend
        
        tasks_cleaned = 0
        
        # Redis backend cleanup
        if hasattr(backend, 'client'):  # Redis backend
            import redis
            client = backend.client
            
            # Pattern for Celery result keys
            result_pattern = 'celery-task-meta-*'
            
            # Scan for keys matching pattern
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=result_pattern, count=100)
                
                for key in keys:
                    try:
                        # Get task result
                        result = client.get(key)
                        if result:
                            import json
                            task_data = json.loads(result)
                            
                            # Check if task is older than cutoff
                            date_done = task_data.get('date_done')
                            if date_done:
                                task_date = datetime.fromisoformat(date_done.replace('Z', '+00:00'))
                                if task_date < cutoff_date:
                                    # Delete the key
                                    client.delete(key)
                                    tasks_cleaned += 1
                    except Exception as e:
                        logger.warning(f"Error processing key {key}: {e}")
                
                if cursor == 0:
                    break
        
        # Database backend cleanup (SQLAlchemy)
        elif hasattr(backend, 'session'):
            from sqlalchemy import text
            
            # Assuming task results are stored in celery_taskmeta table
            delete_query = text("""
                DELETE FROM celery_taskmeta 
                WHERE date_done < :cutoff_date
            """)
            
            result = backend.session.execute(
                delete_query,
                {'cutoff_date': cutoff_date}
            )
            backend.session.commit()
            
            tasks_cleaned = result.rowcount
        
        # File system backend cleanup
        elif hasattr(backend, 'path'):
            import os
            import glob
            
            # Find result files
            result_files = glob.glob(os.path.join(backend.path, '*'))
            
            for filepath in result_files:
                try:
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        tasks_cleaned += 1
                except Exception as e:
                    logger.warning(f"Error processing file {filepath}: {e}")
        
        logger.info(f"Cleaned up {tasks_cleaned} old task results")
        
        return {
            'success': True,
            'cutoff_date': cutoff_date.isoformat(),
            'tasks_cleaned': tasks_cleaned,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up task results: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='tasks.maintenance_tasks.rotate_logs')
def rotate_logs() -> Dict[str, Any]:
    """
    Rotate application logs.
    
    Returns:
        Log rotation results
    """
    try:
        import glob
        from pathlib import Path
        
        log_dir = Path('logs')
        if not log_dir.exists():
            return {
                'success': True,
                'message': 'No logs directory found',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Find log files
        log_files = list(log_dir.glob('*.log'))
        rotated_count = 0
        
        for log_file in log_files:
            # Skip already rotated files
            if any(suffix in log_file.name for suffix in ['.1', '.2', '.gz']):
                continue
            
            # Check file size (rotate if > 100MB)
            if log_file.stat().st_size > 100 * 1024 * 1024:
                # Rotate the log
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                rotated_name = log_file.with_suffix(f'.{timestamp}.log')
                log_file.rename(rotated_name)
                
                # Compress the rotated file
                import gzip
                import shutil
                
                compressed_name = rotated_name.with_suffix('.log.gz')
                
                try:
                    with open(rotated_name, 'rb') as f_in:
                        with gzip.open(compressed_name, 'wb', compresslevel=9) as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Remove the uncompressed rotated file
                    rotated_name.unlink()
                    
                    logger.info(f"Compressed log file: {rotated_name} -> {compressed_name}")
                except Exception as compress_error:
                    logger.warning(f"Failed to compress {rotated_name}: {compress_error}")
                
                rotated_count += 1
                logger.info(f"Rotated log file: {log_file}")
        
        return {
            'success': True,
            'files_rotated': rotated_count,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error rotating logs: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='tasks.maintenance_tasks.system_health_check')
def system_health_check() -> Dict[str, Any]:
    """Synchronous wrapper for async system_health_check."""
    return run_async(_system_health_check_async())


async def _system_health_check_async() -> Dict[str, Any]:
    """
    Perform comprehensive system health check.
    
    Returns:
        System health report
    """
    try:
        health_report = {
            'timestamp': datetime.utcnow().isoformat(),
            'services': {}
        }
        
        # Check token cache
        cache_health = await _monitor_cache_health_async()
        health_report['services']['token_cache'] = {
            'status': cache_health.get('health_status', 'unknown'),
            'details': cache_health.get('cache_stats', {})
        }
        
        # Check Redis connection
        try:
            from redis import Redis
            redis_client = Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
            redis_client.ping()
            health_report['services']['redis'] = {
                'status': 'healthy',
                'info': redis_client.info('server')
            }
        except Exception as e:
            health_report['services']['redis'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        # Check Celery workers
        active_queues = list(current_app.control.inspect().active_queues() or {})
        health_report['services']['celery'] = {
            'status': 'healthy' if active_queues else 'warning',
            'active_workers': len(active_queues)
        }
        
        # Overall health
        all_healthy = all(
            service.get('status') == 'healthy' 
            for service in health_report['services'].values()
        )
        health_report['overall_status'] = 'healthy' if all_healthy else 'degraded'
        
        logger.info(f"System health check completed: {health_report['overall_status']}")
        return health_report
        
    except Exception as e:
        logger.error(f"Error in system health check: {e}")
        return {
            'overall_status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }