#!/usr/bin/env python3
"""
Test script for PDF Care Analyzer
Tests on a small sample before full analysis
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.scripts.pdf_analyzer_simple import SimplePDFAnalyzer
import logging

logging.basicConfig(level=logging.INFO)

def test_single_pdf():
    """Test analysis on a single PDF"""
    print("="*60)
    print("Testing PDF Care Analyzer on Sample PDFs")
    print("="*60)
    
    # Initialize analyzer
    analyzer = SimplePDFAnalyzer()
    
    # Find a few test PDFs
    test_pdfs = []
    organized_dir = "agent_output/organized_pdfs"
    
    # Get one PDF from different procedure types
    target_procedures = ['Total Knee Replacement', 'Appendectomy', 'Cataract Surgery']
    
    for procedure in target_procedures:
        proc_dir = Path(organized_dir) / 'Orthopedic Surgery' / procedure
        if not proc_dir.exists():
            # Try other categories
            for category in Path(organized_dir).iterdir():
                if category.is_dir():
                    proc_dir = category / procedure
                    if proc_dir.exists():
                        break
        
        if proc_dir.exists():
            pdfs = list(proc_dir.glob("*.pdf"))
            if pdfs:
                test_pdfs.append(pdfs[0])
    
    # Also get some from root categories
    for category in ['General Surgery', 'Cardiac Surgery']:
        cat_dir = Path(organized_dir) / category
        if cat_dir.exists():
            pdfs = list(cat_dir.glob("*.pdf"))
            if pdfs:
                test_pdfs.append(pdfs[0])
    
    print(f"\nFound {len(test_pdfs)} test PDFs:")
    for pdf in test_pdfs[:5]:  # Test up to 5 PDFs
        print(f"  • {pdf.name}")
    
    print("\nStarting analysis...")
    print("-"*60)
    
    all_tasks = []
    for pdf_path in test_pdfs[:5]:
        try:
            print(f"\n📄 Analyzing: {pdf_path.name}")
            
            # Extract procedure info from path
            parts = str(pdf_path).split(os.sep)
            category = parts[-3] if len(parts) > 3 else "Unknown"
            procedure = parts[-2] if len(parts) > 2 else "Unknown"
            
            # Analyze PDF
            tasks, overview = analyzer.analyze_pdf(
                str(pdf_path),
                {
                    'category': category,
                    'procedure': procedure,
                    'confidence': 0.8
                }
            )
            
            print(f"  ✓ Extracted {len(tasks)} tasks")
            
            # Show sample tasks
            if tasks:
                print("  Sample tasks:")
                for task in tasks[:3]:
                    print(f"    - [{task['task_category']}] {task['task_description'][:80]}...")
            
            all_tasks.extend(tasks)
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total tasks extracted: {len(all_tasks)}")
    
    # Show category distribution
    from collections import Counter
    categories = Counter(task['task_category'] for task in all_tasks)
    print("\nCategory distribution:")
    for cat, count in categories.most_common():
        print(f"  • {cat}: {count}")
    
    # Show discovered categories
    if analyzer.discovered_categories:
        print(f"\n🎯 New categories discovered:")
        for cat in analyzer.discovered_categories:
            print(f"  • {cat}")
    
    print("\n✅ Test complete! Ready for full analysis.")
    return len(all_tasks) > 0

if __name__ == "__main__":
    success = test_single_pdf()
    sys.exit(0 if success else 1)