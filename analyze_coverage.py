#!/usr/bin/env python3
import json
import os
from pathlib import Path

# Load procedure database
with open('procedure_database.json', 'r') as f:
    data = json.load(f)

# Get all procedures from database
all_procedures = []
procedure_categories = {}
for category_key, category_data in data['surgical_procedures'].items():
    category_name = category_data['category']
    for procedure in category_data['procedures']:
        all_procedures.append(procedure)
        procedure_categories[procedure] = category_name

# Get procedures we have PDFs for
organized_path = Path('agent_output/organized_pdfs')
covered_procedures = set()

# Check all subdirectories for procedure-specific folders
for category_dir in organized_path.iterdir():
    if category_dir.is_dir() and not category_dir.name.startswith('_'):
        # Check for procedure-specific subdirectories
        for proc_dir in category_dir.iterdir():
            if proc_dir.is_dir():
                covered_procedures.add(proc_dir.name)
                
# Also check for procedures that might be in the directory names themselves
for root, dirs, files in os.walk(organized_path):
    for dirname in dirs:
        # Check if directory name matches any procedure
        for procedure in all_procedures:
            if procedure.lower() in dirname.lower() or dirname.lower() in procedure.lower():
                covered_procedures.add(procedure)

# Calculate coverage
total_procedures = len(all_procedures)
covered_count = len(covered_procedures)
missing_procedures = sorted(set(all_procedures) - covered_procedures)

# Group missing procedures by category
missing_by_category = {}
for proc in missing_procedures:
    category = procedure_categories.get(proc, "Unknown")
    if category not in missing_by_category:
        missing_by_category[category] = []
    missing_by_category[category].append(proc)

# Print report
print("=" * 70)
print("PDF COLLECTION COVERAGE REPORT")
print("=" * 70)
print(f"\nTotal procedures in database: {total_procedures}")
print(f"Procedures with PDFs: {covered_count}")
print(f"Coverage: {covered_count/total_procedures*100:.1f}%")
print(f"Missing procedures: {len(missing_procedures)}")

print("\n" + "=" * 70)
print("MISSING PROCEDURES BY CATEGORY")
print("=" * 70)

for category in sorted(missing_by_category.keys()):
    procedures = missing_by_category[category]
    print(f"\n{category} ({len(procedures)} missing):")
    for proc in procedures:
        print(f"  - {proc}")

print("\n" + "=" * 70)
print("HIGH PRIORITY MISSING PROCEDURES")
print("=" * 70)
print("\nMost common procedures still needed:")
high_priority = [
    "Carpal Tunnel Release",
    "Cataract Surgery", 
    "Colonoscopy",
    "C-Section",
    "Vasectomy",
    "Kidney Stone Removal",
    "Appendectomy",
    "Tonsillectomy",
    "Hemorrhoidectomy",
    "Varicose Vein Surgery"
]

for proc in high_priority:
    if proc in missing_procedures:
        print(f"  ⚠️  {proc}")