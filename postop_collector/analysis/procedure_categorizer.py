"""Procedure categorization module for classifying surgical procedures."""

import logging
import re
from typing import Dict, List, Optional, Tuple

from ..core.models import ProcedureType

logger = logging.getLogger(__name__)


class ProcedureCategorizer:
    """Categorizes surgical procedures based on text analysis."""
    
    def __init__(self):
        """Initialize categorizer with procedure patterns."""
        self.procedure_patterns = {
            ProcedureType.ORTHOPEDIC: {
                "keywords": [
                    "knee replacement", "hip replacement", "joint replacement",
                    "arthroscopy", "arthroscopic", "fracture", "bone",
                    "ligament", "tendon", "rotator cuff", "meniscus",
                    "spine", "spinal fusion", "disc", "vertebrae",
                    "shoulder", "ankle", "wrist", "elbow",
                    "total knee", "total hip", "TKA", "THA",
                    "ACL", "PCL", "MCL", "reconstruction"
                ],
                "specialties": ["orthopedic", "orthopaedic", "orthopedist"],
                "weight": 1.0
            },
            ProcedureType.CARDIAC: {
                "keywords": [
                    "heart", "cardiac", "coronary", "bypass", "CABG",
                    "valve", "angioplasty", "stent", "pacemaker",
                    "defibrillator", "ablation", "cardiovascular",
                    "aortic", "mitral", "tricuspid", "pulmonary",
                    "aneurysm", "arrhythmia", "atrial", "ventricular"
                ],
                "specialties": ["cardiac", "cardiology", "cardiovascular"],
                "weight": 1.0
            },
            ProcedureType.GENERAL: {
                "keywords": [
                    "appendectomy", "appendix", "gallbladder", "cholecystectomy",
                    "hernia", "inguinal", "umbilical", "hiatal",
                    "bowel", "intestine", "colon", "colectomy",
                    "hemorrhoid", "fistula", "abscess", "laparoscopy",
                    "laparoscopic", "abdominal", "stomach", "gastric"
                ],
                "specialties": ["general surgery", "general surgeon"],
                "weight": 0.9
            },
            ProcedureType.NEUROLOGICAL: {
                "keywords": [
                    "brain", "neurosurgery", "craniotomy", "tumor",
                    "aneurysm", "spine", "spinal cord", "nerve",
                    "disc", "laminectomy", "discectomy", "fusion",
                    "shunt", "epilepsy", "deep brain", "gamma knife"
                ],
                "specialties": ["neurosurgery", "neurological", "neurosurgeon"],
                "weight": 1.0
            },
            ProcedureType.UROLOGICAL: {
                "keywords": [
                    "prostate", "prostatectomy", "bladder", "kidney",
                    "ureter", "urethra", "stone", "lithotripsy",
                    "cystoscopy", "vasectomy", "hydrocele", "varicocele",
                    "incontinence", "urinary", "renal", "nephrectomy"
                ],
                "specialties": ["urology", "urological", "urologist"],
                "weight": 0.95
            },
            ProcedureType.GYNECOLOGICAL: {
                "keywords": [
                    "hysterectomy", "ovary", "ovarian", "uterus",
                    "fibroid", "endometriosis", "cesarean", "c-section",
                    "tubal", "cervical", "vaginal", "laparoscopy",
                    "myomectomy", "oophorectomy", "salpingectomy"
                ],
                "specialties": ["gynecology", "gynecological", "obstetrics"],
                "weight": 0.95
            },
            ProcedureType.PLASTIC: {
                "keywords": [
                    "reconstruction", "plastic surgery", "cosmetic",
                    "breast", "augmentation", "reduction", "lift",
                    "tummy tuck", "abdominoplasty", "liposuction",
                    "rhinoplasty", "facelift", "skin graft", "flap"
                ],
                "specialties": ["plastic surgery", "cosmetic", "reconstructive"],
                "weight": 0.9
            },
            ProcedureType.ENT: {
                "keywords": [
                    "tonsillectomy", "tonsil", "adenoidectomy", "adenoid",
                    "sinus", "septoplasty", "turbinate", "ear",
                    "tympanoplasty", "mastoidectomy", "thyroid",
                    "thyroidectomy", "laryngoscopy", "vocal", "throat"
                ],
                "specialties": ["ENT", "otolaryngology", "ear nose throat"],
                "weight": 0.95
            },
            ProcedureType.OPHTHALMIC: {
                "keywords": [
                    "cataract", "lens", "glaucoma", "retina",
                    "cornea", "LASIK", "PRK", "vision",
                    "eye surgery", "vitrectomy", "macular",
                    "strabismus", "pterygium", "blepharoplasty"
                ],
                "specialties": ["ophthalmology", "ophthalmic", "eye"],
                "weight": 0.95
            },
            ProcedureType.DENTAL: {
                "keywords": [
                    "tooth", "teeth", "extraction", "wisdom",
                    "implant", "dental", "oral surgery", "jaw",
                    "TMJ", "maxillofacial", "gum", "periodontal",
                    "root canal", "crown", "bridge"
                ],
                "specialties": ["dental", "oral surgery", "maxillofacial"],
                "weight": 0.9
            },
            ProcedureType.VASCULAR: {
                "keywords": [
                    "vascular", "artery", "vein", "aneurysm",
                    "carotid", "endovascular", "bypass", "graft",
                    "varicose", "thrombosis", "embolism", "stent",
                    "angiogram", "endarterectomy", "fistula"
                ],
                "specialties": ["vascular", "vascular surgery"],
                "weight": 0.95
            },
            ProcedureType.GASTROINTESTINAL: {
                "keywords": [
                    "gastric", "stomach", "esophagus", "intestinal",
                    "colostomy", "ileostomy", "bariatric", "sleeve",
                    "bypass", "band", "reflux", "GERD",
                    "endoscopy", "colonoscopy", "polyp", "resection"
                ],
                "specialties": ["gastroenterology", "GI", "bariatric"],
                "weight": 0.9
            }
        }
        
        # Common post-op terms that don't indicate specific procedures
        self.generic_terms = [
            "surgery", "procedure", "operation", "post-operative",
            "recovery", "incision", "anesthesia", "surgical"
        ]
    
    def categorize(self, text: str) -> Tuple[ProcedureType, float]:
        """
        Categorize the procedure type from text.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Tuple of (ProcedureType, confidence_score)
        """
        if not text:
            return ProcedureType.UNKNOWN, 0.0
        
        text_lower = text.lower()
        scores = self._calculate_scores(text_lower)
        
        if not scores:
            return ProcedureType.UNKNOWN, 0.0
        
        # Get the highest scoring category
        best_category = max(scores.items(), key=lambda x: x[1])
        procedure_type, score = best_category
        
        # Normalize score to 0-1 range
        confidence = min(1.0, score / 10.0)  # Assuming max score around 10
        
        # Require minimum confidence
        if confidence < 0.3:
            return ProcedureType.UNKNOWN, confidence
        
        return procedure_type, confidence
    
    def categorize_multiple(
        self, text: str, top_n: int = 3
    ) -> List[Tuple[ProcedureType, float]]:
        """
        Get multiple possible procedure categories.
        
        Args:
            text: Text content to analyze
            top_n: Number of top categories to return
            
        Returns:
            List of (ProcedureType, confidence_score) tuples
        """
        if not text:
            return [(ProcedureType.UNKNOWN, 0.0)]
        
        text_lower = text.lower()
        scores = self._calculate_scores(text_lower)
        
        if not scores:
            return [(ProcedureType.UNKNOWN, 0.0)]
        
        # Sort by score and get top N
        sorted_scores = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        # Normalize scores and filter low confidence
        results = []
        for proc_type, score in sorted_scores:
            confidence = min(1.0, score / 10.0)
            if confidence >= 0.2:  # Lower threshold for multiple results
                results.append((proc_type, confidence))
        
        if not results:
            results = [(ProcedureType.UNKNOWN, 0.0)]
        
        return results
    
    def _calculate_scores(self, text: str) -> Dict[ProcedureType, float]:
        """Calculate scores for each procedure type."""
        scores = {}
        
        for proc_type, patterns in self.procedure_patterns.items():
            score = 0.0
            
            # Check keywords
            for keyword in patterns["keywords"]:
                if keyword in text:
                    # Higher score for exact phrases
                    if " " in keyword:
                        score += 2.0 * patterns["weight"]
                    else:
                        score += 1.0 * patterns["weight"]
                    
                    # Bonus for multiple occurrences
                    count = text.count(keyword)
                    if count > 1:
                        score += min(count - 1, 3) * 0.5 * patterns["weight"]
            
            # Check specialty mentions
            for specialty in patterns["specialties"]:
                if specialty in text:
                    score += 3.0 * patterns["weight"]
            
            # Store score if significant
            if score > 0:
                scores[proc_type] = score
        
        return scores
    
    def extract_procedure_details(self, text: str) -> Dict:
        """
        Extract detailed procedure information.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary with procedure details
        """
        details = {
            "primary_procedure": None,
            "procedure_name": None,
            "body_part": None,
            "surgical_approach": None,
            "implants_used": [],
            "complexity": "standard",
        }
        
        text_lower = text.lower()
        
        # Extract specific procedure names
        procedure_names = self._extract_procedure_names(text_lower)
        if procedure_names:
            details["procedure_name"] = procedure_names[0]
            details["primary_procedure"] = procedure_names[0]
        
        # Extract body parts
        details["body_part"] = self._extract_body_part(text_lower)
        
        # Extract surgical approach
        details["surgical_approach"] = self._extract_approach(text_lower)
        
        # Extract implant information
        details["implants_used"] = self._extract_implants(text_lower)
        
        # Assess complexity
        details["complexity"] = self._assess_complexity(text_lower)
        
        return details
    
    def _extract_procedure_names(self, text: str) -> List[str]:
        """Extract specific procedure names."""
        procedures = []
        
        # Common procedure patterns
        procedure_patterns = [
            r"(?i)(total|partial)\s+(knee|hip|shoulder)\s+replacement",
            r"(?i)\w+ectomy",  # Matches appendectomy, cholecystectomy, etc.
            r"(?i)\w+oscopy",  # Matches arthroscopy, laparoscopy, etc.
            r"(?i)\w+plasty",  # Matches rhinoplasty, angioplasty, etc.
            r"(?i)(open|closed|percutaneous)\s+\w+\s+(repair|reduction)",
            r"(?i)(anterior|posterior|lateral)\s+\w+\s+(fusion|approach)",
        ]
        
        for pattern in procedure_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                procedure = match.group(0).strip()
                if procedure and len(procedure) > 5:
                    procedures.append(procedure.title())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_procedures = []
        for proc in procedures:
            if proc not in seen:
                seen.add(proc)
                unique_procedures.append(proc)
        
        return unique_procedures
    
    def _extract_body_part(self, text: str) -> Optional[str]:
        """Extract the primary body part involved."""
        body_parts = [
            "knee", "hip", "shoulder", "ankle", "wrist", "elbow",
            "spine", "back", "neck", "heart", "lung", "liver",
            "kidney", "bladder", "prostate", "uterus", "ovary",
            "stomach", "intestine", "colon", "gallbladder",
            "brain", "eye", "ear", "nose", "throat", "thyroid"
        ]
        
        for part in body_parts:
            if part in text:
                # Check for left/right specification
                if f"left {part}" in text:
                    return f"left {part}"
                elif f"right {part}" in text:
                    return f"right {part}"
                elif f"bilateral {part}" in text:
                    return f"bilateral {part}s"
                else:
                    return part
        
        return None
    
    def _extract_approach(self, text: str) -> Optional[str]:
        """Extract surgical approach information."""
        approaches = {
            "minimally invasive": ["minimally invasive", "arthroscopic", "laparoscopic", "endoscopic"],
            "open": ["open surgery", "open procedure", "traditional approach"],
            "robotic": ["robotic", "robot-assisted", "da vinci"],
            "percutaneous": ["percutaneous", "through the skin"],
        }
        
        for approach_type, keywords in approaches.items():
            for keyword in keywords:
                if keyword in text:
                    return approach_type
        
        return None
    
    def _extract_implants(self, text: str) -> List[str]:
        """Extract information about implants used."""
        implants = []
        
        implant_keywords = [
            "implant", "prosthesis", "prosthetic", "graft",
            "mesh", "plate", "screw", "rod", "pin",
            "stent", "valve", "pacemaker", "defibrillator"
        ]
        
        for keyword in implant_keywords:
            if keyword in text:
                implants.append(keyword)
        
        return implants
    
    def _assess_complexity(self, text: str) -> str:
        """Assess the complexity of the procedure."""
        complexity_indicators = {
            "complex": [
                "complex", "complicated", "extensive", "revision",
                "multi-level", "multiple", "combined", "staged"
            ],
            "moderate": [
                "standard", "routine", "typical", "conventional"
            ],
            "simple": [
                "simple", "minor", "straightforward", "uncomplicated"
            ]
        }
        
        for level, indicators in complexity_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    return level
        
        return "standard"