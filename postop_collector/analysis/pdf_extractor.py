"""PDF text extraction and processing module."""

import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pdfplumber
import PyPDF2
from PIL import Image
from pdfplumber.page import Page

logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """Extracts text and metadata from PDF files."""
    
    def __init__(self, enable_ocr: bool = False):
        """
        Initialize PDF text extractor.
        
        Args:
            enable_ocr: Whether to enable OCR for scanned PDFs
        """
        self.enable_ocr = enable_ocr
        if enable_ocr:
            try:
                import pytesseract
                self.pytesseract = pytesseract
            except ImportError:
                logger.warning("pytesseract not installed, OCR disabled")
                self.enable_ocr = False
                self.pytesseract = None
    
    def extract_text_from_file(self, file_path: Union[str, Path]) -> Dict:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        with open(file_path, "rb") as f:
            return self.extract_text_from_bytes(f.read())
    
    def extract_text_from_bytes(self, pdf_content: bytes) -> Dict:
        """
        Extract text from PDF bytes.
        
        Args:
            pdf_content: PDF content as bytes
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        result = {
            "text_content": "",
            "page_count": 0,
            "extraction_method": "standard",
            "has_images": False,
            "has_tables": False,
            "page_texts": [],
            "tables": [],
            "images": [],
            "metadata": {},
            "confidence_score": 0.0,
        }
        
        # Try pdfplumber first (better for tables and layout)
        try:
            result = self._extract_with_pdfplumber(pdf_content, result)
            if result["text_content"].strip():
                result["extraction_method"] = "pdfplumber"
                result["confidence_score"] = self._calculate_confidence(result)
                return result
        except Exception as e:
            logger.debug(f"pdfplumber extraction failed: {e}")
        
        # Fallback to PyPDF2
        try:
            result = self._extract_with_pypdf2(pdf_content, result)
            if result["text_content"].strip():
                result["extraction_method"] = "pypdf2"
                result["confidence_score"] = self._calculate_confidence(result)
                return result
        except Exception as e:
            logger.debug(f"PyPDF2 extraction failed: {e}")
        
        # If OCR is enabled and text extraction failed, try OCR
        if self.enable_ocr and not result["text_content"].strip():
            try:
                result = self._extract_with_ocr(pdf_content, result)
                result["extraction_method"] = "ocr"
            except Exception as e:
                logger.error(f"OCR extraction failed: {e}")
        
        result["confidence_score"] = self._calculate_confidence(result)
        return result
    
    def _extract_with_pdfplumber(
        self, pdf_content: bytes, result: Dict
    ) -> Dict:
        """Extract text using pdfplumber."""
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            result["page_count"] = len(pdf.pages)
            
            # Extract metadata
            if pdf.metadata:
                result["metadata"] = {
                    k: str(v) for k, v in pdf.metadata.items()
                    if v is not None
                }
            
            all_text = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                page_text = page.extract_text() or ""
                all_text.append(page_text)
                result["page_texts"].append({
                    "page": page_num,
                    "text": page_text,
                    "char_count": len(page_text),
                })
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    result["has_tables"] = True
                    for table_idx, table in enumerate(tables):
                        result["tables"].append({
                            "page": page_num,
                            "table_index": table_idx,
                            "data": table,
                            "rows": len(table),
                            "cols": len(table[0]) if table else 0,
                        })
                
                # Check for images
                if page.images:
                    result["has_images"] = True
                    for img in page.images:
                        result["images"].append({
                            "page": page_num,
                            "bbox": img.get("bbox"),
                            "width": img.get("width"),
                            "height": img.get("height"),
                        })
            
            result["text_content"] = "\n\n".join(all_text)
        
        return result
    
    def _extract_with_pypdf2(
        self, pdf_content: bytes, result: Dict
    ) -> Dict:
        """Extract text using PyPDF2."""
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        result["page_count"] = len(pdf_reader.pages)
        
        # Extract metadata
        if pdf_reader.metadata:
            result["metadata"] = {
                k[1:] if k.startswith("/") else k: str(v)
                for k, v in pdf_reader.metadata.items()
                if v is not None
            }
        
        all_text = []
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            # Extract text
            page_text = page.extract_text()
            all_text.append(page_text)
            result["page_texts"].append({
                "page": page_num,
                "text": page_text,
                "char_count": len(page_text),
            })
            
            # Check for images
            if "/XObject" in page.get("/Resources", {}):
                xobjects = page["/Resources"]["/XObject"].get_object()
                for obj in xobjects:
                    if xobjects[obj]["/Subtype"] == "/Image":
                        result["has_images"] = True
                        break
        
        result["text_content"] = "\n\n".join(all_text)
        return result
    
    def _extract_with_ocr(
        self, pdf_content: bytes, result: Dict
    ) -> Dict:
        """Extract text using OCR (requires pytesseract)."""
        if not self.pytesseract:
            return result
        
        import fitz  # PyMuPDF for image conversion
        
        try:
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            result["page_count"] = len(pdf_document)
            
            all_text = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Convert page to image
                mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.pil_tobytes(format="PNG")
                image = Image.open(BytesIO(img_data))
                
                # Perform OCR
                page_text = self.pytesseract.image_to_string(image)
                all_text.append(page_text)
                
                result["page_texts"].append({
                    "page": page_num + 1,
                    "text": page_text,
                    "char_count": len(page_text),
                    "ocr": True,
                })
                
                result["has_images"] = True
            
            result["text_content"] = "\n\n".join(all_text)
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
        
        return result
    
    def _calculate_confidence(self, result: Dict) -> float:
        """
        Calculate confidence score for extracted text.
        
        Args:
            result: Extraction result dictionary
            
        Returns:
            Confidence score between 0 and 1
        """
        score = 0.0
        factors = []
        
        # Text length factor
        text_length = len(result["text_content"])
        if text_length > 1000:
            factors.append(1.0)
        elif text_length > 500:
            factors.append(0.8)
        elif text_length > 100:
            factors.append(0.6)
        elif text_length > 0:
            factors.append(0.3)
        else:
            return 0.0
        
        # Extraction method factor
        method_scores = {
            "pdfplumber": 1.0,
            "pypdf2": 0.9,
            "standard": 0.7,
            "ocr": 0.6,
        }
        factors.append(method_scores.get(result["extraction_method"], 0.5))
        
        # Metadata presence
        if result.get("metadata"):
            factors.append(0.1)
        
        # Tables presence (good for structured content)
        if result.get("has_tables"):
            factors.append(0.1)
        
        # Page count reasonableness
        page_count = result.get("page_count", 0)
        if 1 <= page_count <= 50:
            factors.append(0.1)
        
        # Calculate weighted average
        if factors:
            score = sum(factors) / len(factors)
        
        return min(1.0, score)
    
    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        Extract common sections from medical PDF text.
        
        Args:
            text: Full text content
            
        Returns:
            Dictionary of section names to content
        """
        sections = {}
        
        # Common section headers in medical PDFs
        section_patterns = [
            r"(?i)(before\s+surgery|pre-?operative\s+instructions?)",
            r"(?i)(after\s+surgery|post-?operative\s+instructions?)",
            r"(?i)(medications?|prescriptions?)",
            r"(?i)(activity\s+restrictions?|physical\s+limitations?)",
            r"(?i)(diet|nutrition|eating)",
            r"(?i)(wound\s+care|incision\s+care)",
            r"(?i)(follow-?up|appointments?)",
            r"(?i)(warning\s+signs?|when\s+to\s+call|emergency)",
            r"(?i)(recovery\s+timeline|what\s+to\s+expect)",
            r"(?i)(pain\s+management|pain\s+control)",
        ]
        
        lines = text.split("\n")
        current_section = "introduction"
        current_content = []
        
        for line in lines:
            # Check if line matches any section pattern
            matched_section = None
            for pattern in section_patterns:
                if re.search(pattern, line):
                    # Save previous section
                    if current_content:
                        sections[current_section] = "\n".join(current_content)
                    
                    # Start new section
                    matched_section = re.search(pattern, line).group(0)
                    current_section = matched_section.lower().replace(" ", "_")
                    current_content = [line]
                    break
            
            if not matched_section and line.strip():
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content)
        
        return sections
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        
        # Remove page numbers (common patterns)
        text = re.sub(r"(?i)page\s+\d+\s+of\s+\d+", "", text)
        text = re.sub(r"^\d+$", "", text, flags=re.MULTILINE)
        
        # Remove common headers/footers
        text = re.sub(
            r"(?i)(confidential|proprietary|copyright.*\d{4})",
            "",
            text
        )
        
        # Fix common OCR errors
        replacements = {
            "  ": " ",
            "¬": "",
            "™": "",
            "®": "",
            "©": "",
            "\x00": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove lines that are mostly special characters
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            if line.strip():
                special_char_ratio = sum(
                    1 for c in line if not c.isalnum() and not c.isspace()
                ) / len(line)
                if special_char_ratio < 0.5:  # Less than 50% special chars
                    cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines).strip()