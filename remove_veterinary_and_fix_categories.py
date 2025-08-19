#!/usr/bin/env python3
"""
Remove veterinary PDFs and fix miscategorized "Pet Care" tasks
"""

import pandas as pd
import shutil
from pathlib import Path
import json

def main():
    print("="*60)
    print("REMOVING VETERINARY PDFs AND FIXING CATEGORIES")
    print("="*60)
    
    # 1. First, archive the veterinary PDF
    veterinary_pdfs = [
        "agent_output/organized_pdfs/Uncategorized/[84%] SAFE-Care-Spay-Neuter-Post-Operative-Care-Instructions-2020.pdf",
        "agent_output/organized_pdfs/_High_Quality_PDFs/[84%] SAFE-Care-Spay-Neuter-Post-Operative-Care-Instructions-2020.pdf"
    ]
    
    archive_dir = Path("agent_output/archived_veterinary")
    archive_dir.mkdir(exist_ok=True)
    
    print("\n📦 Archiving veterinary PDFs...")
    for pdf_path in veterinary_pdfs:
        if Path(pdf_path).exists():
            dest = archive_dir / Path(pdf_path).name
            shutil.move(pdf_path, dest)
            print(f"  ✓ Moved: {Path(pdf_path).name}")
    
    # 2. Load and clean the patient care tasks CSV
    print("\n🔧 Fixing miscategorized tasks...")
    tasks_df = pd.read_csv('analysis/outputs/clean_final/patient_care_tasks_final.csv')
    
    # Remove tasks from veterinary PDFs
    vet_pdf_name = "[84%] SAFE-Care-Spay-Neuter-Post-Operative-Care-Instructions-2020.pdf"
    initial_count = len(tasks_df)
    tasks_df = tasks_df[tasks_df['pdf_filename'] != vet_pdf_name]
    removed_vet = initial_count - len(tasks_df)
    print(f"  ✓ Removed {removed_vet} tasks from veterinary PDF")
    
    # Analyze Pet Care tasks to recategorize them
    pet_care_tasks = tasks_df[tasks_df['task_category'] == 'Pet Care'].copy()
    print(f"\n📊 Found {len(pet_care_tasks)} miscategorized 'Pet Care' tasks")
    
    # Recategorize based on actual content
    def recategorize_task(row):
        desc = row['task_description'].lower()
        
        # Check for actual categories
        if any(word in desc for word in ['medication', 'medicine', 'pill', 'prescribed', 'dose', 'drug']):
            return 'Medication Management'
        elif any(word in desc for word in ['appointment', 'check-in', 'visit', 'follow-up', 'schedule']):
            return 'Follow-up Care'
        elif any(word in desc for word in ['procedure', 'surgery', 'operation', 'consent', 'explain']):
            return 'Pre-procedure'
        elif any(word in desc for word in ['complaint', 'grievance', 'contact', 'phone', 'email']):
            return 'Administrative'
        elif any(word in desc for word in ['trial', 'study', 'research', 'anticoagulation']):
            return 'Medical Information'
        else:
            return 'Uncategorized'
    
    # Apply recategorization
    for idx in pet_care_tasks.index:
        new_category = recategorize_task(tasks_df.loc[idx])
        tasks_df.at[idx, 'task_category'] = new_category
    
    print("\n📈 Recategorization results:")
    recategorized = tasks_df.loc[pet_care_tasks.index]['task_category'].value_counts()
    for cat, count in recategorized.items():
        print(f"  • {cat}: {count} tasks")
    
    # 3. Save cleaned CSV
    output_path = 'analysis/outputs/clean_final/patient_care_tasks_final_cleaned.csv'
    tasks_df.to_csv(output_path, index=False)
    print(f"\n💾 Saved cleaned tasks to: {output_path}")
    
    # 4. Update procedure overviews
    print("\n🔧 Updating procedure overviews...")
    overviews_df = pd.read_csv('analysis/outputs/clean_final/procedure_overviews_final_with_names.csv')
    initial_overview_count = len(overviews_df)
    overviews_df = overviews_df[overviews_df['pdf_filename'] != vet_pdf_name]
    removed_overview = initial_overview_count - len(overviews_df)
    
    output_path = 'analysis/outputs/clean_final/procedure_overviews_final_cleaned.csv'
    overviews_df.to_csv(output_path, index=False)
    print(f"  ✓ Removed {removed_overview} veterinary procedure overview")
    print(f"  ✓ Saved to: {output_path}")
    
    # 5. Update discovered categories
    print("\n🔧 Updating discovered categories...")
    categories_df = pd.read_csv('analysis/outputs/clean_final/discovered_categories_final.csv')
    
    # Remove Pet Care category since it was a miscategorization
    categories_df = categories_df[categories_df['category_name'] != 'Pet Care']
    
    # Add the new categories we actually found
    new_categories = ['Administrative', 'Medical Information', 'Pre-procedure']
    for cat in new_categories:
        if cat not in categories_df['category_name'].values:
            cat_tasks = tasks_df[tasks_df['task_category'] == cat]
            if len(cat_tasks) > 0:
                new_row = {
                    'category_name': cat,
                    'first_discovered': pd.Timestamp.now().isoformat(),
                    'frequency_count': len(cat_tasks),
                    'example_tasks': '; '.join(cat_tasks['task_description'].head(3).str[:100]),
                    'confidence': 'high' if len(cat_tasks) > 10 else 'medium'
                }
                categories_df = pd.concat([categories_df, pd.DataFrame([new_row])], ignore_index=True)
    
    output_path = 'analysis/outputs/clean_final/discovered_categories_final_cleaned.csv'
    categories_df.to_csv(output_path, index=False)
    print(f"  ✓ Updated categories (removed Pet Care, added proper categories)")
    print(f"  ✓ Saved to: {output_path}")
    
    # 6. Update category frequency
    print("\n🔧 Updating category frequency...")
    category_freq = tasks_df['task_category'].value_counts().to_dict()
    
    output_path = 'analysis/outputs/clean_final/category_frequency_final_cleaned.json'
    with open(output_path, 'w') as f:
        json.dump(category_freq, f, indent=2)
    print(f"  ✓ Saved to: {output_path}")
    
    # Print final statistics
    print("\n" + "="*60)
    print("CLEANING COMPLETE")
    print("="*60)
    print(f"✅ Removed {removed_vet} veterinary tasks")
    print(f"✅ Recategorized {len(pet_care_tasks)} miscategorized 'Pet Care' tasks")
    print(f"✅ Final task count: {len(tasks_df)}")
    print(f"✅ Final procedure count: {len(overviews_df)}")
    
    print("\n📊 Top 10 Categories After Cleaning:")
    for cat, count in list(category_freq.items())[:10]:
        print(f"  • {cat}: {count} tasks")
    
    print("\n📁 Cleaned files saved with '_cleaned' suffix in:")
    print("   analysis/outputs/clean_final/")
    
    return len(tasks_df)

if __name__ == "__main__":
    main()