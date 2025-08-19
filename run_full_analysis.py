#!/usr/bin/env python3
"""
Run full analysis on all organized PDFs to extract care tasks
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from analysis.scripts.pdf_analyzer_simple import SimplePDFAnalyzer

def main():
    """Run full PDF analysis"""
    print("="*60)
    print("🚀 STARTING FULL PDF CARE TASK ANALYSIS")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup logging
    log_file = 'analysis/outputs/analysis_log.txt'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Initialize analyzer
    analyzer = SimplePDFAnalyzer()
    
    # Find all PDFs in organized directory
    pdf_directory = "agent_output/organized_pdfs"
    pdf_files = []
    
    print(f"\n📂 Scanning directory: {pdf_directory}")
    
    for root, dirs, files in os.walk(pdf_directory):
        # Skip hidden directories and the high quality folder
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '_High_Quality_PDFs']
        
        for file in files:
            if file.endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                
                # Extract procedure info from path structure
                parts = Path(pdf_path).parts
                
                # Find indices of important path components
                organized_idx = parts.index('organized_pdfs') if 'organized_pdfs' in parts else -1
                
                if organized_idx >= 0 and len(parts) > organized_idx + 1:
                    # Next part after organized_pdfs is the category
                    category = parts[organized_idx + 1]
                    
                    # Check if there's a procedure subfolder
                    procedure = parts[organized_idx + 2] if len(parts) > organized_idx + 2 else category
                    
                    # If the last part is the PDF file, use the parent as procedure
                    if procedure.endswith('.pdf'):
                        procedure = category
                else:
                    category = "Unknown"
                    procedure = "Unknown"
                
                # Extract confidence from filename
                import re
                confidence_match = re.search(r'\[(\d+)%\]', file)
                confidence = int(confidence_match.group(1))/100 if confidence_match else 0.5
                
                pdf_files.append({
                    'path': pdf_path,
                    'category': category,
                    'procedure': procedure,
                    'confidence': confidence,
                    'filename': file
                })
    
    print(f"✓ Found {len(pdf_files)} PDFs to analyze")
    
    # Show category distribution
    from collections import Counter
    categories = Counter(pdf['category'] for pdf in pdf_files)
    print(f"\n📊 PDF Distribution by Category:")
    for cat, count in categories.most_common():
        print(f"  • {cat}: {count} PDFs")
    
    print(f"\n⏳ Starting analysis...")
    print("-"*60)
    
    # Process PDFs
    all_tasks = []
    all_overviews = []
    errors = []
    
    for i, pdf_info in enumerate(pdf_files, 1):
        try:
            # Progress indicator
            if i % 10 == 0:
                print(f"\n📈 Progress: {i}/{len(pdf_files)} ({i/len(pdf_files)*100:.1f}%)")
                print(f"   Tasks extracted so far: {len(all_tasks)}")
                if analyzer.discovered_categories:
                    print(f"   New categories discovered: {len(analyzer.discovered_categories)}")
            
            # Analyze PDF
            tasks, overview = analyzer.analyze_pdf(
                pdf_info['path'],
                {
                    'category': pdf_info['category'],
                    'procedure': pdf_info['procedure'],
                    'confidence': pdf_info['confidence']
                }
            )
            
            all_tasks.extend(tasks)
            if overview and overview.get('procedure_description'):
                all_overviews.append(overview)
            
            # Log individual file results
            if tasks:
                logger.info(f"✓ {pdf_info['filename']}: {len(tasks)} tasks")
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
            
            # Don't stop on individual errors
            continue
    
    print("\n" + "="*60)
    print("💾 Saving results...")
    
    # Save all results
    output_dir = 'analysis/outputs'
    analyzer.save_results(all_tasks, all_overviews, errors, output_dir)
    
    # Print final summary
    analyzer.print_summary(all_tasks)
    
    # Additional statistics
    print(f"\n📊 Additional Statistics:")
    print(f"  • PDFs successfully processed: {len(pdf_files) - len(errors)}/{len(pdf_files)}")
    print(f"  • PDFs with errors: {len(errors)}")
    print(f"  • Procedure overviews extracted: {len(all_overviews)}")
    
    if errors:
        print(f"\n⚠️  Files with errors ({len(errors)}):")
        for err in errors[:5]:
            print(f"    • {err['filename']}: {err['error'][:50]}...")
        if len(errors) > 5:
            print(f"    ... and {len(errors) - 5} more")
    
    print(f"\n⏱️  Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📁 Output files saved to: analysis/outputs/")
    print("  • postop_care_analysis.csv - All extracted care tasks")
    print("  • procedure_overviews.csv - Procedure summaries")
    print("  • discovered_categories.csv - New categories found")
    print("  • category_frequency.json - Task category distribution")
    print("  • error_report.csv - Processing errors (if any)")
    print("  • analysis_log.txt - Detailed processing log")
    
    return len(all_tasks) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)