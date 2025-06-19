"""
Webhook Processing Tasks
Handles webhook event processing with replay protection
"""

import logging
import json
import hashlib
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from celery import current_task
from config.celery_config import celery_app
from services.token_replay_cache import get_token_replay_cache
from utils.retry_config import retry_on_failure
from utils.notification_service import get_notification_service

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name='tasks.webhook_tasks.process_webhook')
@retry_on_failure(max_retries=3)
def process_webhook(
    self,
    webhook_data: Dict[str, Any],
    webhook_type: str,
    source_ip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process incoming webhook with replay protection.
    
    Args:
        webhook_data: Webhook payload data
        webhook_type: Type of webhook (mailgun, github, etc.)
        source_ip: Source IP address
        
    Returns:
        Processing result
    """
    return run_async(_process_webhook_async(self, webhook_data, webhook_type, source_ip))


async def _process_webhook_async(
    self,
    webhook_data: Dict[str, Any],
    webhook_type: str,
    source_ip: Optional[str] = None
) -> Dict[str, Any]:
    """Async implementation of webhook processing."""
    try:
        # Extract or generate unique identifier
        webhook_id = webhook_data.get('id') or webhook_data.get('event_id')
        if not webhook_id:
            # Generate from payload hash
            payload_str = json.dumps(webhook_data, sort_keys=True)
            webhook_id = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
        
        # Check for replay
        token_cache = get_token_replay_cache()
        token = f"{webhook_type}:{webhook_id}"
        context = {
            'source_ip': source_ip,
            'webhook_type': webhook_type
        }
        
        is_replay = await token_cache.has_seen_token(token, context)
        if is_replay:
            logger.warning(f"Duplicate webhook detected: {token}")
            return {
                'status': 'skipped',
                'reason': 'duplicate_webhook',
                'webhook_id': webhook_id
            }
        
        # Route to appropriate processor
        processors = {
            'mailgun': _process_mailgun_webhook,
            'github': _process_github_webhook,
            'slack': _process_slack_webhook,
            'calendar': _process_calendar_webhook
        }
        
        processor = processors.get(webhook_type)
        if not processor:
            raise ValueError(f"Unknown webhook type: {webhook_type}")
        
        # Process webhook
        result = await processor(webhook_data)
        
        return {
            'status': 'completed',
            'webhook_id': webhook_id,
            'webhook_type': webhook_type,
            'result': result,
            'processed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
        
        # Send notification on final failure
        notification_service = get_notification_service()
        await notification_service.send_webhook_failure_alert(
            webhook_url=f"{webhook_type} webhook",
            attempts=self.request.retries + 1,
            error=str(e)
        )
        
        return {
            'status': 'failed',
            'error': str(e),
            'webhook_type': webhook_type
        }


async def _process_mailgun_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process Mailgun webhook events"""
    from tasks.email_tasks import process_email_event
    
    # Delegate to email task
    result = process_email_event.apply_async(
        args=[data],
        queue='email_queue'
    ).get()
    
    return result


async def _process_github_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process GitHub webhook events"""
    event_type = data.get('action')
    repository = data.get('repository', {}).get('name')
    event_name = data.get('event')  # GitHub sends event type in header
    
    logger.info(f"Processing GitHub {event_name} event (action: {event_type}) for {repository}")
    
    # Import services
    from services.service_container import get_service_container
    container = get_service_container()
    
    try:
        # Get appropriate agent based on event type
        agent_id = _get_agent_for_github_event(event_name, event_type)
        
        # Format message for agent
        message = _format_github_message(event_name, event_type, data)
        
        # Route to appropriate agent
        if agent_id:
            multi_agent_service = container.get('multi_agent_task_service')
            
            # Create task for the agent
            from models.agent_task import AgentTask, TaskType, TaskPriority
            task = AgentTask(
                title=f"GitHub {event_name}: {repository}",
                description=message,
                task_type=TaskType.GENERAL,
                priority=_get_github_priority(event_name)
            )
            
            # Assign to specific agent
            task.agent_assignment.primary_agent = agent_id
            
            # Execute task
            result = await multi_agent_service.execute_task_async(task)
            
            return {
                'success': True,
                'event_type': event_name,
                'repository': repository,
                'task_id': task.task_id,
                'assigned_to': agent_id,
                'result': result
            }
        else:
            logger.warning(f"No agent configured for GitHub event: {event_name}")
            return {
                'success': True,
                'event_type': event_name,
                'repository': repository,
                'message': 'Event received but no agent assigned'
            }
            
    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'event_type': event_name,
            'repository': repository
        }


async def _process_slack_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process Slack webhook events"""
    event_type = data.get('type')
    
    # TODO: Implement Slack webhook processing
    logger.info(f"Processing Slack {event_type} event")
    
    return {
        'success': True,
        'event_type': event_type
    }


async def _process_calendar_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process Calendar webhook events"""
    event_type = data.get('type')
    calendar_id = data.get('calendar_id')
    
    logger.info(f"Processing Calendar {event_type} event for {calendar_id}")
    
    # Import services
    from services.service_container import get_service_container
    container = get_service_container()
    
    try:
        # Extract event details
        event = data.get('event', {})
        event_id = event.get('id')
        summary = event.get('summary', 'No title')
        description = event.get('description', '')
        start_time = event.get('start', {})
        end_time = event.get('end', {})
        attendees = event.get('attendees', [])
        organizer = event.get('organizer', {})
        
        # Determine action based on event type
        if event_type in ['created', 'updated', 'deleted', 'started', 'ended']:
            # Get appropriate agent
            agent_id = _get_agent_for_calendar_event(event_type, event)
            
            # Format message
            message = _format_calendar_message(event_type, event, data)
            
            # Create task for agent
            multi_agent_service = container.get('multi_agent_task_service')
            
            from models.agent_task import AgentTask, TaskType, TaskPriority
            task = AgentTask(
                title=f"Calendar Event: {summary}",
                description=message,
                task_type=TaskType.GENERAL,
                priority=_get_calendar_priority(event_type, event)
            )
            
            # Set deadline if it's a future event
            if event_type == 'created' and start_time:
                start_dt = _parse_calendar_datetime(start_time)
                if start_dt and start_dt > datetime.now(timezone.utc):
                    task.requirements.deadline = start_dt
            
            # Assign to agent
            task.agent_assignment.primary_agent = agent_id
            
            # Execute task
            result = await multi_agent_service.execute_task_async(task)
            
            return {
                'success': True,
                'event_type': event_type,
                'calendar_id': calendar_id,
                'event_id': event_id,
                'task_id': task.task_id,
                'assigned_to': agent_id,
                'result': result
            }
        else:
            logger.warning(f"Unknown calendar event type: {event_type}")
            return {
                'success': True,
                'event_type': event_type,
                'calendar_id': calendar_id,
                'message': 'Event received but no action taken'
            }
            
    except Exception as e:
        logger.error(f"Error processing calendar webhook: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'event_type': event_type,
            'calendar_id': calendar_id
        }


@celery_app.task(name='tasks.webhook_tasks.validate_webhook_signature')
def validate_webhook_signature(
    payload: str,
    signature: str,
    webhook_type: str
) -> bool:
    """
    Validate webhook signature for security.
    
    Args:
        payload: Raw webhook payload
        signature: Signature from webhook headers
        webhook_type: Type of webhook
        
    Returns:
        True if signature is valid
    """
    return run_async(_validate_webhook_signature_async(payload, signature, webhook_type))


async def _validate_webhook_signature_async(
    payload: str,
    signature: str,
    webhook_type: str
) -> bool:
    """Async implementation of webhook signature validation."""
    validators = {
        'mailgun': _validate_mailgun_signature,
        'github': _validate_github_signature,
        'slack': _validate_slack_signature
    }
    
    validator = validators.get(webhook_type)
    if not validator:
        logger.warning(f"No validator for webhook type: {webhook_type}")
        return False
    
    return await validator(payload, signature)


async def _validate_mailgun_signature(payload: str, signature: str) -> bool:
    """Validate Mailgun webhook signature"""
    import hmac
    import os
    
    # Get Mailgun webhook signing key from environment
    signing_key = os.environ.get('MAILGUN_SIGNING_KEY', '')
    if not signing_key:
        logger.warning("Mailgun signing key not configured")
        return False
    
    expected_signature = hmac.new(
        signing_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def _get_agent_for_github_event(event_name: str, action: str = None) -> str:
    """Determine which agent should handle a GitHub event"""
    # Map GitHub events to agents
    event_mapping = {
        'issues': 'bug_01',  # Bug Agent handles issues
        'pull_request': 'coder_01',  # Coding Agent handles PRs
        'push': 'devops_01',  # DevOps handles deployments
        'workflow_run': 'devops_01',  # DevOps handles CI/CD
        'release': 'devops_01',  # DevOps handles releases
        'issue_comment': 'bug_01',  # Bug Agent handles issue comments
        'pull_request_review': 'tester_01',  # QA handles PR reviews
        'pull_request_review_comment': 'coder_01',  # Coder handles review comments
        'create': 'coder_01',  # Branch/tag creation
        'delete': 'devops_01',  # Branch/tag deletion
    }
    
    return event_mapping.get(event_name, 'general_01')  # Default to General Assistant


def _get_github_priority(event_name: str) -> 'TaskPriority':
    """Determine task priority based on GitHub event type"""
    from models.agent_task import TaskPriority
    
    high_priority_events = ['issues', 'pull_request', 'workflow_run']
    medium_priority_events = ['push', 'release', 'pull_request_review']
    
    if event_name in high_priority_events:
        return TaskPriority.HIGH
    elif event_name in medium_priority_events:
        return TaskPriority.MEDIUM
    else:
        return TaskPriority.LOW


def _format_github_message(event_name: str, action: str, data: Dict[str, Any]) -> str:
    """Format GitHub webhook data into a readable message for agents"""
    repository = data.get('repository', {})
    repo_name = repository.get('full_name', 'Unknown')
    repo_url = repository.get('html_url', '')
    
    sender = data.get('sender', {})
    sender_login = sender.get('login', 'Unknown')
    
    message_parts = [
        f"GitHub Event: {event_name}",
        f"Repository: {repo_name}",
        f"Triggered by: @{sender_login}",
    ]
    
    # Add event-specific details
    if event_name == 'issues':
        issue = data.get('issue', {})
        issue_title = issue.get('title', 'No title')
        issue_number = issue.get('number', 'Unknown')
        issue_url = issue.get('html_url', '')
        message_parts.extend([
            f"Issue #{issue_number}: {issue_title}",
            f"Action: {action}",
            f"URL: {issue_url}"
        ])
        
    elif event_name == 'pull_request':
        pr = data.get('pull_request', {})
        pr_title = pr.get('title', 'No title')
        pr_number = pr.get('number', 'Unknown')
        pr_url = pr.get('html_url', '')
        base_branch = pr.get('base', {}).get('ref', 'Unknown')
        head_branch = pr.get('head', {}).get('ref', 'Unknown')
        message_parts.extend([
            f"PR #{pr_number}: {pr_title}",
            f"Action: {action}",
            f"From: {head_branch} → To: {base_branch}",
            f"URL: {pr_url}"
        ])
        
    elif event_name == 'push':
        ref = data.get('ref', 'Unknown')
        commits = data.get('commits', [])
        message_parts.extend([
            f"Branch: {ref.replace('refs/heads/', '')}",
            f"Commits: {len(commits)}",
        ])
        if commits:
            message_parts.append("Latest commit: " + commits[-1].get('message', 'No message'))
            
    elif event_name == 'workflow_run':
        workflow = data.get('workflow_run', {})
        workflow_name = workflow.get('name', 'Unknown')
        status = workflow.get('status', 'Unknown')
        conclusion = workflow.get('conclusion', 'N/A')
        message_parts.extend([
            f"Workflow: {workflow_name}",
            f"Status: {status}",
            f"Conclusion: {conclusion}"
        ])
    
    # Add repository context
    if repo_url:
        message_parts.append(f"\nRepository URL: {repo_url}")
    
    return "\n".join(message_parts)


def _get_agent_for_calendar_event(event_type: str, event: Dict[str, Any]) -> str:
    """Determine which agent should handle a calendar event"""
    # Check event details for routing hints
    summary = event.get('summary', '').lower()
    description = event.get('description', '').lower()
    
    # Route based on keywords in event
    if any(word in summary + description for word in ['bug', 'issue', 'problem', 'error']):
        return 'bug_01'
    elif any(word in summary + description for word in ['deploy', 'release', 'build', 'ci/cd']):
        return 'devops_01'
    elif any(word in summary + description for word in ['test', 'qa', 'quality', 'testing']):
        return 'tester_01'
    elif any(word in summary + description for word in ['code review', 'pr review', 'implementation']):
        return 'coder_01'
    elif any(word in summary + description for word in ['planning', 'product', 'feature', 'requirement']):
        return 'product_01'
    else:
        return 'general_01'  # Default to General Assistant


def _get_calendar_priority(event_type: str, event: Dict[str, Any]) -> 'TaskPriority':
    """Determine priority based on calendar event"""
    from models.agent_task import TaskPriority
    
    # Deleted events are high priority
    if event_type == 'deleted':
        return TaskPriority.HIGH
    
    # Check if event is soon
    start_time = event.get('start', {})
    if start_time:
        start_dt = _parse_calendar_datetime(start_time)
        if start_dt:
            time_until = (start_dt - datetime.now(timezone.utc)).total_seconds()
            if time_until < 3600:  # Less than 1 hour
                return TaskPriority.HIGH
            elif time_until < 86400:  # Less than 24 hours
                return TaskPriority.MEDIUM
    
    return TaskPriority.LOW


def _parse_calendar_datetime(dt_obj: Dict[str, Any]) -> Optional[datetime]:
    """Parse calendar datetime object to Python datetime"""
    if isinstance(dt_obj, str):
        # Simple ISO string
        try:
            return datetime.fromisoformat(dt_obj.replace('Z', '+00:00'))
        except:
            return None
    elif isinstance(dt_obj, dict):
        # Google Calendar style object
        if 'dateTime' in dt_obj:
            try:
                return datetime.fromisoformat(dt_obj['dateTime'].replace('Z', '+00:00'))
            except:
                return None
        elif 'date' in dt_obj:
            # All-day event
            try:
                return datetime.strptime(dt_obj['date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except:
                return None
    return None


def _format_calendar_message(event_type: str, event: Dict[str, Any], data: Dict[str, Any]) -> str:
    """Format calendar event into readable message"""
    calendar_id = data.get('calendar_id', 'Unknown')
    summary = event.get('summary', 'No title')
    description = event.get('description', '')
    location = event.get('location', '')
    
    start_time = event.get('start', {})
    end_time = event.get('end', {})
    attendees = event.get('attendees', [])
    organizer = event.get('organizer', {})
    
    message_parts = [
        f"Calendar Event: {event_type}",
        f"Calendar: {calendar_id}",
        f"Title: {summary}",
    ]
    
    if description:
        message_parts.append(f"Description: {description}")
    
    if location:
        message_parts.append(f"Location: {location}")
    
    # Format time
    start_dt = _parse_calendar_datetime(start_time)
    end_dt = _parse_calendar_datetime(end_time)
    
    if start_dt:
        message_parts.append(f"Start: {start_dt.strftime('%Y-%m-%d %H:%M %Z')}")
    if end_dt:
        message_parts.append(f"End: {end_dt.strftime('%Y-%m-%d %H:%M %Z')}")
    
    # Add organizer
    if organizer:
        org_email = organizer.get('email', 'Unknown')
        org_name = organizer.get('displayName', org_email)
        message_parts.append(f"Organizer: {org_name}")
    
    # Add attendees
    if attendees:
        attendee_list = []
        for attendee in attendees[:5]:  # Limit to first 5
            att_email = attendee.get('email', 'Unknown')
            att_name = attendee.get('displayName', att_email)
            att_status = attendee.get('responseStatus', 'needsAction')
            attendee_list.append(f"{att_name} ({att_status})")
        
        message_parts.append(f"Attendees: {', '.join(attendee_list)}")
        if len(attendees) > 5:
            message_parts.append(f"... and {len(attendees) - 5} more")
    
    # Add event-specific context
    if event_type == 'deleted':
        message_parts.append("\n⚠️ This event has been cancelled/deleted.")
    elif event_type == 'updated':
        message_parts.append("\n📝 This event has been updated. Please review changes.")
    elif event_type == 'started':
        message_parts.append("\n🔔 This event is starting now!")
    
    return "\n".join(message_parts)


async def _validate_github_signature(payload: str, signature: str) -> bool:
    """Validate GitHub webhook signature"""
    import hmac
    import os
    
    # Get GitHub webhook secret from environment
    secret = os.environ.get('GITHUB_WEBHOOK_SECRET', '')
    if not secret:
        logger.warning("GitHub webhook secret not configured")
        return False
    
    expected_signature = 'sha256=' + hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


async def _validate_slack_signature(payload: str, signature: str) -> bool:
    """Validate Slack webhook signature"""
    # TODO: Implement Slack signature validation
    import os
    
    signing_secret = os.environ.get('SLACK_SIGNING_SECRET', '')
    if not signing_secret:
        logger.warning("Slack signing secret not configured")
        return False
    
    # Slack uses a different signature format
    # Would need timestamp and request body for proper validation
    return True


@celery_app.task(name='tasks.webhook_tasks.cleanup_webhook_logs')
def cleanup_webhook_logs(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Clean up old webhook logs.
    
    Args:
        days_to_keep: Number of days of logs to retain
        
    Returns:
        Cleanup results
    """
    logger.info(f"Cleaning up webhook logs older than {days_to_keep} days")
    
    try:
        from datetime import datetime, timedelta
        import os
        import glob
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        logs_cleaned = 0
        space_freed = 0
        
        # Clean up log files
        log_patterns = [
            'logs/webhooks/*.log',
            'logs/webhook_*.log',
            '/var/log/webhooks/*.log'
        ]
        
        for pattern in log_patterns:
            for log_file in glob.glob(pattern):
                try:
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    if file_mtime < cutoff_date:
                        file_size = os.path.getsize(log_file)
                        os.remove(log_file)
                        logs_cleaned += 1
                        space_freed += file_size
                except Exception as e:
                    logger.warning(f"Error processing log file {log_file}: {e}")
        
        # Clean up database webhook logs if using database logging
        try:
            from services.service_container import get_service_container
            container = get_service_container()
            
            # If there's a database service for webhook logs
            if container.has('database'):
                db = container.get('database')
                from sqlalchemy import text
                
                # Assuming webhook_logs table exists
                delete_query = text("""
                    DELETE FROM webhook_logs 
                    WHERE created_at < :cutoff_date
                """)
                
                result = db.session.execute(
                    delete_query,
                    {'cutoff_date': cutoff_date}
                )
                db.session.commit()
                
                logs_cleaned += result.rowcount
        except Exception as e:
            logger.debug(f"No database webhook logs to clean: {e}")
        
        # Convert bytes to MB
        space_freed_mb = round(space_freed / (1024 * 1024), 2)
        
        logger.info(f"Cleaned up {logs_cleaned} webhook logs, freed {space_freed_mb} MB")
        
        return {
            'success': True,
            'logs_cleaned': logs_cleaned,
            'space_freed': f'{space_freed_mb} MB',
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up webhook logs: {e}")
        return {
            'success': False,
            'error': str(e),
            'logs_cleaned': 0,
            'space_freed': '0 MB'
        }