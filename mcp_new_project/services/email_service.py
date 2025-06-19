"""
Email Service
Handles email sending through multiple providers with Apprise integration
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import hmac
import hashlib

from utils.notification_service import get_notification_service
from utils.tenacity_retry import retry_api_call
from services.resilient_http_client import ResilientHTTPClient

logger = logging.getLogger(__name__)


class EmailService:
    """
    Unified email service supporting multiple providers.
    Primary: Mailgun API
    Fallback: Apprise notifications
    """
    
    def __init__(self):
        """Initialize email service."""
        self.mailgun_api_key = os.environ.get('MAILGUN_API_KEY')
        self.mailgun_domain = os.environ.get('MAILGUN_DOMAIN', 'mg.example.com')
        self.mailgun_base_url = os.environ.get('MAILGUN_BASE_URL', 'https://api.mailgun.net/v3')
        self.notification_service = get_notification_service()
        self.from_email = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        # Initialize HTTP client for Mailgun
        if self.mailgun_api_key:
            self.http_client = ResilientHTTPClient(
                base_url=self.mailgun_base_url,
                headers={
                    'Authorization': f'Basic {self._encode_mailgun_auth()}'
                }
            )
        else:
            self.http_client = None
            logger.warning("Mailgun API key not configured, using Apprise fallback")
    
    def _encode_mailgun_auth(self) -> str:
        """Encode Mailgun API authentication."""
        import base64
        auth_string = f"api:{self.mailgun_api_key}"
        return base64.b64encode(auth_string.encode()).decode()
    
    @retry_api_call(max_attempts=3)
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send email using available provider.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            html: Optional HTML body
            from_email: Sender email (defaults to configured)
            reply_to: Reply-to address
            cc: CC recipients
            bcc: BCC recipients
            tags: Email tags for tracking
            headers: Additional headers
            attachments: List of attachments
            
        Returns:
            Send result with message ID
        """
        try:
            # Try Mailgun first if configured
            if self.http_client and self.mailgun_api_key:
                return await self._send_via_mailgun(
                    to=to,
                    subject=subject,
                    body=body,
                    html=html,
                    from_email=from_email,
                    reply_to=reply_to,
                    cc=cc,
                    bcc=bcc,
                    tags=tags,
                    headers=headers,
                    attachments=attachments
                )
            else:
                # Fallback to Apprise
                return await self._send_via_apprise(
                    to=to,
                    subject=subject,
                    body=body
                )
                
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            # Last resort - send notification about email failure
            await self.notification_service.send_critical_alert(
                title="Email Send Failed",
                message=f"Failed to send email to {to}",
                details={
                    'subject': subject,
                    'error': str(e)
                }
            )
            raise
    
    async def _send_via_mailgun(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send email via Mailgun API."""
        # Prepare form data
        data = {
            'from': from_email or self.from_email,
            'to': to,
            'subject': subject,
            'text': body
        }
        
        if html:
            data['html'] = html
        
        if reply_to:
            data['h:Reply-To'] = reply_to
        
        if cc:
            data['cc'] = ','.join(cc)
        
        if bcc:
            data['bcc'] = ','.join(bcc)
        
        if tags:
            # Mailgun limits to 3 tags
            for i, tag in enumerate(tags[:3]):
                data[f'o:tag'] = tag
        
        # Add custom headers
        if headers:
            for key, value in headers.items():
                data[f'h:{key}'] = value
        
        # Add tracking headers
        data['o:tracking'] = 'yes'
        data['o:tracking-clicks'] = 'yes'
        data['o:tracking-opens'] = 'yes'
        
        # Handle attachments
        files = None
        if attachments:
            files = []
            for attachment in attachments:
                files.append(
                    ('attachment', (
                        attachment['filename'],
                        attachment['content'],
                        attachment.get('content_type', 'application/octet-stream')
                    ))
                )
        
        # Send via Mailgun
        response = await self.http_client.post(
            f"/{self.mailgun_domain}/messages",
            data=data,
            files=files
        )
        
        result = response.json()
        
        logger.info(f"Email sent via Mailgun: {result.get('id')}")
        
        return {
            'success': True,
            'provider': 'mailgun',
            'message_id': result.get('id'),
            'queued_at': datetime.utcnow().isoformat()
        }
    
    async def _send_via_apprise(
        self,
        to: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """Send email via Apprise as fallback."""
        # Format for Apprise
        formatted_body = f"""
**To:** {to}
**Subject:** {subject}

{body}
"""
        
        success = await self.notification_service.send_notification(
            title=f"Email: {subject}",
            body=formatted_body,
            tags=['email']
        )
        
        if success:
            logger.info(f"Email sent via Apprise to {to}")
            return {
                'success': True,
                'provider': 'apprise',
                'message_id': f"apprise_{datetime.utcnow().timestamp()}",
                'queued_at': datetime.utcnow().isoformat()
            }
        else:
            return {
                'success': False,
                'error': 'Failed to send via Apprise'
            }
    
    def verify_webhook_signature(
        self,
        signature: str,
        timestamp: str,
        token: str,
        signing_key: Optional[str] = None
    ) -> bool:
        """
        Verify Mailgun webhook signature.
        
        Args:
            signature: Signature from webhook
            timestamp: Timestamp from webhook
            token: Token from webhook
            signing_key: Signing key (defaults to env var)
            
        Returns:
            True if signature is valid
        """
        signing_key = signing_key or os.environ.get('MAILGUN_SIGNING_KEY')
        if not signing_key:
            logger.warning("No Mailgun signing key configured")
            return False
        
        # Construct the signature data
        signed_data = f"{timestamp}{token}".encode()
        
        # Calculate expected signature
        expected_signature = hmac.new(
            signing_key.encode(),
            signed_data,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
    
    async def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        template_subject: str,
        template_body: str,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Send bulk emails with personalization.
        
        Args:
            recipients: List of recipient dicts with email and variables
            template_subject: Subject template with variables
            template_body: Body template with variables
            batch_size: Number of emails per batch
            
        Returns:
            Bulk send results
        """
        results = []
        errors = []
        
        # Process in batches
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]
            
            for recipient in batch:
                try:
                    # Personalize content
                    email = recipient['email']
                    variables = recipient.get('variables', {})
                    
                    subject = template_subject.format(**variables)
                    body = template_body.format(**variables)
                    
                    # Send email
                    result = await self.send_email(
                        to=email,
                        subject=subject,
                        body=body,
                        tags=['bulk']
                    )
                    
                    results.append({
                        'email': email,
                        'status': 'sent',
                        'message_id': result.get('message_id')
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to send to {recipient.get('email')}: {e}")
                    errors.append({
                        'email': recipient.get('email'),
                        'error': str(e)
                    })
            
            # Small delay between batches
            import asyncio
            await asyncio.sleep(1)
        
        return {
            'total': len(recipients),
            'sent': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        }
    
    async def get_email_stats(self) -> Dict[str, Any]:
        """Get email sending statistics."""
        # This would integrate with Mailgun's stats API
        # For now, return mock stats
        return {
            'provider': 'mailgun' if self.mailgun_api_key else 'apprise',
            'stats': {
                'sent_today': 0,
                'sent_this_week': 0,
                'sent_this_month': 0
            }
        }