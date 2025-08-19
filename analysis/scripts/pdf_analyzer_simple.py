#!/usr/bin/env python3
"""
Simplified Post-Operative PDF Care Task Analyzer with Dynamic Category Discovery
Works without external AI APIs, using pattern matching and rule-based extraction
"""

import os
import re
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict, Counter
import hashlib

# PDF processing
import PyPDF2

# Data processing  
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimplePDFAnalyzer:
    """Analyzes post-operative PDFs using pattern matching"""
    
    def __init__(self):
        """Initialize the analyzer"""
        
        # Initial categories
        self.known_categories = {
            'wound_care': 'Wound Care',
            'medication': 'Medication Management', 
            'activity': 'Activity Restrictions',
            'physical_therapy': 'Physical Therapy',
            'diet': 'Diet & Nutrition',
            'hygiene': 'Hygiene',
            'monitoring': 'Monitoring',
            'follow_up': 'Follow-up Care',
            'emergency': 'Emergency Signs',
            'pain_management': 'Pain Management',
            'breathing': 'Breathing Exercises',
            'equipment': 'Equipment Management',
            'sleep': 'Sleep Positioning'
        }
        
        # Track discovered categories
        self.discovered_categories = {}
        self.uncategorized_tasks = []
        self.category_frequency = Counter()
        
        # Enhanced pattern library
        self.task_patterns = [
            # Direct instructions
            r'(?:You (?:should|must|may|can|cannot|should not)|Do not|Avoid|Keep|Take|Apply|Change|Call|Contact|Return|Resume|Stop|Start|Continue|Limit|Elevate|Ice|Rest|Wear|Remove|Check|Monitor|Watch for|Report|Schedule|Follow.?up)\s+[^.!?]{10,200}[.!?]',
            
            # Temporal instructions
            r'(?:For the first|During the first|After|Within|Before|Until|Once|When|While|As soon as)\s+[^.!?]{10,200}[.!?]',
            
            # Restrictions and permissions
            r'(?:No|Avoid|Do not|Don\'t|Cannot|Must not|Should not)\s+[^.!?]{10,150}[.!?]',
            r'(?:You may|You can|It is safe to|You are allowed to|Resume|Begin|Start)\s+[^.!?]{10,150}[.!?]',
            
            # Warning signs - critical
            r'(?:Call (?:your doctor|us|the office|911)|Seek (?:medical attention|emergency care)|Go to (?:emergency|the ER)|Contact (?:us|your surgeon) (?:if|when))[^.!?]{10,200}[.!?]',
            r'(?:Signs of (?:infection|complication)|Warning signs|Red flags)[^.!?]{10,200}[.!?]',
            
            # Specific care instructions
            r'(?:Change (?:your|the) (?:dressing|bandage)|Clean (?:the|your) (?:wound|incision))[^.!?]{5,150}[.!?]',
            r'(?:Take (?:your|pain) (?:medication|medicine)|Use (?:ice|heat))[^.!?]{5,150}[.!?]',
            
            # Activity-specific
            r'(?:Do not (?:lift|drive|swim|bathe)|Avoid (?:lifting|driving|swimming))[^.!?]{5,150}[.!?]',
            r'(?:Walk|Exercise|Stretch|Move)[^.!?]{10,150}[.!?]',
            
            # Diet instructions
            r'(?:Drink|Eat|Diet|Avoid (?:alcohol|caffeine))[^.!?]{10,150}[.!?]',
            
            # Numbered lists (more specific)
            r'^\s*\d{1,2}[\.\)]\s+[A-Z][^.!?]{10,200}[.!?]',
            
            # Bullet points with content
            r'^\s*[•·▪▫◦‣⁃]\s+[A-Z][^.!?]{10,200}[.!?]'
        ]
        
        # Compile patterns
        self.compiled_patterns = [re.compile(p, re.MULTILINE) for p in self.task_patterns]
        
        # Timing patterns
        self.timing_patterns = {
            'duration': r'for\s+(\d+)\s*(days?|weeks?|months?|hours?)',
            'frequency': r'(?:every|each)\s*(\d+)?\s*(hours?|days?|times?\s*(?:a|per)\s*day)',
            'start_time': r'(?:after|within|starting)\s*(\d+)?\s*(days?|weeks?|hours?)',
            'end_time': r'(?:until|before|for the first)\s*(\d+)?\s*(days?|weeks?|months?)'
        }
        
        # Category keywords (expanded)
        self.category_keywords = {
            'wound_care': ['wound', 'incision', 'dressing', 'bandage', 'suture', 'staple', 'drainage', 'steri-strip', 'stitches', 'surgical site', 'scar'],
            'medication': ['medication', 'medicine', 'pill', 'tablet', 'antibiotic', 'pain', 'painkiller', 'ibuprofen', 'acetaminophen', 'prescription', 'dose', 'tylenol', 'advil', 'narcotic', 'opioid'],
            'activity': ['activity', 'exercise', 'lift', 'weight', 'drive', 'driving', 'work', 'walk', 'stairs', 'bend', 'twist', 'sports', 'return to', 'resume'],
            'physical_therapy': ['therapy', 'stretching', 'strengthen', 'range of motion', 'rehabilitation', 'exercises', 'PT', 'physio'],
            'diet': ['eat', 'drink', 'food', 'diet', 'nutrition', 'fluid', 'water', 'alcohol', 'caffeine', 'meal', 'appetite', 'nausea'],
            'hygiene': ['shower', 'bath', 'bathe', 'wash', 'clean', 'hygiene', 'soap', 'wet', 'dry', 'towel'],
            'monitoring': ['monitor', 'check', 'temperature', 'fever', 'swelling', 'redness', 'discharge', 'vital', 'blood pressure', 'watch for', 'observe'],
            'follow_up': ['appointment', 'follow-up', 'follow up', 'visit', 'doctor', 'surgeon', 'clinic', 'check-up', 'return visit', 'schedule'],
            'emergency': ['emergency', 'immediately', '911', 'urgent', 'severe', 'hospital', 'ER', 'chest pain', 'shortness of breath', 'excessive bleeding'],
            'pain_management': ['pain', 'discomfort', 'ice', 'heat', 'elevate', 'rest', 'comfortable', 'ache', 'sore'],
            'breathing': ['breath', 'breathing', 'spirometer', 'cough', 'deep breath', 'lung', 'respiratory', 'inhale', 'exhale'],
            'equipment': ['brace', 'crutches', 'walker', 'compression', 'device', 'machine', 'cpap', 'drain', 'catheter', 'splint', 'cast'],
            'sleep': ['sleep', 'position', 'elevate', 'pillow', 'lying', 'side', 'back', 'stomach', 'bed']
        }
        
        # New category discovery keywords
        self.discovery_keywords = {
            'sexual_activity': ['sexual', 'intercourse', 'intimacy', 'sex'],
            'travel': ['travel', 'fly', 'airplane', 'altitude', 'car ride', 'trip'],
            'work_return': ['work', 'job', 'occupation', 'return to work', 'disability', 'desk', 'manual labor'],
            'scar_care': ['scar', 'massage', 'sunscreen', 'moisturize', 'vitamin e'],
            'mental_health': ['mood', 'depression', 'anxiety', 'memory', 'cognitive', 'emotional'],
            'pet_care': ['pet', 'animal', 'cat', 'dog', 'litter'],
            'insurance': ['insurance', 'form', 'paperwork', 'documentation', 'claim', 'billing'],
            'bowel_bladder': ['bowel', 'bladder', 'constipation', 'urination', 'stool', 'bathroom'],
            'smoking': ['smoking', 'tobacco', 'nicotine', 'cigarette', 'vaping'],
            'dental': ['dental', 'teeth', 'mouth', 'oral'],
            'vision': ['vision', 'eye', 'glasses', 'contact lens', 'sight'],
            'hearing': ['hearing', 'ear', 'sound', 'deaf']
        }
        
        # Results storage
        self.results = []
        self.overview_results = []
        self.category_discoveries = []
        
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(reader.pages[:10]):  # Limit to first 10 pages
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {str(e)}")
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Fix common OCR issues
        text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)  # Add space between camelCase
        # Remove page numbers and headers/footers
        text = re.sub(r'Page \d+|^\d+$', '', text, flags=re.MULTILINE)
        return text.strip()
    
    def parse_care_tasks(self, text: str) -> List[Dict]:
        """Extract care tasks from text using patterns"""
        tasks = []
        text = self.clean_text(text)
        
        # Track what we've already extracted to avoid duplicates
        seen_tasks = set()
        
        for pattern in self.compiled_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                task_text = match.group(0).strip()
                
                # Filter out noise
                if len(task_text) < 20 or len(task_text) > 500:
                    continue
                    
                # Check for duplicate
                task_hash = hashlib.md5(task_text.lower().encode()).hexdigest()[:8]
                if task_hash in seen_tasks:
                    continue
                    
                seen_tasks.add(task_hash)
                
                # Determine importance based on keywords
                importance = 'medium'
                if any(word in task_text.lower() for word in ['immediately', 'emergency', '911', 'urgent']):
                    importance = 'critical'
                elif any(word in task_text.lower() for word in ['important', 'must', 'required', 'necessary']):
                    importance = 'high'
                elif any(word in task_text.lower() for word in ['may', 'optional', 'if desired']):
                    importance = 'low'
                
                task = {
                    'description': task_text,
                    'raw_text': task_text,
                    'importance': importance,
                    'method': 'pattern'
                }
                tasks.append(task)
        
        return tasks
    
    def categorize_task(self, task: Dict) -> Tuple[str, str]:
        """Categorize a task and return category and subcategory"""
        description = task['description'].lower()
        
        # Check known categories
        best_match = None
        best_score = 0
        
        for cat_key, keywords in self.category_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in description)
            if matches > best_score:
                best_score = matches
                best_match = self.known_categories[cat_key]
        
        # Check for new categories
        for cat_key, keywords in self.discovery_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in description)
            if matches > 0 and matches >= best_score:
                category_name = cat_key.replace('_', ' ').title()
                self.handle_new_category(category_name, task['description'])
                return category_name, ''
        
        if best_match:
            self.category_frequency[best_match] += 1
            return best_match, ''
        
        # If no match, mark as uncategorized
        self.uncategorized_tasks.append(task)
        return "Uncategorized", ''
    
    def handle_new_category(self, category_name: str, example_task: str):
        """Handle discovery of a new category"""
        if category_name not in self.discovered_categories:
            self.discovered_categories[category_name] = {
                'first_discovered': datetime.now().isoformat(),
                'examples': [],
                'frequency': 0
            }
            logger.info(f"🎯 NEW CATEGORY DISCOVERED: {category_name}")
        
        self.discovered_categories[category_name]['examples'].append(example_task[:100])
        self.discovered_categories[category_name]['frequency'] += 1
        self.category_frequency[category_name] += 1
    
    def extract_timing_info(self, text: str) -> Dict:
        """Extract timing information from task text"""
        timing = {
            'duration': '',
            'frequency': '',
            'start_time': '',
            'end_time': ''
        }
        
        for key, pattern in self.timing_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                timing[key] = match.group(0)
        
        return timing
    
    def extract_procedure_overview(self, text: str, pdf_name: str) -> Dict:
        """Extract procedure overview information"""
        text = self.clean_text(text)
        
        overview = {
            'pdf_filename': pdf_name,
            'procedure_description': '',
            'typical_duration': '',
            'anesthesia_type': '',
            'hospital_stay': '',
            'recovery_timeline': '',
            'risks_mentioned': []
        }
        
        # Look for procedure description in first part of document
        sentences = text.split('.')[:20]  # First 20 sentences
        for sentence in sentences:
            if len(sentence) > 50 and any(word in sentence.lower() for word in ['procedure', 'surgery', 'operation']):
                overview['procedure_description'] = sentence.strip()[:500]
                break
        
        # Extract specific information
        duration_match = re.search(r'(?:procedure|surgery|operation)\s+(?:takes?|lasts?|duration)[:\s]+(?:about|approximately)?\s*(\d+\s*(?:hours?|minutes?))', text, re.IGNORECASE)
        if duration_match:
            overview['typical_duration'] = duration_match.group(1)
        
        anesthesia_match = re.search(r'(general|local|regional|spinal|epidural|sedation)\s+(?:anesthesia|anaesthesia)', text, re.IGNORECASE)
        if anesthesia_match:
            overview['anesthesia_type'] = anesthesia_match.group(1)
        
        stay_match = re.search(r'hospital\s+stay[:\s]+(\d+\s*(?:days?|nights?|hours?))', text, re.IGNORECASE)
        if stay_match:
            overview['hospital_stay'] = stay_match.group(1)
        
        recovery_match = re.search(r'(?:full|complete)?\s*recovery[:\s]+(?:takes?|is|expected)?\s*(?:about|approximately)?\s*(\d+\s*(?:days?|weeks?|months?))', text, re.IGNORECASE)
        if recovery_match:
            overview['recovery_timeline'] = recovery_match.group(1)
        
        # Extract risks
        risk_keywords = ['bleeding', 'infection', 'blood clot', 'nerve damage', 'scarring', 'anesthesia reaction', 'complications']
        risks = [risk for risk in risk_keywords if risk in text.lower()]
        overview['risks_mentioned'] = risks
        
        return overview
    
    def analyze_pdf(self, pdf_path: str, procedure_info: Dict) -> Tuple[List[Dict], Dict]:
        """Analyze a single PDF"""
        logger.info(f"Analyzing: {Path(pdf_path).name}")
        
        # Extract text
        text = self.extract_pdf_text(pdf_path)
        if not text or len(text) < 100:
            logger.warning(f"Insufficient text from {pdf_path}")
            return [], {}
        
        # Extract overview
        overview = self.extract_procedure_overview(text, Path(pdf_path).name)
        overview.update(procedure_info)
        
        # Extract tasks
        tasks = self.parse_care_tasks(text)
        
        # Process tasks
        processed_tasks = []
        for i, task in enumerate(tasks):
            # Categorize
            category, subcategory = self.categorize_task(task)
            
            # Extract timing
            timing = self.extract_timing_info(task['description'])
            
            # Check for special equipment mentions
            equipment = ''
            equipment_keywords = ['brace', 'crutches', 'walker', 'compression', 'splint', 'device']
            for keyword in equipment_keywords:
                if keyword in task['description'].lower():
                    equipment = keyword
                    break
            
            # Check for follow-up requirement
            follow_up = any(word in task['description'].lower() for word in ['appointment', 'follow-up', 'visit', 'return'])
            
            # Create record
            task_record = {
                'pdf_filename': Path(pdf_path).name,
                'pdf_path': str(pdf_path),
                'procedure_category': procedure_info.get('category', ''),
                'specific_procedure': procedure_info.get('procedure', ''),
                'confidence_score': procedure_info.get('confidence', 0),
                'task_id': f"{Path(pdf_path).stem}_{i+1}",
                'task_category': category,
                'task_subcategory': subcategory,
                'task_description': task['description'][:500],
                'timing': timing.get('start_time', ''),
                'frequency': timing.get('frequency', ''),
                'duration': timing.get('duration', ''),
                'importance_level': task.get('importance', 'medium'),
                'prerequisites': '',
                'contraindications': '',
                'warning_signs': '',
                'special_equipment': equipment,
                'provider_contact': '',
                'follow_up_required': follow_up,
                'notes': task.get('method', ''),
                'is_new_category': category in self.discovered_categories
            }
            
            processed_tasks.append(task_record)
        
        return processed_tasks, overview
    
    def save_results(self, tasks: List[Dict], overviews: List[Dict], errors: List[Dict], output_dir: str):
        """Save analysis results to CSV files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save main task analysis
        if tasks:
            df_tasks = pd.DataFrame(tasks)
            output_path = f"{output_dir}/postop_care_analysis.csv"
            df_tasks.to_csv(output_path, index=False)
            logger.info(f"Saved {len(tasks)} tasks to {output_path}")
        
        # Save procedure overviews
        if overviews:
            df_overviews = pd.DataFrame(overviews)
            output_path = f"{output_dir}/procedure_overviews.csv"
            df_overviews.to_csv(output_path, index=False)
            logger.info(f"Saved {len(overviews)} overviews to {output_path}")
        
        # Save discovered categories
        if self.discovered_categories:
            category_data = []
            for cat_name, cat_info in self.discovered_categories.items():
                category_data.append({
                    'category_name': cat_name,
                    'first_discovered': cat_info['first_discovered'],
                    'frequency_count': cat_info['frequency'],
                    'example_tasks': '; '.join(cat_info['examples'][:3]),
                    'confidence': 'high' if cat_info['frequency'] > 10 else 'medium'
                })
            
            df_categories = pd.DataFrame(category_data)
            output_path = f"{output_dir}/discovered_categories.csv"
            df_categories.to_csv(output_path, index=False)
            logger.info(f"Saved {len(self.discovered_categories)} discovered categories")
        
        # Save error report
        if errors:
            df_errors = pd.DataFrame(errors)
            output_path = f"{output_dir}/error_report.csv"
            df_errors.to_csv(output_path, index=False)
            logger.warning(f"Saved {len(errors)} errors")
        
        # Save category frequency
        freq_data = dict(self.category_frequency)
        output_path = f"{output_dir}/category_frequency.json"
        with open(output_path, 'w') as f:
            json.dump(freq_data, f, indent=2)
        logger.info(f"Saved category frequency analysis")
    
    def print_summary(self, tasks: List[Dict]):
        """Print analysis summary"""
        print("\n" + "="*60)
        print("📊 PDF CARE TASK ANALYSIS SUMMARY")
        print("="*60)
        
        if not tasks:
            print("No tasks extracted")
            return
        
        print(f"\n📈 Task Extraction:")
        print(f"  • Total tasks extracted: {len(tasks)}")
        unique_pdfs = len(set(t['pdf_filename'] for t in tasks))
        print(f"  • PDFs analyzed: {unique_pdfs}")
        print(f"  • Average tasks per PDF: {len(tasks) / unique_pdfs:.1f}")
        
        print(f"\n📁 Category Distribution:")
        for category, count in self.category_frequency.most_common(15):
            percentage = (count / len(tasks)) * 100
            print(f"  • {category}: {count} ({percentage:.1f}%)")
        
        if self.discovered_categories:
            print(f"\n🎯 New Categories Discovered: {len(self.discovered_categories)}")
            for cat_name in list(self.discovered_categories.keys())[:10]:
                print(f"  • {cat_name}")
        
        uncategorized = sum(1 for t in tasks if t['task_category'] == 'Uncategorized')
        if uncategorized:
            print(f"\n⚠️  Uncategorized tasks: {uncategorized} ({(uncategorized/len(tasks))*100:.1f}%)")
        
        # Show importance distribution
        importance_counts = Counter(t['importance_level'] for t in tasks)
        print(f"\n🎨 Task Importance:")
        for level, count in importance_counts.most_common():
            print(f"  • {level}: {count}")
        
        print("\n✅ Analysis complete! Check 'analysis/outputs' for detailed CSV files.")
        print("="*60)