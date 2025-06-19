#!/usr/bin/env python3
"""
Test suite for the Email Agent webhook and security features.
Run with: python test_email_agent.py
"""

import os
import sys
import hmac
import hashlib
import json
import time
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.email_agent import verify_mailgun_signature, verify_timestamp

class EmailAgentTester:
    def __init__(self, signing_key="test-signing-key"):
        self.signing_key = signing_key
        # Set environment variable for testing
        os.environ["MAILGUN_SIGNING_KEY"] = signing_key
        
    def generate_valid_signature(self, timestamp=None):
        """Generate a valid Mailgun signature for testing."""
        if timestamp is None:
            timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        
        token = "test-token-" + str(int(time.time()))
        message = f"{timestamp}{token}".encode('utf-8')
        key = self.signing_key.encode('utf-8')
        
        signature = hmac.new(key=key, msg=message, digestmod=hashlib.sha256).hexdigest()
        
        return {
            "token": token,
            "timestamp": timestamp,
            "signature": signature
        }
    
    def test_signature_verification(self):
        """Test the signature verification function."""
        print("\n🔐 Testing Signature Verification...")
        
        # Test 1: Valid signature
        sig_data = self.generate_valid_signature()
        result = verify_mailgun_signature(
            sig_data["token"],
            sig_data["timestamp"],
            sig_data["signature"]
        )
        print(f"✅ Valid signature test: {'PASSED' if result else 'FAILED'}")
        
        # Test 2: Invalid signature
        result = verify_mailgun_signature(
            sig_data["token"],
            sig_data["timestamp"],
            "invalid-signature"
        )
        print(f"✅ Invalid signature test: {'PASSED' if not result else 'FAILED'}")
        
        # Test 3: Wrong token
        wrong_token_result = verify_mailgun_signature(
            "wrong-token",
            sig_data["timestamp"],
            sig_data["signature"]
        )
        print(f"✅ Wrong token test: {'PASSED' if not wrong_token_result else 'FAILED'}")
        
    def test_timestamp_verification(self):
        """Test the timestamp replay attack protection."""
        print("\n⏰ Testing Timestamp Verification...")
        
        # Test 1: Current timestamp (valid)
        current_ts = str(int(datetime.now(timezone.utc).timestamp()))
        is_valid, error = verify_timestamp(current_ts)
        print(f"✅ Current timestamp test: {'PASSED' if is_valid else 'FAILED'}")
        
        # Test 2: Old timestamp (replay attack)
        old_ts = str(int(datetime.now(timezone.utc).timestamp()) - 150)  # 150 seconds old
        is_valid, error = verify_timestamp(old_ts)
        print(f"✅ Old timestamp test: {'PASSED' if not is_valid else 'FAILED'}")
        if error:
            print(f"   Error message: {error}")
        
        # Test 3: Future timestamp (should be valid within threshold)
        future_ts = str(int(datetime.now(timezone.utc).timestamp()) + 60)  # 60 seconds future
        is_valid, error = verify_timestamp(future_ts)
        print(f"✅ Future timestamp test: {'PASSED' if is_valid else 'FAILED'}")
        
        # Test 4: Invalid format
        is_valid, error = verify_timestamp("not-a-timestamp")
        print(f"✅ Invalid format test: {'PASSED' if not is_valid else 'FAILED'}")
        if error:
            print(f"   Error message: {error}")
    
    def generate_sample_webhook_payload(self):
        """Generate a sample Mailgun webhook payload."""
        sig_data = self.generate_valid_signature()
        
        return {
            "signature": sig_data,
            "event-data": {
                "event": "delivered",
                "timestamp": sig_data["timestamp"],
                "message": {
                    "headers": {
                        "from": "sender@example.com",
                        "subject": "Test Email",
                        "message-id": "<test-message-id@mailgun.org>"
                    },
                    "recipients": ["recipient@example.com"],
                    "body-plain": "This is a test email body."
                }
            }
        }
    
    def print_sample_webhook(self):
        """Print a sample webhook payload for testing."""
        print("\n📧 Sample Mailgun Webhook Payload:")
        payload = self.generate_sample_webhook_payload()
        print(json.dumps(payload, indent=2))
        
        print("\n🔧 cURL command to test the webhook:")
        print(f"""
curl -X POST http://localhost:5000/api/email-agent/webhooks/mailgun \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(payload)}'
        """)

def main():
    print("=" * 80)
    print("EMAIL AGENT TEST SUITE")
    print("=" * 80)
    
    tester = EmailAgentTester()
    
    # Run tests
    tester.test_signature_verification()
    tester.test_timestamp_verification()
    tester.print_sample_webhook()
    
    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80)

if __name__ == "__main__":
    main()