"""
Notification Service using Apprise
Handles alerts and notifications for critical system events
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json

import apprise
from apprise import AppriseAsset, NotifyType, NotifyFormat

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Unified notification service using Apprise.
    Supports multiple notification channels.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize notification service.
        
        Args:
            config: Configuration for notification channels
        """
        self.apprise = apprise.Apprise()
        self.config = config or {}
        self._setup_channels()
        
    def _setup_channels(self):
        """Configure notification channels from config or environment."""
        import os
        
        # Email notifications
        if email_url := os.environ.get('NOTIFICATION_EMAIL_URL'):
            self.apprise.add(email_url)
            logger.info("Email notification channel configured")
        
        # Slack notifications
        if slack_webhook := os.environ.get('NOTIFICATION_SLACK_WEBHOOK'):
            self.apprise.add(f"slack://{slack_webhook}")
            logger.info("Slack notification channel configured")
        
        # Discord notifications
        if discord_webhook := os.environ.get('NOTIFICATION_DISCORD_WEBHOOK'):
            self.apprise.add(discord_webhook)
            logger.info("Discord notification channel configured")
        
        # Telegram notifications
        if telegram_token := os.environ.get('NOTIFICATION_TELEGRAM_TOKEN'):
            chat_id = os.environ.get('NOTIFICATION_TELEGRAM_CHAT_ID')
            if chat_id:
                self.apprise.add(f"tgram://{telegram_token}/{chat_id}")
                logger.info("Telegram notification channel configured")
        
        # PagerDuty for critical alerts
        if pagerduty_key := os.environ.get('NOTIFICATION_PAGERDUTY_KEY'):
            self.apprise.add(f"pagerduty://{pagerduty_key}")
            logger.info("PagerDuty notification channel configured")
        
        # Custom webhook
        if webhook_url := os.environ.get('NOTIFICATION_WEBHOOK_URL'):
            self.apprise.add(webhook_url)
            logger.info("Custom webhook notification channel configured")
        
        # Add channels from config
        for channel_url in self.config.get('channels', []):
            self.apprise.add(channel_url)
            
    async def send_notification(
        self,
        title: str,
        body: str,
        notify_type: NotifyType = NotifyType.INFO,
        attach: Optional[Union[str, List[str]]] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Send notification through configured channels.
        
        Args:
            title: Notification title
            body: Notification body
            notify_type: Type of notification (INFO, SUCCESS, WARNING, FAILURE)
            attach: File attachments
            tags: Target specific channels by tag
            
        Returns:
            Success status
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.apprise.notify,
                body,
                title,
                notify_type,
                attach,
                NotifyFormat.MARKDOWN,
                tags
            )
            
            if result:
                logger.info(f"Notification sent: {title}")
            else:
                logger.error(f"Failed to send notification: {title}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def send_critical_alert(
        self,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Send critical alert notification.
        
        Args:
            title: Alert title
            message: Alert message
            details: Additional details
            tags: Target specific channels
            
        Returns:
            Success status
        """
        # Format the alert body
        body_parts = [
            f"🚨 **CRITICAL ALERT** 🚨",
            f"",
            f"**Message:** {message}",
            f"**Time:** {datetime.utcnow().isoformat()}Z",
        ]
        
        if details:
            body_parts.extend([
                f"",
                f"**Details:**",
                "```json",
                json.dumps(details, indent=2),
                "```"
            ])
        
        body = "\n".join(body_parts)
        
        # Send to critical channels (tagged as 'critical')
        critical_tags = tags or []
        if 'critical' not in critical_tags:
            critical_tags.append('critical')
        
        return await self.send_notification(
            title=f"[CRITICAL] {title}",
            body=body,
            notify_type=NotifyType.FAILURE,
            tags=critical_tags
        )
    
    async def send_webhook_failure_alert(
        self,
        webhook_url: str,
        attempts: int,
        error: str
    ) -> bool:
        """
        Send alert for webhook delivery failure.
        
        Args:
            webhook_url: Failed webhook URL
            attempts: Number of attempts made
            error: Error message
            
        Returns:
            Success status
        """
        body = f"""
⚠️ **Webhook Delivery Failed**

**URL:** `{webhook_url}`
**Attempts:** {attempts}
**Error:** {error}
**Time:** {datetime.utcnow().isoformat()}Z

The webhook has exhausted all retry attempts and will not be retried automatically.
Please investigate the endpoint and consider manual intervention.
"""
        
        return await self.send_notification(
            title="Webhook Delivery Failed",
            body=body,
            notify_type=NotifyType.WARNING,
            tags=['webhooks', 'failures']
        )
    
    async def send_task_failure_alert(
        self,
        task_name: str,
        task_id: str,
        error: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send alert for background task failure.
        
        Args:
            task_name: Name of the failed task
            task_id: Task ID
            error: Error message
            context: Additional context
            
        Returns:
            Success status
        """
        body_parts = [
            f"❌ **Background Task Failed**",
            f"",
            f"**Task:** {task_name}",
            f"**ID:** {task_id}",
            f"**Error:** {error}",
            f"**Time:** {datetime.utcnow().isoformat()}Z",
        ]
        
        if context:
            body_parts.extend([
                f"",
                f"**Context:**",
                "```json",
                json.dumps(context, indent=2),
                "```"
            ])
        
        body = "\n".join(body_parts)
        
        return await self.send_notification(
            title=f"Task Failed: {task_name}",
            body=body,
            notify_type=NotifyType.FAILURE,
            tags=['tasks', 'failures']
        )
    
    async def send_security_alert(
        self,
        alert_type: str,
        message: str,
        source_ip: Optional[str] = None,
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send security-related alert.
        
        Args:
            alert_type: Type of security alert
            message: Alert message
            source_ip: Source IP address
            user: User involved
            details: Additional details
            
        Returns:
            Success status
        """
        body_parts = [
            f"🔐 **Security Alert: {alert_type}**",
            f"",
            f"**Message:** {message}",
            f"**Time:** {datetime.utcnow().isoformat()}Z",
        ]
        
        if source_ip:
            body_parts.append(f"**Source IP:** {source_ip}")
        
        if user:
            body_parts.append(f"**User:** {user}")
        
        if details:
            body_parts.extend([
                f"",
                f"**Additional Details:**",
                "```json",
                json.dumps(details, indent=2),
                "```"
            ])
        
        body = "\n".join(body_parts)
        
        return await self.send_notification(
            title=f"[SECURITY] {alert_type}",
            body=body,
            notify_type=NotifyType.WARNING,
            tags=['security', 'critical']
        )
    
    async def send_performance_alert(
        self,
        metric: str,
        current_value: float,
        threshold: float,
        unit: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send performance/metrics alert.
        
        Args:
            metric: Metric name
            current_value: Current metric value
            threshold: Threshold that was exceeded
            unit: Metric unit
            details: Additional details
            
        Returns:
            Success status
        """
        body = f"""
📊 **Performance Alert**

**Metric:** {metric}
**Current Value:** {current_value} {unit}
**Threshold:** {threshold} {unit}
**Exceeded By:** {current_value - threshold} {unit}
**Time:** {datetime.utcnow().isoformat()}Z
"""
        
        if details:
            body += f"\n**Details:**\n```json\n{json.dumps(details, indent=2)}\n```"
        
        return await self.send_notification(
            title=f"Performance Alert: {metric}",
            body=body,
            notify_type=NotifyType.WARNING,
            tags=['performance', 'metrics']
        )
    
    async def send_success_notification(
        self,
        operation: str,
        message: str,
        stats: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send success notification for completed operations.
        
        Args:
            operation: Operation name
            message: Success message
            stats: Operation statistics
            
        Returns:
            Success status
        """
        body_parts = [
            f"✅ **Operation Completed Successfully**",
            f"",
            f"**Operation:** {operation}",
            f"**Message:** {message}",
            f"**Time:** {datetime.utcnow().isoformat()}Z",
        ]
        
        if stats:
            body_parts.extend([
                f"",
                f"**Statistics:**",
            ])
            for key, value in stats.items():
                body_parts.append(f"- {key}: {value}")
        
        body = "\n".join(body_parts)
        
        return await self.send_notification(
            title=f"Success: {operation}",
            body=body,
            notify_type=NotifyType.SUCCESS,
            tags=['success']
        )
    
    def add_channel(self, url: str, tag: Optional[str] = None) -> bool:
        """
        Add a notification channel dynamically.
        
        Args:
            url: Apprise URL for the channel
            tag: Optional tag for the channel
            
        Returns:
            Success status
        """
        try:
            result = self.apprise.add(url, tag=tag)
            if result:
                logger.info(f"Added notification channel: {url}")
            return result
        except Exception as e:
            logger.error(f"Failed to add notification channel: {e}")
            return False
    
    def remove_channel(self, url: str) -> bool:
        """
        Remove a notification channel.
        
        Args:
            url: Channel URL to remove
            
        Returns:
            Success status
        """
        try:
            self.apprise.remove(url)
            logger.info(f"Removed notification channel: {url}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove notification channel: {e}")
            return False
    
    def get_channels(self) -> List[str]:
        """Get list of configured notification channels."""
        return [str(server) for server in self.apprise]


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the notification service singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


# Convenience functions
async def send_critical_alert(title: str, message: str, **kwargs):
    """Send a critical alert through the notification service."""
    service = get_notification_service()
    return await service.send_critical_alert(title, message, **kwargs)


async def send_notification(title: str, body: str, **kwargs):
    """Send a general notification through the notification service."""
    service = get_notification_service()
    return await service.send_notification(title, body, **kwargs)