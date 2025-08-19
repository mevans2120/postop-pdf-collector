#!/usr/bin/env python3
"""
Archive non-patient PDFs to a separate folder
"""

import os
import shutil
from pathlib import Path
import pandas as pd

def archive_pdfs():
    print("="*80)
    print("ARCHIVING NON-PATIENT PDFs")
    print("="*80)
    
    # Read the list of files to archive
    files_to_archive = []
    current_category = None
    
    with open('non_patient_pdfs_to_archive.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('=') and not line.startswith('-'):
                if line.endswith(':'):
                    current_category = line[:-1]
                elif line.startswith('Path:'):
                    path = line.replace('Path:', '').strip()
                    if os.path.exists(path):
                        files_to_archive.append({
                            'path': path,
                            'category': current_category,
                            'filename': os.path.basename(path)
                        })
    
    # Create archive directory structure
    archive_base = Path('agent_output/archived_non_patient_pdfs')
    archive_base.mkdir(exist_ok=True)
    
    # Create category subdirectories
    categories = set(f['category'] for f in files_to_archive if f['category'])
    for category in categories:
        (archive_base / category.replace('/', '_')).mkdir(exist_ok=True)
    
    # Move files
    moved = 0
    errors = []
    
    print(f"\n📦 Moving {len(files_to_archive)} files to archive...")
    print("-"*40)
    
    for file_info in files_to_archive:
        try:
            source = Path(file_info['path'])
            if not source.exists():
                errors.append(f"Not found: {file_info['filename']}")
                continue
            
            # Determine destination
            if file_info['category']:
                dest_dir = archive_base / file_info['category'].replace('/', '_')
            else:
                dest_dir = archive_base / 'Uncategorized'
                dest_dir.mkdir(exist_ok=True)
            
            dest = dest_dir / file_info['filename']
            
            # Move the file
            shutil.move(str(source), str(dest))
            moved += 1
            
            # Show progress
            if moved % 10 == 0:
                print(f"  ✓ Moved {moved} files...")
                
        except Exception as e:
            errors.append(f"Error moving {file_info['filename']}: {str(e)}")
    
    print("\n" + "="*80)
    print("ARCHIVE COMPLETE")
    print("="*80)
    print(f"✅ Successfully archived: {moved} files")
    print(f"📁 Archive location: {archive_base}")
    
    if errors:
        print(f"\n⚠️  Errors encountered ({len(errors)}):")
        for err in errors[:5]:
            print(f"  • {err}")
    
    # Update the analysis CSVs to remove archived files
    print("\n📊 Updating analysis files...")
    
    # Get list of archived filenames
    archived_filenames = {f['filename'] for f in files_to_archive}
    
    # Update main analysis CSV
    try:
        df = pd.read_csv('analysis/outputs/postop_care_analysis_enhanced.csv')
        original_count = len(df)
        df_filtered = df[~df['pdf_filename'].isin(archived_filenames)]
        df_filtered.to_csv('analysis/outputs/postop_care_analysis_cleaned.csv', index=False)
        print(f"  ✓ Created cleaned analysis: {len(df_filtered)} tasks (removed {original_count - len(df_filtered)})")
    except Exception as e:
        print(f"  ✗ Error updating analysis: {e}")
    
    # Update overview CSV
    try:
        df = pd.read_csv('analysis/outputs/procedure_overviews.csv')
        original_count = len(df)
        df_filtered = df[~df['pdf_filename'].isin(archived_filenames)]
        df_filtered.to_csv('analysis/outputs/procedure_overviews_cleaned.csv', index=False)
        print(f"  ✓ Created cleaned overviews: {len(df_filtered)} procedures (removed {original_count - len(df_filtered)})")
    except Exception as e:
        print(f"  ✗ Error updating overviews: {e}")
    
    print("\n✨ Archive complete! Your collection now contains only patient instructions.")
    print("   Cleaned analysis files saved with '_cleaned' suffix")
    
    return moved, errors

if __name__ == "__main__":
    moved, errors = archive_pdfs()