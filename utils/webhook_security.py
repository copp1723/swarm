"""Webhook security utilities for request signing and verification"""
import hmac
import hashlib
import time
import json
from typing import Union, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


class WebhookSecurity:
    """Handles webhook signature generation and verification"""
    
    def __init__(self, secret_key: str):
        """
        Initialize webhook security with a secret key
        
        Args:
            secret_key: Secret key for HMAC signing
        """
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
    
    def generate_signature(self, payload: Union[str, dict], timestamp: Optional[int] = None) -> tuple:
        """
        Generate HMAC signature for webhook payload
        
        Args:
            payload: The webhook payload (string or dict)
            timestamp: Unix timestamp (current time if not provided)
            
        Returns:
            Tuple of (signature, timestamp)
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # Convert payload to string if dict
        if isinstance(payload, dict):
            payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        else:
            payload_str = payload
        
        # Create message: timestamp.payload
        message = f"{timestamp}.{payload_str}".encode()
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key,
            message,
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"Generated webhook signature for timestamp {timestamp}")
        return signature, timestamp
    
    def verify_signature(self, 
                        payload: Union[str, dict], 
                        signature: str, 
                        timestamp: Union[str, int],
                        max_age_seconds: int = 300) -> bool:
        """
        Verify webhook signature and timestamp
        
        Args:
            payload: The webhook payload (string or dict)
            signature: The provided signature to verify
            timestamp: The provided timestamp
            max_age_seconds: Maximum age of request in seconds (default 5 minutes)
            
        Returns:
            True if signature is valid and not expired, False otherwise
        """
        try:
            # Convert timestamp to int
            timestamp_int = int(timestamp)
            
            # Check timestamp age
            current_time = int(time.time())
            age = abs(current_time - timestamp_int)
            
            if age > max_age_seconds:
                logger.warning(f"Webhook timestamp too old: {age} seconds")
                return False
            
            # Generate expected signature
            expected_signature, _ = self.generate_signature(payload, timestamp_int)
            
            # Use constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(expected_signature, signature)
            
            if not is_valid:
                logger.warning("Webhook signature verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def sign_request(self, payload: Union[str, dict]) -> dict:
        """
        Sign a request payload and return headers
        
        Args:
            payload: The request payload
            
        Returns:
            Dict of headers to add to the request
        """
        signature, timestamp = self.generate_signature(payload)
        
        return {
            'X-Webhook-Signature': signature,
            'X-Webhook-Timestamp': str(timestamp),
            'X-Webhook-Version': 'v1'
        }
    
    def verify_request(self, 
                      request_data: Union[str, bytes, dict],
                      headers: dict,
                      max_age_seconds: int = 300) -> bool:
        """
        Verify an incoming webhook request
        
        Args:
            request_data: The request body
            headers: Request headers (case-insensitive dict)
            max_age_seconds: Maximum age of request
            
        Returns:
            True if request is valid, False otherwise
        """
        # Get headers (case-insensitive)
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        signature = headers_lower.get('x-webhook-signature')
        timestamp = headers_lower.get('x-webhook-timestamp')
        
        if not signature or not timestamp:
            logger.warning("Missing webhook signature or timestamp headers")
            return False
        
        # Convert bytes to string if needed
        if isinstance(request_data, bytes):
            request_data = request_data.decode('utf-8')
        
        return self.verify_signature(request_data, signature, timestamp, max_age_seconds)


# Webhook security middleware
def require_webhook_signature(secret_key: str, max_age_seconds: int = 300):
    """
    Flask decorator to require valid webhook signature
    
    Args:
        secret_key: Secret key for signature verification
        max_age_seconds: Maximum age of request
    """
    from functools import wraps
    from flask import request, jsonify
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            webhook_security = WebhookSecurity(secret_key)
            
            # Get request data and headers
            request_data = request.get_data(as_text=True)
            
            if not webhook_security.verify_request(request_data, request.headers, max_age_seconds):
                return jsonify({
                    'error': 'Invalid webhook signature',
                    'message': 'Request signature verification failed'
                }), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# Convenience function for Mailgun webhook verification
def verify_mailgun_webhook(token: str, timestamp: str, signature: str) -> bool:
    """
    Verify Mailgun webhook signature
    
    Mailgun uses a specific format: timestamp + token
    """
    try:
        # Get Mailgun webhook signing key from environment
        import os
        signing_key = os.environ.get('MAILGUN_WEBHOOK_SIGNING_KEY', '')
        
        if not signing_key:
            logger.error("MAILGUN_WEBHOOK_SIGNING_KEY not configured")
            return False
        
        # Mailgun signature format
        message = f"{timestamp}{token}".encode()
        
        expected_signature = hmac.new(
            signing_key.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
        
    except Exception as e:
        logger.error(f"Error verifying Mailgun webhook: {e}")
        return False