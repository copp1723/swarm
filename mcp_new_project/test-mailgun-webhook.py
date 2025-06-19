#!/usr/bin/env python3
"""
Mailgun Webhook Test Script
Tests the webhook endpoint and email parsing functionality
"""

import requests
import hashlib
import hmac
import time
import json
from datetime import datetime

# Configuration - Update these values
WEBHOOK_URL = "http://localhost:8000/api/email-agent/webhooks/mailgun"  # Change to your ngrok URL
SIGNING_KEY = "your-mailgun-signing-key"  # Get from Mailgun dashboard

def generate_signature(timestamp, token, signing_key):
    """Generate Mailgun webhook signature"""
    message = f"{timestamp}{token}".encode()
    signature = hmac.new(
        signing_key.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature

def test_webhook_accessibility():
    """Test if webhook endpoint is accessible"""
    print("🔍 Testing webhook accessibility...")
    try:
        response = requests.post(WEBHOOK_URL, timeout=5)
        print(f"✅ Webhook reachable - Status: {response.status_code}")
        print(f"   Response: {response.text[:100]}...")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Webhook not reachable: {e}")
        return False

def test_webhook_validation():
    """Test webhook signature validation"""
    print("\n🔐 Testing signature validation...")
    
    # Test with invalid signature
    response = requests.post(WEBHOOK_URL, data={
        "timestamp": "1234567890",
        "token": "test-token",
        "signature": "invalid-signature"
    })
    
    if response.status_code == 400:
        print("✅ Invalid signature correctly rejected")
    else:
        print(f"⚠️  Unexpected response for invalid signature: {response.status_code}")

def test_valid_webhook():
    """Test with valid webhook data"""
    print("\n📧 Testing valid webhook...")
    
    timestamp = str(int(time.time()))
    token = "test-token-" + timestamp
    signature = generate_signature(timestamp, token, SIGNING_KEY)
    
    # Simulate Mailgun webhook data
    webhook_data = {
        "signature": {
            "timestamp": timestamp,
            "token": token,
            "signature": signature
        },
        "event-data": {
            "event": "stored",
            "timestamp": float(timestamp),
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Test Task: Debug webhook"
                },
                "recipients": ["mailagent@onerylie.com"],
                "body-plain": "Priority: High\nThis is a test task for webhook debugging."
            }
        }
    }
    
    response = requests.post(
        WEBHOOK_URL,
        data={
            "timestamp": timestamp,
            "token": token,
            "signature": signature,
            **webhook_data
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        print("✅ Valid webhook accepted!")
        data = response.json()
        if "task_id" in data:
            print(f"📋 Task created with ID: {data['task_id']}")
    else:
        print("❌ Webhook rejected")

def test_calendar_invite_webhook():
    """Test webhook with calendar invite simulation"""
    print("\n📅 Testing calendar invite webhook...")
    
    timestamp = str(int(time.time()))
    token = "calendar-test-" + timestamp
    signature = generate_signature(timestamp, token, SIGNING_KEY)
    
    # ICS file content
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test@onerylie.com
DTSTAMP:20240120T120000Z
DTSTART:20240125T140000Z
DTEND:20240125T150000Z
SUMMARY:Team Planning Meeting
DESCRIPTION:Quarterly planning session
LOCATION:Conference Room A
END:VEVENT
END:VCALENDAR"""
    
    webhook_data = {
        "timestamp": timestamp,
        "token": token,
        "signature": signature,
        "event-data": {
            "event": "stored",
            "timestamp": float(timestamp),
            "message": {
                "headers": {
                    "from": "manager@example.com",
                    "subject": "Meeting: Team Planning Session"
                },
                "recipients": ["mailagent@onerylie.com"],
                "body-plain": "Please add this meeting to the calendar.",
                "attachments": [{
                    "filename": "meeting.ics",
                    "content-type": "text/calendar",
                    "size": len(ics_content)
                }]
            }
        }
    }
    
    response = requests.post(WEBHOOK_URL, json=webhook_data)
    
    print(f"Response Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Calendar invite webhook processed!")
    else:
        print(f"Response: {response.text}")

def main():
    print("🚀 Mailgun Webhook Test Suite")
    print(f"📍 Testing webhook at: {WEBHOOK_URL}")
    print(f"🔑 Using signing key: {'*' * 10 + SIGNING_KEY[-4:] if len(SIGNING_KEY) > 4 else 'NOT SET'}")
    
    if SIGNING_KEY == "your-mailgun-signing-key":
        print("\n⚠️  WARNING: Update SIGNING_KEY with your actual Mailgun webhook signing key!")
        print("   Get it from: Mailgun Dashboard → Settings → Webhooks → HTTP webhook signing key")
    
    # Run tests
    if test_webhook_accessibility():
        test_webhook_validation()
        
        if SIGNING_KEY != "your-mailgun-signing-key":
            test_valid_webhook()
            test_calendar_invite_webhook()
    
    print("\n✅ Test suite complete!")
    print("\n📝 Next steps:")
    print("1. Update WEBHOOK_URL with your ngrok URL")
    print("2. Update SIGNING_KEY from Mailgun dashboard")
    print("3. Configure Mailgun route to forward to your webhook URL")
    print("4. Send a real email to mailagent@onerylie.com")

if __name__ == "__main__":
    main()