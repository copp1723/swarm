"""
Email Parser Enhancements - T-207
Enhanced deadline extraction and list parsing capabilities
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
from dateutil import parser as date_parser
from loguru import logger


class EnhancedDeadlineExtractor:
    """Enhanced deadline extraction with better natural language understanding"""
    
    def __init__(self):
        # Enhanced deadline patterns with better coverage
        self.deadline_patterns = [
            # Standard deadline phrases with better capture
            (r"(?:deadline|due|by|before)\s*:?\s*([^.!?\n]+?)(?:[.!?\n]|$)", 0.9),
            (r"(?:need(?:ed)?|required?)\s*(?:by)?\s*:?\s*([^.!?\n]+?)(?:[.!?\n]|$)", 0.8),
            (r"(?:complete|finish|deliver|submit)\s*(?:by)?\s*:?\s*([^.!?\n]+?)(?:[.!?\n]|$)", 0.8),
            
            # Time-based patterns with better specificity
            (r"(?:within|in)\s+(\d+)\s*(?:business\s+)?(?:hours?|days?|weeks?|months?)", 0.95),
            (r"(?:by|before)\s+(tomorrow|today|tonight|this\s+(?:evening|afternoon|morning))", 0.95),
            (r"(?:by|before)\s+(this|next)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", 0.9),
            (r"(?:by|before)\s+(next|this)\s+(week|month|quarter|year)", 0.85),
            (r"(?:end\s+of)\s+(?:the\s+)?(day|week|month|quarter|year|business\s+day)", 0.9),
            
            # Business day patterns
            (r"(?:by|before)\s+(?:close\s+of\s+business|COB|EOB|end\s+of\s+business)\s*(?:on\s+)?([^.!?\n]+)?", 0.95),
            (r"(?:by|before)\s+(?:start\s+of\s+business|SOB|beginning\s+of\s+business)\s*(?:on\s+)?([^.!?\n]+)?", 0.95),
            
            # Explicit dates with more formats
            (r"(?:on|by|before)\s+(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)", 0.95),
            (r"(?:on|by|before)\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)", 0.95),
            (r"(?:on|by|before)\s+(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?(?:,?\s+\d{4})?)", 0.95),
            
            # ISO date format
            (r"(?:on|by|before)\s+(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2})?)", 0.98),
            
            # Relative time expressions
            (r"(?:in|within)\s+(?:the\s+)?next\s+(\d+)\s*(?:business\s+)?(?:hours?|days?|weeks?)", 0.9),
            (r"(?:over\s+the\s+)?next\s+(\d+)\s*(?:business\s+)?(?:days?|weeks?)", 0.85),
            (r"(\d+)\s*(?:business\s+)?(?:days?|weeks?)\s+from\s+(?:now|today)", 0.9),
            
            # ASAP and urgent patterns
            (r"(?:asap|as\s+soon\s+as\s+possible|immediately|right\s+away|urgent(?:ly)?)", 0.8),
            
            # Quarter/fiscal patterns
            (r"(?:by|before)\s+(?:the\s+)?end\s+of\s+Q(\d)\s*(?:\d{4})?", 0.9),
            (r"(?:by|before)\s+(?:the\s+)?(?:end\s+of\s+)?(?:fiscal|calendar)\s+year\s*(?:\d{4})?", 0.85),
            
            # Milestone-based deadlines
            (r"(?:before|by)\s+(?:the\s+)?(?:next\s+)?(?:sprint|milestone|release|deployment)", 0.7),
            
            # Time of day patterns
            (r"(?:by|before)\s+(\d{1,2})\s*(?::(\d{2}))?\s*(?:am|pm|AM|PM)", 0.9),
            (r"(?:by|before)\s+(\d{1,2}:\d{2})\s*(?:hours?)?", 0.9),
        ]
        
        # Days of week mapping
        self.weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
        }
        
        # Month mapping
        self.months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7,
            'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
    
    def extract_deadline(self, text: str) -> Optional[Tuple[datetime, float]]:
        """
        Extract deadline from text with confidence score
        
        Returns:
            Tuple of (deadline_datetime, confidence_score) or None
        """
        now = datetime.now()
        best_deadline = None
        best_confidence = 0.0
        
        # Normalize text for better matching
        normalized_text = self._normalize_text(text)
        
        # First, try to find standalone ISO dates in the text
        iso_matches = re.findall(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?)?', normalized_text)
        for iso_match in iso_matches:
            try:
                deadline = date_parser.parse(iso_match)
                if deadline and deadline > now:
                    confidence = 0.98  # High confidence for ISO dates
                    if confidence > best_confidence:
                        best_deadline = deadline
                        best_confidence = confidence
            except:
                continue
        
        for pattern, base_confidence in self.deadline_patterns:
            matches = re.findall(pattern, normalized_text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                try:
                    # Extract the match text
                    match_text = match if isinstance(match, str) else match[0]
                    
                    # Try to parse the deadline
                    deadline = self._parse_deadline_match(match_text, pattern)
                    
                    if deadline and deadline > now:
                        # Adjust confidence based on how specific the match is
                        confidence = self._calculate_confidence(match_text, base_confidence)
                        
                        if confidence > best_confidence:
                            best_deadline = deadline
                            best_confidence = confidence
                            
                except Exception as e:
                    logger.debug(f"Failed to parse deadline match '{match}': {e}")
                    continue
        
        if best_deadline:
            logger.info(f"Extracted deadline: {best_deadline} with confidence {best_confidence:.2f}")
            return (best_deadline, best_confidence)
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better pattern matching"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Add space after punctuation if missing
        text = re.sub(r'([.!?,:;])([A-Za-z])', r'\1 \2', text)
        return text
    
    def _parse_deadline_match(self, match_text: str, pattern: str) -> Optional[datetime]:
        """Parse a deadline match into a datetime object"""
        match_text = match_text.strip()
        now = datetime.now()
        
        # Check for ISO date format first
        iso_match = re.search(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2})?', match_text)
        if iso_match:
            try:
                return date_parser.parse(iso_match.group())
            except:
                pass
        
        # Handle ASAP patterns
        if re.search(r'asap|immediately|right\s+away|urgent', match_text, re.IGNORECASE):
            return now + timedelta(hours=4)  # Default to 4 hours for urgent tasks
        
        # Handle relative time patterns
        relative_match = re.search(r'(\d+)\s*(?:business\s+)?(?:hours?|days?|weeks?|months?)', match_text, re.IGNORECASE)
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(0).lower()
            
            if 'hour' in unit:
                return now + timedelta(hours=amount)
            elif 'week' in unit:
                days = amount * 7
                if 'business' in unit:
                    # Adjust for business days
                    return self._add_business_days(now, days)
                return now + timedelta(days=days)
            elif 'month' in unit:
                return now + timedelta(days=amount * 30)
            else:  # days
                if 'business' in unit:
                    return self._add_business_days(now, amount)
                return now + timedelta(days=amount)
        
        # Handle named relative dates
        if 'tomorrow' in match_text.lower():
            return (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
        elif 'today' in match_text.lower() or 'tonight' in match_text.lower():
            return now.replace(hour=23, minute=59, second=59, microsecond=0)
        
        # Handle day of week
        for day_name, day_num in self.weekdays.items():
            if day_name in match_text.lower():
                days_ahead = (day_num - now.weekday()) % 7
                if days_ahead == 0:  # If it's the same day, assume next week
                    days_ahead = 7
                if 'next' in match_text.lower():
                    days_ahead += 7
                return (now + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Handle end of period patterns
        if 'end of' in match_text.lower():
            if 'day' in match_text.lower():
                return now.replace(hour=23, minute=59, second=59, microsecond=0)
            elif 'week' in match_text.lower():
                days_to_friday = 4 - now.weekday()
                if days_to_friday < 0:
                    days_to_friday += 7
                return (now + timedelta(days=days_to_friday)).replace(hour=17, minute=0, second=0, microsecond=0)
            elif 'month' in match_text.lower():
                # Last day of current month
                next_month = now.replace(day=1) + timedelta(days=32)
                return (next_month.replace(day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
            elif 'quarter' in match_text.lower():
                current_quarter = (now.month - 1) // 3
                quarter_end_month = (current_quarter + 1) * 3
                year = now.year
                if quarter_end_month > 12:
                    quarter_end_month = 12
                return datetime(year, quarter_end_month, 1) + timedelta(days=32)
            elif 'year' in match_text.lower():
                return datetime(now.year, 12, 31, 23, 59, 59)
        
        # Handle COB/EOB patterns
        if re.search(r'(?:close|end)\s+of\s+business|COB|EOB', match_text, re.IGNORECASE):
            base_date = now
            # Look for a specific date after COB/EOB
            date_after = re.search(r'(?:on\s+)?(.+)$', match_text)
            if date_after:
                try:
                    base_date = date_parser.parse(date_after.group(1), fuzzy=True)
                except:
                    pass
            return base_date.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Handle quarter patterns
        quarter_match = re.search(r'Q(\d)\s*(?:(\d{4}))?', match_text, re.IGNORECASE)
        if quarter_match:
            quarter = int(quarter_match.group(1))
            year = int(quarter_match.group(2)) if quarter_match.group(2) else now.year
            if quarter < 1 or quarter > 4:
                quarter = 1
            quarter_end_month = quarter * 3
            return datetime(year, quarter_end_month, 1) + timedelta(days=32)
        
        # Try dateutil parser as fallback
        try:
            parsed_date = date_parser.parse(match_text, fuzzy=True, default=now)
            # If only time was parsed, assume today
            if parsed_date.date() == now.date() and parsed_date.time() != now.time():
                return parsed_date
            # If date is in the past, it might be a misparse
            if parsed_date > now:
                return parsed_date
        except:
            pass
        
        return None
    
    def _add_business_days(self, start_date: datetime, days: int) -> datetime:
        """Add business days to a date, skipping weekends"""
        current = start_date
        remaining = days
        
        while remaining > 0:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Monday-Friday
                remaining -= 1
        
        return current.replace(hour=17, minute=0, second=0, microsecond=0)
    
    def _calculate_confidence(self, match_text: str, base_confidence: float) -> float:
        """Calculate confidence score based on match specificity"""
        confidence = base_confidence
        
        # Boost confidence for very specific patterns
        if re.search(r'\d{4}-\d{2}-\d{2}', match_text):  # ISO date
            confidence = min(confidence * 1.1, 1.0)
        elif re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', match_text):  # Explicit date
            confidence = min(confidence * 1.05, 1.0)
        elif re.search(r'(?:urgent|asap|immediately)', match_text, re.IGNORECASE):
            confidence = min(confidence * 1.05, 1.0)
        
        # Lower confidence for vague patterns
        if re.search(r'(?:soon|later|eventually)', match_text, re.IGNORECASE):
            confidence *= 0.7
        
        return confidence


class EnhancedListExtractor:
    """Enhanced list extraction with better structure understanding"""
    
    def __init__(self):
        # Comprehensive list patterns - ORDER MATTERS for priority
        self.list_patterns = [
            # Task checkboxes (highest priority)
            (r"^\s*\[\s*[xX ]?\s*\]\s*(.+)$", 0.95, 'task'),
            # Numbered lists with various formats (higher priority than bullets)
            (r"^\s*(\d{1,2})[.)\]]\s*(.+)$", 0.95, 'numbered'),
            (r"^\s*\((\d{1,2})\)\s*(.+)$", 0.9, 'numbered'),
            # Letter lists
            (r"^\s*([a-zA-Z])[.)\]]\s*(.+)$", 0.9, 'lettered'),
            (r"^\s*\(([a-zA-Z])\)\s*(.+)$", 0.85, 'lettered'),
            # Roman numerals
            (r"^\s*([ivxIVX]+)[.)\]]\s*(.+)$", 0.85, 'numbered'),
            # Bullet points with various markers (after numbered to avoid conflicts)
            (r"^\s*[-•*→▪▸◦‣⁃✓✔✗✘◯●○■□▶►]\s*(.+)$", 0.95, 'bullet'),
            # Indented items (at least 2 spaces)
            (r"^(\s{2,})([^-•*→▪▸◦‣⁃\d].+)$", 0.7, 'bullet'),
            # Emoji bullets
            (r"^\s*[🔸🔹🔶🔷📌📍➡️⚡💡]\s*(.+)$", 0.9, 'bullet'),
        ]
        
        # Section headers that indicate lists
        self.list_indicators = [
            r"(?:following|these|list\s+of|items?|steps?|requirements?|deliverables?|tasks?):",
            r"(?:please|kindly)?\s*(?:do|complete|implement|fix|review)\s+(?:the\s+)?following:",
            r"(?:action\s+items?|to-?do|checklist):",
            r"(?:includes?|contains?|consists?\s+of):",
        ]
        
        # Inline list separators
        self.inline_separators = [
            r',\s*(?:and\s+)?',  # Comma with optional 'and'
            r';\s*',  # Semicolon
            r'\s+and\s+',  # 'and' separator
            r'\s*\|\s*',  # Pipe separator
            r'\s*/\s*',  # Slash separator
        ]
    
    def extract_lists(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all types of lists from text
        
        Returns:
            Dictionary with list types as keys and extracted items as values
        """
        lists = {
            'bullet_lists': [],
            'numbered_lists': [],
            'task_lists': [],
            'inline_lists': [],
            'nested_lists': []
        }
        
        # Split text into sections
        sections = self._split_into_sections(text)
        
        for section in sections:
            # Check if section contains list indicators
            has_list_indicator = any(
                re.search(pattern, section['header'], re.IGNORECASE) 
                for pattern in self.list_indicators
            )
            
            # Extract structured lists
            structured_lists = self._extract_structured_lists(section['content'], has_list_indicator)
            for list_type, items in structured_lists.items():
                lists[list_type].extend(items)
            
            # Extract inline lists
            inline_lists = self._extract_inline_lists(section['content'])
            lists['inline_lists'].extend(inline_lists)
        
        return lists
    
    def _split_into_sections(self, text: str) -> List[Dict[str, str]]:
        """Split text into logical sections"""
        sections = []
        lines = text.split('\n')
        
        current_section = {'header': '', 'content': []}
        
        for i, line in enumerate(lines):
            # Check if line is a section header
            if (line.strip() and 
                (line.endswith(':') or 
                 re.match(r'^[A-Z][^.!?]*$', line.strip()) or
                 re.match(r'^\d+\.\s+[A-Z]', line.strip()))):
                
                # Save previous section if it has content
                if current_section['content']:
                    sections.append({
                        'header': current_section['header'],
                        'content': '\n'.join(current_section['content'])
                    })
                
                current_section = {'header': line.strip(), 'content': []}
            else:
                current_section['content'].append(line)
        
        # Add last section
        if current_section['content']:
            sections.append({
                'header': current_section['header'],
                'content': '\n'.join(current_section['content'])
            })
        
        # If no sections found, treat entire text as one section
        if not sections:
            sections.append({'header': '', 'content': text})
        
        return sections
    
    def _extract_structured_lists(self, text: str, has_indicator: bool) -> Dict[str, List[Dict[str, Any]]]:
        """Extract structured lists (bullet, numbered, etc.)"""
        lists = {
            'bullet_lists': [],
            'numbered_lists': [],
            'task_lists': []
        }
        
        lines = text.split('\n')
        current_list = []
        current_type = None
        current_indent = 0
        
        for line in lines:
            if not line.strip():
                # Empty line might indicate end of list
                if current_list and current_type:
                    lists[current_type].append({
                        'items': current_list,
                        'confidence': 0.9 if has_indicator else 0.7
                    })
                    current_list = []
                    current_type = None
                continue
            
            # Check each pattern
            matched = False
            for pattern, confidence, pattern_type in self.list_patterns:
                match = re.match(pattern, line)
                if match:
                    # Determine list type based on pattern type
                    if pattern_type == 'task':
                        list_type = 'task_lists'
                    elif pattern_type in ['numbered', 'lettered']:
                        list_type = 'numbered_lists'
                    else:  # bullet
                        list_type = 'bullet_lists'
                    
                    # Extract item text
                    if match.groups():
                        # Get the last non-None group (the actual content)
                        item_text = None
                        for group in reversed(match.groups()):
                            if group is not None:
                                item_text = group.strip()
                                break
                        if not item_text:
                            item_text = line.strip()
                    else:
                        item_text = line.strip()
                    
                    # Calculate indent level
                    indent = len(line) - len(line.lstrip())
                    
                    # Add to current list or start new list
                    if current_type == list_type:
                        current_list.append({
                            'text': item_text,
                            'indent': indent,
                            'confidence': confidence
                        })
                    else:
                        # Save previous list
                        if current_list and current_type:
                            lists[current_type].append({
                                'items': current_list,
                                'confidence': 0.9 if has_indicator else 0.7
                            })
                        # Start new list
                        current_list = [{
                            'text': item_text,
                            'indent': indent,
                            'confidence': confidence
                        }]
                        current_type = list_type
                    
                    matched = True
                    break
            
            if not matched and current_list:
                # Check if this might be a continuation of the previous item
                if line.startswith(' ' * (current_indent + 2)):
                    # Continuation line
                    current_list[-1]['text'] += ' ' + line.strip()
        
        # Save final list
        if current_list and current_type:
            lists[current_type].append({
                'items': current_list,
                'confidence': 0.9 if has_indicator else 0.7
            })
        
        return lists
    
    def _extract_inline_lists(self, text: str) -> List[Dict[str, Any]]:
        """Extract inline lists from text"""
        inline_lists = []
        
        # Look for sentences that might contain inline lists
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            # Check for list indicators in sentence
            if re.search(r'(?:includes?|such\s+as|like|following|these)\s*:?\s*', sentence, re.IGNORECASE):
                # Try to extract the list part
                list_match = re.search(r'(?:includes?|such\s+as|like|following|these)\s*:?\s*(.+)$', sentence, re.IGNORECASE)
                if list_match:
                    list_text = list_match.group(1)
                    items = self._parse_inline_items(list_text)
                    if len(items) >= 2:  # At least 2 items to be considered a list
                        inline_lists.append({
                            'items': items,
                            'confidence': 0.8,
                            'context': sentence[:50] + '...' if len(sentence) > 50 else sentence
                        })
            else:
                # Also check for simple comma-separated lists without explicit indicators
                items = self._parse_inline_items(sentence)
                if len(items) >= 3:  # Require at least 3 items for non-indicated lists
                    inline_lists.append({
                        'items': items,
                        'confidence': 0.6,
                        'context': sentence[:50] + '...' if len(sentence) > 50 else sentence
                    })
        
        return inline_lists
    
    def _parse_inline_items(self, text: str) -> List[str]:
        """Parse inline list items"""
        items = []
        
        # Try each separator pattern
        for separator in self.inline_separators:
            potential_items = re.split(separator, text)
            if len(potential_items) >= 2:
                # Clean and validate items
                cleaned_items = []
                for item in potential_items:
                    item = item.strip()
                    # Remove trailing punctuation
                    item = re.sub(r'[.!?]+$', '', item)
                    # Skip if too short or too long
                    if 3 < len(item) < 100:
                        cleaned_items.append(item)
                
                if len(cleaned_items) >= 2:
                    return cleaned_items
        
        return items