"""
Email API Routes
REST endpoints for email service with draft/review workflow
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any, List
import asyncio

from utils.logging_config import get_logger
from utils.auth import require_auth
from utils.rate_limiter import rate_limit
from utils.async_wrapper import async_manager
from schemas.email_schemas import (
    validate_email_draft,
    validate_email_send,
    validate_email_review,
    validate_bulk_email,
    validate_email_webhook,
    validate_email_query
)
from models.email_models import EmailDraft, EmailLog
from models.core import db

logger = get_logger(__name__)

email_api_bp = Blueprint('email_api', __name__, url_prefix='/api/email')

# Storage for drafts (should be in database in production)
email_drafts = {}


@email_api_bp.route('/send', methods=['POST'])
@require_auth
@rate_limit(requests_per_minute=10)
@async_manager.async_route
async def send_email():
    """
    Send a simple email immediately.
    
    Request body:
    {
        "to": "recipient@example.com",
        "subject": "Test Email",
        "body": "Email content",
        "html": "<p>Optional HTML content</p>",
        "cc": ["cc@example.com"],
        "tags": ["notification"]
    }
    """
    try:
        # Validate request data
        data = validate_email_send(request.get_json())
        
        # Get email service from DI container
        from core.service_registry import get_service
        email_service = get_service('email_service')
        
        if not email_service:
            return jsonify({
                'error': 'Email service not available'
            }), 503
        
        # Send email
        result = await email_service.send_email(
            to=data['to'],
            subject=data['subject'],
            body=data['body'],
            html=data.get('html'),
            from_email=data.get('from_email'),
            reply_to=data.get('reply_to'),
            cc=data.get('cc'),
            bcc=data.get('bcc'),
            tags=data.get('tags'),
            headers=data.get('headers')
        )
        
        # Log email
        try:
            email_log = EmailLog(
                recipient=data['to'],
                subject=data['subject'],
                status='sent' if result.get('success') else 'failed',
                provider=result.get('provider', 'unknown'),
                message_id=result.get('message_id'),
                sent_at=datetime.utcnow(),
                email_metadata={
                    'cc': data.get('cc'),
                    'tags': data.get('tags'),
                    'priority': data.get('priority', 'normal')
                }
            )
            db.session.add(email_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log email: {e}")
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@email_api_bp.route('/draft', methods=['POST'])
@require_auth
@rate_limit(requests_per_minute=20)
async def create_draft():
    """
    Create an email draft for review.
    
    Request body:
    {
        "to": [{"email": "recipient@example.com", "name": "John Doe"}],
        "subject": "Draft Email",
        "body": "Email content",
        "attachments": [
            {
                "filename": "report.pdf",
                "content": "base64_encoded_content",
                "content_type": "application/pdf"
            }
        ],
        "schedule_time": "2024-12-25T10:00:00Z"
    }
    """
    try:
        # Validate request data
        data = validate_email_draft(request.get_json())
        
        # Store draft
        draft_id = data['draft_id']
        email_drafts[draft_id] = data
        
        # Save to database
        try:
            draft = EmailDraft(
                draft_id=draft_id,
                recipients=data['to'],
                subject=data['subject'],
                body=data['body'],
                html=data.get('html'),
                attachments=data.get('attachments', []),
                status='draft',
                created_by=request.user.get('username', 'system'),
                created_at=datetime.utcnow(),
                email_metadata={
                    'cc': data.get('cc'),
                    'bcc': data.get('bcc'),
                    'tags': data.get('tags'),
                    'headers': data.get('headers'),
                    'schedule_time': data.get('schedule_time').isoformat() if data.get('schedule_time') else None
                }
            )
            db.session.add(draft)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to save draft to database: {e}")
        
        # Return draft details
        return jsonify({
            'draft_id': draft_id,
            'status': 'draft',
            'created_at': data['created_at'].isoformat(),
            'preview_url': f'/api/email/draft/{draft_id}/preview'
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Draft creation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@email_api_bp.route('/draft/<draft_id>', methods=['GET'])
@require_auth
async def get_draft(draft_id: str):
    """Get email draft details."""
    draft = email_drafts.get(draft_id)
    
    if not draft:
        # Try database
        try:
            db_draft = EmailDraft.query.filter_by(draft_id=draft_id).first()
            if db_draft:
                draft = {
                    'draft_id': db_draft.draft_id,
                    'recipients': db_draft.recipients,
                    'subject': db_draft.subject,
                    'body': db_draft.body,
                    'html': db_draft.html,
                    'status': db_draft.status,
                    'created_at': db_draft.created_at.isoformat(),
                    'metadata': db_draft.email_metadata
                }
            else:
                return jsonify({'error': 'Draft not found'}), 404
        except Exception as e:
            logger.error(f"Failed to retrieve draft from database: {e}")
            return jsonify({'error': 'Draft not found'}), 404
    
    return jsonify(draft), 200


@email_api_bp.route('/draft/<draft_id>/preview', methods=['GET'])
@require_auth
async def preview_draft(draft_id: str):
    """Preview email draft as HTML."""
    draft = email_drafts.get(draft_id)
    
    if not draft:
        return jsonify({'error': 'Draft not found'}), 404
    
    # Generate preview HTML
    preview_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
            .field {{ margin: 10px 0; }}
            .label {{ font-weight: bold; }}
            .content {{ border: 1px solid #ddd; padding: 20px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Email Preview</h2>
        </div>
        <div class="field">
            <span class="label">To:</span> {', '.join([r['formatted'] for r in draft['to']])}
        </div>
        <div class="field">
            <span class="label">Subject:</span> {draft['subject']}
        </div>
        <div class="content">
            {draft.get('html', f"<pre>{draft['body']}</pre>")}
        </div>
    </body>
    </html>
    """
    
    from flask import Response
    return Response(preview_html, mimetype='text/html')


@email_api_bp.route('/draft/<draft_id>/review', methods=['POST'])
@require_auth
@async_manager.async_route
async def review_draft(draft_id: str):
    """
    Review and approve/reject email draft.
    
    Request body:
    {
        "action": "approve|reject|revise",
        "comments": "Optional review comments",
        "revisions": {
            "subject": "Updated subject"
        },
        "reviewer": "reviewer_username"
    }
    """
    try:
        # Validate review data
        review_data = request.get_json()
        review_data['draft_id'] = draft_id
        validated = validate_email_review(review_data)
        
        draft = email_drafts.get(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        
        # Handle review action
        if validated['action'] == 'approve':
            # Send the email
            from core.service_registry import get_service
            email_service = get_service('email_service')
            
            if not email_service:
                return jsonify({'error': 'Email service not available'}), 503
            
            # Convert draft format to send format
            # Send to first recipient (enhance for multiple later)
            primary_recipient = draft['to'][0]['email']
            
            result = await email_service.send_email(
                to=primary_recipient,
                subject=draft['subject'],
                body=draft['body'],
                html=draft.get('html'),
                cc=[r['email'] for r in draft.get('cc', [])],
                bcc=[r['email'] for r in draft.get('bcc', [])],
                tags=draft.get('tags'),
                headers=draft.get('headers'),
                attachments=draft.get('attachments')
            )
            
            # Update draft status
            draft['status'] = 'sent' if result.get('success') else 'failed'
            draft['sent_at'] = datetime.utcnow().isoformat()
            draft['review'] = validated
            
            # Update database
            try:
                db_draft = EmailDraft.query.filter_by(draft_id=draft_id).first()
                if db_draft:
                    db_draft.status = draft['status']
                    db_draft.reviewed_by = validated['reviewer']
                    db_draft.reviewed_at = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                logger.error(f"Failed to update draft in database: {e}")
            
            return jsonify({
                'status': draft['status'],
                'result': result,
                'reviewed_by': validated['reviewer']
            }), 200
            
        elif validated['action'] == 'reject':
            # Mark as rejected
            draft['status'] = 'rejected'
            draft['review'] = validated
            
            return jsonify({
                'status': 'rejected',
                'comments': validated.get('comments')
            }), 200
            
        elif validated['action'] == 'revise':
            # Apply revisions
            revisions = validated.get('revisions', {})
            for field, value in revisions.items():
                if field in draft:
                    draft[field] = value
            
            draft['status'] = 'revised'
            draft['revisions'] = revisions
            draft['revised_at'] = datetime.utcnow().isoformat()
            
            return jsonify({
                'status': 'revised',
                'draft_id': draft_id,
                'revisions': revisions
            }), 200
            
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Review error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@email_api_bp.route('/bulk', methods=['POST'])
@require_auth
@rate_limit(requests_per_minute=5)
@async_manager.async_route
async def send_bulk_email():
    """
    Send bulk emails with personalization.
    
    Request body:
    {
        "recipients": [
            {"email": "user1@example.com", "variables": {"name": "John"}},
            {"email": "user2@example.com", "variables": {"name": "Jane"}}
        ],
        "template_subject": "Hello {name}!",
        "template_body": "Dear {name}, ...",
        "batch_size": 50
    }
    """
    try:
        # Validate request
        data = validate_bulk_email(request.get_json())
        
        # Get email service
        from core.service_registry import get_service
        email_service = get_service('email_service')
        
        if not email_service:
            return jsonify({'error': 'Email service not available'}), 503
        
        # Send bulk emails
        result = await email_service.send_bulk_emails(
            recipients=data['recipients'],
            template_subject=data['template_subject'],
            template_body=data['template_body'],
            batch_size=data.get('batch_size', 50)
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Bulk email error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@email_api_bp.route('/webhook/mailgun', methods=['POST'])
@rate_limit(requests_per_minute=100)
async def mailgun_webhook():
    """Handle Mailgun webhook events."""
    try:
        # Get webhook data
        data = request.get_json() or {}
        
        # Validate webhook signature
        from core.service_registry import get_service
        email_service = get_service('email_service')
        
        if email_service:
            signature = data.get('signature', {})
            is_valid = email_service.verify_webhook_signature(
                signature=signature.get('signature', ''),
                timestamp=signature.get('timestamp', ''),
                token=signature.get('token', '')
            )
            
            if not is_valid:
                logger.warning("Invalid webhook signature")
                return jsonify({'error': 'Invalid signature'}), 403
        
        # Process webhook event
        event_data = data.get('event-data', {})
        event_type = event_data.get('event')
        
        logger.info(f"Received Mailgun webhook: {event_type}")
        
        # Update email log based on event
        if event_type in ['delivered', 'failed', 'opened', 'clicked']:
            message_id = event_data.get('message', {}).get('headers', {}).get('message-id')
            if message_id:
                try:
                    email_log = EmailLog.query.filter_by(message_id=message_id).first()
                    if email_log:
                        if event_type == 'delivered':
                            email_log.status = 'delivered'
                            email_log.delivered_at = datetime.utcnow()
                        elif event_type == 'failed':
                            email_log.status = 'failed'
                            email_log.error = event_data.get('delivery-status', {}).get('message')
                        elif event_type == 'opened':
                            email_log.opened_at = datetime.utcnow()
                            email_log.open_count = (email_log.open_count or 0) + 1
                        elif event_type == 'clicked':
                            email_log.clicked_at = datetime.utcnow()
                            email_log.click_count = (email_log.click_count or 0) + 1
                        
                        db.session.commit()
                except Exception as e:
                    logger.error(f"Failed to update email log: {e}")
        
        return jsonify({'status': 'processed'}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@email_api_bp.route('/history', methods=['GET'])
@require_auth
async def email_history():
    """
    Get email sending history.
    
    Query parameters:
    - status: sent|failed|pending|draft|all
    - date_from: ISO date
    - date_to: ISO date
    - recipient: email address
    - limit: max results (default 20)
    - offset: pagination offset
    """
    try:
        # Validate query parameters
        query_params = validate_email_query(request.args.to_dict())
        
        # Build query
        query = EmailLog.query
        
        if query_params.get('status') and query_params['status'] != 'all':
            query = query.filter_by(status=query_params['status'])
        
        if query_params.get('recipient'):
            query = query.filter_by(recipient=query_params['recipient'])
        
        if query_params.get('date_from'):
            query = query.filter(EmailLog.sent_at >= query_params['date_from'])
        
        if query_params.get('date_to'):
            query = query.filter(EmailLog.sent_at <= query_params['date_to'])
        
        if query_params.get('subject_contains'):
            query = query.filter(EmailLog.subject.contains(query_params['subject_contains']))
        
        # Pagination
        total = query.count()
        emails = query.order_by(EmailLog.sent_at.desc()).limit(
            query_params['limit']
        ).offset(
            query_params['offset']
        ).all()
        
        return jsonify({
            'total': total,
            'limit': query_params['limit'],
            'offset': query_params['offset'],
            'emails': [
                {
                    'id': email.id,
                    'recipient': email.recipient,
                    'subject': email.subject,
                    'status': email.status,
                    'provider': email.provider,
                    'sent_at': email.sent_at.isoformat() if email.sent_at else None,
                    'delivered_at': email.delivered_at.isoformat() if email.delivered_at else None,
                    'opened_at': email.opened_at.isoformat() if email.opened_at else None,
                    'metadata': email.email_metadata
                }
                for email in emails
            ]
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"History query error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@email_api_bp.route('/stats', methods=['GET'])
@require_auth
@async_manager.async_route
async def email_stats():
    """Get email sending statistics."""
    try:
        from core.service_registry import get_service
        email_service = get_service('email_service')
        
        if not email_service:
            return jsonify({'error': 'Email service not available'}), 503
        
        stats = await email_service.get_email_stats()
        
        # Add database stats
        try:
            from sqlalchemy import func
            today_count = db.session.query(func.count(EmailLog.id)).filter(
                func.date(EmailLog.sent_at) == func.date(func.now())
            ).scalar()
            
            stats['emails_sent_today'] = today_count
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Internal server error'}), 500