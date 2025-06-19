"""
Email to Agent Integration Service
Connects email processing to multi-agent workflow with response generation
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from flask import current_app
from services.email_service import EmailService
from services.email_parser import EmailParser
from services.multi_agent_executor import MultiAgentExecutor
from services.db_task_storage import get_task_storage, log_action
from models.task_storage import create_task, add_conversation
from tasks.email_tasks import process_email_task, send_email_response
from utils.logging_config import get_logger

logger = get_logger(__name__)

class EmailAgentIntegration:
    """
    Orchestrates the email → agent → response pipeline
    """
    
    def __init__(self):
        self.email_service = EmailService()
        self.email_parser = EmailParser()
        self.task_storage = get_task_storage()
        self.executor = MultiAgentExecutor()
        
    def process_incoming_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming email through the complete pipeline:
        1. Parse email into structured task
        2. Create persistent task in database
        3. Route to appropriate agents
        4. Generate and send response
        """
        try:
            # Extract email details
            sender = email_data.get('from', '')
            subject = email_data.get('subject', '')
            body = email_data.get('body_plain', email_data.get('body', ''))
            message_id = email_data.get('message_id', f"email_{uuid.uuid4().hex[:8]}")
            
            logger.info(f"Processing email from {sender}: {subject}")
            
            # 1. Parse email into agent task
            parsed_task = self.email_parser.parse(body)
            
            # Enhance with email metadata
            parsed_task['email_metadata'] = {
                'sender': sender,
                'subject': subject,
                'message_id': message_id,
                'timestamp': email_data.get('timestamp', time.time())
            }
            
            # 2. Determine task type and agents
            task_type = self._determine_task_type(subject, body, parsed_task)
            agents = self._select_agents(task_type, parsed_task)
            
            # 3. Create task in database
            task_description = f"Email from {sender}: {subject}"
            task = create_task(
                description=task_description,
                session_id=f"email_{message_id}",
                agents_involved=agents,
                priority=parsed_task.get('priority', 'medium'),
                metadata={
                    'source': 'email',
                    'email_data': email_data,
                    'parsed_task': parsed_task,
                    'task_type': task_type
                }
            )
            
            # Log email processing
            log_action(
                action_type='email_received',
                action_description=f'Processing email: {subject}',
                agent_id='email_agent',
                task_id=task.task_id,
                metadata={'sender': sender, 'subject': subject}
            )
            
            # 4. Execute agent workflow asynchronously
            from celery import current_app as celery_app
            process_email_task.delay(
                task_id=task.task_id,
                email_data=email_data,
                parsed_task=parsed_task,
                agents=agents
            )
            
            return {
                'success': True,
                'task_id': task.task_id,
                'task_type': task_type,
                'agents_assigned': agents,
                'status': 'processing'
            }
            
        except Exception as e:
            logger.error(f"Failed to process email: {e}")
            log_action(
                action_type='email_error',
                action_description=f'Failed to process email: {str(e)}',
                agent_id='email_agent',
                error_message=str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    def _determine_task_type(self, subject: str, body: str, parsed_task: Dict) -> str:
        """Determine the type of task based on email content"""
        content = f"{subject} {body}".lower()
        
        # Priority-based task type detection
        if any(word in content for word in ['bug', 'error', 'broken', 'fix']):
            return 'bug_report'
        elif any(word in content for word in ['feature', 'request', 'add', 'new']):
            return 'feature_request'
        elif any(word in content for word in ['code review', 'review code', 'check code']):
            return 'code_review'
        elif any(word in content for word in ['deploy', 'deployment', 'release']):
            return 'deployment'
        elif any(word in content for word in ['document', 'docs', 'readme']):
            return 'documentation'
        elif any(word in content for word in ['meeting', 'calendar', 'schedule']):
            return 'calendar_event'
        elif any(word in content for word in ['urgent', 'asap', 'critical']):
            return 'urgent_request'
        else:
            return 'general_inquiry'
    
    def _select_agents(self, task_type: str, parsed_task: Dict) -> List[str]:
        """Select appropriate agents based on task type"""
        agent_mapping = {
            'bug_report': ['bug_01', 'coding_01'],
            'feature_request': ['product_01', 'architect_01', 'coding_01'],
            'code_review': ['coding_01', 'security_01'],
            'deployment': ['devops_01', 'testing_01'],
            'documentation': ['doc_01', 'general_01'],
            'calendar_event': ['calendar_agent', 'general_01'],
            'urgent_request': ['general_01', 'product_01'],
            'general_inquiry': ['general_01']
        }
        
        # Get base agents for task type
        agents = agent_mapping.get(task_type, ['general_01'])
        
        # Add specialized agents based on content
        if 'security' in str(parsed_task).lower():
            agents.append('security_01')
        if 'performance' in str(parsed_task).lower():
            agents.append('performance_01')
        if 'database' in str(parsed_task).lower():
            agents.append('database_01')
            
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in agents if not (x in seen or seen.add(x))]
    
    async def execute_email_task(self, task_id: str, email_data: Dict, 
                                parsed_task: Dict, agents: List[str]) -> Dict[str, Any]:
        """
        Execute the agent workflow for an email task
        This is called by the Celery worker
        """
        try:
            # Update task status
            self.task_storage.update_task(
                task_id,
                status='running',
                current_phase='Processing with agents'
            )
            
            # Create agent request
            agent_request = {
                'task_description': parsed_task.get('description', email_data.get('subject', '')),
                'context': {
                    'source': 'email',
                    'sender': email_data.get('from'),
                    'subject': email_data.get('subject'),
                    'priority': parsed_task.get('priority', 'medium'),
                    'requirements': parsed_task.get('requirements', []),
                    'deadline': parsed_task.get('deadline')
                }
            }
            
            # Execute multi-agent workflow
            result = await self.executor.execute_workflow(
                task_id=task_id,
                agents=agents,
                task_description=agent_request['task_description'],
                context=agent_request['context']
            )
            
            # Generate email response
            response_content = self._generate_email_response(
                task_id=task_id,
                result=result,
                email_data=email_data,
                parsed_task=parsed_task
            )
            
            # Send response email
            if response_content:
                await self._send_email_response(
                    task_id=task_id,
                    email_data=email_data,
                    response_content=response_content
                )
            
            # Update task as completed
            self.task_storage.update_task(
                task_id,
                status='completed',
                summary=result.get('summary', ''),
                results=result
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'result': result,
                'response_sent': bool(response_content)
            }
            
        except Exception as e:
            logger.error(f"Failed to execute email task {task_id}: {e}")
            self.task_storage.update_task(
                task_id,
                status='error',
                error_message=str(e)
            )
            raise
    
    def _generate_email_response(self, task_id: str, result: Dict, 
                                email_data: Dict, parsed_task: Dict) -> Optional[str]:
        """Generate email response based on agent results"""
        try:
            # Get task details
            task = self.task_storage.get_task(task_id)
            if not task:
                return None
            
            # Get conversation history
            conversations = self.task_storage.get_task_conversations(task_id)
            
            # Build response components
            sender_name = email_data.get('from', '').split('<')[0].strip()
            subject = email_data.get('subject', 'Your request')
            
            # Generate response based on task type
            task_type = task.get('metadata', {}).get('task_type', 'general_inquiry')
            
            response_templates = {
                'bug_report': """Hi {name},

Thank you for reporting this issue. Our team has analyzed the bug and here's what we found:

{summary}

{details}

We'll work on fixing this issue and will update you once it's resolved.

Best regards,
The Team""",
                
                'feature_request': """Hi {name},

Thank you for your feature request. We've reviewed your suggestion and here's our assessment:

{summary}

{details}

We've added this to our product roadmap for consideration.

Best regards,
The Team""",
                
                'general_inquiry': """Hi {name},

Thank you for your inquiry. Here's the information you requested:

{summary}

{details}

If you need any clarification, please don't hesitate to ask.

Best regards,
The Team"""
            }
            
            # Get appropriate template
            template = response_templates.get(task_type, response_templates['general_inquiry'])
            
            # Extract key points from agent conversations
            details = self._extract_key_points(conversations)
            
            # Format response
            response = template.format(
                name=sender_name or 'there',
                summary=result.get('summary', task.get('summary', 'We have processed your request.')),
                details=details
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate email response: {e}")
            return None
    
    def _extract_key_points(self, conversations: List[Dict]) -> str:
        """Extract key points from agent conversations"""
        key_points = []
        
        for conv in conversations:
            if conv.get('agent_id') != 'executive_summary':
                # Extract first 2 sentences or 100 chars
                content = conv.get('content', '')
                sentences = content.split('. ')[:2]
                point = '. '.join(sentences)
                if len(point) > 100:
                    point = point[:97] + '...'
                if point:
                    key_points.append(f"• {point}")
        
        return '\n'.join(key_points[:5])  # Limit to 5 key points
    
    async def _send_email_response(self, task_id: str, email_data: Dict, response_content: str):
        """Send email response via email service"""
        try:
            # Prepare response email
            response_email = {
                'to': email_data.get('from'),
                'subject': f"Re: {email_data.get('subject', 'Your request')}",
                'body': response_content,
                'reply_to_message_id': email_data.get('message_id'),
                'tags': ['auto_response', f'task_{task_id}']
            }
            
            # Send via email service
            result = await self.email_service.send_email(**response_email)
            
            # Log response
            log_action(
                action_type='email_sent',
                action_description=f'Sent response to {response_email["to"]}',
                agent_id='email_agent',
                task_id=task_id,
                metadata={'email_id': result.get('id')}
            )
            
            # Store response in conversation history
            add_conversation(
                task_id=task_id,
                agent_id='email_agent',
                role='assistant',
                content=f"Email response sent:\n\n{response_content}",
                metadata={'email_sent': True, 'recipient': response_email['to']}
            )
            
        except Exception as e:
            logger.error(f"Failed to send email response: {e}")
            raise

# Global instance
_email_integration = None

def get_email_integration() -> EmailAgentIntegration:
    """Get or create email integration instance"""
    global _email_integration
    if _email_integration is None:
        _email_integration = EmailAgentIntegration()
    return _email_integration