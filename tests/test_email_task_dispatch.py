#!/usr/bin/env python3
"""
Test suite for Email Task Parsing and Dispatch
Tests the email parser, task model, and dispatcher functionality
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.email_parser import EmailParser
from services.task_dispatcher import task_dispatcher
from models.agent_task import AgentTask, TaskType, TaskPriority, AgentAssignment


class EmailTaskTester:
    def __init__(self):
        self.parser = EmailParser()
        self.test_results = []
    
    def run_all_tests(self):
        """Run all test cases"""
        print("=" * 80)
        print("EMAIL TASK PARSING & DISPATCH TEST SUITE")
        print("=" * 80)
        
        self.test_basic_email_parsing()
        self.test_priority_detection()
        self.test_task_type_detection()
        self.test_deadline_extraction()
        self.test_agent_assignment()
        self.test_complex_email_parsing()
        self.test_task_dispatch_flow()
        
        self.print_summary()
    
    def test_basic_email_parsing(self):
        """Test basic email parsing functionality"""
        print("\n📧 Testing Basic Email Parsing...")
        
        email_data = {
            "message": {
                "headers": {
                    "from": "john@example.com",
                    "subject": "Please review the new authentication code",
                    "message-id": "<test-123@example.com>"
                },
                "recipients": ["dev@company.com"],
                "body-plain": "Hi team,\n\nCould you please review the authentication module I just pushed? The PR is #234.\n\nThanks,\nJohn"
            },
            "timestamp": str(int(datetime.utcnow().timestamp()))
        }
        
        task = self.parser.parse_email(email_data)
        
        # Verify results
        assert task.title == "Please review the new authentication code", "Title extraction failed"
        assert task.task_type == TaskType.CODE_REVIEW, "Task type detection failed"
        assert task.email_metadata.sender == "john@example.com", "Sender extraction failed"
        assert task.agent_assignment.primary_agent == "coder_01", "Agent assignment failed"
        
        self.test_results.append(("Basic Email Parsing", "PASSED"))
        print("✅ Basic email parsing test passed")
    
    def test_priority_detection(self):
        """Test priority detection from email content"""
        print("\n🚨 Testing Priority Detection...")
        
        test_cases = [
            ("URGENT: Fix production bug", "Critical issue needs immediate attention", TaskPriority.URGENT),
            ("High priority feature request", "This is important for the client", TaskPriority.HIGH),
            ("When you have time, update docs", "No rush on this one", TaskPriority.LOW),
            ("Regular task", "Please complete this task", TaskPriority.MEDIUM)
        ]
        
        all_passed = True
        for subject, body, expected_priority in test_cases:
            email_data = self._create_test_email(subject, body)
            task = self.parser.parse_email(email_data)
            
            if task.priority != expected_priority:
                print(f"❌ Failed: '{subject}' - Expected {expected_priority}, got {task.priority}")
                all_passed = False
            else:
                print(f"✅ Correct priority for: '{subject}'")
        
        self.test_results.append(("Priority Detection", "PASSED" if all_passed else "FAILED"))
    
    def test_task_type_detection(self):
        """Test task type detection from content"""
        print("\n📋 Testing Task Type Detection...")
        
        test_cases = [
            ("Bug in login flow", "Users can't login", TaskType.BUG_REPORT),
            ("Code review needed", "Please review PR", TaskType.CODE_REVIEW),
            ("New feature: Dark mode", "Implement dark mode", TaskType.FEATURE_REQUEST),
            ("Update API docs", "Documentation is outdated", TaskType.DOCUMENTATION),
            ("Deploy to staging", "Ready for deployment", TaskType.DEPLOYMENT),
            ("Investigate performance", "App is slow", TaskType.INVESTIGATION)
        ]
        
        all_passed = True
        for subject, body, expected_type in test_cases:
            email_data = self._create_test_email(subject, body)
            task = self.parser.parse_email(email_data)
            
            if task.task_type != expected_type:
                print(f"❌ Failed: '{subject}' - Expected {expected_type}, got {task.task_type}")
                all_passed = False
            else:
                print(f"✅ Correct type for: '{subject}'")
        
        self.test_results.append(("Task Type Detection", "PASSED" if all_passed else "FAILED"))
    
    def test_deadline_extraction(self):
        """Test deadline extraction from email"""
        print("\n⏰ Testing Deadline Extraction...")
        
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        next_week = now + timedelta(weeks=1)
        
        test_cases = [
            ("Task due tomorrow", f"Please complete by {tomorrow.strftime('%B %d')}", True),
            ("Deadline: next week", "Need this done by next week", True),
            ("Due in 3 days", "Complete within 3 days please", True),
            ("No specific deadline", "Work on this when possible", False)
        ]
        
        all_passed = True
        for subject, body, has_deadline in test_cases:
            email_data = self._create_test_email(subject, body)
            task = self.parser.parse_email(email_data)
            
            if has_deadline:
                if task.requirements.deadline is None:
                    print(f"❌ Failed to extract deadline from: '{subject}'")
                    all_passed = False
                else:
                    print(f"✅ Extracted deadline from: '{subject}' -> {task.requirements.deadline}")
            else:
                if task.requirements.deadline is not None:
                    print(f"❌ False positive deadline in: '{subject}'")
                    all_passed = False
                else:
                    print(f"✅ Correctly no deadline for: '{subject}'")
        
        self.test_results.append(("Deadline Extraction", "PASSED" if all_passed else "FAILED"))
    
    def test_agent_assignment(self):
        """Test agent assignment based on task type"""
        print("\n🤖 Testing Agent Assignment...")
        
        test_cases = [
            (TaskType.CODE_REVIEW, "coder_01", ["tester_01"]),
            (TaskType.BUG_REPORT, "bug_01", ["coder_01", "tester_01"]),
            (TaskType.FEATURE_REQUEST, "product_01", ["coder_01"]),
            (TaskType.DOCUMENTATION, "product_01", []),
            (TaskType.DEPLOYMENT, "devops_01", ["tester_01"])
        ]
        
        all_passed = True
        for task_type, expected_primary, expected_supporting in test_cases:
            assignment = AgentAssignment.from_task_type(task_type)
            
            if assignment.primary_agent != expected_primary:
                print(f"❌ Wrong primary agent for {task_type}: {assignment.primary_agent}")
                all_passed = False
            elif assignment.supporting_agents != expected_supporting:
                print(f"❌ Wrong supporting agents for {task_type}: {assignment.supporting_agents}")
                all_passed = False
            else:
                print(f"✅ Correct assignment for {task_type}")
        
        self.test_results.append(("Agent Assignment", "PASSED" if all_passed else "FAILED"))
    
    def test_complex_email_parsing(self):
        """Test parsing of complex email with multiple elements"""
        print("\n🔧 Testing Complex Email Parsing...")
        
        email_data = {
            "message": {
                "headers": {
                    "from": "manager@company.com",
                    "subject": "URGENT: Fix authentication bug by end of day",
                    "message-id": "<complex-test@company.com>",
                    "cc": "team@company.com, qa@company.com"
                },
                "recipients": ["dev@company.com", "senior-dev@company.com"],
                "body-plain": """Hi team,

We have a critical bug in the authentication system that's affecting production users.

Issue: Users are getting logged out randomly
Impact: 30% of users affected
Priority: URGENT - needs to be fixed by end of day

Deliverables:
- Root cause analysis
- Hotfix for immediate deployment
- Long-term solution proposal

Success Criteria:
- No more random logouts
- All affected users can login normally
- Performance not degraded

Dependencies:
- Need access to production logs
- QA team needs to validate the fix

Please check these URLs for more context:
- Sentry: https://sentry.io/issues/12345
- User reports: https://support.company.com/tickets/6789

Thanks,
Manager

--
Sent from my iPhone"""
            },
            "timestamp": str(int(datetime.utcnow().timestamp()))
        }
        
        task = self.parser.parse_email(email_data)
        
        # Verify comprehensive parsing
        checks = [
            (task.priority == TaskPriority.URGENT, "Priority detection"),
            (task.task_type == TaskType.BUG_REPORT, "Task type detection"),
            (len(task.requirements.deliverables) == 3, "Deliverables extraction"),
            (len(task.requirements.success_criteria) == 3, "Success criteria extraction"),
            (len(task.requirements.dependencies) > 0, "Dependencies extraction"),
            (task.requirements.deadline is not None, "Deadline extraction"),
            (len(task.context.get("referenced_urls", [])) == 2, "URL extraction"),
            (len(task.email_metadata.cc) == 2, "CC extraction"),
            ("authentication" in task.tags, "Tag extraction")
        ]
        
        all_passed = True
        for check, description in checks:
            if not check:
                print(f"❌ Failed: {description}")
                all_passed = False
            else:
                print(f"✅ Passed: {description}")
        
        self.test_results.append(("Complex Email Parsing", "PASSED" if all_passed else "FAILED"))
    
    def test_task_dispatch_flow(self):
        """Test the complete flow from email to dispatch"""
        print("\n🚀 Testing Task Dispatch Flow...")
        
        # Create a test email
        email_data = self._create_test_email(
            "Code review for payment module",
            "Please review the new payment integration code in PR #456"
        )
        
        # Parse email
        task = self.parser.parse_email(email_data)
        print(f"✅ Parsed email into task: {task.task_id}")
        
        # Test queue functionality
        queue_position = task_dispatcher.queue_task(task)
        print(f"✅ Queued task: {queue_position}")
        
        # Test dispatch status check
        status = task_dispatcher.get_dispatch_status(task.task_id)
        print(f"✅ Status check: {status or 'Not yet dispatched'}")
        
        # Note: Actual dispatch would require multi-agent service running
        print("ℹ️  Skipping actual dispatch (requires running services)")
        
        self.test_results.append(("Task Dispatch Flow", "PASSED"))
    
    def _create_test_email(self, subject: str, body: str) -> dict:
        """Helper to create test email data"""
        return {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": subject,
                    "message-id": f"<test-{datetime.now().timestamp()}@example.com>"
                },
                "recipients": ["dev@company.com"],
                "body-plain": body
            },
            "timestamp": str(int(datetime.utcnow().timestamp()))
        }
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for _, result in self.test_results if result == "PASSED")
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            emoji = "✅" if result == "PASSED" else "❌"
            print(f"{emoji} {test_name}: {result}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {total - passed} tests failed")


def demo_email_to_task_api():
    """Demonstrate the Email Agent API endpoints"""
    print("\n" + "=" * 80)
    print("EMAIL AGENT API DEMONSTRATION")
    print("=" * 80)
    
    # Example 1: Parse Email
    print("\n1️⃣ Parse Email API Call:")
    parse_request = {
        "action": "parse_email",
        "parameters": {
            "email_data": {
                "message": {
                    "headers": {
                        "from": "client@example.com",
                        "subject": "Bug: Users can't reset passwords"
                    },
                    "recipients": ["support@company.com"],
                    "body-plain": "Several users reported they can't reset their passwords. The reset email never arrives. This is urgent!"
                }
            }
        }
    }
    print(f"POST /api/email-agent/tasks")
    print(json.dumps(parse_request, indent=2))
    
    # Example 2: Dispatch Task
    print("\n2️⃣ Dispatch Task API Call:")
    dispatch_request = {
        "action": "dispatch_task",
        "parameters": {
            "task": {
                "task_id": "task_12345",
                "title": "Fix password reset functionality",
                "task_type": "bug_report",
                "priority": "urgent",
                "agent_assignment": {
                    "primary_agent": "bug_01",
                    "supporting_agents": ["coder_01", "tester_01"]
                }
            }
        }
    }
    print(f"POST /api/email-agent/tasks")
    print(json.dumps(dispatch_request, indent=2))
    
    # Example 3: Analyze Email
    print("\n3️⃣ Analyze Email API Call:")
    analyze_request = {
        "action": "analyze_email",
        "parameters": {
            "email_data": {
                "subject": "Feature request: Dark mode",
                "body-plain": "Would love to have a dark mode option in the app"
            },
            "analysis_type": "general"
        }
    }
    print(f"POST /api/email-agent/tasks")
    print(json.dumps(analyze_request, indent=2))


if __name__ == "__main__":
    # Run tests
    tester = EmailTaskTester()
    tester.run_all_tests()
    
    # Show API examples
    demo_email_to_task_api()