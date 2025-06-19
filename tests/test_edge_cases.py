#!/usr/bin/env python3
"""
Edge Case and Error Scenario Tests for Email Agent
Tests system behavior with invalid, malformed, and edge case inputs
"""

import os
import sys
import json
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.email_parser import EmailParser
from models.agent_task import TaskType, TaskPriority, AgentAssignment
from config.config_loader import get_config_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EdgeCaseTestSuite:
    """Test suite for edge cases and error scenarios"""
    
    def __init__(self):
        self.parser = EmailParser()
        self.config = get_config_loader()
        self.passed = 0
        self.failed = 0
    
    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        try:
            logger.info(f"\n📋 Testing: {test_name}")
            result = test_func()
            if result:
                logger.info("✅ PASSED")
                self.passed += 1
            else:
                logger.error("❌ FAILED")
                self.failed += 1
            return result
        except Exception as e:
            logger.error(f"❌ FAILED with exception: {str(e)}")
            self.failed += 1
            return False
    
    def test_empty_email(self):
        """Test parsing completely empty email"""
        email_data = {
            "message": {
                "headers": {},
                "stripped-text": ""
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should create a fallback task
        assert task is not None
        assert task.title != ""
        assert task.task_type == TaskType.GENERAL
        assert task.priority == TaskPriority.MEDIUM
        return True
    
    def test_no_subject(self):
        """Test email with no subject"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com"
                },
                "stripped-text": "This is an email without a subject line."
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        assert task is not None
        assert task.title != ""  # Should extract from body
        assert "No Subject" in task.email_metadata.subject
        return True
    
    def test_very_long_email(self):
        """Test parsing very long email body"""
        long_body = "This is a test. " * 1000  # ~15,000 characters
        
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Long email test"
                },
                "stripped-text": long_body
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        assert task is not None
        assert len(task.description) > 0
        assert len(task.description) < len(long_body)  # Should be truncated
        return True
    
    def test_multiple_priorities(self):
        """Test email with conflicting priority indicators"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Low priority but URGENT task"
                },
                "stripped-text": "This is not urgent, please handle when you have time. Actually, it's critical!"
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should prioritize higher priority keywords
        assert task.priority == TaskPriority.URGENT
        return True
    
    def test_ambiguous_task_type(self):
        """Test email that could match multiple task types"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Review the bug in the new feature documentation"
                },
                "stripped-text": "Please review the documentation for the new feature. There's a bug in the example code."
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should pick the first matching type
        assert task.task_type in [TaskType.CODE_REVIEW, TaskType.BUG_REPORT, TaskType.DOCUMENTATION]
        return True
    
    def test_malformed_deadline(self):
        """Test email with ambiguous deadline"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Task with unclear deadline"
                },
                "stripped-text": "Please complete this by yesterday. Just kidding, do it by the 32nd of this month."
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should handle gracefully without crashing
        assert task is not None
        # Deadline should be None or a valid date
        if task.requirements.deadline:
            assert isinstance(task.requirements.deadline, datetime)
        return True
    
    def test_circular_dependencies(self):
        """Test email with circular dependency description"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Complex task dependencies"
                },
                "stripped-text": "Task A depends on Task B. Task B depends on Task C. Task C depends on Task A."
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should parse without infinite loops
        assert task is not None
        assert len(task.requirements.dependencies) >= 0
        return True
    
    def test_special_characters(self):
        """Test email with special characters and emojis"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "🔥 URGENT: Fix the <script> bug! 🐛"
                },
                "stripped-text": "The system is showing: Error: Invalid character '\\x00' in input"
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should handle special characters gracefully
        assert task is not None
        assert task.priority == TaskPriority.URGENT
        assert task.task_type == TaskType.BUG_REPORT
        return True
    
    def test_reply_chain(self):
        """Test email that's part of a reply chain"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Re: Re: Fw: Original task",
                    "in-reply-to": "<original@example.com>"
                },
                "stripped-text": "> Previous message\n> More previous text\n\nHere's my actual response about the bug."
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should extract relevant content
        assert task is not None
        assert "bug" in task.description.lower()
        assert task.context.get("is_reply") is True
        return True
    
    def test_attachment_references(self):
        """Test email referencing attachments"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Bug report with screenshots"
                },
                "stripped-text": "See attached screenshots for the error. The files error1.png and error2.png show the issue.",
                "attachments": [
                    {"filename": "error1.png", "size": 102400},
                    {"filename": "error2.png", "size": 204800}
                ]
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should note attachments
        assert task is not None
        assert len(task.email_metadata.attachments) == 2
        return True
    
    def test_config_reload(self):
        """Test configuration reload functionality"""
        # Get initial config
        initial_keywords = self.config.get_priority_keywords('urgent')
        
        # Reload config
        self.config.reload_configs()
        
        # Get config again
        reloaded_keywords = self.config.get_priority_keywords('urgent')
        
        # Should have same content
        assert initial_keywords == reloaded_keywords
        return True
    
    def test_missing_agent_assignment(self):
        """Test task type with no configured agent"""
        # Create a task type that might not have assignment
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Unknown task type"
                },
                "stripped-text": "This is a completely new type of request that doesn't match any patterns."
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should fall back to general agent
        assert task.agent_assignment.primary_agent == "general_01"
        return True
    
    def test_concurrent_priority_keywords(self):
        """Test all priority levels in one email"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Task priority test"
                },
                "stripped-text": "This is urgent but also low priority when you have time, yet it's critical and no rush."
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should pick highest priority
        assert task.priority == TaskPriority.URGENT
        return True
    
    def test_future_timestamp(self):
        """Test email with future timestamp"""
        future_time = datetime.utcnow() + timedelta(days=1)
        
        email_data = {
            "timestamp": str(int(future_time.timestamp())),
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Time traveler's email"
                },
                "stripped-text": "This email is from the future!"
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should handle gracefully
        assert task is not None
        return True
    
    def test_recursive_lists(self):
        """Test deeply nested list extraction"""
        email_data = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "Complex requirements"
                },
                "stripped-text": """
                Requirements:
                1. Main task
                   a. Subtask 1
                      - Sub-subtask 1.1
                      - Sub-subtask 1.2
                   b. Subtask 2
                2. Another main task
                   - Simple subtask
                """
            }
        }
        
        task = self.parser.parse_email(email_data)
        
        # Should extract some requirements
        assert task is not None
        assert len(task.requirements.deliverables) > 0 or len(task.requirements.success_criteria) > 0
        return True


def main():
    """Run all edge case tests"""
    logger.info("🧪 EMAIL AGENT EDGE CASE TEST SUITE")
    logger.info("="*60)
    
    suite = EdgeCaseTestSuite()
    
    # Define all tests
    tests = [
        ("Empty Email", suite.test_empty_email),
        ("No Subject", suite.test_no_subject),
        ("Very Long Email", suite.test_very_long_email),
        ("Multiple Priorities", suite.test_multiple_priorities),
        ("Ambiguous Task Type", suite.test_ambiguous_task_type),
        ("Malformed Deadline", suite.test_malformed_deadline),
        ("Circular Dependencies", suite.test_circular_dependencies),
        ("Special Characters", suite.test_special_characters),
        ("Reply Chain", suite.test_reply_chain),
        ("Attachment References", suite.test_attachment_references),
        ("Config Reload", suite.test_config_reload),
        ("Missing Agent Assignment", suite.test_missing_agent_assignment),
        ("Concurrent Priority Keywords", suite.test_concurrent_priority_keywords),
        ("Future Timestamp", suite.test_future_timestamp),
        ("Recursive Lists", suite.test_recursive_lists)
    ]
    
    # Run all tests
    for test_name, test_func in tests:
        suite.run_test(test_name, test_func)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total Tests: {suite.passed + suite.failed}")
    logger.info(f"Passed: {suite.passed}")
    logger.info(f"Failed: {suite.failed}")
    
    if suite.failed == 0:
        logger.info("\n🎉 All edge case tests passed!")
    else:
        logger.info(f"\n⚠️ {suite.failed} tests failed")
    
    return suite.failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)