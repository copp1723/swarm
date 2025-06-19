"""
Audit and Explainability API Routes
"""
# Stdlib
from datetime import datetime, timedelta
import csv
import io
from typing import Dict, Any

# Third-party
from flask import Blueprint, jsonify, request, make_response

# Local

from core.service_registry import get_service
from utils.logging_config import get_logger
from utils.auth import require_auth

logger = get_logger(__name__)

audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit')


@audit_bp.route('/task/<task_id>', methods=['GET'])
@require_auth
def get_task_audit_trail(task_id: str):
    """Get complete audit trail for a task"""
    try:
        auditor = get_service('agent_auditor')
        if not auditor:
            return jsonify({"error": "Audit system not initialized"}), 503
        
        # Get audit records
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        records = loop.run_until_complete(
            auditor.get_audit_trail(task_id)
        )
        
        return jsonify({
            "task_id": task_id,
            "audit_records": [record.to_dict() for record in records],
            "record_count": len(records)
        })
        
    except Exception as e:
        logger.error(f"Error getting audit trail for task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500


@audit_bp.route('/agent/<agent_id>', methods=['GET'])
@require_auth
def get_agent_audit_history(agent_id: str):
    """Get recent audit history for a specific agent"""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        auditor = get_service('agent_auditor')
        if not auditor:
            return jsonify({"error": "Audit system not initialized"}), 503
        
        # Get audit records
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        records = loop.run_until_complete(
            auditor.get_agent_actions(agent_id, limit)
        )
        
        return jsonify({
            "agent_id": agent_id,
            "audit_records": [record.to_dict() for record in records],
            "record_count": len(records),
            "limit": limit
        })
        
    except Exception as e:
        logger.error(f"Error getting audit history for agent {agent_id}: {e}")
        return jsonify({"error": str(e)}), 500


@audit_bp.route('/task/<task_id>/explain', methods=['GET'])
@require_auth
def explain_task(task_id: str):
    """Generate explainability report for a task"""
    try:
        explainability_engine = get_service('explainability_engine')
        if not explainability_engine:
            return jsonify({"error": "Explainability engine not initialized"}), 503
        
        # Generate explanation
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        explanation = loop.run_until_complete(
            explainability_engine.generate_task_explanation(task_id)
        )
        
        return jsonify(explanation)
        
    except Exception as e:
        logger.error(f"Error generating explanation for task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500


@audit_bp.route('/task/<task_id>/export', methods=['GET'])
@require_auth
def export_task_audit_trail(task_id: str):
    """
    Export audit trail for a task.
    Query param `format` supports:
      • csv (default)
      • pdf  – returns 501 placeholder for now
    """
    export_format = request.args.get("format", "csv").lower()

    try:
        auditor = get_service('agent_auditor')
        if not auditor:
            return jsonify({"error": "Audit system not initialized"}), 503

        # Fetch records (sync wrapper around async call)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        records = loop.run_until_complete(auditor.get_audit_trail(task_id))
        records_dicts = [r.to_dict() for r in records]

        if export_format == "csv":
            if not records_dicts:
                return jsonify({"error": "No audit records found"}), 404

            # Dynamically create CSV with headers from dict keys
            csv_buffer = io.StringIO()
            writer = csv.DictWriter(csv_buffer, fieldnames=records_dicts[0].keys())
            writer.writeheader()
            writer.writerows(records_dicts)

            response = make_response(csv_buffer.getvalue())
            response.headers["Content-Disposition"] = f"attachment; filename=audit_task_{task_id}.csv"
            response.headers["Content-Type"] = "text/csv"
            return response

        elif export_format == "pdf":
            # Placeholder: PDF export not yet implemented
            return jsonify({
                "error": "PDF export is not implemented yet",
                "supported_formats": ["csv"]
            }), 501

        else:
            return jsonify({
                "error": f"Unsupported format '{export_format}'",
                "supported_formats": ["csv", "pdf"]
            }), 400

    except Exception as e:
        logger.error(f"Error exporting audit trail for task {task_id}: {e}")
        return jsonify({"error": str(e)}), 500


@audit_bp.route('/statistics', methods=['GET'])
@require_auth
def get_audit_statistics():
    """Get audit statistics for a date range"""
    try:
        # Parse date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date)
        else:
            # Default to last 7 days
            start_date = datetime.now() - timedelta(days=7)
            
        if end_date:
            end_date = datetime.fromisoformat(end_date)
        else:
            end_date = datetime.now()
        
        audit_storage = get_service('audit_storage')
        if not audit_storage:
            return jsonify({"error": "Audit storage not initialized"}), 503
        
        # Get statistics
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        stats = loop.run_until_complete(
            audit_storage.get_statistics(start_date, end_date)
        )
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting audit statistics: {e}")
        return jsonify({"error": str(e)}), 500


@audit_bp.route('/level', methods=['POST'])
@require_auth
def set_audit_level():
    """Set the global audit level"""
    try:
        data = request.get_json()
        level = data.get('level', 'standard').upper()
        
        auditor = get_service('agent_auditor')
        if not auditor:
            return jsonify({"error": "Audit system not initialized"}), 503
        
        # Set audit level
        from services.auditing import AuditLevel
        try:
            audit_level = AuditLevel[level]
            auditor.set_audit_level(audit_level)
            
            return jsonify({
                "message": f"Audit level set to {audit_level.value}",
                "level": audit_level.value
            })
        except KeyError:
            return jsonify({
                "error": f"Invalid audit level: {level}",
                "valid_levels": [level.name for level in AuditLevel]
            }), 400
            
    except Exception as e:
        logger.error(f"Error setting audit level: {e}")
        return jsonify({"error": str(e)}), 500