#!/usr/bin/env python3
"""
Enhanced PDF analyzer that captures fuller task descriptions
Processes PDFs to extract complete care instructions with context
"""

import os
import re
import pandas as pd
import PyPDF2
from pathlib import Path
import logging
from typing import List, Dict, Tuple
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedTaskExtractor:
    """Extract fuller, more descriptive care tasks from PDFs"""
    
    def __init__(self):
        # Enhanced patterns to capture more context
        self.instruction_patterns = [
            # Multi-sentence instructions (capture up to 3 sentences)
            r'(?:You (?:should|must|may|can|cannot|should not)|Do not|Avoid|Keep|Take|Apply|Change|Call|Contact|Return|Resume|Stop|Start|Continue|Limit|Elevate|Ice|Rest|Wear|Remove|Check|Monitor|Watch for|Report|Schedule)[^.!?]*[.!?](?:[^.!?]*[.!?]){0,2}',
            
            # Temporal instructions with context
            r'(?:For the first|During the first|After|Within|Before|Until|Once|When|While|As soon as)[^.!?]*[.!?](?:[^.!?]*[.!?]){0,2}',
            
            # Warning signs - capture full description
            r'(?:Call (?:your doctor|us|the office|911)|Seek (?:medical attention|emergency care)|Go to (?:emergency|the ER)|Contact)[^.!?]*[.!?](?:\s*(?:This|These|Signs|Symptoms)[^.!?]*[.!?]){0,2}',
            
            # Activity instructions with details
            r'(?:Do not (?:lift|drive|swim|bathe)|Avoid (?:lifting|driving|swimming)|No (?:lifting|driving|swimming))[^.!?]*[.!?](?:\s*[A-Z][^.!?]*[.!?]){0,1}',
            
            # Medication instructions - complete
            r'(?:Take|Use|Apply|Continue|Stop taking)[^.!?]*(?:medication|medicine|pills?|tablets?|dose|cream|ointment)[^.!?]*[.!?](?:[^.!?]*[.!?]){0,1}',
            
            # Wound care - full instructions
            r'(?:Change|Clean|Keep|Cover|Inspect|Watch)[^.!?]*(?:wound|incision|dressing|bandage|surgical site)[^.!?]*[.!?](?:[^.!?]*[.!?]){0,1}',
            
            # Exercise/therapy instructions
            r'(?:Perform|Do|Begin|Start|Continue)[^.!?]*(?:exercise|therapy|stretching|walking|movement)[^.!?]*[.!?](?:[^.!?]*[.!?]){0,1}',
            
            # Follow-up appointments
            r'(?:Schedule|Make|Call for|Return for|Follow.?up)[^.!?]*(?:appointment|visit|check.?up)[^.!?]*[.!?](?:[^.!?]*[.!?]){0,1}',
            
            # Bullet points with context (capture item + following explanation)
            r'^\s*[•·▪▫◦‣⁃\-\*]\s+[A-Z][^.!?\n]*[.!?](?:\s+[A-Z][^.!?\n]*[.!?])?',
            
            # Numbered instructions with details
            r'^\s*\d{1,2}[\.\)]\s*[A-Z][^.!?\n]*[.!?](?:\s+[A-Z][^.!?\n]*[.!?])?'
        ]
        
        self.compiled_patterns = [re.compile(p, re.MULTILINE | re.DOTALL) for p in self.instruction_patterns]
        
    def extract_pdf_text_with_structure(self, pdf_path: str) -> Dict[str, str]:
        """Extract text while preserving structure and context"""
        try:
            sections = {
                'full_text': '',
                'post_op_sections': [],
                'instruction_sections': []
            }
            
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                full_text = ""
                
                for page_num, page in enumerate(reader.pages[:15]):  # More pages for context
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            full_text += page_text + "\n\n"
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {e}")
                
                sections['full_text'] = full_text
                
                # Find specific sections
                section_headers = [
                    r'(?i)post.?operative\s+(?:care|instructions)',
                    r'(?i)after\s+(?:your\s+)?surgery',
                    r'(?i)discharge\s+instructions',
                    r'(?i)home\s+care',
                    r'(?i)recovery\s+(?:instructions|guidelines)',
                    r'(?i)what\s+to\s+expect',
                    r'(?i)activity\s+(?:restrictions|guidelines)',
                    r'(?i)wound\s+care',
                    r'(?i)pain\s+management',
                    r'(?i)when\s+to\s+call',
                    r'(?i)warning\s+signs',
                    r'(?i)follow.?up\s+care'
                ]
                
                for header_pattern in section_headers:
                    matches = re.finditer(header_pattern, full_text)
                    for match in matches:
                        start = match.start()
                        # Extract section (up to next section header or 2000 chars)
                        section_text = full_text[start:start+2000]
                        # Find next section header
                        next_header = re.search(r'\n[A-Z][A-Z\s]{3,}\n', section_text[100:])
                        if next_header:
                            section_text = section_text[:next_header.start()+100]
                        sections['instruction_sections'].append(section_text)
                
            return sections
            
        except Exception as e:
            logger.error(f"Error extracting from {pdf_path}: {e}")
            return {'full_text': '', 'post_op_sections': [], 'instruction_sections': []}
    
    def extract_complete_tasks(self, text_sections: Dict[str, str]) -> List[Dict]:
        """Extract complete task descriptions with context"""
        tasks = []
        seen_tasks = set()
        
        # First process instruction sections for better context
        for section in text_sections.get('instruction_sections', []):
            tasks.extend(self._extract_from_section(section, priority='high'))
        
        # Then process full text for anything missed
        if text_sections.get('full_text'):
            tasks.extend(self._extract_from_section(text_sections['full_text'], priority='medium'))
        
        # Deduplicate while keeping longer descriptions
        unique_tasks = []
        for task in tasks:
            # Create a simplified version for comparison
            simplified = re.sub(r'\s+', ' ', task['description'][:50].lower())
            
            # Check if we've seen a similar task
            is_duplicate = False
            for seen in seen_tasks:
                if seen in simplified or simplified in seen:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_tasks.add(simplified)
                unique_tasks.append(task)
        
        return unique_tasks
    
    def _extract_from_section(self, text: str, priority: str = 'medium') -> List[Dict]:
        """Extract tasks from a text section"""
        tasks = []
        
        # Clean text
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(?<=[a-z])(?=[A-Z])', '. ', text)  # Add periods between sentences
        
        for pattern in self.compiled_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                task_text = match.group(0).strip()
                
                # Quality filters
                if len(task_text) < 30:  # Too short
                    continue
                if len(task_text) > 1500:  # Too long (probably grabbed too much)
                    task_text = task_text[:1500] + "..."
                
                # Clean up the text
                task_text = re.sub(r'\s+', ' ', task_text)
                task_text = re.sub(r'^[\s\-\*\•\·\▪\▫\◦\‣\⁃]+', '', task_text)
                
                # Determine importance
                importance = priority
                if any(word in task_text.lower() for word in ['immediately', 'emergency', '911', 'urgent', 'severe']):
                    importance = 'critical'
                elif any(word in task_text.lower() for word in ['important', 'must', 'required', 'do not', 'avoid']):
                    importance = 'high'
                elif any(word in task_text.lower() for word in ['may', 'optional', 'if desired', 'as needed']):
                    importance = 'low'
                
                task = {
                    'description': task_text,
                    'importance': importance,
                    'length': len(task_text)
                }
                tasks.append(task)
        
        return tasks
    
    def enhance_existing_csv(self, input_csv: str, output_csv: str):
        """Re-process PDFs to get better descriptions"""
        # Load existing CSV
        df = pd.read_csv(input_csv)
        
        # Group by PDF to avoid re-processing same file multiple times
        pdf_groups = df.groupby('pdf_path')
        
        enhanced_rows = []
        processed_pdfs = set()
        
        for pdf_path, group in pdf_groups:
            if pdf_path in processed_pdfs:
                continue
                
            logger.info(f"Re-processing: {Path(pdf_path).name}")
            processed_pdfs.add(pdf_path)
            
            # Extract enhanced text
            text_sections = self.extract_pdf_text_with_structure(pdf_path)
            enhanced_tasks = self.extract_complete_tasks(text_sections)
            
            # Try to match enhanced tasks with existing ones
            for _, row in group.iterrows():
                row_dict = row.to_dict()
                
                # Find best matching enhanced task
                best_match = None
                best_score = 0
                
                original_desc = row_dict['task_description'][:50].lower()
                
                for task in enhanced_tasks:
                    # Simple matching based on overlap
                    if original_desc[:30] in task['description'].lower():
                        score = len(task['description'])
                        if score > best_score:
                            best_score = score
                            best_match = task
                
                if best_match:
                    row_dict['task_description'] = best_match['description']
                    row_dict['description_length'] = len(best_match['description'])
                    row_dict['enhanced'] = True
                else:
                    row_dict['description_length'] = len(row_dict['task_description'])
                    row_dict['enhanced'] = False
                
                enhanced_rows.append(row_dict)
        
        # Create enhanced dataframe
        enhanced_df = pd.DataFrame(enhanced_rows)
        
        # Save enhanced CSV
        enhanced_df.to_csv(output_csv, index=False)
        logger.info(f"Saved enhanced CSV to {output_csv}")
        
        # Print statistics
        print("\n" + "="*60)
        print("ENHANCEMENT STATISTICS")
        print("="*60)
        print(f"Total tasks: {len(enhanced_df)}")
        print(f"Enhanced tasks: {enhanced_df['enhanced'].sum()}")
        print(f"Average description length (original): {df['task_description'].str.len().mean():.1f}")
        print(f"Average description length (enhanced): {enhanced_df['description_length'].mean():.1f}")
        print(f"Max description length: {enhanced_df['description_length'].max()}")
        
        # Show samples
        print("\n" + "="*60)
        print("SAMPLE ENHANCED DESCRIPTIONS")
        print("="*60)
        
        samples = enhanced_df[enhanced_df['enhanced'] == True].sample(min(5, enhanced_df['enhanced'].sum()))
        for _, sample in samples.iterrows():
            print(f"\nProcedure: {sample['specific_procedure']}")
            print(f"Category: {sample['task_category']}")
            print(f"Description ({sample['description_length']} chars):")
            print(f"  {sample['task_description'][:300]}...")
            print("-"*40)
    
    def create_fresh_analysis(self, pdf_directory: str, output_csv: str):
        """Create a completely new analysis with enhanced descriptions"""
        logger.info("Starting fresh enhanced analysis...")
        
        all_tasks = []
        
        # Find all PDFs
        for root, dirs, files in os.walk(pdf_directory):
            for file in files:
                if file.endswith('.pdf'):
                    pdf_path = os.path.join(root, file)
                    
                    logger.info(f"Processing: {file}")
                    
                    # Extract text with structure
                    text_sections = self.extract_pdf_text_with_structure(pdf_path)
                    
                    # Extract enhanced tasks
                    tasks = self.extract_complete_tasks(text_sections)
                    
                    # Add metadata
                    for i, task in enumerate(tasks):
                        task_record = {
                            'pdf_filename': file,
                            'pdf_path': pdf_path,
                            'task_id': f"{Path(file).stem}_{i+1}",
                            'task_description': task['description'],
                            'description_length': task['length'],
                            'importance': task['importance']
                        }
                        all_tasks.append(task_record)
        
        # Save to CSV
        df = pd.DataFrame(all_tasks)
        df.to_csv(output_csv, index=False)
        
        print(f"\nExtracted {len(all_tasks)} enhanced tasks")
        print(f"Average description length: {df['description_length'].mean():.1f} characters")
        print(f"Saved to: {output_csv}")


def main():
    """Run enhancement on existing analysis"""
    extractor = EnhancedTaskExtractor()
    
    print("="*60)
    print("ENHANCING TASK DESCRIPTIONS")
    print("="*60)
    
    # Option 1: Enhance existing CSV
    print("\nEnhancing existing analysis...")
    extractor.enhance_existing_csv(
        input_csv='analysis/outputs/postop_care_analysis.csv',
        output_csv='analysis/outputs/postop_care_analysis_enhanced.csv'
    )
    
    print("\n✅ Enhancement complete!")
    print("Check: analysis/outputs/postop_care_analysis_enhanced.csv")


if __name__ == "__main__":
    main()