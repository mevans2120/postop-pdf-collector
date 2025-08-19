#!/usr/bin/env python3
"""
Run complete analysis on cleaned patient-only PDF dataset
Combines initial extraction with enhanced descriptions
"""

import os
import sys
import re
from pathlib import Path
import logging
from datetime import datetime
from collections import Counter
import pandas as pd

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from analysis.scripts.pdf_analyzer_simple import SimplePDFAnalyzer
from analysis.scripts.enhance_descriptions import EnhancedTaskExtractor

def main():
    """Run full analysis on cleaned dataset"""
    print("="*80)
    print("🚀 RUNNING COMPLETE ANALYSIS ON CLEANED PATIENT PDF DATASET")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup logging
    log_file = 'analysis/outputs/clean_analysis_log.txt'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Exclude archived PDFs
    archive_dir = Path('agent_output/archived_non_patient_pdfs')
    archived_files = set()
    if archive_dir.exists():
        for root, dirs, files in os.walk(archive_dir):
            for file in files:
                if file.endswith('.pdf'):
                    archived_files.add(file)
    
    print(f"\n📁 Excluding {len(archived_files)} archived non-patient PDFs")
    
    # Find all remaining PDFs
    pdf_directory = "agent_output/organized_pdfs"
    pdf_files = []
    
    print(f"📂 Scanning directory: {pdf_directory}")
    
    for root, dirs, files in os.walk(pdf_directory):
        # Skip hidden directories and special folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '_High_Quality_PDFs']
        
        for file in files:
            if file.endswith('.pdf') and file not in archived_files:
                pdf_path = os.path.join(root, file)
                
                # Extract metadata from path
                parts = Path(pdf_path).parts
                organized_idx = parts.index('organized_pdfs') if 'organized_pdfs' in parts else -1
                
                if organized_idx >= 0 and len(parts) > organized_idx + 1:
                    category = parts[organized_idx + 1]
                    procedure = parts[organized_idx + 2] if len(parts) > organized_idx + 2 else category
                    if procedure.endswith('.pdf'):
                        procedure = category
                else:
                    category = "Unknown"
                    procedure = "Unknown"
                
                # Extract confidence
                confidence_match = re.search(r'\[(\d+)%\]', file)
                confidence = int(confidence_match.group(1))/100 if confidence_match else 0.5
                
                pdf_files.append({
                    'path': pdf_path,
                    'category': category,
                    'procedure': procedure,
                    'confidence': confidence,
                    'filename': file
                })
    
    print(f"✓ Found {len(pdf_files)} patient instruction PDFs to analyze")
    
    # Show distribution
    categories = Counter(pdf['category'] for pdf in pdf_files)
    print(f"\n📊 Clean PDF Distribution by Category:")
    for cat, count in categories.most_common():
        print(f"  • {cat}: {count} PDFs")
    
    print(f"\n⏳ Phase 1: Extracting care tasks...")
    print("-"*60)
    
    # Initialize analyzers
    simple_analyzer = SimplePDFAnalyzer()
    enhanced_extractor = EnhancedTaskExtractor()
    
    # Process PDFs
    all_tasks = []
    all_overviews = []
    errors = []
    
    for i, pdf_info in enumerate(pdf_files, 1):
        try:
            # Progress
            if i % 20 == 0:
                print(f"\n📈 Progress: {i}/{len(pdf_files)} ({i/len(pdf_files)*100:.1f}%)")
                print(f"   Tasks extracted: {len(all_tasks)}")
                if simple_analyzer.discovered_categories:
                    print(f"   New categories discovered: {len(simple_analyzer.discovered_categories)}")
            
            # Extract basic tasks
            tasks, overview = simple_analyzer.analyze_pdf(
                pdf_info['path'],
                {
                    'category': pdf_info['category'],
                    'procedure': pdf_info['procedure'],
                    'confidence': pdf_info['confidence']
                }
            )
            
            # Enhance descriptions
            text_sections = enhanced_extractor.extract_pdf_text_with_structure(pdf_info['path'])
            enhanced_tasks = enhanced_extractor.extract_complete_tasks(text_sections)
            
            # Merge enhanced descriptions with basic tasks
            for task in tasks:
                # Find best matching enhanced description
                best_match = None
                best_score = 0
                
                task_start = task['task_description'][:30].lower()
                
                for enhanced in enhanced_tasks:
                    if task_start in enhanced['description'].lower():
                        score = len(enhanced['description'])
                        if score > best_score:
                            best_score = score
                            best_match = enhanced
                
                if best_match and len(best_match['description']) > len(task['task_description']):
                    task['task_description'] = best_match['description']
                    task['enhanced'] = True
                    task['description_length'] = len(best_match['description'])
                else:
                    task['enhanced'] = False
                    task['description_length'] = len(task['task_description'])
            
            all_tasks.extend(tasks)
            if overview and overview.get('procedure_description'):
                all_overviews.append(overview)
            
            # Log results
            if tasks:
                logger.info(f"✓ {pdf_info['filename']}: {len(tasks)} tasks (enhanced: {sum(1 for t in tasks if t.get('enhanced', False))})")
            else:
                logger.warning(f"⚠ {pdf_info['filename']}: No tasks extracted")
                
        except Exception as e:
            error_msg = f"Error processing {pdf_info['filename']}: {str(e)[:100]}"
            logger.error(error_msg)
            errors.append({
                'pdf': pdf_info['path'],
                'filename': pdf_info['filename'],
                'error': str(e)[:200]
            })
            continue
    
    print("\n" + "="*80)
    print("💾 Phase 2: Saving enhanced results...")
    
    # Save all results
    output_dir = 'analysis/outputs/clean_final'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save main task analysis
    if all_tasks:
        df_tasks = pd.DataFrame(all_tasks)
        output_path = f"{output_dir}/patient_care_tasks_final.csv"
        df_tasks.to_csv(output_path, index=False)
        logger.info(f"Saved {len(all_tasks)} tasks to {output_path}")
    
    # Save procedure overviews
    if all_overviews:
        df_overviews = pd.DataFrame(all_overviews)
        output_path = f"{output_dir}/procedure_overviews_final.csv"
        df_overviews.to_csv(output_path, index=False)
        logger.info(f"Saved {len(all_overviews)} overviews to {output_path}")
    
    # Save discovered categories
    if simple_analyzer.discovered_categories:
        category_data = []
        for cat_name, cat_info in simple_analyzer.discovered_categories.items():
            category_data.append({
                'category_name': cat_name,
                'first_discovered': cat_info['first_discovered'],
                'frequency_count': cat_info['frequency'],
                'example_tasks': '; '.join(cat_info['examples'][:3]),
                'confidence': 'high' if cat_info['frequency'] > 10 else 'medium'
            })
        
        df_categories = pd.DataFrame(category_data)
        output_path = f"{output_dir}/discovered_categories_final.csv"
        df_categories.to_csv(output_path, index=False)
        logger.info(f"Saved {len(simple_analyzer.discovered_categories)} discovered categories")
    
    # Save error report
    if errors:
        df_errors = pd.DataFrame(errors)
        output_path = f"{output_dir}/error_report_final.csv"
        df_errors.to_csv(output_path, index=False)
        logger.warning(f"Saved {len(errors)} errors")
    
    # Save category frequency
    import json
    freq_data = dict(simple_analyzer.category_frequency)
    output_path = f"{output_dir}/category_frequency_final.json"
    with open(output_path, 'w') as f:
        json.dump(freq_data, f, indent=2)
    
    # Print comprehensive summary
    print("\n" + "="*80)
    print("📊 FINAL ANALYSIS SUMMARY - PATIENT INSTRUCTIONS ONLY")
    print("="*80)
    
    if all_tasks:
        df_tasks = pd.DataFrame(all_tasks)
        
        print(f"\n📈 Task Extraction Statistics:")
        print(f"  • Total tasks extracted: {len(all_tasks)}")
        print(f"  • PDFs successfully processed: {len(pdf_files) - len(errors)}/{len(pdf_files)}")
        print(f"  • Average tasks per PDF: {len(all_tasks)/len(set(t['pdf_filename'] for t in all_tasks)):.1f}")
        print(f"  • Enhanced descriptions: {df_tasks['enhanced'].sum() if 'enhanced' in df_tasks else 0}")
        print(f"  • Average description length: {df_tasks['description_length'].mean():.1f} characters")
        
        print(f"\n📁 Top 15 Task Categories:")
        for category, count in simple_analyzer.category_frequency.most_common(15):
            percentage = (count / len(all_tasks)) * 100
            print(f"  • {category}: {count} ({percentage:.1f}%)")
        
        if simple_analyzer.discovered_categories:
            print(f"\n🎯 New Categories Discovered: {len(simple_analyzer.discovered_categories)}")
            for cat_name in list(simple_analyzer.discovered_categories.keys())[:10]:
                freq = simple_analyzer.discovered_categories[cat_name]['frequency']
                print(f"  • {cat_name} ({freq} occurrences)")
        
        # Task importance distribution
        if 'importance_level' in df_tasks.columns:
            print(f"\n🎨 Task Importance Distribution:")
            for level, count in df_tasks['importance_level'].value_counts().items():
                print(f"  • {level}: {count}")
        
        # Procedure coverage
        print(f"\n🏥 Procedure Coverage:")
        procedure_counts = df_tasks.groupby('specific_procedure').size().sort_values(ascending=False)
        print(f"  • Total unique procedures: {len(procedure_counts)}")
        print(f"  • Top procedures by task count:")
        for proc, count in procedure_counts.head(10).items():
            print(f"    - {proc}: {count} tasks")
        
        uncategorized = sum(1 for t in all_tasks if t['task_category'] == 'Uncategorized')
        if uncategorized:
            print(f"\n⚠️  Uncategorized tasks: {uncategorized} ({(uncategorized/len(all_tasks))*100:.1f}%)")
    
    print(f"\n⏱️  Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📁 Final output files saved to: analysis/outputs/clean_final/")
    print("  • patient_care_tasks_final.csv - All patient care tasks with enhanced descriptions")
    print("  • procedure_overviews_final.csv - Procedure summaries")
    print("  • discovered_categories_final.csv - New task categories found")
    print("  • category_frequency_final.json - Task distribution data")
    if errors:
        print("  • error_report_final.csv - Processing errors")
    
    print("\n✅ Clean dataset analysis complete!")
    return len(all_tasks) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)