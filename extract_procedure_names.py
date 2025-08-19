#!/usr/bin/env python3
"""
Extract specific procedure names from PDFs and update procedure overviews CSV
"""

import pandas as pd
import re
import PyPDF2
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcedureNameExtractor:
    """Extract specific procedure names from PDF content"""
    
    def __init__(self):
        # Common procedure name patterns
        self.procedure_patterns = [
            # Specific procedure mentions
            r'(?:following|after|underwent|had|scheduled for)\s+(?:a|an|your)?\s*([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+){1,4}(?:\s+(?:surgery|procedure|operation|repair|replacement|removal|reconstruction|resection|fusion|arthroplasty|plasty)))',
            
            # Procedure type patterns
            r'(?:Total|Partial|Laparoscopic|Robotic|Arthroscopic|Open|Minimally Invasive)\s+([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+){0,3}(?:\s+(?:Replacement|Repair|Surgery|Procedure|Reconstruction)))',
            
            # Medical procedure abbreviations expanded
            r'\b(TKR|TKA|THR|THA|ACL|PCL|CABG|LAP|TURP|LASIK|PRK)\b.*?(?:\(([^)]+)\))?',
            
            # Specific anatomical procedures
            r'(?:Hip|Knee|Shoulder|Ankle|Spine|Back|Neck|Heart|Cardiac|Lung|Liver|Kidney|Gallbladder|Appendix|Hernia|Thyroid|Prostate)\s+(?:Replacement|Surgery|Repair|Procedure|Operation)',
            
            # Title/Header patterns
            r'^(?:Post[-\s]?(?:Op|Operative)|After|Following)\s+([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+){1,4})\s*(?:Instructions|Care|Guidelines)?',
            
            # Document title patterns
            r'(?:Instructions|Care|Guidelines)\s+(?:for|after|following)\s+([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+){1,4}(?:\s+(?:Surgery|Procedure|Operation)))',
        ]
        
        # Abbreviation expansions
        self.abbreviations = {
            'TKR': 'Total Knee Replacement',
            'TKA': 'Total Knee Arthroplasty',
            'THR': 'Total Hip Replacement',
            'THA': 'Total Hip Arthroplasty',
            'ACL': 'ACL Reconstruction',
            'PCL': 'PCL Reconstruction',
            'CABG': 'Coronary Artery Bypass Graft',
            'LAP': 'Laparoscopic Surgery',
            'TURP': 'Transurethral Resection of Prostate',
            'LASIK': 'LASIK Eye Surgery',
            'PRK': 'Photorefractive Keratectomy',
        }
        
        # Common procedure keywords to validate
        self.procedure_keywords = [
            'replacement', 'repair', 'surgery', 'procedure', 'operation',
            'reconstruction', 'resection', 'fusion', 'arthroplasty', 'plasty',
            'removal', 'excision', 'transplant', 'bypass', 'implant'
        ]
    
    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 3) -> str:
        """Extract text from first few pages of PDF"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for i, page in enumerate(reader.pages[:max_pages]):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except:
                        continue
            return text
        except Exception as e:
            logger.error(f"Error reading {pdf_path}: {e}")
            return ""
    
    def extract_procedure_name(self, text: str, filename: str = "") -> str:
        """Extract the most specific procedure name from text"""
        text = text[:3000]  # Focus on beginning of document
        
        # Clean filename for potential procedure info
        filename_clean = re.sub(r'[\[\]%\d]', ' ', filename)
        filename_clean = re.sub(r'[_-]', ' ', filename_clean)
        
        found_procedures = []
        
        # Try each pattern
        for pattern in self.procedure_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                procedure = match.group(1) if match.lastindex else match.group(0)
                
                # Clean up the procedure name
                procedure = procedure.strip()
                procedure = re.sub(r'\s+', ' ', procedure)
                
                # Check for abbreviations
                for abbr, full_name in self.abbreviations.items():
                    if abbr in procedure.upper():
                        procedure = full_name
                        break
                
                # Validate it's actually a procedure
                if any(keyword in procedure.lower() for keyword in self.procedure_keywords):
                    # Score based on specificity
                    score = len(procedure.split())
                    if 'total' in procedure.lower() or 'partial' in procedure.lower():
                        score += 2
                    if any(body_part in procedure.lower() for body_part in ['knee', 'hip', 'shoulder', 'heart', 'spine']):
                        score += 2
                    
                    found_procedures.append((procedure, score))
        
        # Also check filename for procedures
        for pattern in self.procedure_patterns[:4]:  # Use simpler patterns for filename
            match = re.search(pattern, filename_clean, re.IGNORECASE)
            if match:
                procedure = match.group(1) if match.lastindex else match.group(0)
                found_procedures.append((procedure, 1))  # Lower score for filename matches
        
        # Return the highest scoring procedure
        if found_procedures:
            found_procedures.sort(key=lambda x: x[1], reverse=True)
            best_procedure = found_procedures[0][0]
            
            # Title case formatting
            words = best_procedure.split()
            formatted = []
            for word in words:
                if word.upper() in self.abbreviations:
                    formatted.append(word.upper())
                elif word.lower() in ['of', 'the', 'and', 'or', 'for', 'with']:
                    formatted.append(word.lower())
                else:
                    formatted.append(word.capitalize())
            
            return ' '.join(formatted)
        
        return ""
    
    def update_procedure_overviews(self, csv_path: str, output_path: str):
        """Update procedure overviews CSV with extracted procedure names"""
        # Load existing CSV
        df = pd.read_csv(csv_path)
        
        # Add procedure_name column if it doesn't exist
        if 'procedure_name' not in df.columns:
            df['procedure_name'] = ''
        
        # Process each row
        for idx, row in df.iterrows():
            pdf_filename = row['pdf_filename']
            
            # Find the PDF file
            pdf_found = False
            for root, dirs, files in os.walk('agent_output/organized_pdfs'):
                if pdf_filename in files:
                    pdf_path = os.path.join(root, pdf_filename)
                    pdf_found = True
                    
                    # Extract text and procedure name
                    logger.info(f"Processing {pdf_filename}...")
                    text = self.extract_text_from_pdf(pdf_path)
                    
                    # Try to extract from PDF content
                    procedure_name = self.extract_procedure_name(text, pdf_filename)
                    
                    # If no procedure found in content, try the procedure description
                    if not procedure_name and row.get('procedure_description'):
                        procedure_name = self.extract_procedure_name(
                            row['procedure_description'], 
                            pdf_filename
                        )
                    
                    # If still no procedure, use the category/procedure with some cleanup
                    if not procedure_name:
                        if row.get('procedure') and row['procedure'] != row.get('category'):
                            procedure_name = row['procedure']
                        else:
                            # Try to extract from filename
                            filename_parts = pdf_filename.replace('.pdf', '').split('-')
                            for part in filename_parts:
                                if len(part) > 10 and not part.isdigit():
                                    procedure_name = part.replace('_', ' ').title()
                                    break
                    
                    df.at[idx, 'procedure_name'] = procedure_name
                    
                    if procedure_name:
                        logger.info(f"  ✓ Found: {procedure_name}")
                    else:
                        logger.info(f"  ✗ No specific procedure found")
                    
                    break
            
            if not pdf_found:
                logger.warning(f"PDF not found: {pdf_filename}")
        
        # Reorder columns to put procedure_name after pdf_filename
        cols = df.columns.tolist()
        if 'procedure_name' in cols:
            cols.remove('procedure_name')
            cols.insert(1, 'procedure_name')
            df = df[cols]
        
        # Save updated CSV
        df.to_csv(output_path, index=False)
        logger.info(f"\nSaved updated CSV to: {output_path}")
        
        # Print statistics
        total = len(df)
        with_names = len(df[df['procedure_name'].notna() & (df['procedure_name'] != '')])
        print(f"\n📊 Statistics:")
        print(f"  Total procedures: {total}")
        print(f"  With specific names: {with_names} ({with_names/total*100:.1f}%)")
        
        # Show sample of extracted names
        print(f"\n📋 Sample Procedure Names Extracted:")
        samples = df[df['procedure_name'].notna() & (df['procedure_name'] != '')].head(10)
        for _, row in samples.iterrows():
            print(f"  • {row['procedure_name'][:50]}")
            print(f"    File: {row['pdf_filename'][:60]}")


import os

def main():
    """Run procedure name extraction"""
    print("="*60)
    print("EXTRACTING SPECIFIC PROCEDURE NAMES")
    print("="*60)
    
    extractor = ProcedureNameExtractor()
    
    # Update the final clean CSV
    input_csv = 'analysis/outputs/clean_final/procedure_overviews_final.csv'
    output_csv = 'analysis/outputs/clean_final/procedure_overviews_final_with_names.csv'
    
    print(f"\n📂 Input: {input_csv}")
    print(f"📝 Output: {output_csv}")
    print("\nProcessing PDFs...")
    print("-"*40)
    
    extractor.update_procedure_overviews(input_csv, output_csv)
    
    print("\n✅ Procedure name extraction complete!")
    print(f"Updated CSV saved to: {output_csv}")


if __name__ == "__main__":
    main()