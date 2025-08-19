#!/usr/bin/env python3
"""
Identify and move PDFs that aren't patient post-op instructions
"""

import pandas as pd
import re
import os
import shutil
from pathlib import Path
from collections import defaultdict

# Load the enhanced analysis data
tasks_df = pd.read_csv('analysis/outputs/postop_care_analysis_enhanced.csv')
overview_df = pd.read_csv('analysis/outputs/procedure_overviews.csv')

print("="*80)
print("IDENTIFYING NON-PATIENT INSTRUCTION PDFs")
print("="*80)

# Patterns that indicate NON-patient materials
non_patient_patterns = {
    'Clinical Guidelines': [
        r'guideline', r'cpg', r'protocol[^s]', r'consensus', r'recommendation',
        r'clinical.?practice', r'evidence.?based', r'best.?practice', r'standard.?of.?care'
    ],
    'Research/Academic': [
        r'systematic.?review', r'meta.?analysis', r'study', r'trial', r'research',
        r'journal', r'pmid', r'doi', r'pubmed', r'springer', r'elsevier', r'wiley',
        r'bmj', r'jama', r'nejm', r'lancet', r'nature', r'science'
    ],
    'Professional/Training': [
        r'society', r'academy', r'association', r'college', r'board',
        r'training', r'curriculum', r'module', r'education(?!.*patient)',
        r'symposium', r'conference', r'webinar', r'presentation', r'slide'
    ],
    'Administrative': [
        r'annual.?report', r'newsletter', r'policy', r'manual', r'billing',
        r'coding', r'reimbursement', r'medicare', r'cms', r'ncd\d+',
        r'quality.?measure', r'performance', r'metric', r'audit'
    ],
    'Provider Resources': [
        r'provider', r'physician', r'surgeon', r'clinician', r'staff',
        r'professional', r'practitioner', r'referral', r'consultation'
    ],
    'Technical/Surgical': [
        r'surgical.?technique', r'operative.?technique', r'technical.?guide',
        r'instrumentation', r'device.?manual', r'product.?guide', r'ifu'
    ]
}

# Patterns that CONFIRM patient materials (to avoid false positives)
patient_patterns = [
    r'patient', r'recovery', r'after.?surgery', r'post.?op', r'discharge',
    r'home.?care', r'what.?to.?expect', r'instructions', r'aftercare'
]

def classify_pdf(filename, task_count=0):
    """Classify a PDF based on filename and content"""
    filename_lower = filename.lower()
    
    # Check for patient patterns first (these are likely good)
    patient_score = sum(1 for p in patient_patterns if re.search(p, filename_lower))
    
    # Check for non-patient patterns
    non_patient_matches = []
    for category, patterns in non_patient_patterns.items():
        for pattern in patterns:
            if re.search(pattern, filename_lower):
                non_patient_matches.append((category, pattern))
    
    # Decision logic
    if non_patient_matches and patient_score == 0:
        # Strong indication it's not for patients
        return 'non-patient', non_patient_matches[0]
    elif len(non_patient_matches) > 1 and patient_score <= 1:
        # Multiple non-patient indicators
        return 'non-patient', non_patient_matches[0]
    elif task_count == 0:
        # No tasks extracted - suspicious
        return 'suspicious', ('No tasks', 'No care tasks found')
    elif task_count < 3 and patient_score == 0:
        # Very few tasks and no patient indicators
        return 'suspicious', ('Low task count', f'Only {task_count} tasks')
    else:
        return 'patient', None

# Analyze each unique PDF
pdf_analysis = defaultdict(lambda: {'task_count': 0, 'categories': set()})

# Count tasks per PDF
for _, row in tasks_df.iterrows():
    pdf = row['pdf_filename']
    pdf_analysis[pdf]['task_count'] += 1
    pdf_analysis[pdf]['categories'].add(row['task_category'])
    pdf_analysis[pdf]['path'] = row['pdf_path']

# Classify PDFs
non_patient_pdfs = []
suspicious_pdfs = []
patient_pdfs = []

for pdf_name, info in pdf_analysis.items():
    classification, reason = classify_pdf(pdf_name, info['task_count'])
    
    pdf_info = {
        'filename': pdf_name,
        'path': info['path'],
        'task_count': info['task_count'],
        'categories': list(info['categories'])[:3],  # First 3 categories
        'classification': classification,
        'reason': reason
    }
    
    if classification == 'non-patient':
        non_patient_pdfs.append(pdf_info)
    elif classification == 'suspicious':
        suspicious_pdfs.append(pdf_info)
    else:
        patient_pdfs.append(pdf_info)

# Also check PDFs with no tasks at all
all_pdfs = set()
for root, dirs, files in os.walk('agent_output/organized_pdfs'):
    for file in files:
        if file.endswith('.pdf'):
            all_pdfs.add(file)

analyzed_pdfs = set(pdf_analysis.keys())
unanalyzed_pdfs = all_pdfs - analyzed_pdfs

for pdf in unanalyzed_pdfs:
    classification, reason = classify_pdf(pdf, 0)
    if classification == 'non-patient':
        # Find the full path
        for root, dirs, files in os.walk('agent_output/organized_pdfs'):
            if pdf in files:
                non_patient_pdfs.append({
                    'filename': pdf,
                    'path': os.path.join(root, pdf),
                    'task_count': 0,
                    'categories': [],
                    'classification': 'non-patient',
                    'reason': reason
                })
                break

# Print findings
print(f"\n📊 CLASSIFICATION RESULTS:")
print(f"  • Patient Instructions: {len(patient_pdfs)} PDFs")
print(f"  • Non-Patient Materials: {len(non_patient_pdfs)} PDFs")
print(f"  • Suspicious/Review: {len(suspicious_pdfs)} PDFs")
print(f"  • Unanalyzed: {len(unanalyzed_pdfs)} PDFs")

print("\n" + "="*80)
print("NON-PATIENT PDFs TO ARCHIVE:")
print("="*80)

# Sort by reason category
non_patient_by_category = defaultdict(list)
for pdf in non_patient_pdfs:
    if pdf['reason']:
        category = pdf['reason'][0] if isinstance(pdf['reason'], tuple) else 'Other'
        non_patient_by_category[category].append(pdf)

for category, pdfs in sorted(non_patient_by_category.items()):
    print(f"\n📁 {category} ({len(pdfs)} files):")
    for pdf in pdfs[:10]:  # Show first 10 per category
        print(f"  • {pdf['filename']}")
        print(f"    Tasks: {pdf['task_count']}, Categories: {', '.join(pdf['categories'][:2]) if pdf['categories'] else 'None'}")
    if len(pdfs) > 10:
        print(f"  ... and {len(pdfs) - 10} more")

print("\n" + "="*80)
print("SUSPICIOUS PDFs (Manual Review Recommended):")
print("="*80)

for pdf in suspicious_pdfs[:15]:
    print(f"  • {pdf['filename']}")
    print(f"    Reason: {pdf['reason'][1] if pdf['reason'] else 'Unknown'}")
    print(f"    Tasks: {pdf['task_count']}, Categories: {', '.join(pdf['categories'][:2])}")

# Create archive directory
archive_dir = Path('agent_output/archived_non_patient_pdfs')
archive_dir.mkdir(exist_ok=True)

print("\n" + "="*80)
print("ARCHIVING NON-PATIENT PDFs")
print("="*80)

# Save list of files to move
with open('non_patient_pdfs_to_archive.txt', 'w') as f:
    f.write("Non-Patient PDFs Identified for Archiving\n")
    f.write("="*60 + "\n\n")
    
    for category, pdfs in sorted(non_patient_by_category.items()):
        f.write(f"\n{category}:\n")
        f.write("-"*40 + "\n")
        for pdf in pdfs:
            f.write(f"{pdf['filename']}\n")
            f.write(f"  Path: {pdf['path']}\n")
            f.write(f"  Tasks: {pdf['task_count']}\n")
            f.write("\n")

print(f"\n✅ Analysis complete!")
print(f"   • {len(non_patient_pdfs)} PDFs identified as non-patient materials")
print(f"   • {len(suspicious_pdfs)} PDFs need manual review")
print(f"   • List saved to: non_patient_pdfs_to_archive.txt")
print(f"\nTo move non-patient PDFs to archive, run:")
print(f"   python3 archive_non_patient_pdfs.py")