"""
Email Parser Service - Fixed Version
Extracts structured tasks from email content using improved NLP and pattern matching
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dateutil import parser as date_parser
import json

from models.agent_task import (
    AgentTask, EmailMetadata, TaskRequirements, 
    TaskType, TaskPriority, AgentAssignment
)
from config.config_loader import get_config_loader
from utils.logging_config import get_logger, LogContext
from services.email_parser_enhancements import EnhancedDeadlineExtractor, EnhancedListExtractor

logger = get_logger(__name__)


class EmailParser:
    """
    Parses emails to extract structured tasks for agent processing
    """
    
    def __init__(self):
        # Initialize enhanced extractors
        self.deadline_extractor = EnhancedDeadlineExtractor()
        self.list_extractor = EnhancedListExtractor()
        
        # Keep original patterns as fallback
        self.deadline_patterns = [
            # Standard deadline phrases
            r"(?:deadline|due|by|before)\s*:?\s*([^.!?\n]+?)(?:[.!?\n]|$)",
            r"(?:need(?:ed)?|required?)\s*(?:by)?\s*:?\s*([^.!?\n]+?)(?:[.!?\n]|$)",
            r"(?:complete|finish|deliver)\s*(?:by)?\s*:?\s*([^.!?\n]+?)(?:[.!?\n]|$)",
            # Time-based patterns
            r"(?:within|in)\s+(\d+\s*(?:hours?|days?|weeks?))",
            r"(?:by|before)\s+(tomorrow|today|tonight|this\s+(?:week|month)|next\s+(?:week|month))",
            r"(?:end\s+of)\s+(?:the\s+)?(day|week|month)",
            # Explicit dates
            r"(?:on|by)\s+(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",
            r"(?:on|by)\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?)"
        ]
        
        # Improved list extraction patterns
        self.list_item_patterns = [
            # Bullet points with various markers
            r"^\s*[-•*→▪▸◦‣⁃]\s*(.+)$",
            # Numbered lists
            r"^\s*\d+[.)]\s*(.+)$",
            # Letter lists
            r"^\s*[a-zA-Z][.)]\s*(.+)$",
            # Indented items
            r"^\s{2,}(.+)$"
        ]
        
        # Section header patterns for better extraction
        self.section_patterns = {
            "deliverables": r"(?:deliverables?|outputs?|results?|outcomes?)\s*:?\s*\n",
            "success_criteria": r"(?:success\s+criteria|acceptance\s+criteria|done\s+when|definition\s+of\s+done)\s*:?\s*\n",
            "requirements": r"(?:requirements?|needs?|prerequisites?)\s*:?\s*\n",
            "dependencies": r"(?:dependencies|depends?\s+on|blocked\s+by|waiting\s+for|requires?)\s*:?\s*\n"
        }
        
        # Priority patterns including casual language
        self.priority_patterns = {
            TaskPriority.URGENT: [
                r"\b(?:urgent|asap|critical|emergency|immediately|right\s+away|high\s+priority|top\s+priority)\b",
                r"\b(?:fire|burning|blocker|showstopper)\b",
                r"(?:!!!|🔥|🚨|⚠️)"
            ],
            TaskPriority.HIGH: [
                r"\b(?:high\s+priority|important|needed\s+soon|priority|soon\s+as\s+possible)\b",
                r"\b(?:by\s+end\s+of\s+day|eod|today)\b"
            ],
            TaskPriority.LOW: [
                r"\b(?:low\s+priority|when\s+you\s+(?:have|get)\s+time|no\s+rush|not\s+urgent|whenever)\b",
                r"\b(?:nice\s+to\s+have|optional|if\s+possible|backlog)\b",
                r"\b(?:eventually|someday|future)\b"
            ]
        }
        
        # Action keywords that indicate tasks
        self.action_keywords = [
            "review", "fix", "implement", "create", "update", "deploy",
            "investigate", "analyze", "document", "test", "debug",
            "refactor", "optimize", "integrate", "configure", "setup",
            "build", "design", "develop", "resolve", "troubleshoot"
        ]
    
    def parse_email(self, email_data: Dict[str, Any]) -> AgentTask:
        """
        Parse email data into a structured AgentTask
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            AgentTask: Structured task ready for agent processing
        """
        try:
            # Extract email metadata
            email_metadata = self._extract_email_metadata(email_data)
            
            # Extract core task information
            subject = email_metadata.subject
            body = email_data.get("body_plain", "") or email_data.get("stripped_text", "")
            
            # Detect task type and priority
            task_type = TaskType.detect_from_content(subject, body)
            priority = self._detect_priority(subject, body)
            
            # Extract task title and description
            title = self._extract_task_title(subject, body)
            description = self._extract_task_description(subject, body)
            
            # Extract requirements
            requirements = self._extract_requirements(body)
            
            # Determine agent assignment
            agent_assignment = AgentAssignment.from_task_type(task_type, body)
            
            # Extract tags and context
            tags = self._extract_tags(subject, body)
            context = self._extract_context(email_data, body)
            
            # Create the task
            task = AgentTask(
                title=title,
                description=description,
                task_type=task_type,
                priority=priority,
                email_metadata=email_metadata,
                requirements=requirements,
                agent_assignment=agent_assignment,
                tags=tags,
                context=context
            )
            
            logger.info("Successfully parsed email", message_id=email_metadata.message_id, task_id=task.task_id)
            return task
            
        except Exception as e:
            logger.error("Failed to parse email", error=str(e))
            # Return a basic task with error information
            return self._create_fallback_task(email_data, str(e))
    
    def _detect_priority(self, subject: str, body: str) -> TaskPriority:
        """Detect priority using configuration"""
        # Use the method from TaskPriority which now uses config
        return TaskPriority.from_email_markers(subject, body)
    
    def _extract_email_metadata(self, email_data: Dict[str, Any]) -> EmailMetadata:
        """Extract metadata from email data"""
        # Handle both direct fields and nested structures
        message = email_data.get("message", {})
        headers = message.get("headers", {})
        
        # Extract timestamp
        timestamp_str = email_data.get("timestamp") or email_data.get("Date")
        timestamp = self._parse_timestamp(timestamp_str) if timestamp_str else datetime.utcnow()
        
        # Extract recipients
        recipients = message.get("recipients", [])
        if not recipients and "recipient" in email_data:
            recipients = [email_data["recipient"]]
        elif not recipients and "To" in headers:
            recipients = [headers["To"]]
        
        return EmailMetadata(
            message_id=headers.get("message-id") or email_data.get("Message-Id", f"email_{datetime.utcnow().timestamp()}"),
            sender=headers.get("from") or email_data.get("sender", "unknown@email.com"),
            recipients=recipients,
            subject=headers.get("subject") or email_data.get("subject", "No Subject"),
            timestamp=timestamp,
            cc=self._extract_cc_list(headers),
            reply_to=headers.get("reply-to"),
            thread_id=headers.get("in-reply-to"),
            attachments=self._extract_attachments(email_data),
            headers=headers
        )
    
    def _extract_task_title(self, subject: str, body: str) -> str:
        """Extract a concise task title"""
        # Clean up subject line
        title = re.sub(r"^(Re:|Fwd:|Fw:)\s*", "", subject, flags=re.IGNORECASE).strip()
        
        # If subject is too generic, try to extract from body
        if len(title) < 10 or title.lower() in ["task", "request", "help", "question"]:
            # Look for action keywords in the first few lines
            lines = body.split("\n")[:5]
            for line in lines:
                for keyword in self.action_keywords:
                    if keyword in line.lower():
                        title = line.strip()[:100]  # Limit length
                        break
                if len(title) > 10:
                    break
        
        return title or "Email Task"
    
    def _extract_task_description(self, subject: str, body: str) -> str:
        """Extract detailed task description"""
        # Start with the email body
        description = body.strip()
        
        # Remove common email signatures and footers
        description = self._remove_email_artifacts(description)
        
        # If body is empty or too short, include subject
        if len(description) < 20:
            description = f"Subject: {subject}\n\n{description}"
        
        return description
    
    def _extract_requirements(self, body: str) -> TaskRequirements:
        """Extract task requirements from email body"""
        requirements = TaskRequirements()
        
        # Extract deadline
        deadline = self._extract_deadline(body)
        if deadline:
            requirements.deadline = deadline
        
        # Extract lists for each section
        requirements.deliverables = self._extract_section_items(body, "deliverables")
        requirements.success_criteria = self._extract_section_items(body, "success_criteria")
        requirements.dependencies = self._extract_section_items(body, "dependencies")
        
        return requirements
    
    def _extract_section_items(self, body: str, section_type: str) -> List[str]:
        """Extract items from a specific section"""
        items = []
        
        # Look for section headers
        section_pattern = self.section_patterns.get(section_type)
        if section_pattern:
            match = re.search(section_pattern, body, re.IGNORECASE | re.MULTILINE)
            if match:
                # Extract content after the section header
                start_pos = match.end()
                # Find the next section or end of content
                remaining_text = body[start_pos:]
                next_section = re.search(r'\n\s*\n|\n[A-Z]', remaining_text)
                end_pos = next_section.start() if next_section else len(remaining_text)
                section_content = remaining_text[:end_pos]
                
                # Extract list items from section
                items = self._extract_list_items_from_text(section_content)
        
        # If no section header found, try general patterns
        if not items:
            if section_type == "deliverables":
                patterns = [
                    r"(?:deliverables?|outputs?|results?)[:;\s]+([^.!?\n]+)",
                    r"(?:please provide|need|want)[:;\s]+([^.!?\n]+)",
                ]
            elif section_type == "success_criteria":
                patterns = [
                    r"(?:success criteria|acceptance criteria|done when)[:;\s]+([^.!?\n]+)",
                    r"(?:should|must|needs? to)[:;\s]+([^.!?\n]+)"
                ]
            elif section_type == "dependencies":
                patterns = [
                    r"(?:depends? on|requires?|needs?)[:;\s]+([^.!?\n]+)",
                    r"(?:blocked by|waiting for)[:;\s]+([^.!?\n]+)"
                ]
            else:
                patterns = []
            
            for pattern in patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                for match in matches:
                    items.extend(self._parse_inline_list(match))
        
        return items
    
    def _extract_list_items_from_text(self, text: str) -> List[str]:
        """Extract list items from a block of text"""
        # First try the enhanced list extractor
        extracted_lists = self.list_extractor.extract_lists(text)
        
        # Combine all extracted list items
        all_items = []
        
        # Add bullet list items
        for bullet_list in extracted_lists.get('bullet_lists', []):
            for item in bullet_list.get('items', []):
                if isinstance(item, dict) and 'text' in item:
                    all_items.append(item['text'])
                
        # Add numbered list items
        for numbered_list in extracted_lists.get('numbered_lists', []):
            for item in numbered_list.get('items', []):
                if isinstance(item, dict) and 'text' in item:
                    all_items.append(item['text'])
        
        # Add task list items
        for task_list in extracted_lists.get('task_lists', []):
            for item in task_list.get('items', []):
                if isinstance(item, dict) and 'text' in item:
                    all_items.append(item['text'])
        
        # If enhanced extraction found items, return them
        if all_items:
            return all_items
        
        # Fallback to original method
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check each list pattern
            for pattern in self.list_item_patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    item = match.group(1).strip() if match.groups() else line
                    if item and len(item) > 3:  # Avoid very short items
                        items.append(item)
                    break
            else:
                # If no pattern matches but line has content, include it
                if len(line) > 10 and not line.endswith(':'):
                    items.append(line)
        
        return items
    
    def _parse_inline_list(self, text: str) -> List[str]:
        """Parse inline lists separated by commas, semicolons, or 'and'"""
        # First try enhanced inline list extraction
        extracted_lists = self.list_extractor.extract_lists(text)
        inline_items = []
        
        for inline_list in extracted_lists.get('inline_lists', []):
            inline_items.extend(inline_list.get('items', []))
        
        if inline_items:
            return inline_items
        
        # Fallback to original method
        items = re.split(r'[,;]|\s+and\s+', text)
        # Clean and filter items
        return [item.strip() for item in items if item.strip() and len(item.strip()) > 3]
    
    def _extract_deadline(self, text: str) -> Optional[datetime]:
        """Extract deadline from text using enhanced patterns"""
        # First try the enhanced deadline extractor
        result = self.deadline_extractor.extract_deadline(text)
        if result:
            deadline, confidence = result
            # Use deadline if confidence is high enough
            if confidence >= 0.7:
                return deadline
        
        # Fallback to original method for backwards compatibility
        now = datetime.now()
        
        for pattern in self.deadline_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # First try relative date parsing
                    deadline = self._parse_relative_date(match)
                    if deadline and deadline > now:
                        return deadline
                    
                    # Then try dateutil parser
                    deadline = date_parser.parse(match, fuzzy=True, default=now)
                    # If the date is in the past, it might be a misparse
                    if deadline > now:
                        return deadline
                except:
                    pass
        return None
    
    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        """Parse relative dates like 'next week', 'in 3 days', etc."""
        text = text.lower().strip()
        now = datetime.now()
        
        # Comprehensive pattern matching for relative dates
        patterns = {
            # Numeric intervals
            r"(?:in\s+)?(\d+)\s*(?:hours?|hrs?)": lambda x: now + timedelta(hours=int(x)),
            r"(?:in\s+)?(\d+)\s*days?": lambda x: now + timedelta(days=int(x)),
            r"(?:in\s+)?(\d+)\s*weeks?": lambda x: now + timedelta(weeks=int(x)),
            r"(?:in\s+)?(\d+)\s*months?": lambda x: now + timedelta(days=int(x)*30),
            
            # Named relative dates
            r"tomorrow": lambda x: now + timedelta(days=1),
            r"today": lambda x: now.replace(hour=23, minute=59),
            r"tonight": lambda x: now.replace(hour=23, minute=59),
            r"next\s+week": lambda x: now + timedelta(weeks=1),
            r"this\s+week": lambda x: now + timedelta(days=(4 - now.weekday())),
            r"next\s+month": lambda x: now + timedelta(days=30),
            r"end\s+of\s+(?:the\s+)?day": lambda x: now.replace(hour=23, minute=59),
            r"end\s+of\s+(?:the\s+)?week": lambda x: now + timedelta(days=(4 - now.weekday())),
            r"end\s+of\s+(?:the\s+)?month": lambda x: (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        }
        
        for pattern, calculator in patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    if match.groups():
                        return calculator(match.group(1))
                    else:
                        return calculator(None)
                except:
                    pass
        
        return None
    
    def _extract_tags(self, subject: str, body: str) -> List[str]:
        """Extract relevant tags from email content"""
        tags = []
        content = f"{subject} {body}".lower()
        
        # Extract hashtags (improved pattern)
        hashtags = re.findall(r'#(\w+)', content)
        tags.extend(hashtags)
        
        # Extract @mentions
        mentions = re.findall(r'@(\w+)', content)
        tags.extend([f"mention:{m}" for m in mentions])
        
        # Extract mentioned technologies/tools
        tech_keywords = [
            "python", "javascript", "react", "docker", "kubernetes",
            "aws", "azure", "gcp", "api", "database", "frontend",
            "backend", "ci/cd", "testing", "security", "authentication",
            "payment", "login", "deployment", "production", "staging"
        ]
        for tech in tech_keywords:
            if tech in content:
                tags.append(tech)
        
        # Extract mentioned projects or features
        project_pattern = r"(?:project|feature|module|component|pr|pull request)[:;\s]+(?:#)?(\w+)"
        projects = re.findall(project_pattern, content, re.IGNORECASE)
        tags.extend([f"project:{p}" for p in projects])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_tags.append(tag)
        
        return unique_tags
    
    def _extract_context(self, email_data: Dict[str, Any], body: str) -> Dict[str, Any]:
        """Extract additional context from email"""
        context = {}
        
        # Check if it's a reply or forward
        headers = email_data.get("message", {}).get("headers", {})
        if headers.get("in-reply-to"):
            context["is_reply"] = True
            context["thread_id"] = headers["in-reply-to"]
        
        # Extract URLs with improved pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+(?:[/?#][^\s<>"{}|\\^`\[\]]*)?'
        urls = re.findall(url_pattern, body)
        if urls:
            context["referenced_urls"] = urls
        
        # Extract any code blocks or technical content
        code_blocks = re.findall(r'```[\s\S]*?```', body)
        if code_blocks:
            context["has_code"] = True
            context["code_blocks_count"] = len(code_blocks)
        
        # Extract mentioned usernames or emails
        mentions = re.findall(r'@(\w+)', body)
        emails = re.findall(r'\b[\w.-]+@[\w.-]+\.\w+\b', body)
        if mentions or emails:
            context["mentions"] = list(set(mentions + emails))
        
        # Extract PR/Issue numbers
        pr_issues = re.findall(r'(?:#|PR|pr|issue)\s*(\d+)', body)
        if pr_issues:
            context["referenced_items"] = list(set(pr_issues))
        
        return context
    
    def _remove_email_artifacts(self, text: str) -> str:
        """Remove common email signatures and artifacts"""
        # Remove quoted text
        text = re.sub(r'^>.*$', "", text, flags=re.MULTILINE)
        
        # Remove common signature patterns
        signature_patterns = [
            r'--\s*\n.*',  # Standard email signature delimiter
            r'(?:Best regards|Sincerely|Thanks|Regards|Cheers),?\s*\n.*',
            r'Sent from my.*',
            r'This email and any attachments.*',
            r'CONFIDENTIAL.*'
        ]
        
        for pattern in signature_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
        
        return text.strip()
    
    def _extract_cc_list(self, headers: Dict[str, str]) -> List[str]:
        """Extract CC recipients from headers"""
        cc = headers.get("cc", "")
        if cc:
            # Parse comma-separated emails
            return [email.strip() for email in cc.split(",") if email.strip()]
        return []
    
    def _extract_attachments(self, email_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information"""
        attachments = []
        
        # Check for attachments in various formats
        if "attachments" in email_data:
            for attachment in email_data["attachments"]:
                attachments.append({
                    "filename": attachment.get("filename", "unknown"),
                    "content_type": attachment.get("content-type", "application/octet-stream"),
                    "size": attachment.get("size", 0)
                })
        
        return attachments
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp from various formats"""
        try:
            # Try Unix timestamp first
            if timestamp_str.isdigit():
                return datetime.fromtimestamp(int(timestamp_str))
            else:
                # Try dateutil parser
                return date_parser.parse(timestamp_str)
        except:
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return datetime.utcnow()
    
    def _create_fallback_task(self, email_data: Dict[str, Any], error: str) -> AgentTask:
        """Create a basic task when parsing fails"""
        return AgentTask(
            title="Unparsed Email Task",
            description=f"Failed to parse email: {error}\n\nOriginal content:\n{json.dumps(email_data, indent=2)}",
            task_type=TaskType.GENERAL,
            priority=TaskPriority.MEDIUM,
            agent_assignment=AgentAssignment(
                primary_agent="general_01",
                reason="Fallback assignment due to parsing error"
            ),
            processing_notes=[f"Parsing error: {error}"]
        )