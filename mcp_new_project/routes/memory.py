"""
Memory Management Routes
"""
from flask import Blueprint, jsonify, request
from utils.auth import require_auth
from utils.memory_optimizer import get_memory_monitor, get_memory_optimizer
from services.memory_aware_chat_service import get_memory_aware_chat_service
from services.multi_agent_service import get_multi_agent_service
from services.chat_history_storage import get_chat_history_storage
import gc

memory_bp = Blueprint('memory', __name__, url_prefix='/api/memory')


@memory_bp.route('/stats', methods=['GET'])
@require_auth
def get_memory_stats():
    """Get comprehensive memory statistics"""
    monitor = get_memory_monitor()
    chat_service = get_memory_aware_chat_service()
    agent_service = get_multi_agent_service()
    chat_storage = get_chat_history_storage()
    
    # Get all memory stats
    system_stats = monitor.get_memory_stats()
    chat_stats = chat_service.get_memory_stats()
    agent_stats = agent_service.get_memory_stats()
    storage_stats = chat_storage.get_memory_usage()
    
    return jsonify({
        "success": True,
        "system": {
            "memory_used_mb": round(system_stats["memory_used_mb"], 1),
            "memory_percent": round(system_stats["memory_percent"], 1),
            "system_memory_percent": round(system_stats["system_memory_percent"], 1),
            "system_available_mb": round(system_stats["system_available_mb"], 1)
        },
        "chat_service": chat_stats,
        "agent_service": agent_stats,
        "chat_storage": storage_stats,
        "gc_stats": gc.get_stats()
    })


@memory_bp.route('/optimize', methods=['POST'])
@require_auth
def optimize_memory():
    """Manually trigger memory optimization"""
    data = request.get_json() or {}
    level = data.get('level', 'normal')
    
    if level not in ['normal', 'aggressive', 'emergency']:
        return jsonify({
            "success": False,
            "error": "Invalid optimization level. Must be: normal, aggressive, or emergency"
        }), 400
    
    optimizer = get_memory_optimizer()
    
    # Get before stats
    before_stats = get_memory_monitor().get_memory_stats()
    
    # Run optimization
    results = optimizer.optimize_memory(level)
    
    # Get after stats
    after_stats = get_memory_monitor().get_memory_stats()
    
    return jsonify({
        "success": True,
        "optimization_level": level,
        "before": {
            "memory_used_mb": round(before_stats["memory_used_mb"], 1)
        },
        "after": {
            "memory_used_mb": round(after_stats["memory_used_mb"], 1)
        },
        "freed_mb": round(before_stats["memory_used_mb"] - after_stats["memory_used_mb"], 1),
        "results": results
    })


@memory_bp.route('/gc', methods=['POST'])
@require_auth
def force_garbage_collection():
    """Force garbage collection"""
    # Get before stats
    before_stats = get_memory_monitor().get_memory_stats()
    
    # Run GC
    collected = gc.collect()
    
    # Get after stats
    after_stats = get_memory_monitor().get_memory_stats()
    
    return jsonify({
        "success": True,
        "objects_collected": collected,
        "before_mb": round(before_stats["memory_used_mb"], 1),
        "after_mb": round(after_stats["memory_used_mb"], 1),
        "freed_mb": round(before_stats["memory_used_mb"] - after_stats["memory_used_mb"], 1)
    })


@memory_bp.route('/chat/cleanup', methods=['POST'])
@require_auth
def cleanup_chat_history():
    """Clean up old chat history"""
    data = request.get_json() or {}
    days = data.get('days', 30)
    
    chat_storage = get_chat_history_storage()
    chat_storage.cleanup_old_messages(days)
    
    # Also trigger chat service cleanup
    chat_service = get_memory_aware_chat_service()
    chat_service._cleanup_old_chats()
    
    return jsonify({
        "success": True,
        "message": f"Cleaned up chat history older than {days} days"
    })


@memory_bp.route('/monitoring/status', methods=['GET'])
@require_auth
def get_monitoring_status():
    """Get memory monitoring status"""
    monitor = get_memory_monitor()
    
    return jsonify({
        "success": True,
        "monitoring_active": monitor._monitoring,
        "check_interval_seconds": monitor.check_interval,
        "thresholds": {
            "warning_mb": monitor.warning_threshold / (1024 * 1024),
            "critical_mb": monitor.critical_threshold / (1024 * 1024)
        },
        "current_state": monitor._last_state
    })


@memory_bp.route('/monitoring/toggle', methods=['POST'])
@require_auth
def toggle_monitoring():
    """Start or stop memory monitoring"""
    data = request.get_json() or {}
    enable = data.get('enable', True)
    
    monitor = get_memory_monitor()
    
    if enable:
        monitor.start_monitoring()
        message = "Memory monitoring started"
    else:
        monitor.stop_monitoring()
        message = "Memory monitoring stopped"
    
    return jsonify({
        "success": True,
        "message": message,
        "monitoring_active": monitor._monitoring
    })