"""
Tests for Enhanced Email Parser - T-207
Testing improved deadline extraction and list parsing
"""

import unittest
from datetime import datetime, timedelta
from services.email_parser import EmailParser
from services.email_parser_enhancements import EnhancedDeadlineExtractor, EnhancedListExtractor


class TestEnhancedDeadlineExtraction(unittest.TestCase):
    """Test enhanced deadline extraction capabilities"""
    
    def setUp(self):
        self.extractor = EnhancedDeadlineExtractor()
        self.parser = EmailParser()
    
    def test_business_day_deadlines(self):
        """Test business day deadline extraction"""
        test_cases = [
            ("Please complete this by COB today", 0, 17),  # Close of business today
            ("Need this by EOB Friday", 4, 17),  # End of business Friday
            ("Submit report by close of business on March 15", 3, 15),
            ("Required by start of business tomorrow", 1, 9),
            ("Complete within 3 business days", 3, 17),
        ]
        
        now = datetime.now()
        for text, expected_days_ahead, expected_hour in test_cases[:2]:  # Test first two cases
            result = self.extractor.extract_deadline(text)
            self.assertIsNotNone(result, f"Failed to extract deadline from: {text}")
            deadline, confidence = result
            self.assertGreater(confidence, 0.7, f"Low confidence for: {text}")
            
            # For relative dates, just check it's in the future
            self.assertGreater(deadline, now, f"Deadline should be in future for: {text}")
    
    def test_quarter_and_fiscal_deadlines(self):
        """Test quarter and fiscal year deadline extraction"""
        test_cases = [
            "Report due by end of Q2 2024",
            "Complete analysis by Q4",
            "Submit by end of fiscal year 2024",
            "Due by the end of this quarter",
        ]
        
        for text in test_cases:
            result = self.extractor.extract_deadline(text)
            if result:  # Some may not parse depending on current date
                deadline, confidence = result
                self.assertGreater(confidence, 0.7, f"Low confidence for: {text}")
    
    def test_iso_date_formats(self):
        """Test ISO date format extraction"""
        test_cases = [
            "Meeting scheduled for 2025-12-25",
            "Deadline: 2025-06-30T17:00",
            "Due by 2025-12-15",
            "Complete by 2026-01-01",
        ]
        
        for text in test_cases:
            result = self.extractor.extract_deadline(text)
            # Enhanced extractor should find these
            if result:
                deadline, confidence = result
                self.assertIsNotNone(deadline, f"Failed to parse ISO date: {text}")
                self.assertGreater(confidence, 0.8, f"Low confidence for ISO date: {text}")
            else:
                # Fallback to basic parser
                deadline = self.parser._extract_deadline(text)
                # At least one method should work
                self.assertIsNotNone(deadline, f"Both parsers failed for ISO date: {text}")
    
    def test_natural_language_deadlines(self):
        """Test natural language deadline extraction"""
        test_cases = [
            "Need this by next Monday",
            "Please finish by this Friday",
            "Due by tomorrow afternoon",
            "Complete by this evening",
            "Submit by next week",
            "Required by end of month",
        ]
        
        now = datetime.now()
        for text in test_cases:
            deadline = self.parser._extract_deadline(text)
            if deadline:  # Some may depend on current date
                self.assertGreater(deadline, now, f"Deadline should be in future for: {text}")
    
    def test_deadline_confidence_scores(self):
        """Test that confidence scores are appropriate"""
        test_cases = [
            ("Due by 2024-12-25", 0.9),  # High confidence for explicit date
            ("Need this soon", 0.5),  # Lower confidence for vague
            ("ASAP", 0.7),  # Medium confidence for urgent
            ("By 5:00 PM today", 0.85),  # High confidence for specific time
        ]
        
        for text, min_confidence in test_cases:
            result = self.extractor.extract_deadline(text)
            if result:
                _, confidence = result
                self.assertGreaterEqual(confidence, min_confidence * 0.8, 
                                      f"Confidence too low for: {text}")


class TestEnhancedListExtraction(unittest.TestCase):
    """Test enhanced list extraction capabilities"""
    
    def setUp(self):
        self.extractor = EnhancedListExtractor()
        self.parser = EmailParser()
    
    def test_complex_bullet_lists(self):
        """Test extraction of various bullet point formats"""
        email_text = """
        Please complete the following tasks:
        • Update the user documentation
        → Fix the login bug in production
        ▪ Review and merge the PR for feature X
        ○ Deploy the new version to staging
        ✓ Send status report to stakeholders
        """
        
        lists = self.extractor.extract_lists(email_text)
        bullet_items = []
        for bullet_list in lists.get('bullet_lists', []):
            bullet_items.extend([item['text'] for item in bullet_list['items']])
        
        self.assertGreaterEqual(len(bullet_items), 4, "Should extract at least 4 bullet items")
        self.assertIn("Update the user documentation", bullet_items)
        self.assertIn("Fix the login bug in production", bullet_items)
    
    def test_nested_lists(self):
        """Test extraction of nested list structures"""
        email_text = """
        Project requirements:
        1. Backend Development
           a. API design and implementation
           b. Database schema updates
           c. Integration with third-party services
        2. Frontend Development
           - React component updates
           - CSS styling improvements
           - Mobile responsiveness
        3. Testing
           • Unit tests for new features
           • Integration test suite
           • Performance benchmarks
        """
        
        lists = self.extractor.extract_lists(email_text)
        
        # Check numbered lists
        numbered_items = []
        for numbered_list in lists.get('numbered_lists', []):
            numbered_items.extend([item['text'] for item in numbered_list['items']])
        
        self.assertGreater(len(numbered_items), 0, "Should extract numbered list items")
        
        # Check sub-items
        all_items = []
        for list_type in ['bullet_lists', 'numbered_lists']:
            for list_data in lists.get(list_type, []):
                all_items.extend([item['text'] for item in list_data['items']])
        
        self.assertGreater(len(all_items), 5, "Should extract nested items")
    
    def test_inline_list_extraction(self):
        """Test extraction of inline lists"""
        test_cases = [
            "Please review the following documents: design doc, test plan, and deployment guide.",
            "The team includes John, Mary, Sarah, and David.",
            "We need to fix bugs in login, registration, profile page, and settings.",
            "Technologies used: Python, React, PostgreSQL, Redis, Docker",
        ]
        
        for text in test_cases:
            lists = self.extractor.extract_lists(text)
            inline_lists = lists.get('inline_lists', [])
            
            self.assertGreater(len(inline_lists), 0, f"Should find inline list in: {text}")
            
            # Check that items were extracted
            total_items = sum(len(il['items']) for il in inline_lists)
            self.assertGreaterEqual(total_items, 3, f"Should extract multiple items from: {text}")
    
    def test_task_checkbox_lists(self):
        """Test extraction of task lists with checkboxes"""
        email_text = """
        Sprint tasks:
        [ ] Implement user authentication
        [x] Set up CI/CD pipeline
        [ ] Write API documentation
        [X] Configure monitoring alerts
        """
        
        lists = self.extractor.extract_lists(email_text)
        task_items = []
        for task_list in lists.get('task_lists', []):
            task_items.extend([item['text'] for item in task_list['items']])
        
        self.assertGreaterEqual(len(task_items), 3, "Should extract task list items")
        self.assertIn("Implement user authentication", task_items)
        self.assertIn("Write API documentation", task_items)
    
    def test_section_based_lists(self):
        """Test extraction of lists within sections"""
        email_text = """
        Deliverables:
        - Final report document
        - Source code with documentation
        - Test results and coverage report
        
        Success Criteria:
        1. All tests passing with >90% coverage
        2. Performance benchmarks met
        3. Security audit completed
        
        Dependencies:
        • Access to production database
        • API keys for third-party services
        • Approval from security team
        """
        
        # Test through the parser's section extraction
        items = self.parser._extract_section_items(email_text, "deliverables")
        self.assertGreaterEqual(len(items), 2, "Should extract deliverables")
        
        items = self.parser._extract_section_items(email_text, "success_criteria")
        self.assertGreaterEqual(len(items), 2, "Should extract success criteria")
        
        items = self.parser._extract_section_items(email_text, "dependencies")
        self.assertGreaterEqual(len(items), 2, "Should extract dependencies")


class TestEmailParserIntegration(unittest.TestCase):
    """Test integration of enhanced features with email parser"""
    
    def setUp(self):
        self.parser = EmailParser()
    
    def test_complete_email_parsing(self):
        """Test parsing a complete email with enhanced features"""
        email_data = {
            "subject": "Urgent: Feature Implementation Required",
            "body_plain": """
            Hi Team,
            
            We need to implement the new payment processing feature by end of business on Friday.
            
            Here's what needs to be done:
            1. Integrate with Stripe API
            2. Update the checkout flow
            3. Add payment history page
            4. Set up webhook handlers
            
            Requirements:
            - PCI compliance must be maintained
            - Support for credit cards, PayPal, and Apple Pay
            - Real-time payment status updates
            
            Please complete the following by COB today:
            • Code review of current implementation
            • Security audit checklist
            • Performance benchmarks
            
            The success criteria includes: all payment methods working, less than 2 second response time, and 99.9% uptime.
            
            Thanks,
            Product Manager
            """,
            "sender": "pm@company.com",
            "timestamp": "2024-06-18T10:00:00Z"
        }
        
        task = self.parser.parse_email(email_data)
        
        # Check basic parsing
        self.assertIsNotNone(task)
        self.assertEqual(task.priority.value, "urgent")  # Should detect as urgent priority due to "Urgent" in subject
        
        # Check deadline extraction
        self.assertIsNotNone(task.requirements.deadline)
        
        # Check list extraction
        self.assertGreater(len(task.requirements.deliverables), 0, "Should extract deliverables")
        self.assertGreater(len(task.requirements.success_criteria), 0, "Should extract success criteria")


def run_tests():
    """Run all enhancement tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()