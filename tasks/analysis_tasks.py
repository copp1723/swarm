"""
Analysis Task Definitions for Celery
Handles data analysis and reporting tasks
"""
import time
import logging
from typing import Dict, Any, List
from celery import current_task
from config.celery_config import celery_app
from repositories.async_repositories import AsyncSystemLogRepository, AsyncModelUsageRepository
from utils.async_wrapper import async_manager

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='tasks.analysis_tasks.generate_usage_report')
def generate_usage_report(self, report_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate comprehensive usage report in background
    
    Args:
        report_config: Configuration for report generation
        
    Returns:
        Dict containing generated report data
    """
    task_id = self.request.id
    logger.info(f"Starting usage report generation task {task_id}")
    
    try:
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Gathering usage data...', 'progress': 20}
        )
        
        # Gather usage statistics
        days = report_config.get('days', 30)
        session_id = report_config.get('session_id')
        
        usage_stats = async_manager.run_sync(
            AsyncModelUsageRepository.get_usage_stats(session_id=session_id, days=days)
        )
        
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Analyzing usage patterns...', 'progress': 50}
        )
        
        # Analyze patterns (simulate analysis)
        time.sleep(1)
        
        # Generate insights
        insights = analyze_usage_patterns(usage_stats)
        
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Generating report...', 'progress': 80}
        )
        
        report = {
            'report_id': task_id,
            'period': f'{days} days',
            'generated_at': time.time(),
            'usage_stats': usage_stats,
            'insights': insights,
            'recommendations': generate_recommendations(usage_stats, insights)
        }
        
        # Log report generation
        async_manager.run_sync(
            AsyncSystemLogRepository.log_event(
                event_type='report_generated',
                event_source='celery',
                message=f'Usage report generated: {task_id}',
                additional_data={'report_config': report_config}
            )
        )
        
        return {
            'status': 'SUCCESS',
            'task_id': task_id,
            'report': report
        }
        
    except Exception as e:
        logger.error(f"Usage report generation failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'status': 'Failed'}
        )
        raise


@celery_app.task(bind=True, name='tasks.analysis_tasks.analyze_model_performance')
def analyze_model_performance(self, analysis_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze model performance metrics in background
    
    Args:
        analysis_config: Configuration for performance analysis
        
    Returns:
        Dict containing performance analysis results
    """
    task_id = self.request.id
    logger.info(f"Starting model performance analysis task {task_id}")
    
    try:
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Loading model data...', 'progress': 15}
        )
        
        # Load model usage data
        models = analysis_config.get('models', [])
        timeframe = analysis_config.get('timeframe', 7)  # days
        
        performance_data = {}
        
        for i, model in enumerate(models):
            progress = 15 + int((i / len(models)) * 60)
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': f'Analyzing model: {model}',
                    'progress': progress
                }
            )
            
            # Analyze model performance
            model_stats = analyze_single_model(model, timeframe)
            performance_data[model] = model_stats
            
            time.sleep(0.5)  # Simulate analysis time
        
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Generating insights...', 'progress': 85}
        )
        
        # Generate comparative insights
        insights = generate_model_insights(performance_data)
        
        return {
            'status': 'SUCCESS',
            'task_id': task_id,
            'analysis': {
                'timeframe': f'{timeframe} days',
                'models_analyzed': len(models),
                'performance_data': performance_data,
                'insights': insights,
                'top_performers': get_top_performers(performance_data)
            }
        }
        
    except Exception as e:
        logger.error(f"Model performance analysis failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'status': 'Failed'}
        )
        raise


def analyze_usage_patterns(usage_stats: List[Dict]) -> Dict[str, Any]:
    """Analyze usage patterns from statistics"""
    if not usage_stats:
        return {'pattern': 'No usage data available'}
    
    # Simple pattern analysis
    total_usage = len(usage_stats)
    unique_models = len(set(stat.get('model_id', '') for stat in usage_stats))
    
    return {
        'total_requests': total_usage,
        'unique_models_used': unique_models,
        'avg_requests_per_model': total_usage / unique_models if unique_models > 0 else 0,
        'pattern': 'active' if total_usage > 100 else 'moderate' if total_usage > 10 else 'low'
    }


def generate_recommendations(usage_stats: List[Dict], insights: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on usage patterns"""
    recommendations = []
    
    pattern = insights.get('pattern', 'unknown')
    
    if pattern == 'active':
        recommendations.append("Consider implementing caching to reduce API calls")
        recommendations.append("Monitor rate limits to avoid throttling")
    elif pattern == 'moderate':
        recommendations.append("Current usage is well balanced")
        recommendations.append("Consider A/B testing different models")
    else:
        recommendations.append("Explore additional use cases to maximize value")
        recommendations.append("Consider model fine-tuning for specific tasks")
    
    return recommendations


def analyze_single_model(model_id: str, timeframe: int) -> Dict[str, Any]:
    """Analyze performance of a single model"""
    # Placeholder analysis - integrate with actual model metrics
    return {
        'model_id': model_id,
        'timeframe_days': timeframe,
        'total_requests': 150,  # Placeholder
        'avg_response_time': 1.2,  # seconds
        'success_rate': 0.95,
        'error_rate': 0.05,
        'cost_per_request': 0.002,  # USD
        'performance_score': 8.5  # out of 10
    }


def generate_model_insights(performance_data: Dict[str, Dict]) -> Dict[str, Any]:
    """Generate insights from model performance data"""
    if not performance_data:
        return {'insight': 'No model data available'}
    
    # Find best performing model
    best_model = max(
        performance_data.keys(), 
        key=lambda k: performance_data[k].get('performance_score', 0)
    )
    
    # Calculate averages
    avg_response_time = sum(
        data.get('avg_response_time', 0) for data in performance_data.values()
    ) / len(performance_data)
    
    return {
        'best_performing_model': best_model,
        'avg_response_time_all_models': round(avg_response_time, 2),
        'total_models_analyzed': len(performance_data),
        'insight': f'{best_model} shows the best overall performance'
    }


def get_top_performers(performance_data: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Get top performing models"""
    sorted_models = sorted(
        performance_data.items(),
        key=lambda x: x[1].get('performance_score', 0),
        reverse=True
    )
    
    return [
        {
            'model_id': model_id,
            'performance_score': data.get('performance_score', 0),
            'success_rate': data.get('success_rate', 0)
        }
        for model_id, data in sorted_models[:3]  # Top 3
    ]