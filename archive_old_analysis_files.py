#!/usr/bin/env python3
"""
Archive older/intermediate analysis files to focus on final outputs
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def create_archive_structure():
    """Create organized archive directories"""
    archive_base = Path('analysis/outputs/archive_intermediate')
    archive_base.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    dirs = [
        'initial_analysis',
        'enhanced_versions',
        'pre_cleaning',
        'logs'
    ]
    
    for dir_name in dirs:
        (archive_base / dir_name).mkdir(exist_ok=True)
    
    return archive_base

def archive_files():
    """Move older/intermediate files to archive"""
    print("="*60)
    print("ARCHIVING INTERMEDIATE ANALYSIS FILES")
    print("="*60)
    
    archive_base = create_archive_structure()
    
    # Define what to archive
    files_to_archive = {
        'initial_analysis': [
            'analysis/outputs/postop_care_analysis.csv',
            'analysis/outputs/procedure_overviews.csv',
            'analysis/outputs/discovered_categories.csv',
            'analysis/outputs/category_frequency.json'
        ],
        'enhanced_versions': [
            'analysis/outputs/postop_care_analysis_enhanced.csv',
        ],
        'pre_cleaning': [
            'analysis/outputs/postop_care_analysis_cleaned.csv',
            'analysis/outputs/procedure_overviews_cleaned.csv'
        ],
        'logs': [
            'analysis/outputs/analysis_log.txt',
            'analysis/outputs/clean_analysis_log.txt'
        ]
    }
    
    # Files to keep in main directory (final outputs)
    keep_files = [
        'analysis/outputs/clean_final/',  # Keep entire final directory
    ]
    
    moved_count = 0
    errors = []
    
    print("\n📦 Archiving intermediate files...")
    print("-"*40)
    
    for category, file_list in files_to_archive.items():
        dest_dir = archive_base / category
        
        for file_path in file_list:
            source = Path(file_path)
            if source.exists():
                try:
                    dest = dest_dir / source.name
                    shutil.move(str(source), str(dest))
                    moved_count += 1
                    print(f"  ✓ Archived: {source.name} → {category}/")
                except Exception as e:
                    errors.append(f"Error moving {source.name}: {e}")
    
    # Archive other analysis scripts we don't need anymore
    old_scripts = [
        'run_full_analysis.py',
        'identify_non_patient_pdfs.py', 
        'archive_non_patient_pdfs.py',
        'non_patient_pdfs_to_archive.txt',
        'analyze_coverage.py',
        'collect_missing.py'
    ]
    
    archive_scripts = Path('archive_old_scripts')
    archive_scripts.mkdir(exist_ok=True)
    
    print("\n📂 Archiving old scripts...")
    print("-"*40)
    
    for script in old_scripts:
        if Path(script).exists():
            try:
                shutil.move(script, str(archive_scripts / script))
                moved_count += 1
                print(f"  ✓ Archived script: {script}")
            except Exception as e:
                errors.append(f"Error moving {script}: {e}")
    
    # Create a clear structure document
    create_final_structure_doc()
    
    print("\n" + "="*60)
    print("ARCHIVE COMPLETE")
    print("="*60)
    print(f"✅ Archived {moved_count} files")
    
    if errors:
        print(f"\n⚠️  Errors encountered:")
        for err in errors:
            print(f"  • {err}")
    
    print("\n📁 FINAL OUTPUT STRUCTURE:")
    print("-"*40)
    print("analysis/outputs/clean_final/")
    print("  ├── patient_care_tasks_final.csv (4,371 tasks)")
    print("  ├── procedure_overviews_final_with_names.csv (275 procedures)")
    print("  ├── discovered_categories_final.csv (12 new categories)")
    print("  └── category_frequency_final.json (task distribution)")
    
    print("\n📚 KEY REFERENCE FILES:")
    print("  • CLAUDE.md - Complete system documentation")
    print("  • pdf_analysis_plan.md - Analysis methodology")
    print("  • dashboard_live.html - Live monitoring dashboard")
    
    print("\n✨ Your workspace is now clean and organized!")
    print("   Focus on files in: analysis/outputs/clean_final/")

def create_final_structure_doc():
    """Create a README for the final outputs"""
    readme_content = """# PostOp PDF Analysis - Final Outputs

## 📊 Final Analysis Results

This directory contains the final, cleaned analysis outputs from the PostOp PDF Collector system.

### Primary Output Files

#### 1. `patient_care_tasks_final.csv`
- **4,371 patient care tasks** extracted from 232 patient-only PDFs
- Enhanced descriptions averaging 243 characters
- 16 task categories including newly discovered ones
- Key columns:
  - `pdf_filename` - Source PDF
  - `task_description` - Full task description with context
  - `task_category` - Categorization (Activity, Medication, etc.)
  - `importance_level` - Critical/High/Medium/Low
  - `timing_info` - When to perform task
  - `specific_procedure` - Associated procedure

#### 2. `procedure_overviews_final_with_names.csv`
- **275 procedure overviews** from patient instruction PDFs
- Extracted specific procedure names for 97.1% of files
- Key columns:
  - `pdf_filename` - Source PDF
  - `procedure_name` - Specific procedure (e.g., "Total Knee Replacement")
  - `procedure_description` - Overview text
  - `typical_duration` - Surgery duration if mentioned
  - `recovery_timeline` - Recovery period information
  - `confidence` - Relevance score (0-1)

#### 3. `discovered_categories_final.csv`
- **12 new task categories** discovered beyond predefined ones
- Categories like: Pet Care, Hearing, Vision, Sexual Activity, Travel
- Includes frequency counts and example tasks

#### 4. `category_frequency_final.json`
- Task distribution across all categories
- Top categories: Activity Restrictions (516), Medication (451), Diet (379)

## 🗂️ Archived Files

Intermediate and older analysis files have been moved to:
- `archive_intermediate/` - Initial and enhanced analysis versions
- `../archive_old_scripts/` - Scripts used for one-time processing

## 📈 Analysis Statistics

- **Total PDFs Analyzed**: 232 (after removing 44 non-patient materials)
- **Tasks Extracted**: 4,371 with enhanced descriptions
- **Average Tasks per PDF**: 19
- **Procedure Coverage**: 275 unique procedures documented
- **Task Categories**: 16 distinct categories
- **Confidence Score**: 75% average

## 🚀 Next Steps

To work with this data:

1. **View Tasks by Procedure**:
   ```python
   import pandas as pd
   tasks = pd.read_csv('patient_care_tasks_final.csv')
   tasks[tasks['specific_procedure'].str.contains('Knee')]
   ```

2. **Get Procedure-Specific Instructions**:
   ```python
   overviews = pd.read_csv('procedure_overviews_final_with_names.csv')
   overviews[overviews['procedure_name'] == 'Total Hip Replacement']
   ```

3. **Analyze Task Categories**:
   ```python
   import json
   with open('category_frequency_final.json') as f:
       freq = json.load(f)
   ```

## 📝 Documentation

- Full system documentation: `../../../CLAUDE.md`
- Analysis methodology: `../../../pdf_analysis_plan.md`
- Web dashboard: `../../../dashboard_live.html`

---
*Generated: {date}*
"""
    
    output_path = Path('analysis/outputs/clean_final/README.md')
    output_path.write_text(readme_content.format(date=datetime.now().strftime('%Y-%m-%d')))
    print(f"\n📄 Created README at: {output_path}")

if __name__ == "__main__":
    archive_files()