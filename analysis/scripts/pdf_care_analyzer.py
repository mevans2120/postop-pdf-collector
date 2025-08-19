#!/usr/bin/env python3
"""
Post-Operative PDF Care Task Analyzer with Dynamic Category Discovery
Analyzes PDFs to extract care tasks, metadata, and discovers new categories
"""

import os
import re
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime
from collections import defaultdict, Counter
import hashlib

# PDF processing
import PyPDF2
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams

# AI/NLP
import google.generativeai as genai

# Data processing
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analysis/outputs/analysis_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PDFCareAnalyzer:
    """Analyzes post-operative PDFs to extract care tasks and metadata"""
    
    def __init__(self, gemini_api_key: str = None):
        """Initialize the analyzer with AI capabilities"""
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            logger.warning("No Gemini API key provided - AI features disabled")
        
        # Initial categories (will expand during analysis)
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
            'pain_management': 'Pain Management'
        }
        
        # Track discovered categories
        self.discovered_categories = {}
        self.uncategorized_tasks = []
        self.category_frequency = Counter()
        
        # Pattern library for task extraction
        self.task_patterns = [
            # Instructions
            r'(?:You (?:should|must|may|can|cannot|should not)|Do not|Avoid|Keep|Take|Apply|Change|Call|Contact|Return|Resume|Stop|Start|Continue|Limit|Elevate|Ice|Rest|Wear|Remove|Check|Monitor|Watch for|Report|Schedule|Follow up)\s+[^.!?]+[.!?]',
            # Temporal patterns
            r'(?:For the first|During the first|After|Within|Before|Until|Once|When|While|As soon as)\s+[^.!?]+[.!?]',
            # Restrictions
            r'(?:No|Avoid|Do not|Don\'t|Cannot|Must not|Should not)\s+[^.!?]+(?:for|until|before|after)\s+[^.!?]+[.!?]',
            # Permissions
            r'(?:You may|You can|It is safe to|You are allowed to|Resume|Begin|Start)\s+[^.!?]+(?:after|once|when)\s+[^.!?]+[.!?]',
            # Warning signs
            r'(?:Call your doctor if|Seek medical attention if|Go to emergency if|Contact us if|Signs of infection include|Warning signs include)\s+[^.!?]+[.!?]',
            # Numbered lists
            r'^\s*\d+[\.\)]\s+[^.!?]+[.!?]',
            # Bullet points
            r'^\s*[•·▪▫◦‣⁃]\s+[^.!?]+[.!?]'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(p, re.MULTILINE | re.IGNORECASE) for p in self.task_patterns]
        
        # Timing extraction patterns
        self.timing_patterns = {
            'duration': r'(?:for\s+)?(\d+)\s*(days?|weeks?|months?|hours?)',
            'frequency': r'(?:every|each)\s*(\d+)?\s*(hours?|days?|times?\s*(?:a|per)\s*day)',
            'start_time': r'(?:after|within|starting|beginning)\s*(\d+)?\s*(days?|weeks?|hours?)\s*(?:after|post|following)?',
            'end_time': r'(?:until|before|for the first|up to)\s*(\d+)?\s*(days?|weeks?|months?)'
        }
        
        # Initialize results storage
        self.results = []
        self.overview_results = []
        self.category_discoveries = []
        
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using multiple methods"""
        try:
            # Try pdfminer first (better for complex layouts)
            text = extract_text(pdf_path, laparams=LAParams())
            if text and len(text.strip()) > 100:
                return text
            
            # Fallback to PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return ""
    
    def parse_care_tasks(self, text: str) -> List[Dict]:
        """Extract care tasks from text using patterns and AI"""
        tasks = []
        
        # Use pattern matching first
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if len(match) > 20 and len(match) < 500:  # Filter noise
                    task = {
                        'description': match.strip(),
                        'raw_text': match,
                        'method': 'pattern'
                    }
                    tasks.append(task)
        
        # Use AI for enhanced extraction if available
        if self.model and len(text) > 0:
            tasks.extend(self.ai_extract_tasks(text[:10000]))  # Limit text length for API
        
        # Deduplicate tasks
        seen = set()
        unique_tasks = []
        for task in tasks:
            task_hash = hashlib.md5(task['description'].lower().encode()).hexdigest()
            if task_hash not in seen:
                seen.add(task_hash)
                unique_tasks.append(task)
        
        return unique_tasks
    
    def ai_extract_tasks(self, text: str) -> List[Dict]:
        """Use AI to extract tasks and suggest categories"""
        try:
            prompt = f"""
            Extract all post-operative care instructions from this text.
            For each instruction, provide:
            1. The specific task or action
            2. Category (from: {', '.join(self.known_categories.values())}, or suggest NEW)
            3. Timing information (when, how often, duration)
            4. Importance level (critical, high, medium, low)
            5. Any warnings or contraindications
            
            Format as JSON array with fields: task, category, timing, importance, warnings
            
            Text: {text[:5000]}
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse AI response
            try:
                # Extract JSON from response
                json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if json_match:
                    tasks_data = json.loads(json_match.group())
                    tasks = []
                    for item in tasks_data:
                        task = {
                            'description': item.get('task', ''),
                            'suggested_category': item.get('category', 'Unknown'),
                            'timing': item.get('timing', ''),
                            'importance': item.get('importance', 'medium'),
                            'warnings': item.get('warnings', ''),
                            'method': 'ai'
                        }
                        
                        # Check if this is a new category
                        if task['suggested_category'] not in self.known_categories.values():
                            self.handle_new_category(task['suggested_category'], task['description'])
                        
                        tasks.append(task)
                    return tasks
            except json.JSONDecodeError:
                logger.warning("Could not parse AI response as JSON")
                
        except Exception as e:
            logger.error(f"AI extraction error: {str(e)}")
        
        return []
    
    def categorize_task(self, task: Dict) -> str:
        """Categorize a task, discovering new categories if needed"""
        description = task['description'].lower()
        
        # Check against known category keywords
        category_keywords = {
            'wound_care': ['wound', 'incision', 'dressing', 'bandage', 'suture', 'staple', 'drainage', 'steri-strip'],
            'medication': ['medication', 'medicine', 'pill', 'tablet', 'antibiotic', 'pain', 'painkiller', 'ibuprofen', 'acetaminophen', 'prescription'],
            'activity': ['activity', 'exercise', 'lift', 'weight', 'drive', 'work', 'walk', 'stairs', 'bend', 'twist', 'sports'],
            'physical_therapy': ['therapy', 'stretching', 'strengthen', 'range of motion', 'rehabilitation', 'exercises'],
            'diet': ['eat', 'drink', 'food', 'diet', 'nutrition', 'fluid', 'water', 'alcohol', 'caffeine'],
            'hygiene': ['shower', 'bath', 'wash', 'clean', 'hygiene', 'soap', 'water'],
            'monitoring': ['monitor', 'check', 'temperature', 'fever', 'swelling', 'redness', 'discharge', 'vital'],
            'follow_up': ['appointment', 'follow-up', 'visit', 'doctor', 'surgeon', 'clinic', 'check-up'],
            'emergency': ['emergency', 'immediately', '911', 'urgent', 'severe', 'hospital', 'bleeding', 'chest pain'],
            'pain_management': ['pain', 'discomfort', 'ice', 'heat', 'elevate', 'rest']
        }
        
        # New category keywords to discover
        discovery_keywords = {
            'equipment': ['brace', 'crutches', 'walker', 'compression', 'device', 'machine', 'cpap', 'drain'],
            'breathing': ['breathing', 'spirometry', 'cough', 'deep breath', 'lung', 'respiratory'],
            'sleep': ['sleep', 'position', 'elevate', 'pillow', 'lying', 'side'],
            'sexual': ['sexual', 'intercourse', 'intimacy'],
            'travel': ['travel', 'fly', 'airplane', 'altitude', 'car ride'],
            'work': ['work', 'job', 'occupation', 'return to work', 'disability'],
            'scar': ['scar', 'massage', 'sunscreen', 'moisturize'],
            'mental': ['mood', 'depression', 'anxiety', 'memory', 'cognitive'],
            'pet': ['pet', 'animal', 'cat', 'dog'],
            'insurance': ['insurance', 'form', 'paperwork', 'documentation', 'claim']
        }
        
        # Check known categories first
        for cat_key, keywords in category_keywords.items():
            if any(keyword in description for keyword in keywords):
                self.category_frequency[self.known_categories[cat_key]] += 1
                return self.known_categories[cat_key]
        
        # Check for potential new categories
        for cat_key, keywords in discovery_keywords.items():
            if any(keyword in description for keyword in keywords):
                category_name = cat_key.replace('_', ' ').title()
                self.handle_new_category(category_name, task['description'])
                return category_name
        
        # If AI suggested a category, use it
        if 'suggested_category' in task and task['suggested_category']:
            return task['suggested_category']
        
        # Track uncategorized for later analysis
        self.uncategorized_tasks.append(task)
        return "Uncategorized"
    
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
            'duration': None,
            'frequency': None,
            'start_time': None,
            'end_time': None
        }
        
        for key, pattern in self.timing_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                timing[key] = match.group(0)
        
        return timing
    
    def extract_procedure_overview(self, text: str, pdf_name: str) -> Dict:
        """Extract procedure overview information"""
        overview = {
            'pdf_filename': pdf_name,
            'procedure_description': '',
            'typical_duration': '',
            'anesthesia_type': '',
            'hospital_stay': '',
            'recovery_timeline': '',
            'risks_mentioned': []
        }
        
        # Extract first substantial paragraph as description
        paragraphs = text.split('\n\n')
        for para in paragraphs[:5]:  # Check first 5 paragraphs
            if len(para) > 100 and not any(word in para.lower() for word in ['contents', 'index', 'page']):
                overview['procedure_description'] = para[:500]
                break
        
        # Look for specific information
        duration_match = re.search(r'(?:procedure|surgery|operation)\s+(?:takes?|lasts?|duration)\s+(?:about|approximately)?\s*(\d+\s*(?:hours?|minutes?))', text, re.IGNORECASE)
        if duration_match:
            overview['typical_duration'] = duration_match.group(1)
        
        anesthesia_match = re.search(r'(general|local|regional|spinal|epidural)\s+anesthesia', text, re.IGNORECASE)
        if anesthesia_match:
            overview['anesthesia_type'] = anesthesia_match.group(1)
        
        stay_match = re.search(r'(?:hospital|overnight)\s+stay\s+(?:of|is)?\s*(\d+\s*(?:days?|nights?|hours?))', text, re.IGNORECASE)
        if stay_match:
            overview['hospital_stay'] = stay_match.group(1)
        
        recovery_match = re.search(r'(?:full|complete)?\s*recovery\s+(?:takes?|is|expected)?\s*(?:about|approximately)?\s*(\d+\s*(?:days?|weeks?|months?))', text, re.IGNORECASE)
        if recovery_match:
            overview['recovery_timeline'] = recovery_match.group(1)
        
        # Extract risks
        risk_patterns = ['bleeding', 'infection', 'blood clot', 'nerve damage', 'scarring', 'reaction to anesthesia']
        risks = []
        for risk in risk_patterns:
            if risk in text.lower():
                risks.append(risk)
        overview['risks_mentioned'] = risks
        
        return overview
    
    def analyze_pdf(self, pdf_path: str, procedure_info: Dict) -> Tuple[List[Dict], Dict]:
        """Analyze a single PDF and extract all information"""
        logger.info(f"Analyzing: {pdf_path}")
        
        # Extract text
        text = self.extract_pdf_text(pdf_path)
        if not text:
            logger.warning(f"No text extracted from {pdf_path}")
            return [], {}
        
        # Extract procedure overview
        overview = self.extract_procedure_overview(text, Path(pdf_path).name)
        overview.update(procedure_info)
        
        # Extract care tasks
        tasks = self.parse_care_tasks(text)
        
        # Process each task
        processed_tasks = []
        for i, task in enumerate(tasks):
            # Categorize task
            category = self.categorize_task(task)
            
            # Extract timing
            timing = self.extract_timing_info(task['description'])
            
            # Determine if this is a new category
            is_new = category in self.discovered_categories
            
            # Create task record
            task_record = {
                'pdf_filename': Path(pdf_path).name,
                'pdf_path': pdf_path,
                'procedure_category': procedure_info.get('category', ''),
                'specific_procedure': procedure_info.get('procedure', ''),
                'confidence_score': procedure_info.get('confidence', 0),
                'task_id': f"{Path(pdf_path).stem}_{i+1}",
                'task_category': category,
                'task_subcategory': '',  # Could be enhanced with subcategory detection
                'task_description': task['description'][:500],  # Limit length
                'timing': timing.get('start_time', ''),
                'frequency': timing.get('frequency', ''),
                'duration': timing.get('duration', ''),
                'importance_level': task.get('importance', 'medium'),
                'prerequisites': '',  # Could be enhanced
                'contraindications': '',  # Could be enhanced
                'warning_signs': task.get('warnings', ''),
                'special_equipment': '',  # Could be enhanced
                'provider_contact': '',  # Could be enhanced
                'follow_up_required': 'follow-up' in task['description'].lower(),
                'notes': task.get('method', ''),
                'is_new_category': is_new
            }
            
            processed_tasks.append(task_record)
        
        return processed_tasks, overview
    
    def analyze_collection(self, pdf_directory: str, output_dir: str = 'analysis/outputs'):
        """Analyze entire collection of PDFs"""
        logger.info(f"Starting analysis of PDFs in {pdf_directory}")
        
        # Find all PDFs
        pdf_files = []
        for root, dirs, files in os.walk(pdf_directory):
            for file in files:
                if file.endswith('.pdf'):
                    pdf_path = os.path.join(root, file)
                    
                    # Extract procedure info from path and filename
                    parts = pdf_path.split(os.sep)
                    category = parts[-3] if len(parts) > 2 else "Unknown"
                    procedure = parts[-2] if len(parts) > 1 else "Unknown"
                    
                    # Extract confidence from filename
                    confidence_match = re.search(r'\[(\d+)%\]', file)
                    confidence = int(confidence_match.group(1))/100 if confidence_match else 0.5
                    
                    pdf_files.append({
                        'path': pdf_path,
                        'category': category,
                        'procedure': procedure,
                        'confidence': confidence
                    })
        
        logger.info(f"Found {len(pdf_files)} PDFs to analyze")
        
        # Process each PDF
        all_tasks = []
        all_overviews = []
        errors = []
        
        for i, pdf_info in enumerate(pdf_files, 1):
            try:
                logger.info(f"Processing {i}/{len(pdf_files)}: {Path(pdf_info['path']).name}")
                
                tasks, overview = self.analyze_pdf(
                    pdf_info['path'],
                    {
                        'category': pdf_info['category'],
                        'procedure': pdf_info['procedure'],
                        'confidence': pdf_info['confidence']
                    }
                )
                
                all_tasks.extend(tasks)
                if overview:
                    all_overviews.append(overview)
                
                # Periodic category discovery analysis
                if i % 10 == 0:
                    self.analyze_uncategorized_tasks()
                    
            except Exception as e:
                logger.error(f"Error processing {pdf_info['path']}: {str(e)}")
                errors.append({
                    'pdf': pdf_info['path'],
                    'error': str(e)
                })
        
        # Final category discovery analysis
        self.analyze_uncategorized_tasks()
        
        # Save results
        self.save_results(all_tasks, all_overviews, errors, output_dir)
        
        # Print summary
        self.print_summary(all_tasks)
    
    def analyze_uncategorized_tasks(self):
        """Analyze uncategorized tasks to discover patterns"""
        if len(self.uncategorized_tasks) < 5:
            return
        
        logger.info(f"Analyzing {len(self.uncategorized_tasks)} uncategorized tasks for patterns...")
        
        # Group by similarity (simple approach - could use more sophisticated clustering)
        task_groups = defaultdict(list)
        for task in self.uncategorized_tasks:
            # Extract key words
            words = set(task['description'].lower().split())
            key_words = words - {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
            
            # Find most common word as group key
            for word in key_words:
                if len(word) > 4:  # Skip short words
                    task_groups[word].append(task)
                    break
        
        # Identify potential new categories
        for key_word, tasks in task_groups.items():
            if len(tasks) >= 3:  # Need at least 3 similar tasks
                category_name = key_word.title() + " Care"
                self.handle_new_category(category_name, tasks[0]['description'])
        
        # Clear processed uncategorized tasks
        self.uncategorized_tasks = []
    
    def save_results(self, tasks: List[Dict], overviews: List[Dict], errors: List[Dict], output_dir: str):
        """Save analysis results to CSV files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save main task analysis
        if tasks:
            df_tasks = pd.DataFrame(tasks)
            df_tasks.to_csv(f"{output_dir}/postop_care_analysis.csv", index=False)
            logger.info(f"Saved {len(tasks)} tasks to postop_care_analysis.csv")
        
        # Save procedure overviews
        if overviews:
            df_overviews = pd.DataFrame(overviews)
            df_overviews.to_csv(f"{output_dir}/procedure_overviews.csv", index=False)
            logger.info(f"Saved {len(overviews)} overviews to procedure_overviews.csv")
        
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
            df_categories.to_csv(f"{output_dir}/discovered_categories.csv", index=False)
            logger.info(f"Saved {len(self.discovered_categories)} discovered categories")
        
        # Save error report
        if errors:
            df_errors = pd.DataFrame(errors)
            df_errors.to_csv(f"{output_dir}/error_report.csv", index=False)
            logger.warning(f"Saved {len(errors)} errors to error_report.csv")
        
        # Save category frequency analysis
        with open(f"{output_dir}/category_frequency.json", 'w') as f:
            json.dump(dict(self.category_frequency), f, indent=2)
    
    def print_summary(self, tasks: List[Dict]):
        """Print analysis summary"""
        print("\n" + "="*60)
        print("📊 ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"\n📈 Task Extraction:")
        print(f"  • Total tasks extracted: {len(tasks)}")
        print(f"  • Unique procedures: {len(set(t['specific_procedure'] for t in tasks))}")
        print(f"  • Average tasks per PDF: {len(tasks) / len(set(t['pdf_filename'] for t in tasks)):.1f}")
        
        print(f"\n📁 Category Distribution:")
        for category, count in self.category_frequency.most_common(10):
            percentage = (count / len(tasks)) * 100
            print(f"  • {category}: {count} ({percentage:.1f}%)")
        
        if self.discovered_categories:
            print(f"\n🎯 New Categories Discovered: {len(self.discovered_categories)}")
            for cat_name in list(self.discovered_categories.keys())[:5]:
                print(f"  • {cat_name}")
        
        uncategorized = sum(1 for t in tasks if t['task_category'] == 'Uncategorized')
        if uncategorized:
            print(f"\n⚠️  Uncategorized tasks: {uncategorized} ({(uncategorized/len(tasks))*100:.1f}%)")
        
        print("\n✅ Analysis complete! Check 'analysis/outputs' for detailed results.")
        print("="*60)


def main():
    """Main execution function"""
    analyzer = PDFCareAnalyzer()
    
    # Analyze the organized PDFs
    pdf_directory = "agent_output/organized_pdfs"
    analyzer.analyze_collection(pdf_directory)


if __name__ == "__main__":
    main()