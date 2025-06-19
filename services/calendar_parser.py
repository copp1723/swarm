"""
Calendar Parser for .ics files
Extracts meeting/event information from calendar attachments
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from icalendar import Calendar, Event
import pytz

from utils.logging_config import get_logger

logger = get_logger(__name__)

class CalendarParser:
    """Parse .ics calendar files and extract event information"""
    
    def parse_ics_content(self, ics_content: str) -> List[Dict[str, Any]]:
        """
        Parse ICS calendar content and extract events
        
        Args:
            ics_content: Raw .ics file content
            
        Returns:
            List of parsed events with details
        """
        events = []
        
        try:
            cal = Calendar.from_ical(ics_content)
            
            for component in cal.walk():
                if component.name == "VEVENT":
                    event = self._parse_event(component)
                    if event:
                        events.append(event)
                        
        except Exception as e:
            logger.error(f"Failed to parse ICS content: {e}")
            # Try basic parsing as fallback
            event = self._parse_ics_basic(ics_content)
            if event:
                events.append(event)
        
        return events
    
    def _parse_event(self, event: Event) -> Optional[Dict[str, Any]]:
        """Parse individual calendar event"""
        try:
            # Extract basic information
            summary = str(event.get('summary', ''))
            description = str(event.get('description', ''))
            location = str(event.get('location', ''))
            
            # Parse dates
            dtstart = event.get('dtstart')
            dtend = event.get('dtend')
            
            start_time = None
            end_time = None
            
            if dtstart:
                start_time = self._convert_to_datetime(dtstart.dt)
            if dtend:
                end_time = self._convert_to_datetime(dtend.dt)
            
            # Extract organizer
            organizer = event.get('organizer', '')
            if hasattr(organizer, 'email'):
                organizer = organizer.email
            
            # Extract attendees
            attendees = []
            for attendee in event.get('attendee', []):
                if hasattr(attendee, 'email'):
                    attendees.append(attendee.email)
            
            return {
                'type': 'calendar_event',
                'summary': summary,
                'description': description,
                'location': location,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'organizer': str(organizer),
                'attendees': attendees,
                'uid': str(event.get('uid', '')),
                'recurrence': str(event.get('rrule', '')) if event.get('rrule') else None
            }
            
        except Exception as e:
            logger.error(f"Failed to parse calendar event: {e}")
            return None
    
    def _convert_to_datetime(self, dt) -> Optional[datetime]:
        """Convert various date formats to datetime"""
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                # Assume UTC if no timezone
                dt = pytz.UTC.localize(dt)
            return dt
        elif hasattr(dt, 'year'):  # date object
            # Convert date to datetime at midnight UTC
            return datetime.combine(dt, datetime.min.time()).replace(tzinfo=pytz.UTC)
        return None
    
    def _parse_ics_basic(self, content: str) -> Optional[Dict[str, Any]]:
        """Basic ICS parsing using regex as fallback"""
        try:
            # Extract key fields using regex
            summary_match = re.search(r'SUMMARY:(.*?)(?:\r?\n|$)', content)
            dtstart_match = re.search(r'DTSTART:(.*?)(?:\r?\n|$)', content)
            dtend_match = re.search(r'DTEND:(.*?)(?:\r?\n|$)', content)
            location_match = re.search(r'LOCATION:(.*?)(?:\r?\n|$)', content)
            description_match = re.search(r'DESCRIPTION:(.*?)(?:\r?\n|$)', content)
            
            if summary_match:
                return {
                    'type': 'calendar_event',
                    'summary': summary_match.group(1).strip(),
                    'description': description_match.group(1).strip() if description_match else '',
                    'location': location_match.group(1).strip() if location_match else '',
                    'start_time': self._parse_ics_datetime(dtstart_match.group(1)) if dtstart_match else None,
                    'end_time': self._parse_ics_datetime(dtend_match.group(1)) if dtend_match else None,
                    'organizer': '',
                    'attendees': [],
                    'uid': '',
                    'recurrence': None
                }
        except Exception as e:
            logger.error(f"Basic ICS parsing failed: {e}")
        
        return None
    
    def _parse_ics_datetime(self, dt_string: str) -> Optional[str]:
        """Parse ICS datetime string"""
        try:
            # Remove timezone indicator for parsing
            dt_string = dt_string.strip().replace('Z', '')
            
            # Try different formats
            for fmt in ['%Y%m%dT%H%M%S', '%Y%m%d']:
                try:
                    dt = datetime.strptime(dt_string, fmt)
                    return dt.replace(tzinfo=pytz.UTC).isoformat()
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to parse ICS datetime: {e}")
        
        return None
    
    def create_task_from_event(self, event: Dict[str, Any], email_from: str) -> Dict[str, Any]:
        """
        Convert calendar event to agent task
        
        Args:
            event: Parsed calendar event
            email_from: Email sender
            
        Returns:
            Task dictionary for agent processing
        """
        # Determine priority based on time
        priority = "medium"
        if event.get('start_time'):
            try:
                start = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
                days_until = (start - datetime.now(pytz.UTC)).days
                if days_until <= 1:
                    priority = "high"
                elif days_until <= 3:
                    priority = "medium"
                else:
                    priority = "low"
            except:
                pass
        
        # Create task
        task = {
            'type': 'calendar_management',
            'title': f"Calendar Event: {event.get('summary', 'Untitled Event')}",
            'priority': priority,
            'description': f"Add calendar event from {email_from}",
            'metadata': {
                'event_details': event,
                'source': 'email_calendar_attachment',
                'sender': email_from
            },
            'requirements': [
                f"Add event '{event.get('summary')}' to calendar",
                f"Start: {event.get('start_time')}",
                f"End: {event.get('end_time')}",
                f"Location: {event.get('location', 'Not specified')}"
            ],
            'assigned_agent': 'calendar_agent',
            'deadline': event.get('start_time')
        }
        
        # Add recurrence info if present
        if event.get('recurrence'):
            task['requirements'].append(f"Recurrence: {event['recurrence']}")
        
        return task