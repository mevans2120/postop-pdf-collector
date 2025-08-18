"""Tests for analysis modules."""

import pytest
from unittest.mock import MagicMock, patch

from postop_collector.analysis.content_analyzer import ContentAnalyzer
from postop_collector.analysis.pdf_extractor import PDFTextExtractor
from postop_collector.analysis.procedure_categorizer import ProcedureCategorizer
from postop_collector.analysis.timeline_parser import TimelineParser, TimelineEvent
from postop_collector.core.models import ProcedureType


class TestPDFTextExtractor:
    """Tests for PDF text extraction."""
    
    def test_extract_from_bytes_empty(self):
        """Test extraction from empty bytes."""
        extractor = PDFTextExtractor()
        result = extractor.extract_text_from_bytes(b"")
        
        assert result["text_content"] == ""
        assert result["page_count"] == 0
        assert result["confidence_score"] == 0.0
    
    def test_clean_text(self):
        """Test text cleaning."""
        extractor = PDFTextExtractor()
        
        dirty_text = """
        Page 1 of 10
        
        This    is    some     text
        With excessive  spaces
        Copyright © 2024
        """
        
        cleaned = extractor.clean_text(dirty_text)
        
        assert "Page 1 of 10" not in cleaned
        assert "Copyright" not in cleaned
        assert "  " not in cleaned  # No double spaces
    
    def test_extract_sections(self):
        """Test section extraction."""
        extractor = PDFTextExtractor()
        
        text = """
        POST-OPERATIVE INSTRUCTIONS
        
        After Surgery:
        Rest for 24 hours.
        
        Medications:
        Take pain medication as prescribed.
        
        Follow-up:
        See your doctor in 2 weeks.
        """
        
        sections = extractor.extract_sections(text)
        
        assert "after_surgery" in sections
        assert "medications" in sections
        assert "follow-up" in sections
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        extractor = PDFTextExtractor()
        
        # High confidence result
        good_result = {
            "text_content": "a" * 2000,  # Long text
            "extraction_method": "pdfplumber",
            "metadata": {"Title": "Surgery Guide"},
            "has_tables": True,
            "page_count": 5,
        }
        
        score = extractor._calculate_confidence(good_result)
        assert score > 0.7
        
        # Low confidence result
        poor_result = {
            "text_content": "short",
            "extraction_method": "ocr",
            "metadata": {},
            "has_tables": False,
            "page_count": 0,
        }
        
        score = extractor._calculate_confidence(poor_result)
        assert score < 0.5


class TestContentAnalyzer:
    """Tests for content analysis."""
    
    def test_analyze_empty_text(self):
        """Test analyzing empty text."""
        analyzer = ContentAnalyzer()
        result = analyzer.analyze("")
        
        assert result["is_post_operative"] == False
        assert result["relevance_score"] == 0.0
        assert result["content_quality"] == "low"
    
    def test_analyze_post_op_content(self):
        """Test analyzing post-operative content."""
        analyzer = ContentAnalyzer()
        
        text = """
        Post-Operative Instructions for Knee Replacement
        
        After your surgery, follow these instructions carefully:
        
        Medications:
        - Take pain medication every 4 hours
        - Continue antibiotics for 7 days
        
        Warning Signs:
        Call your doctor if you experience:
        - Fever over 101°F
        - Severe pain
        - Redness or swelling at the incision site
        
        Activity:
        - No weight bearing for 2 weeks
        - Use walker or crutches
        - Physical therapy starts week 3
        """
        
        result = analyzer.analyze(text)
        
        assert result["is_post_operative"] == True
        assert result["relevance_score"] > 0.5
        assert len(result["warning_signs"]) > 0
        assert len(result["medication_instructions"]) > 0
        assert result["content_quality"] in ["medium", "high"]
    
    def test_keyword_analysis(self):
        """Test keyword matching."""
        analyzer = ContentAnalyzer()
        
        text = "post-operative care after surgery recovery instructions"
        matches = analyzer._analyze_keywords(text)
        
        assert len(matches["primary"]) > 0
        assert "post-operative" in matches["primary"]
        assert "after surgery" in matches["primary"]
        assert "recovery" in matches["primary"]
    
    def test_extract_warning_signs(self):
        """Test warning sign extraction."""
        analyzer = ContentAnalyzer()
        
        text = """
        Call your doctor immediately if you have:
        - Temperature above 101°F
        - Increasing pain
        - Drainage from the incision
        
        Seek emergency care for chest pain or difficulty breathing.
        """
        
        signs = analyzer._extract_warning_signs(text)
        
        assert len(signs) > 0
        assert any("101" in sign for sign in signs)
        assert any("emergency" in sign.lower() for sign in signs)
    
    def test_quality_assessment(self):
        """Test content quality assessment."""
        analyzer = ContentAnalyzer()
        
        # High quality result
        good_result = {
            "relevance_score": 0.8,
            "warning_signs": ["sign1", "sign2"],
            "medication_instructions": ["med1", "med2"],
            "timeline_elements": ["day1", "week2"],
            "sections_found": ["intro", "meds", "activity", "follow-up", "warnings"],
            "statistics": {"word_count": 1500},
        }
        
        quality = analyzer._assess_quality(good_result)
        assert quality == "high"
        
        # Low quality result
        poor_result = {
            "relevance_score": 0.2,
            "warning_signs": [],
            "medication_instructions": [],
            "timeline_elements": [],
            "sections_found": [],
            "statistics": {"word_count": 50},
        }
        
        quality = analyzer._assess_quality(poor_result)
        assert quality == "low"


class TestTimelineParser:
    """Tests for timeline parsing."""
    
    def test_parse_empty_timeline(self):
        """Test parsing empty text."""
        parser = TimelineParser()
        events = parser.parse_timeline("")
        
        assert len(events) == 0
    
    def test_parse_timeline_events(self):
        """Test parsing timeline events."""
        parser = TimelineParser()
        
        text = """
        Day 1: Rest and take pain medication.
        Week 2: Begin physical therapy.
        After 6 weeks: Return to normal activities.
        3 months: Full recovery expected.
        """
        
        events = parser.parse_timeline(text)
        
        assert len(events) > 0
        assert events[0].time_value <= events[-1].time_value  # Sorted
        
        # Check specific events
        day_1_event = next((e for e in events if "Day 1" in e.time_reference), None)
        assert day_1_event is not None
        assert day_1_event.time_value == 1
    
    def test_time_reference_extraction(self):
        """Test extracting time references."""
        parser = TimelineParser()
        
        # Test various formats
        refs = parser._extract_time_references("Day 5 you can shower")
        assert len(refs) > 0
        assert refs[0] == ("Day 5", 5)
        
        refs = parser._extract_time_references("After 2 weeks return to work")
        assert len(refs) > 0
        assert any(r[1] == 14 for r in refs)  # 2 weeks = 14 days
        
        refs = parser._extract_time_references("First month is critical")
        assert len(refs) > 0
        assert any(r[1] == 30 for r in refs)  # 1 month = 30 days
    
    def test_event_categorization(self):
        """Test categorizing timeline events."""
        parser = TimelineParser()
        
        assert parser._categorize_event("Take medication twice daily") == "medication"
        assert parser._categorize_event("Follow-up appointment scheduled") == "appointment"
        assert parser._categorize_event("Begin walking exercises") == "activity"
        assert parser._categorize_event("Change wound dressing") == "wound_care"
        assert parser._categorize_event("Resume normal diet") == "diet"
    
    def test_recovery_schedule(self):
        """Test creating recovery schedule."""
        parser = TimelineParser()
        
        events = [
            TimelineEvent("Immediately", 0, "Rest", "activity", 0.9),
            TimelineEvent("Day 3", 3, "Remove bandage", "wound_care", 0.8),
            TimelineEvent("Week 2", 14, "Start PT", "activity", 0.9),
            TimelineEvent("Month 2", 60, "Full recovery", "general", 0.7),
        ]
        
        schedule = parser.create_recovery_schedule(events)
        
        assert "immediate" in schedule
        assert "first_week" in schedule
        assert "first_month" in schedule
        assert "second_month" in schedule
    
    def test_milestone_extraction(self):
        """Test extracting milestones."""
        parser = TimelineParser()
        
        events = [
            TimelineEvent("Week 2", 14, "Return to work", "activity", 0.9),
            TimelineEvent("Day 10", 10, "Start driving", "activity", 0.8),
            TimelineEvent("Week 1", 7, "Suture removal", "appointment", 0.9),
        ]
        
        milestones = parser.extract_milestones(events)
        
        assert len(milestones) > 0
        assert any(m["type"] == "return_to_work" for m in milestones)
        assert any(m["type"] == "driving" for m in milestones)
        assert any(m["type"] == "suture_removal" for m in milestones)


class TestProcedureCategorizer:
    """Tests for procedure categorization."""
    
    def test_categorize_empty(self):
        """Test categorizing empty text."""
        categorizer = ProcedureCategorizer()
        proc_type, confidence = categorizer.categorize("")
        
        assert proc_type == ProcedureType.UNKNOWN
        assert confidence == 0.0
    
    def test_categorize_orthopedic(self):
        """Test categorizing orthopedic procedures."""
        categorizer = ProcedureCategorizer()
        
        text = """
        Total Knee Replacement Post-Operative Instructions
        
        Your orthopedic surgeon performed a total knee arthroplasty.
        The prosthetic joint will require special care during recovery.
        """
        
        proc_type, confidence = categorizer.categorize(text)
        
        assert proc_type == ProcedureType.ORTHOPEDIC
        assert confidence > 0.5
    
    def test_categorize_cardiac(self):
        """Test categorizing cardiac procedures."""
        categorizer = ProcedureCategorizer()
        
        text = """
        Coronary Artery Bypass Graft (CABG) Recovery
        
        After your heart surgery, monitor for cardiac symptoms.
        Your cardiovascular system needs time to heal.
        """
        
        proc_type, confidence = categorizer.categorize(text)
        
        assert proc_type == ProcedureType.CARDIAC
        assert confidence > 0.5
    
    def test_categorize_multiple(self):
        """Test getting multiple categories."""
        categorizer = ProcedureCategorizer()
        
        text = """
        Post-operative care instructions following your procedure.
        Take medications as prescribed and rest.
        """
        
        results = categorizer.categorize_multiple(text, top_n=3)
        
        assert len(results) > 0
        assert results[0][0] == ProcedureType.UNKNOWN or results[0][1] < 0.3
    
    def test_extract_procedure_details(self):
        """Test extracting procedure details."""
        categorizer = ProcedureCategorizer()
        
        text = """
        Minimally Invasive Total Hip Replacement
        
        A robotic-assisted procedure was performed on your left hip.
        The ceramic implant was successfully placed.
        """
        
        details = categorizer.extract_procedure_details(text)
        
        assert details["procedure_name"] is not None
        assert "hip" in details["body_part"].lower()
        assert details["surgical_approach"] == "minimally invasive"
        assert len(details["implants_used"]) > 0
    
    def test_procedure_name_extraction(self):
        """Test extracting procedure names."""
        categorizer = ProcedureCategorizer()
        
        text = "underwent laparoscopic cholecystectomy and appendectomy"
        names = categorizer._extract_procedure_names(text)
        
        assert len(names) > 0
        assert any("cholecystectomy" in name.lower() for name in names)
        assert any("appendectomy" in name.lower() for name in names)