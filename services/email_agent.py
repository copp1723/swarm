# services/email_agent.py
# Contains all the logic and routes specific to the Email Agent.
# Enhanced with replay attack protection and validation schemas.

from flask import Blueprint, request, jsonify
import os
import hmac
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
import json
from marshmallow import ValidationError

from services.email_parser import EmailParser
from models.agent_task import AgentTask
from schemas.webhook_schemas import (
    validate_mailgun_webhook,
    MailgunSignatureSchema,
    EmailWebhookBaseSchema
)
from schemas.task_schemas import TaskCreateSchema
from utils.logging_config import get_logger, log_webhook_event, log_email_task, LogContext
from utils.performance_monitor import track_webhook_processing, timed_operation, track_operation

# Configure logging
logger = get_logger(__name__)

# --- Constants ---
# Maximum age of a webhook timestamp in seconds to protect against replay attacks.
MAX_TIMESTAMP_AGE_SECONDS = 120

# --- Flask Blueprint Setup ---
email_bp = Blueprint('email_agent', __name__)

# Initialize email parser
email_parser = EmailParser()

# --- Background Processing Integration ---

def process_email_event(email_data: dict):
    """
    Process email event - now integrated with Celery.
    This will be called by the background worker.
    """
    from tasks.email_tasks import process_email_event as celery_process_email
    
    # Queue the task for background processing
    result = celery_process_email.delay(email_data)
    logger.info("Email event queued for processing", task_id=result.id)
    return result.id

def enqueue_for_processing(email_data: dict):
    """
    Enqueue email data for asynchronous processing via Celery.
    """
    logger.info("Event queued for background processing")
    try:
        task_id = process_email_event(email_data)
        return task_id
    except Exception as e:
        logger.error("Failed to process email event", error=str(e))
        raise

# --- Security Verification ---

def verify_mailgun_signature(token: str, timestamp: str, signature: str) -> bool:
    """
    Verifies that the incoming webhook request is genuinely from Mailgun
    using the HMAC-SHA256 signature.
    
    Args:
        token: The token from Mailgun's signature data
        timestamp: The timestamp from Mailgun's signature data  
        signature: The signature to verify
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    signing_key = os.getenv("MAILGUN_SIGNING_KEY")
    if not signing_key:
        logger.error("MAILGUN_SIGNING_KEY not configured")
        return False

    message = f"{timestamp}{token}".encode('utf-8')
    key = signing_key.encode('utf-8')
    
    expected_signature = hmac.new(key=key, msg=message, digestmod=hashlib.sha256).hexdigest()
    
    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_signature, signature)
    
    if not is_valid:
        logger.warning("Invalid signature detected", expected=expected_signature[:8], received=signature[:8])
    
    return is_valid

def verify_timestamp(timestamp_str: str) -> Tuple[bool, Optional[str]]:
    """
    Verifies the webhook timestamp to protect against replay attacks.
    
    Args:
        timestamp_str: The timestamp string to verify
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        timestamp = int(timestamp_str)
        current_time = datetime.now(timezone.utc).timestamp()
        age = abs(current_time - timestamp)
        
        if age > MAX_TIMESTAMP_AGE_SECONDS:
            error_msg = f"Stale timestamp detected. Age: {age:.1f}s > {MAX_TIMESTAMP_AGE_SECONDS}s."
            logger.warning("Stale webhook timestamp", age_seconds=age, max_age=MAX_TIMESTAMP_AGE_SECONDS)
            return False, error_msg
            
        logger.debug("Timestamp verified", age_seconds=age)
        return True, None
        
    except (ValueError, TypeError) as e:
        error_msg = f"Invalid timestamp format received: {timestamp_str}"
        logger.error("Invalid timestamp format", timestamp=timestamp_str, error=str(e))
        return False, error_msg

# --- Health Check Endpoint ---

@email_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for the Email Agent."""
    return jsonify({
        "service": "email_agent",
        "status": "healthy",
        "version": "1.1.0",
        "features": {
            "validation": "enabled",
            "celery_integration": "enabled",
            "supermemory": "enabled"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

# --- Webhook Endpoint ---

@email_bp.route("/webhooks/mailgun", methods=["POST"])
@timed_operation("webhook.mailgun")
def mailgun_webhook():
    """
    Endpoint to receive webhook events from Mailgun with validation.
    """
    start_time = time.time()
    # Log Convoy headers if present
    convoy_headers = {k: v for k, v in request.headers.items() if k.startswith('X-Convoy')}
    if convoy_headers:
        logger.info("Webhook received via Convoy gateway", headers=convoy_headers)
    
    # Check content type
    if not request.is_json:
        logger.warning("Non-JSON webhook request received")
        return jsonify(
            status="error",
            message="Request must be JSON"
        ), 415

    data = request.get_json()
    
    # Validate signature fields first
    try:
        sig_schema = MailgunSignatureSchema()
        sig_data = sig_schema.load({"signature": data.get("signature", {})})
        signature_data = sig_data["signature"]
    except ValidationError as e:
        logger.warning("Invalid webhook signature structure", errors=e.messages)
        return jsonify(
            status="error",
            message="Invalid signature structure",
            errors=e.messages
        ), 400
    
    token = signature_data.get("token")
    timestamp = signature_data.get("timestamp")
    signature = signature_data.get("signature")
    
    # 1. Verify timestamp to prevent replay attacks
    is_valid_timestamp, timestamp_error = verify_timestamp(timestamp)
    if not is_valid_timestamp:
        return jsonify(
            status="error",
            message=timestamp_error
        ), 403

    # 2. Verify signature to ensure authenticity
    if not verify_mailgun_signature(token, timestamp, signature):
        logger.warning("Invalid webhook signature, request rejected")
        return jsonify(
            status="error",
            message="Invalid signature"
        ), 403

    # 3. Validate webhook data structure
    try:
        # Handle both direct fields and nested event-data structure
        event_data = data.get("event-data", data)
        
        # Validate with appropriate schema based on event type
        validated_data = validate_mailgun_webhook(event_data)
        
    except ValidationError as e:
        logger.error("Webhook validation failed", errors=e.messages)
        return jsonify({
            "status": "error",
            "message": "Invalid webhook data",
            "errors": e.messages
        }), 400

    # 4. Extract and structure the email data
    message = event_data.get("message", {})
    headers = message.get("headers", {})
    
    # Build normalized email data
    email_data = {
        "from": headers.get("from") or validated_data.get("sender"),
        "to": message.get("recipients") or validated_data.get("recipient"),
        "subject": headers.get("subject") or event_data.get("subject"),
        "body_plain": message.get("body-plain") or event_data.get("body-plain"),
        "stripped_text": event_data.get("stripped-text"),
        "timestamp": validated_data.get("timestamp", datetime.now(timezone.utc).timestamp()),
        "message_id": headers.get("message-id") or event_data.get("Message-Id"),
        "event_type": validated_data.get("event", "received"),
        "validated_data": validated_data  # Include all validated fields
    }
    
    with LogContext(message_id=email_data['message_id'], sender=email_data['from']):
        logger.info("Valid Mailgun webhook received")
        logger.debug("Email data extracted", to=email_data['to'], subject=email_data['subject'])

    # 5. Enqueue for asynchronous processing
    try:
        task_id = enqueue_for_processing(email_data)
    except Exception as e:
        logger.error("Failed to enqueue email for processing", error=str(e))
        return jsonify(
            status="error",
            message="Failed to process webhook"
        ), 500

    # 6. Track performance and return success response
    duration = time.time() - start_time
    track_webhook_processing("mailgun", duration, 200)
    log_webhook_event("mailgun", email_data['from'], "success", 
                     message_id=email_data['message_id'], task_id=task_id)
    
    return jsonify(
        status="queued",
        message="Webhook received and queued for processing.",
        message_id=email_data['message_id'],
        task_id=task_id
    ), 200

# --- Agent Task Handler ---

@email_bp.route("/tasks", methods=["POST"])
async def handle_email_task():
    """
    Handle email-related tasks with validation.
    """
    if not request.is_json:
        return jsonify(
            status="error",
            message="Request must be JSON"
        ), 415
        
    task_data = request.get_json()
    action = task_data.get("action")
    parameters = task_data.get("parameters", {})
    
    logger.info("Received email task", action=action)
    
    # Supported actions
    supported_actions = [
        "parse_email",      # Parse email into AgentTask
        "compose_draft",    # Compose email draft
        "search_emails",    # Search email history
        "analyze_email",    # Analyze email content
        "ingest_email",     # Ingest email to memory
        "dispatch_task"     # Dispatch parsed task to agents
    ]
    
    if action not in supported_actions:
        return jsonify(
            status="error",
            message=f"Unsupported action: {action}",
            supported_actions=supported_actions
        ), 400
    
    try:
        # Handle different actions
        if action == "parse_email":
            # Parse email into structured task
            email_data = parameters.get("email_data", {})
            if not email_data:
                return jsonify(
                    status="error",
                    message="Email data is required for parsing"
                ), 400
            
            # Parse the email
            agent_task = email_parser.parse_email(email_data)
            
            # Validate the parsed task
            task_schema = TaskCreateSchema()
            try:
                validated_task = task_schema.load(agent_task.to_dict())
            except ValidationError as e:
                logger.warning("Parsed task validation failed", errors=e.messages)
                # Continue anyway, but log the validation issues
                validated_task = agent_task.to_dict()
            
            log_email_task(agent_task.task_id, "parsed", title=agent_task.title)
            
            return jsonify({
                "status": "success",
                "action": action,
                "task": validated_task,
                "message": f"Email parsed into task: {agent_task.title}"
            }), 200
            
        elif action == "dispatch_task":
            # Dispatch a parsed task to agents
            task_dict = parameters.get("task")
            if not task_dict:
                return jsonify(
                    status="error",
                    message="Task data is required for dispatch"
                ), 400
            
            # Validate task data
            task_schema = TaskCreateSchema()
            try:
                validated_task = task_schema.load(task_dict)
            except ValidationError as e:
                return jsonify({
                    "status": "error",
                    "message": "Invalid task data",
                    "errors": e.messages
                }), 400
            
            # Get multi-agent service from DI container
            from services.service_container import get_service_container
            container = get_service_container()
            
            try:
                multi_agent_service = container.get('multi_agent_service')
                
                # Convert to AgentTask if needed
                if not isinstance(validated_task, AgentTask):
                    # Create AgentTask from validated data
                    from models.agent_task import AgentTask, TaskType, TaskPriority
                    agent_task = AgentTask(
                        title=validated_task['title'],
                        description=validated_task['description'],
                        task_type=TaskType[validated_task.get('task_type', 'GENERAL')],
                        priority=TaskPriority[validated_task.get('priority', 'MEDIUM')]
                    )
                else:
                    agent_task = validated_task
                
                # Execute the task
                result = multi_agent_service.execute_task(agent_task)
                
                return jsonify({
                    "status": "dispatched",
                    "action": action,
                    "task_id": agent_task.task_id,
                    "assigned_to": agent_task.agent_assignment.primary_agent if agent_task.agent_assignment else "auto",
                    "result": result
                }), 202
                
            except KeyError:
                logger.warning("[TASK] Multi-agent service not available, simulating dispatch")
                # Fallback if service not available
                task_id = validated_task.get("id", "unknown")
                primary_agent = validated_task.get("assigned_agent", "unknown")
                
                return jsonify({
                    "status": "dispatched",
                    "action": action,
                    "task_id": task_id,
                    "assigned_to": primary_agent,
                    "message": f"Task dispatched to {primary_agent} (simulated)"
                }), 202
            
        elif action == "compose_draft":
            # Compose an email draft using email service
            to = parameters.get("to", [])
            subject = parameters.get("subject", "")
            context = parameters.get("context", "")
            
            # Get email service
            from services.service_container import get_service_container
            container = get_service_container()
            
            try:
                email_service = container.get('email_service')
                
                # Generate email body using OpenRouter
                body = await self._generate_email_body_with_llm(
                    to=to,
                    subject=subject,
                    context=context
                )
                
                # Create draft (not sent)
                draft = {
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "draft"
                }
                
            except KeyError:
                # Fallback if service not available
                draft = {
                    "to": to,
                    "subject": subject,
                    "body": f"Draft based on: {context}",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            
            return jsonify({
                "status": "success",
                "action": action,
                "draft": draft
            }), 200
            
        elif action == "search_emails":
            # Search email history using Celery task
            query = parameters.get("query", "")
            filters = parameters.get("filters", {})
            
            from tasks.email_tasks import search_email_tasks
            
            # Execute search synchronously (Celery task returns result)
            results = search_email_tasks(query, filters)
            
            return jsonify({
                "status": "success",
                "action": action,
                "results": {
                    "query": query,
                    "filters": filters,
                    "count": len(results),
                    "emails": results
                }
            }), 200
            
        elif action == "analyze_email":
            # Analyze email content
            email_data = parameters.get("email_data", {})
            analysis_type = parameters.get("analysis_type", "general")
            
            # Perform analysis using parser
            sentiment_result = await _analyze_email_sentiment(email_data)
            
            analysis = {
                "sentiment": sentiment_result["sentiment"],
                "sentiment_score": sentiment_result["score"],
                "urgency": sentiment_result["urgency"],
                "categories": sentiment_result["categories"],
                "key_points": sentiment_result["key_points"],
                "suggested_actions": sentiment_result["suggested_actions"]
            }
            
            # Use email parser to extract task info
            if email_data:
                try:
                    agent_task = email_parser.parse_email(email_data)
                    analysis.update({
                        "task_type": agent_task.task_type.value,
                        "priority": agent_task.priority.value,
                        "suggested_agent": agent_task.agent_assignment.primary_agent if agent_task.agent_assignment else None,
                        "deadline": agent_task.requirements.deadline.isoformat() if agent_task.requirements.deadline else None
                    })
                except Exception as e:
                    logger.warning(f"[TASK] Email analysis failed: {e}")
            
            return jsonify({
                "status": "success",
                "action": action,
                "analysis": analysis
            }), 200
            
        elif action == "ingest_email":
            # Ingest email to Supermemory using Celery task
            email_data = parameters.get("email_data", {})
            
            from tasks.email_tasks import store_email_in_memory
            
            # Parse the email first to get task data
            agent_task = email_parser.parse_email(email_data)
            
            # Queue the storage task
            task_result = store_email_in_memory.apply_async(
                args=[email_data, agent_task.to_dict()]
            )
            
            return jsonify({
                "status": "success",
                "action": action,
                "message": "Email ingestion queued",
                "task_id": task_result.id,
                "email_task_id": agent_task.task_id
            }), 202
            
        else:
            # Fallback for unimplemented actions
            return jsonify({
                "status": "accepted",
                "action": action,
                "message": f"Email task '{action}' accepted for processing",
                "task_id": f"email_task_{datetime.now().timestamp()}"
            }), 202
            
    except Exception as e:
        logger.error(f"[TASK] Error handling email task: {str(e)}")
        return jsonify({
            "status": "error",
            "action": action,
            "message": f"Failed to process task: {str(e)}"
        }), 500

# --- Utility Functions ---

async def _generate_email_body_with_llm(to: list, subject: str, context: str) -> str:
    """
    Generate email body using OpenRouter LLM API
    
    Args:
        to: List of recipient email addresses
        subject: Email subject line
        context: Context/instructions for email generation
        
    Returns:
        Generated email body text
    """
    import httpx
    
    # Get OpenRouter API configuration
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OpenRouter API key not configured, using fallback template")
        return f"""Dear {', '.join(to)},

{context}

This email was drafted based on your request. Please review and edit as needed before sending.

Best regards,
[Your name]"""
    
    try:
        # Prepare the prompt
        prompt = f"""You are an AI assistant helping to draft professional emails. 
Generate a complete email body based on the following information:

Recipients: {', '.join(to)}
Subject: {subject}
Context/Instructions: {context}

Generate a professional, clear, and concise email body. Include appropriate greeting and closing.
Do not include the subject line in your response, only the email body.
"""
        
        # Make request to OpenRouter
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": os.getenv("APP_URL", "http://localhost:5000"),
                    "X-Title": "MCP Email Agent"
                },
                json={
                    "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo"),
                    "messages": [
                        {"role": "system", "content": "You are a professional email writing assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_body = result['choices'][0]['message']['content']
                logger.info("Successfully generated email body using OpenRouter")
                return generated_body
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                raise Exception(f"OpenRouter API error: {response.status_code}")
                
    except httpx.TimeoutException:
        logger.error("OpenRouter API timeout")
        return _get_fallback_email_body(to, subject, context)
    except Exception as e:
        logger.error(f"Error generating email with LLM: {str(e)}")
        return _get_fallback_email_body(to, subject, context)


def _get_fallback_email_body(to: list, subject: str, context: str) -> str:
    """Fallback email template when LLM generation fails"""
    return f"""Dear {', '.join(to)},

Regarding: {subject}

{context}

This is an automated draft. Please review and personalize before sending.

Best regards,
[Your signature]"""


async def _analyze_email_sentiment(email_data: dict) -> dict:
    """
    Analyze email sentiment and extract key information
    
    Args:
        email_data: Dictionary containing email content
        
    Returns:
        Analysis results including sentiment, urgency, categories, etc.
    """
    # Extract email content
    subject = email_data.get('subject', '')
    body = email_data.get('body_plain', '') or email_data.get('stripped_text', '')
    from_email = email_data.get('from', '')
    
    full_text = f"{subject} {body}".lower()
    
    # Sentiment analysis based on keywords
    positive_words = ['thank', 'thanks', 'appreciate', 'great', 'excellent', 'good', 'happy', 'pleased', 'wonderful', 'perfect', 'love']
    negative_words = ['urgent', 'asap', 'immediately', 'critical', 'problem', 'issue', 'error', 'bug', 'broken', 'fail', 'wrong', 'bad', 'terrible', 'angry', 'frustrated', 'disappointed']
    neutral_words = ['update', 'information', 'regarding', 'about', 'request', 'question']
    
    # Count sentiment indicators
    positive_count = sum(1 for word in positive_words if word in full_text)
    negative_count = sum(1 for word in negative_words if word in full_text)
    
    # Determine sentiment
    if negative_count > positive_count:
        sentiment = 'negative'
        score = -min(negative_count / 10, 1.0)  # Normalize to -1.0 to 0
    elif positive_count > negative_count:
        sentiment = 'positive'
        score = min(positive_count / 10, 1.0)  # Normalize to 0 to 1.0
    else:
        sentiment = 'neutral'
        score = 0.0
    
    # Urgency detection
    urgent_indicators = ['urgent', 'asap', 'immediately', 'critical', 'emergency', 'now', 'today', 'deadline', 'overdue']
    urgency_count = sum(1 for word in urgent_indicators if word in full_text)
    
    if urgency_count >= 3:
        urgency = 'high'
    elif urgency_count >= 1:
        urgency = 'medium'
    else:
        urgency = 'low'
    
    # Category detection
    categories = []
    category_keywords = {
        'support': ['help', 'support', 'assist', 'problem', 'issue'],
        'feedback': ['feedback', 'suggestion', 'improve', 'opinion'],
        'complaint': ['complaint', 'complain', 'dissatisfied', 'unhappy', 'disappointed'],
        'inquiry': ['question', 'ask', 'wondering', 'curious', 'information'],
        'technical': ['bug', 'error', 'technical', 'system', 'software', 'hardware'],
        'billing': ['payment', 'invoice', 'bill', 'charge', 'refund', 'subscription'],
        'feature_request': ['feature', 'request', 'add', 'implement', 'would like']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in full_text for keyword in keywords):
            categories.append(category)
    
    # Extract key points (simple implementation)
    key_points = []
    sentences = body.split('.')
    for sentence in sentences[:3]:  # First 3 sentences
        sentence = sentence.strip()
        if len(sentence) > 20:  # Skip very short sentences
            # Check if sentence contains important keywords
            if any(word in sentence.lower() for word in ['need', 'want', 'require', 'must', 'should', 'please']):
                key_points.append(sentence)
    
    # Suggested actions based on analysis
    suggested_actions = []
    
    if sentiment == 'negative' and urgency == 'high':
        suggested_actions.append('Prioritize immediate response')
        suggested_actions.append('Escalate to senior team member if needed')
    
    if 'technical' in categories:
        suggested_actions.append('Forward to technical support team')
        suggested_actions.append('Gather system logs or error details')
    
    if 'complaint' in categories:
        suggested_actions.append('Acknowledge the concern promptly')
        suggested_actions.append('Offer resolution options')
    
    if 'billing' in categories:
        suggested_actions.append('Review account status')
        suggested_actions.append('Check payment history')
    
    if urgency == 'high':
        suggested_actions.append('Respond within 2-4 hours')
    elif urgency == 'medium':
        suggested_actions.append('Respond within 24 hours')
    else:
        suggested_actions.append('Respond within 2-3 business days')
    
    return {
        'sentiment': sentiment,
        'score': score,
        'urgency': urgency,
        'categories': categories[:3],  # Limit to top 3 categories
        'key_points': key_points[:3],  # Limit to top 3 points
        'suggested_actions': suggested_actions[:4]  # Limit to 4 actions
    }


def register_email_agent(app):
    """
    Register the email agent blueprint with the main Flask app.
    This should be called from the main app initialization.
    """
    app.register_blueprint(email_bp, url_prefix='/api/email-agent')
    logger.info("[INIT] Email Agent registered at /api/email-agent with validation enabled")