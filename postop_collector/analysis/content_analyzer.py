"""Content analysis module for post-operative PDFs."""

import logging
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Analyzes PDF content for post-operative relevance and quality."""
    
    def __init__(self):
        """Initialize content analyzer with keyword patterns."""
        self.post_op_keywords = {
            "primary": [
                "post-operative", "postoperative", "post operative",
                "after surgery", "following surgery", "recovery",
                "discharge instructions", "home care", "aftercare",
                "post-surgical", "postsurgical", "rehabilitation"
            ],
            "secondary": [
                "wound care", "incision", "sutures", "stitches", "staples",
                "dressing", "bandage", "pain management", "medication",
                "activity restrictions", "follow-up", "appointment",
                "symptoms", "complications", "emergency", "call doctor"
            ],
            "procedure_specific": [
                "knee replacement", "hip replacement", "cardiac surgery",
                "spine surgery", "shoulder surgery", "gallbladder",
                "appendectomy", "hernia repair", "cataract surgery",
                "arthroscopy", "laparoscopy", "bypass surgery"
            ]
        }
        
        self.warning_signs_patterns = [
            r"(?i)(call|contact|notify).{0,20}(doctor|physician|surgeon|911|emergency)",
            r"(?i)(seek|get).{0,20}(medical|emergency).{0,20}(attention|care|help)",
            r"(?i)warning.{0,10}signs?",
            r"(?i)red.{0,10}flags?",
            r"(?i)(fever|temperature).{0,20}(above|over|greater|\d+)",
            r"(?i)(severe|worsening|increasing).{0,20}(pain|discomfort)",
            r"(?i)(redness|swelling|drainage|bleeding).{0,20}(incision|wound|surgical site)",
            r"(?i)(shortness.{0,10}breath|chest.{0,10}pain|difficulty.{0,10}breathing)",
        ]
        
        self.medication_patterns = [
            r"(?i)take.{0,20}(tablet|pill|capsule|medication)",
            r"(?i)\d+.{0,10}(mg|mcg|ml).{0,20}(times|daily|twice|three)",
            r"(?i)(antibiotic|pain.{0,10}(medication|killer|reliever)|anti-inflammatory)",
            r"(?i)(prescription|over-the-counter|OTC)",
            r"(?i)(aspirin|ibuprofen|acetaminophen|tylenol|advil|motrin)",
            r"(?i)(opioid|narcotic|oxycodone|hydrocodone|morphine)",
            r"(?i)blood.{0,10}thinner",
        ]
        
        self.timeline_patterns = [
            r"(?i)(day|week|month)\s+(\d+|one|two|three|four|five|six)",
            r"(?i)(\d+|one|two|three|four|five|six).{0,10}(days?|weeks?|months?)",
            r"(?i)(first|second|third).{0,10}(day|week|month)",
            r"(?i)(24|48|72).{0,10}hours?",
            r"(?i)follow-up.{0,20}(\d+|one|two|three).{0,10}(days?|weeks?)",
            r"(?i)(immediately|right away|as soon as)",
        ]
    
    def analyze(self, text: str) -> Dict:
        """
        Perform comprehensive content analysis.
        
        Args:
            text: Extracted text from PDF
            
        Returns:
            Dictionary with analysis results
        """
        if not text or not text.strip():
            return self._empty_result()
        
        # Clean text for analysis
        text_lower = text.lower()
        
        result = {
            "is_post_operative": False,
            "relevance_score": 0.0,
            "content_quality": "low",
            "keyword_matches": {},
            "warning_signs": [],
            "medication_instructions": [],
            "timeline_elements": [],
            "procedure_types": [],
            "sections_found": [],
            "statistics": self._calculate_statistics(text),
        }
        
        # Analyze keyword presence
        result["keyword_matches"] = self._analyze_keywords(text_lower)
        
        # Calculate relevance score
        result["relevance_score"] = self._calculate_relevance_score(
            result["keyword_matches"],
            result["statistics"]
        )
        
        # Determine if content is post-operative
        result["is_post_operative"] = result["relevance_score"] > 0.5
        
        # Extract specific information
        result["warning_signs"] = self._extract_warning_signs(text)
        result["medication_instructions"] = self._extract_medications(text)
        result["timeline_elements"] = self._extract_timeline(text)
        result["procedure_types"] = self._identify_procedures(text)
        
        # Assess content quality
        result["content_quality"] = self._assess_quality(result)
        
        # Identify sections
        result["sections_found"] = self._identify_sections(text)
        
        return result
    
    def _empty_result(self) -> Dict:
        """Return empty analysis result."""
        return {
            "is_post_operative": False,
            "relevance_score": 0.0,
            "content_quality": "low",
            "keyword_matches": {},
            "warning_signs": [],
            "medication_instructions": [],
            "timeline_elements": [],
            "procedure_types": [],
            "sections_found": [],
            "statistics": {},
        }
    
    def _analyze_keywords(self, text: str) -> Dict[str, List[str]]:
        """Analyze keyword presence in text."""
        matches = {
            "primary": [],
            "secondary": [],
            "procedure_specific": []
        }
        
        for category, keywords in self.post_op_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    matches[category].append(keyword)
        
        return matches
    
    def _calculate_relevance_score(
        self,
        keyword_matches: Dict[str, List[str]],
        statistics: Dict
    ) -> float:
        """Calculate relevance score based on keyword matches and statistics."""
        score = 0.0
        
        # Primary keywords (40% weight)
        primary_count = len(keyword_matches.get("primary", []))
        if primary_count > 0:
            score += min(0.4, primary_count * 0.1)
        
        # Secondary keywords (30% weight)
        secondary_count = len(keyword_matches.get("secondary", []))
        if secondary_count > 0:
            score += min(0.3, secondary_count * 0.05)
        
        # Procedure-specific keywords (20% weight)
        procedure_count = len(keyword_matches.get("procedure_specific", []))
        if procedure_count > 0:
            score += min(0.2, procedure_count * 0.1)
        
        # Text length factor (10% weight)
        word_count = statistics.get("word_count", 0)
        if word_count > 500:
            score += 0.1
        elif word_count > 200:
            score += 0.05
        
        return min(1.0, score)
    
    def _extract_warning_signs(self, text: str) -> List[str]:
        """Extract warning signs and emergency instructions."""
        warning_signs = []
        
        for pattern in self.warning_signs_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Get context around the match (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()
                
                # Clean up the context
                context = re.sub(r"\s+", " ", context)
                if context and len(context) > 20:
                    warning_signs.append(context)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_signs = []
        for sign in warning_signs:
            if sign not in seen:
                seen.add(sign)
                unique_signs.append(sign)
        
        return unique_signs[:10]  # Limit to 10 most relevant
    
    def _extract_medications(self, text: str) -> List[str]:
        """Extract medication instructions."""
        medications = []
        
        for pattern in self.medication_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Get context around the match
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                # Clean up the context
                context = re.sub(r"\s+", " ", context)
                if context and len(context) > 15:
                    medications.append(context)
        
        # Remove duplicates
        seen = set()
        unique_meds = []
        for med in medications:
            if med not in seen:
                seen.add(med)
                unique_meds.append(med)
        
        return unique_meds[:15]  # Limit to 15 medications
    
    def _extract_timeline(self, text: str) -> List[str]:
        """Extract timeline and scheduling information."""
        timeline_elements = []
        
        for pattern in self.timeline_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Get context around the match
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 40)
                context = text[start:end].strip()
                
                # Clean up the context
                context = re.sub(r"\s+", " ", context)
                if context and len(context) > 10:
                    timeline_elements.append(context)
        
        # Remove duplicates and sort by timeline order
        seen = set()
        unique_timeline = []
        for element in timeline_elements:
            if element not in seen:
                seen.add(element)
                unique_timeline.append(element)
        
        return unique_timeline[:20]  # Limit to 20 timeline elements
    
    def _identify_procedures(self, text: str) -> List[str]:
        """Identify specific surgical procedures mentioned."""
        procedures = []
        text_lower = text.lower()
        
        procedure_keywords = [
            "knee replacement", "hip replacement", "total knee", "total hip",
            "cardiac surgery", "heart surgery", "bypass", "valve replacement",
            "spine surgery", "spinal fusion", "laminectomy", "discectomy",
            "shoulder surgery", "rotator cuff", "shoulder replacement",
            "gallbladder surgery", "cholecystectomy", "appendectomy",
            "hernia repair", "inguinal hernia", "umbilical hernia",
            "cataract surgery", "lens replacement", "eye surgery",
            "arthroscopy", "arthroscopic surgery", "laparoscopy",
            "hysterectomy", "prostatectomy", "mastectomy",
            "tonsillectomy", "adenoidectomy", "sinus surgery",
        ]
        
        for procedure in procedure_keywords:
            if procedure in text_lower:
                procedures.append(procedure.title())
        
        return list(set(procedures))  # Remove duplicates
    
    def _identify_sections(self, text: str) -> List[str]:
        """Identify major sections in the document."""
        sections = []
        
        section_headers = [
            "before surgery", "pre-operative",
            "after surgery", "post-operative",
            "medications", "prescriptions",
            "activity", "restrictions", "limitations",
            "diet", "nutrition", "eating",
            "wound care", "incision care",
            "follow-up", "appointments",
            "warning signs", "when to call",
            "recovery timeline", "what to expect",
            "pain management", "pain control",
            "discharge instructions", "going home",
            "physical therapy", "exercises",
        ]
        
        text_lower = text.lower()
        for header in section_headers:
            if header in text_lower:
                sections.append(header.title())
        
        return sections
    
    def _calculate_statistics(self, text: str) -> Dict:
        """Calculate text statistics."""
        words = text.split()
        sentences = re.split(r"[.!?]+", text)
        
        return {
            "character_count": len(text),
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "average_word_length": (
                sum(len(word) for word in words) / len(words)
                if words else 0
            ),
            "unique_words": len(set(word.lower() for word in words)),
        }
    
    def _assess_quality(self, result: Dict) -> str:
        """Assess overall content quality."""
        score = 0
        
        # Check relevance score
        if result["relevance_score"] > 0.7:
            score += 3
        elif result["relevance_score"] > 0.5:
            score += 2
        elif result["relevance_score"] > 0.3:
            score += 1
        
        # Check for important sections
        if len(result["warning_signs"]) > 0:
            score += 1
        if len(result["medication_instructions"]) > 0:
            score += 1
        if len(result["timeline_elements"]) > 0:
            score += 1
        if len(result["sections_found"]) > 3:
            score += 1
        
        # Check text length
        word_count = result["statistics"].get("word_count", 0)
        if word_count > 1000:
            score += 2
        elif word_count > 500:
            score += 1
        
        # Determine quality level
        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"
    
    def calculate_confidence_score(self, analysis_result: Dict) -> float:
        """
        Calculate overall confidence score for the analysis.
        
        Args:
            analysis_result: Result from analyze() method
            
        Returns:
            Confidence score between 0 and 1
        """
        if not analysis_result:
            return 0.0
        
        factors = []
        
        # Relevance score (40% weight)
        factors.append(analysis_result.get("relevance_score", 0) * 0.4)
        
        # Content quality (30% weight)
        quality_scores = {"high": 1.0, "medium": 0.6, "low": 0.3}
        quality = analysis_result.get("content_quality", "low")
        factors.append(quality_scores.get(quality, 0.3) * 0.3)
        
        # Information completeness (30% weight)
        info_score = 0
        if analysis_result.get("warning_signs"):
            info_score += 0.25
        if analysis_result.get("medication_instructions"):
            info_score += 0.25
        if analysis_result.get("timeline_elements"):
            info_score += 0.25
        if len(analysis_result.get("sections_found", [])) > 3:
            info_score += 0.25
        factors.append(info_score * 0.3)
        
        return sum(factors)