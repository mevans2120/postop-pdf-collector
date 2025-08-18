"""Timeline parsing module for extracting recovery timelines from PDFs."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TimelineEvent:
    """Represents a single event in the recovery timeline."""
    
    time_reference: str  # e.g., "Day 1", "Week 2", "48 hours"
    time_value: int  # Numeric value in days
    description: str  # What happens at this time
    category: str  # e.g., "activity", "medication", "follow-up"
    confidence: float  # Confidence in the extraction


class TimelineParser:
    """Parses and extracts timeline information from post-operative instructions."""
    
    def __init__(self):
        """Initialize timeline parser with patterns."""
        self.time_patterns = {
            "immediate": [
                (r"(?i)immediately", 0),
                (r"(?i)right\s+away", 0),
                (r"(?i)as\s+soon\s+as", 0),
                (r"(?i)first\s+24\s+hours?", 1),
                (r"(?i)within\s+24\s+hours?", 1),
            ],
            "days": [
                (r"(?i)day\s+(\d+)", "day"),
                (r"(?i)(\d+)\s+days?", "day"),
                (r"(?i)(first|second|third|fourth|fifth)\s+day", "day_word"),
                (r"(?i)(\d+)-(\d+)\s+days?", "day_range"),
                (r"(?i)after\s+(\d+)\s+days?", "day"),
            ],
            "weeks": [
                (r"(?i)week\s+(\d+)", "week"),
                (r"(?i)(\d+)\s+weeks?", "week"),
                (r"(?i)(first|second|third|fourth)\s+week", "week_word"),
                (r"(?i)(\d+)-(\d+)\s+weeks?", "week_range"),
                (r"(?i)after\s+(\d+)\s+weeks?", "week"),
            ],
            "months": [
                (r"(?i)month\s+(\d+)", "month"),
                (r"(?i)(\d+)\s+months?", "month"),
                (r"(?i)(first|second|third)\s+month", "month_word"),
                (r"(?i)(\d+)-(\d+)\s+months?", "month_range"),
            ],
            "hours": [
                (r"(?i)(\d+)\s+hours?", "hour"),
                (r"(?i)within\s+(\d+)\s+hours?", "hour"),
            ]
        }
        
        self.word_to_number = {
            "first": 1, "second": 2, "third": 3,
            "fourth": 4, "fifth": 5, "sixth": 6,
            "one": 1, "two": 2, "three": 3,
            "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "twelve": 12,
        }
        
        self.activity_keywords = [
            "walk", "exercise", "lift", "drive", "work", "shower",
            "bath", "swim", "run", "bend", "stretch", "climb",
            "return to", "resume", "avoid", "restrict"
        ]
        
        self.medication_keywords = [
            "medication", "medicine", "pill", "tablet", "dose",
            "antibiotic", "pain", "aspirin", "blood thinner",
            "prescription", "take", "stop", "continue"
        ]
        
        self.appointment_keywords = [
            "appointment", "follow-up", "visit", "check-up",
            "see", "call", "schedule", "return", "office"
        ]
    
    def parse_timeline(self, text: str) -> List[TimelineEvent]:
        """
        Extract timeline events from text.
        
        Args:
            text: Text content to parse
            
        Returns:
            List of TimelineEvent objects sorted by time
        """
        events = []
        
        # Split text into sentences for context
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            # Extract time references from sentence
            time_refs = self._extract_time_references(sentence)
            
            for time_ref, days_value in time_refs:
                # Determine event category
                category = self._categorize_event(sentence)
                
                # Calculate confidence
                confidence = self._calculate_confidence(sentence, time_ref)
                
                # Create timeline event
                event = TimelineEvent(
                    time_reference=time_ref,
                    time_value=days_value,
                    description=sentence.strip(),
                    category=category,
                    confidence=confidence
                )
                events.append(event)
        
        # Sort events by time value
        events.sort(key=lambda x: x.time_value)
        
        # Remove duplicates
        events = self._remove_duplicate_events(events)
        
        return events
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"[.!?]\s+", text)
        
        # Also split on bullet points and newlines
        expanded = []
        for sentence in sentences:
            parts = sentence.split("\n")
            for part in parts:
                part = part.strip()
                if part and len(part) > 10:
                    expanded.append(part)
        
        return expanded
    
    def _extract_time_references(
        self, sentence: str
    ) -> List[Tuple[str, int]]:
        """Extract time references from a sentence."""
        references = []
        
        # Check immediate patterns
        for pattern, days in self.time_patterns["immediate"]:
            if re.search(pattern, sentence):
                match = re.search(pattern, sentence)
                references.append((match.group(0), days))
        
        # Check day patterns
        for pattern, pattern_type in self.time_patterns["days"]:
            matches = re.finditer(pattern, sentence)
            for match in matches:
                if pattern_type == "day":
                    days = int(match.group(1))
                    references.append((match.group(0), days))
                elif pattern_type == "day_word":
                    word = match.group(1).lower()
                    days = self.word_to_number.get(word, 1)
                    references.append((match.group(0), days))
                elif pattern_type == "day_range":
                    start = int(match.group(1))
                    end = int(match.group(2))
                    avg_days = (start + end) // 2
                    references.append((match.group(0), avg_days))
        
        # Check week patterns
        for pattern, pattern_type in self.time_patterns["weeks"]:
            matches = re.finditer(pattern, sentence)
            for match in matches:
                if pattern_type == "week":
                    weeks = int(match.group(1))
                    references.append((match.group(0), weeks * 7))
                elif pattern_type == "week_word":
                    word = match.group(1).lower()
                    weeks = self.word_to_number.get(word, 1)
                    references.append((match.group(0), weeks * 7))
                elif pattern_type == "week_range":
                    start = int(match.group(1))
                    end = int(match.group(2))
                    avg_weeks = (start + end) // 2
                    references.append((match.group(0), avg_weeks * 7))
        
        # Check month patterns
        for pattern, pattern_type in self.time_patterns["months"]:
            matches = re.finditer(pattern, sentence)
            for match in matches:
                if pattern_type == "month":
                    months = int(match.group(1))
                    references.append((match.group(0), months * 30))
                elif pattern_type == "month_word":
                    word = match.group(1).lower()
                    months = self.word_to_number.get(word, 1)
                    references.append((match.group(0), months * 30))
                elif pattern_type == "month_range":
                    start = int(match.group(1))
                    end = int(match.group(2))
                    avg_months = (start + end) // 2
                    references.append((match.group(0), avg_months * 30))
        
        # Check hour patterns
        for pattern, pattern_type in self.time_patterns["hours"]:
            matches = re.finditer(pattern, sentence)
            for match in matches:
                if pattern_type == "hour":
                    hours = int(match.group(1))
                    days = max(1, hours // 24)  # Convert to days
                    references.append((match.group(0), days))
        
        return references
    
    def _categorize_event(self, sentence: str) -> str:
        """Categorize the timeline event."""
        sentence_lower = sentence.lower()
        
        # Check for activity-related
        for keyword in self.activity_keywords:
            if keyword in sentence_lower:
                return "activity"
        
        # Check for medication-related
        for keyword in self.medication_keywords:
            if keyword in sentence_lower:
                return "medication"
        
        # Check for appointment-related
        for keyword in self.appointment_keywords:
            if keyword in sentence_lower:
                return "appointment"
        
        # Check for wound care
        if any(word in sentence_lower for word in ["wound", "incision", "dressing", "bandage"]):
            return "wound_care"
        
        # Check for diet
        if any(word in sentence_lower for word in ["eat", "diet", "food", "drink"]):
            return "diet"
        
        return "general"
    
    def _calculate_confidence(self, sentence: str, time_ref: str) -> float:
        """Calculate confidence score for timeline extraction."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for clear time markers
        if any(word in sentence.lower() for word in ["must", "should", "will", "need"]):
            confidence += 0.2
        
        # Increase confidence for specific instructions
        if any(char in sentence for char in [":", "-", "•", "1.", "2."]):
            confidence += 0.1
        
        # Increase confidence for medical terms
        medical_terms = ["doctor", "surgeon", "nurse", "hospital", "clinic"]
        if any(term in sentence.lower() for term in medical_terms):
            confidence += 0.1
        
        # Decrease confidence for conditional statements
        if any(word in sentence.lower() for word in ["if", "may", "might", "could"]):
            confidence -= 0.2
        
        return max(0.1, min(1.0, confidence))
    
    def _remove_duplicate_events(
        self, events: List[TimelineEvent]
    ) -> List[TimelineEvent]:
        """Remove duplicate timeline events."""
        unique_events = []
        seen = set()
        
        for event in events:
            # Create a unique key for the event
            key = (event.time_value, event.category, event.description[:50])
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events
    
    def create_recovery_schedule(
        self, events: List[TimelineEvent]
    ) -> Dict[str, List[TimelineEvent]]:
        """
        Organize timeline events into a recovery schedule.
        
        Args:
            events: List of timeline events
            
        Returns:
            Dictionary organizing events by time period
        """
        schedule = {
            "immediate": [],  # 0-2 days
            "first_week": [],  # 3-7 days
            "second_week": [],  # 8-14 days
            "first_month": [],  # 15-30 days
            "second_month": [],  # 31-60 days
            "third_month": [],  # 61-90 days
            "long_term": [],  # 90+ days
        }
        
        for event in events:
            days = event.time_value
            
            if days <= 2:
                schedule["immediate"].append(event)
            elif days <= 7:
                schedule["first_week"].append(event)
            elif days <= 14:
                schedule["second_week"].append(event)
            elif days <= 30:
                schedule["first_month"].append(event)
            elif days <= 60:
                schedule["second_month"].append(event)
            elif days <= 90:
                schedule["third_month"].append(event)
            else:
                schedule["long_term"].append(event)
        
        # Remove empty periods
        schedule = {k: v for k, v in schedule.items() if v}
        
        return schedule
    
    def extract_milestones(
        self, events: List[TimelineEvent]
    ) -> List[Dict]:
        """
        Extract key recovery milestones.
        
        Args:
            events: List of timeline events
            
        Returns:
            List of milestone dictionaries
        """
        milestones = []
        
        # Define milestone patterns
        milestone_patterns = [
            ("return_to_work", ["return to work", "back to work", "resume work"]),
            ("driving", ["drive", "driving", "behind the wheel"]),
            ("full_activity", ["full activity", "normal activities", "all activities"]),
            ("exercise", ["exercise", "gym", "sports", "physical activity"]),
            ("follow_up", ["follow-up", "appointment", "see doctor"]),
            ("suture_removal", ["suture", "stitch", "staple", "removal"]),
        ]
        
        for event in events:
            desc_lower = event.description.lower()
            
            for milestone_type, keywords in milestone_patterns:
                if any(keyword in desc_lower for keyword in keywords):
                    milestones.append({
                        "type": milestone_type,
                        "day": event.time_value,
                        "time_reference": event.time_reference,
                        "description": event.description,
                        "confidence": event.confidence,
                    })
                    break
        
        # Sort by day
        milestones.sort(key=lambda x: x["day"])
        
        return milestones
    
    def generate_timeline_summary(
        self, events: List[TimelineEvent]
    ) -> str:
        """
        Generate a human-readable timeline summary.
        
        Args:
            events: List of timeline events
            
        Returns:
            Formatted timeline summary
        """
        if not events:
            return "No timeline information found."
        
        schedule = self.create_recovery_schedule(events)
        milestones = self.extract_milestones(events)
        
        summary = []
        summary.append("Recovery Timeline Summary")
        summary.append("=" * 40)
        
        # Add schedule by period
        for period, period_events in schedule.items():
            period_title = period.replace("_", " ").title()
            summary.append(f"\n{period_title}:")
            
            for event in period_events[:3]:  # Limit to 3 per period
                summary.append(
                    f"  • {event.time_reference}: {event.description[:80]}"
                )
        
        # Add key milestones
        if milestones:
            summary.append("\n\nKey Milestones:")
            summary.append("-" * 40)
            for milestone in milestones[:5]:  # Top 5 milestones
                summary.append(
                    f"  • {milestone['time_reference']}: "
                    f"{milestone['type'].replace('_', ' ').title()}"
                )
        
        return "\n".join(summary)