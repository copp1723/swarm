"""
Audit Storage Backend - Stores audit records in database
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from abc import ABC, abstractmethod
import asyncio
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from services.auditing.agent_auditor import AuditRecord, AuditLevel
from models.core import db
from utils.logging_config import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class AuditRecordModel(Base):
    """Database model for audit records"""
    __tablename__ = 'agent_audit_records'
    
    record_id = Column(String(50), primary_key=True)
    timestamp = Column(DateTime, index=True)
    task_id = Column(String(100), index=True)
    agent_id = Column(String(100), index=True)
    agent_name = Column(String(200))
    action_type = Column(String(100))
    action_name = Column(String(200))
    level = Column(String(20))
    duration_ms = Column(Float)
    success = Column(Boolean)
    
    # JSON columns for complex data
    inputs = Column(JSON)
    outputs = Column(JSON)
    context = Column(JSON)
    reasoning = Column(Text)
    
    # Error tracking
    error_message = Column(Text)
    error_traceback = Column(Text)
    
    # Performance metrics
    tokens_used = Column(Integer)
    model_calls = Column(Integer)
    memory_used_mb = Column(Float)
    
    # Steps and tools as JSON
    intermediate_steps = Column(JSON)
    tools_used = Column(JSON)
    
    # Indexes for common queries
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AuditStorage(ABC):
    """Abstract base class for audit storage backends"""
    
    @abstractmethod
    async def store_record(self, record: AuditRecord) -> None:
        """Store an audit record"""
        pass
    
    @abstractmethod
    async def get_record(self, record_id: str) -> Optional[AuditRecord]:
        """Retrieve a specific audit record"""
        pass
    
    @abstractmethod
    async def get_records_by_task(self, task_id: str) -> List[AuditRecord]:
        """Get all records for a task"""
        pass
    
    @abstractmethod
    async def get_records_by_agent(self, agent_id: str, limit: int = 100) -> List[AuditRecord]:
        """Get recent records for an agent"""
        pass


class DatabaseAuditStorage(AuditStorage):
    """Database-backed audit storage using SQLAlchemy"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url
        self.logger = get_logger(__name__)
        self._initialized = False
        self._engine = None
        self._sessionmaker = None
        
    async def initialize(self):
        """Initialize the database connection"""
        if not self._initialized:
            if self.database_url:
                # Use async engine for provided URL
                self._engine = create_async_engine(self.database_url, echo=False)
                self._sessionmaker = sessionmaker(
                    self._engine, class_=AsyncSession, expire_on_commit=False
                )
                # Create tables
                async with self._engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            self._initialized = True
            self.logger.info("Audit storage initialized")
    
    async def store_record(self, record: AuditRecord) -> None:
        """Store an audit record in the database"""
        await self.initialize()
        
        try:
            if self._sessionmaker:
                async with self._sessionmaker() as session:
                    db_record = AuditRecordModel(
                        record_id=record.record_id,
                        timestamp=record.timestamp,
                        task_id=record.task_id,
                        agent_id=record.agent_id,
                        agent_name=record.agent_name,
                        action_type=record.action_type,
                        action_name=record.action_name,
                        level=record.level.value,
                        duration_ms=record.duration_ms,
                        success=record.success,
                        inputs=record.inputs,
                        outputs=record.outputs,
                        context=record.context,
                        reasoning=record.reasoning,
                        error_message=record.error_message,
                        error_traceback=record.error_traceback,
                        tokens_used=record.tokens_used,
                        model_calls=record.model_calls,
                        memory_used_mb=record.memory_used_mb,
                        intermediate_steps=record.intermediate_steps,
                        tools_used=record.tools_used
                    )
                    session.add(db_record)
                    await session.commit()
            else:
                # Fallback to sync storage using Flask-SQLAlchemy
                self.store_record_sync(record)
                
        except Exception as e:
            self.logger.error(f"Failed to store audit record: {e}")
    
    def store_record_sync(self, record: AuditRecord) -> None:
        """Synchronous storage method for Flask-SQLAlchemy"""
        try:
            # Use the Flask app's database session
            from models.core import db
            
            # Create SQLAlchemy model compatible with Flask-SQLAlchemy
            from sqlalchemy.ext.declarative import declarative_base
            
            # Store as JSON in a simple audit table
            audit_json = record.to_dict()
            
            # For now, log to file as the table might not exist
            self.logger.info(f"Audit Record: {audit_json}")
            
        except Exception as e:
            self.logger.error(f"Failed to store audit record (sync): {e}")
    
    async def get_record(self, record_id: str) -> Optional[AuditRecord]:
        """Retrieve a specific audit record"""
        await self.initialize()
        
        try:
            if self._sessionmaker:
                async with self._sessionmaker() as session:
                    result = await session.get(AuditRecordModel, record_id)
                    if result:
                        return self._model_to_record(result)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit record: {e}")
            return None
    
    async def get_records_by_task(self, task_id: str) -> List[AuditRecord]:
        """Get all audit records for a task"""
        await self.initialize()
        
        try:
            if self._sessionmaker:
                async with self._sessionmaker() as session:
                    from sqlalchemy import select
                    stmt = select(AuditRecordModel).where(
                        AuditRecordModel.task_id == task_id
                    ).order_by(AuditRecordModel.timestamp)
                    
                    result = await session.execute(stmt)
                    records = result.scalars().all()
                    
                    return [self._model_to_record(r) for r in records]
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get task audit records: {e}")
            return []
    
    async def get_records_by_agent(self, agent_id: str, limit: int = 100) -> List[AuditRecord]:
        """Get recent audit records for an agent"""
        await self.initialize()
        
        try:
            if self._sessionmaker:
                async with self._sessionmaker() as session:
                    from sqlalchemy import select
                    stmt = select(AuditRecordModel).where(
                        AuditRecordModel.agent_id == agent_id
                    ).order_by(
                        AuditRecordModel.timestamp.desc()
                    ).limit(limit)
                    
                    result = await session.execute(stmt)
                    records = result.scalars().all()
                    
                    return [self._model_to_record(r) for r in records]
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get agent audit records: {e}")
            return []
    
    def _model_to_record(self, model: AuditRecordModel) -> AuditRecord:
        """Convert database model to AuditRecord"""
        return AuditRecord(
            record_id=model.record_id,
            timestamp=model.timestamp,
            task_id=model.task_id,
            agent_id=model.agent_id,
            agent_name=model.agent_name,
            action_type=model.action_type,
            action_name=model.action_name,
            level=AuditLevel(model.level),
            duration_ms=model.duration_ms,
            success=model.success,
            inputs=model.inputs or {},
            outputs=model.outputs or {},
            context=model.context or {},
            reasoning=model.reasoning,
            error_message=model.error_message,
            error_traceback=model.error_traceback,
            intermediate_steps=model.intermediate_steps or [],
            tools_used=model.tools_used or [],
            tokens_used=model.tokens_used,
            model_calls=model.model_calls,
            memory_used_mb=model.memory_used_mb
        )
    
    async def get_statistics(self, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get audit statistics for a date range"""
        await self.initialize()
        
        try:
            if self._sessionmaker:
                async with self._sessionmaker() as session:
                    from sqlalchemy import select, func
                    
                    # Build query with date filters
                    query = select(
                        func.count(AuditRecordModel.record_id).label('total_actions'),
                        func.sum(AuditRecordModel.success.cast(Integer)).label('successful_actions'),
                        func.avg(AuditRecordModel.duration_ms).label('avg_duration_ms'),
                        func.sum(AuditRecordModel.tokens_used).label('total_tokens'),
                        func.sum(AuditRecordModel.model_calls).label('total_model_calls')
                    )
                    
                    if start_date:
                        query = query.where(AuditRecordModel.timestamp >= start_date)
                    if end_date:
                        query = query.where(AuditRecordModel.timestamp <= end_date)
                    
                    result = await session.execute(query)
                    stats = result.first()
                    
                    # Get per-agent statistics
                    agent_query = select(
                        AuditRecordModel.agent_id,
                        AuditRecordModel.agent_name,
                        func.count(AuditRecordModel.record_id).label('action_count'),
                        func.avg(AuditRecordModel.duration_ms).label('avg_duration')
                    ).group_by(
                        AuditRecordModel.agent_id,
                        AuditRecordModel.agent_name
                    )
                    
                    if start_date:
                        agent_query = agent_query.where(AuditRecordModel.timestamp >= start_date)
                    if end_date:
                        agent_query = agent_query.where(AuditRecordModel.timestamp <= end_date)
                    
                    agent_result = await session.execute(agent_query)
                    agent_stats = [
                        {
                            'agent_id': row.agent_id,
                            'agent_name': row.agent_name,
                            'action_count': row.action_count,
                            'avg_duration_ms': float(row.avg_duration) if row.avg_duration else 0
                        }
                        for row in agent_result
                    ]
                    
                    return {
                        'total_actions': stats.total_actions or 0,
                        'successful_actions': stats.successful_actions or 0,
                        'success_rate': (stats.successful_actions / stats.total_actions * 100) if stats.total_actions else 0,
                        'avg_duration_ms': float(stats.avg_duration_ms) if stats.avg_duration_ms else 0,
                        'total_tokens': stats.total_tokens or 0,
                        'total_model_calls': stats.total_model_calls or 0,
                        'agent_statistics': agent_stats,
                        'date_range': {
                            'start': start_date.isoformat() if start_date else None,
                            'end': end_date.isoformat() if end_date else None
                        }
                    }
            
            return {
                'error': 'Database not initialized',
                'total_actions': 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get audit statistics: {e}")
            return {
                'error': str(e),
                'total_actions': 0
            }