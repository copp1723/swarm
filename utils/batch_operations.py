"""Batch operations utility for efficient database operations"""
import asyncio
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Generator, Type, Callable, AsyncGenerator
from sqlalchemy import and_, or_, select, update, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from models.core import db

logger = logging.getLogger(__name__)


async def batch_insert(
    db_session: AsyncSession,
    model_class: Type[db.Model],
    records: List[Dict],
    batch_size: int = 1000,
    on_conflict: str = 'raise',
    return_ids: bool = False
) -> Dict[str, Any]:
    """
    Insert multiple records in batches.
    
    Args:
        db_session: SQLAlchemy async session
        model_class: SQLAlchemy model class
        records: List of dictionaries containing record data
        batch_size: Number of records per batch
        on_conflict: How to handle conflicts ('raise', 'ignore', 'update')
        return_ids: Whether to return inserted IDs
        
    Returns:
        Dict with success count, failed records, and optionally IDs
    """
    result = {
        'success_count': 0,
        'failed_count': 0,
        'failed_records': [],
        'errors': []
    }
    
    if return_ids:
        result['inserted_ids'] = []
    
    total_records = len(records)
    logger.info(f"Starting batch insert of {total_records} records into {model_class.__name__}")
    
    for i in range(0, total_records, batch_size):
        batch = records[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            # Create model instances
            instances = []
            for record in batch:
                try:
                    instance = model_class(**record)
                    instances.append(instance)
                except Exception as e:
                    logger.error(f"Error creating instance: {e}")
                    result['failed_count'] += 1
                    result['failed_records'].append({
                        'record': record,
                        'error': str(e)
                    })
                    continue
            
            if not instances:
                continue
                
            # Perform batch insert
            try:
                if on_conflict == 'ignore':
                    # Use merge for upsert behavior
                    for instance in instances:
                        db_session.merge(instance)
                else:
                    # Regular add
                    db_session.add_all(instances)
                
                await db_session.flush()
                
                # Collect IDs if requested
                if return_ids:
                    for instance in instances:
                        result['inserted_ids'].append(instance.id)
                
                result['success_count'] += len(instances)
                logger.debug(f"Batch {batch_num}: Inserted {len(instances)} records")
                
            except IntegrityError as e:
                if on_conflict == 'raise':
                    await db_session.rollback()
                    raise
                elif on_conflict == 'ignore':
                    await db_session.rollback()
                    logger.warning(f"Batch {batch_num}: Integrity error (ignored): {e}")
                    # Try individual inserts to identify problematic records
                    for record in batch:
                        try:
                            instance = model_class(**record)
                            db_session.add(instance)
                            await db_session.flush()
                            result['success_count'] += 1
                        except Exception as sub_e:
                            await db_session.rollback()
                            result['failed_count'] += 1
                            result['failed_records'].append({
                                'record': record,
                                'error': str(sub_e)
                            })
                            
        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            await db_session.rollback()
            result['failed_count'] += len(batch)
            result['errors'].append(f"Batch {batch_num}: {str(e)}")
            
        # Log progress for large operations
        if total_records > 10000 and i % (batch_size * 10) == 0:
            progress = (i + batch_size) / total_records * 100
            logger.info(f"Progress: {progress:.1f}% ({i + batch_size}/{total_records})")
    
    logger.info(
        f"Batch insert completed: {result['success_count']} succeeded, "
        f"{result['failed_count']} failed"
    )
    
    return result


async def batch_update(
    db_session: AsyncSession,
    model_class: Type[db.Model],
    updates: List[Dict],
    batch_size: int = 500,
    key_field: str = 'id'
) -> Dict[str, Any]:
    """
    Update multiple records in batches.
    
    Args:
        db_session: SQLAlchemy async session
        model_class: SQLAlchemy model class
        updates: List of dicts with key field and fields to update
        batch_size: Number of records per batch
        key_field: Field to use for matching records (default: 'id')
        
    Returns:
        Dict with success count and failed updates
    """
    result = {
        'success_count': 0,
        'failed_count': 0,
        'failed_updates': [],
        'errors': []
    }
    
    total_updates = len(updates)
    logger.info(f"Starting batch update of {total_updates} records in {model_class.__name__}")
    
    for i in range(0, total_updates, batch_size):
        batch = updates[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            # Group updates by the fields being updated for efficiency
            update_groups = {}
            for update_data in batch:
                if key_field not in update_data:
                    result['failed_count'] += 1
                    result['failed_updates'].append({
                        'update': update_data,
                        'error': f'Missing key field: {key_field}'
                    })
                    continue
                
                key_value = update_data[key_field]
                update_fields = {k: v for k, v in update_data.items() if k != key_field}
                
                # Create a hashable key for grouping
                fields_key = tuple(sorted(update_fields.keys()))
                if fields_key not in update_groups:
                    update_groups[fields_key] = {
                        'fields': update_fields,
                        'keys': []
                    }
                update_groups[fields_key]['keys'].append(key_value)
            
            # Execute grouped updates
            for fields_key, group in update_groups.items():
                try:
                    stmt = (
                        update(model_class)
                        .where(getattr(model_class, key_field).in_(group['keys']))
                        .values(**group['fields'])
                    )
                    
                    result_proxy = await db_session.execute(stmt)
                    updated_count = result_proxy.rowcount
                    result['success_count'] += updated_count
                    
                    if updated_count < len(group['keys']):
                        logger.warning(
                            f"Batch {batch_num}: Expected to update {len(group['keys'])} "
                            f"records but only updated {updated_count}"
                        )
                        
                except Exception as e:
                    logger.error(f"Failed to update group in batch {batch_num}: {e}")
                    result['failed_count'] += len(group['keys'])
                    result['errors'].append(f"Batch {batch_num}: {str(e)}")
                    
            await db_session.flush()
            logger.debug(f"Batch {batch_num}: Processed {len(batch)} updates")
            
        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            await db_session.rollback()
            result['failed_count'] += len(batch)
            result['errors'].append(f"Batch {batch_num}: {str(e)}")
    
    logger.info(
        f"Batch update completed: {result['success_count']} succeeded, "
        f"{result['failed_count']} failed"
    )
    
    return result


async def batch_delete(
    db_session: AsyncSession,
    model_class: Type[db.Model],
    ids: List[Any],
    batch_size: int = 1000,
    key_field: str = 'id'
) -> Dict[str, Any]:
    """
    Delete multiple records by ID in batches.
    
    Args:
        db_session: SQLAlchemy async session
        model_class: SQLAlchemy model class
        ids: List of IDs to delete
        batch_size: Number of records per batch
        key_field: Field to use for matching records (default: 'id')
        
    Returns:
        Dict with success count and failed deletions
    """
    result = {
        'success_count': 0,
        'failed_count': 0,
        'errors': []
    }
    
    total_deletes = len(ids)
    logger.info(f"Starting batch delete of {total_deletes} records from {model_class.__name__}")
    
    for i in range(0, total_deletes, batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            stmt = (
                delete(model_class)
                .where(getattr(model_class, key_field).in_(batch_ids))
            )
            
            result_proxy = await db_session.execute(stmt)
            deleted_count = result_proxy.rowcount
            result['success_count'] += deleted_count
            
            if deleted_count < len(batch_ids):
                logger.warning(
                    f"Batch {batch_num}: Expected to delete {len(batch_ids)} "
                    f"records but only deleted {deleted_count}"
                )
                result['failed_count'] += (len(batch_ids) - deleted_count)
                
            await db_session.flush()
            logger.debug(f"Batch {batch_num}: Deleted {deleted_count} records")
            
        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            await db_session.rollback()
            result['failed_count'] += len(batch_ids)
            result['errors'].append(f"Batch {batch_num}: {str(e)}")
    
    logger.info(
        f"Batch delete completed: {result['success_count']} succeeded, "
        f"{result['failed_count']} failed"
    )
    
    return result


@contextmanager
def transaction_with_rollback(db_session: Session) -> Generator[None, None, None]:
    """
    Context manager for database transactions with automatic rollback on error.
    
    Args:
        db_session: SQLAlchemy session
        
    Example:
        with transaction_with_rollback(db.session):
            user = User(name='test')
            db.session.add(user)
            # Automatically commits on success, rolls back on exception
    """
    try:
        yield
        db_session.commit()
        logger.debug("Transaction committed successfully")
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error, transaction rolled back: {e}")
        raise
    except Exception as e:
        db_session.rollback()
        logger.error(f"Unexpected error, transaction rolled back: {e}")
        raise


def chunked_query(
    query,
    chunk_size: int = 1000,
    order_by: Optional[Any] = None
) -> Generator[List[Any], None, None]:
    """
    Generator that yields query results in chunks to avoid memory issues.
    
    Args:
        query: SQLAlchemy query object
        chunk_size: Number of records per chunk
        order_by: Column to order by (recommended for consistent chunking)
        
    Yields:
        Lists of records
        
    Example:
        query = db.session.query(User)
        for chunk in chunked_query(query, chunk_size=500):
            for user in chunk:
                process_user(user)
    """
    # Add ordering if specified
    if order_by is not None:
        query = query.order_by(order_by)
    
    offset = 0
    while True:
        # Get chunk
        chunk = query.limit(chunk_size).offset(offset).all()
        
        if not chunk:
            break
            
        logger.debug(f"Retrieved chunk of {len(chunk)} records (offset: {offset})")
        yield chunk
        
        # If we got less than chunk_size, we're done
        if len(chunk) < chunk_size:
            break
            
        offset += chunk_size


async def async_chunked_query(
    query,
    db_session: AsyncSession,
    chunk_size: int = 1000,
    order_by: Optional[Any] = None
) -> AsyncGenerator[List[Any], None]:
    """
    Async generator that yields query results in chunks.
    
    Args:
        query: SQLAlchemy query object
        db_session: Async database session
        chunk_size: Number of records per chunk
        order_by: Column to order by
        
    Yields:
        Lists of records
    """
    # Add ordering if specified
    if order_by is not None:
        query = query.order_by(order_by)
    
    offset = 0
    while True:
        # Get chunk
        result = await db_session.execute(
            query.limit(chunk_size).offset(offset)
        )
        chunk = result.scalars().all()
        
        if not chunk:
            break
            
        logger.debug(f"Retrieved async chunk of {len(chunk)} records (offset: {offset})")
        yield chunk
        
        # If we got less than chunk_size, we're done
        if len(chunk) < chunk_size:
            break
            
        offset += chunk_size


class BatchProcessor:
    """
    Helper class for processing large datasets in batches with progress tracking.
    
    Example:
        processor = BatchProcessor(batch_size=1000)
        
        async def process_user(user):
            # Process individual user
            pass
            
        await processor.process_async(users, process_user)
    """
    
    def __init__(self, batch_size: int = 1000, log_progress: bool = True):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Size of each batch
            log_progress: Whether to log progress
        """
        self.batch_size = batch_size
        self.log_progress = log_progress
        
    async def process_async(
        self,
        items: List[Any],
        process_func: Callable,
        max_concurrent: int = 10
    ) -> Dict[str, Any]:
        """
        Process items in batches asynchronously.
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            max_concurrent: Maximum concurrent operations
            
        Returns:
            Dict with processing results
        """
        result = {
            'total': len(items),
            'succeeded': 0,
            'failed': 0,
            'errors': []
        }
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(item, index):
            async with semaphore:
                try:
                    await process_func(item)
                    return True, None
                except Exception as e:
                    logger.error(f"Error processing item {index}: {e}")
                    return False, str(e)
        
        # Process in batches
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            # Process batch items concurrently
            tasks = [
                process_with_semaphore(item, i + j)
                for j, item in enumerate(batch)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Count results
            for success, error in results:
                if success:
                    result['succeeded'] += 1
                else:
                    result['failed'] += 1
                    if error:
                        result['errors'].append(error)
            
            # Log progress
            if self.log_progress:
                progress = (i + len(batch)) / len(items) * 100
                logger.info(
                    f"Batch {batch_num}: Processed {len(batch)} items. "
                    f"Progress: {progress:.1f}%"
                )
        
        logger.info(
            f"Batch processing completed: {result['succeeded']} succeeded, "
            f"{result['failed']} failed"
        )
        
        return result