#!/usr/bin/env python3
"""Enhanced PDF organization by specific procedures with confidence scores."""

import os
import re
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from postop_collector.storage.database import PDFDocument
import json


def sanitize_folder_name(name: str) -> str:
    """Sanitize procedure name for use as folder name."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


def identify_specific_procedure(filename: str, content: str = "") -> str:
    """Identify specific procedure from filename."""
    filename_lower = filename.lower()
    
    # Define procedure patterns
    procedure_patterns = {
        # Orthopedic procedures
        'Total Knee Replacement': r'(total[\s-]?knee|tkr|tka|knee[\s-]?replacement|knee[\s-]?arthroplasty)',
        'Total Hip Replacement': r'(total[\s-]?hip|thr|tha|hip[\s-]?replacement|hip[\s-]?arthroplasty)',
        'ACL Reconstruction': r'(acl|anterior[\s-]?cruciate)',
        'Rotator Cuff Repair': r'(rotator[\s-]?cuff|rtc|shoulder)',
        'Meniscus Repair': r'(meniscus|meniscal)',
        'Carpal Tunnel Release': r'(carpal[\s-]?tunnel)',
        'Spinal Fusion': r'(spinal[\s-]?fusion|spine)',
        'Ankle Surgery': r'(ankle)',
        'Shoulder Arthroscopy': r'(shoulder[\s-]?arthroscopy)',
        
        # Cardiac procedures
        'Coronary Artery Bypass': r'(cabg|coronary[\s-]?artery[\s-]?bypass|bypass[\s-]?graft)',
        'Heart Valve Replacement': r'(valve[\s-]?replacement|mitral|aortic[\s-]?valve)',
        'Pacemaker Implantation': r'(pacemaker|icd[\s-]?implant)',
        'Angioplasty': r'(angioplasty|stent)',
        'Carotid Endarterectomy': r'(carotid[\s-]?endarterectomy)',
        'Aneurysm Repair': r'(aneurysm|aaa[\s-]?repair)',
        
        # General Surgery
        'Appendectomy': r'(appendectomy|appendix)',
        'Gallbladder Removal': r'(cholecystectomy|gall[\s-]?bladder|gallbladder)',
        'Hernia Repair': r'(hernia[\s-]?repair|inguinal[\s-]?hernia)',
        'Colonoscopy': r'(colonoscopy)',
        'Hemorrhoidectomy': r'(hemorrhoid|rectal)',
        'Thyroidectomy': r'(thyroid|thyroidectomy)',
        
        # Gynecological
        'Hysterectomy': r'(hysterectomy)',
        'C-Section': r'(c[\s-]?section|cesarean)',
        'Ovarian Cyst Removal': r'(ovarian[\s-]?cyst)',
        
        # Ophthalmology
        'Cataract Surgery': r'(cataract)',
        'LASIK': r'(lasik)',
        'Glaucoma Surgery': r'(glaucoma)',
        
        # ENT
        'Tonsillectomy': r'(tonsillectomy|tonsil)',
        'Adenoidectomy': r'(adenoid)',
        'Septoplasty': r'(septoplasty|nasal)',
        'Sinus Surgery': r'(sinus|fess)',
        
        # Plastic Surgery
        'Mastectomy': r'(mastectomy)',
        'Breast Reconstruction': r'(breast[\s-]?reconstruction)',
        'Facelift': r'(facelift|face[\s-]?lift)',
        'Blepharoplasty': r'(blepharoplasty|eyelid)',
        
        # Dental/Oral
        'Tooth Extraction': r'(extraction|tooth)',
        'Wisdom Teeth': r'(wisdom[\s-]?teeth)',
        'Dental Implant': r'(dental[\s-]?implant)',
        
        # Vascular
        'Varicose Veins': r'(varicose[\s-]?vein)',
        'Bypass Surgery': r'(bypass)',
        
        # Urology
        'Prostatectomy': r'(prostatectomy|prostate)',
        'TURP': r'(turp)',
        'Kidney Stone': r'(kidney[\s-]?stone)',
    }
    
    # Check filename against patterns
    for procedure, pattern in procedure_patterns.items():
        if re.search(pattern, filename_lower):
            return procedure
    
    return None


def organize_pdfs_by_procedure():
    """Organize PDFs into procedure-specific folders with confidence scores."""
    base_path = Path("agent_output/organized_pdfs")
    original_path = Path("agent_output/pdfs")
    
    if not original_path.exists():
        print("No PDFs to organize.")
        return
    
    # Get PDF metadata from database
    engine = create_engine('sqlite:///./data/agent_collector.db')
    with Session(engine) as session:
        pdfs = session.query(PDFDocument).all()
    
    print(f"\n📂 Enhanced Organization of {len(pdfs)} PDFs")
    print("="*60)
    
    # Statistics tracking
    stats = {
        'organized': 0,
        'by_procedure': {},
        'uncategorized': []
    }
    
    for pdf in pdfs:
        original_file = original_path / pdf.filename
        if not original_file.exists():
            continue
        
        # Identify specific procedure
        specific_procedure = identify_specific_procedure(pdf.filename)
        
        # Map procedure type to category folder
        category_map = {
            'orthopedic': 'Orthopedic Surgery',
            'cardiac': 'Cardiac Surgery',
            'general_surgery': 'General Surgery',
            'neurological': 'Neurosurgery',
            'urological': 'Urology',
            'gynecological': 'Gynecological Surgery',
            'ent': 'ENT Surgery',
            'ophthalmic': 'Ophthalmology',
            'plastic_surgery': 'Plastic Surgery',
            'dental': 'Oral Surgery',
            'vascular': 'Vascular Surgery',
            'gastrointestinal': 'GI Surgery',
            'thoracic': 'Thoracic Surgery',
            'pediatric': 'Pediatric Surgery',
            'unknown': 'Uncategorized'
        }
        
        category_name = category_map.get(pdf.procedure_type, 'Uncategorized')
        category_path = base_path / sanitize_folder_name(category_name)
        
        # If specific procedure identified, create subfolder
        if specific_procedure:
            target_path = category_path / sanitize_folder_name(specific_procedure)
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Track statistics
            if specific_procedure not in stats['by_procedure']:
                stats['by_procedure'][specific_procedure] = 0
            stats['by_procedure'][specific_procedure] += 1
        else:
            target_path = category_path
            target_path.mkdir(parents=True, exist_ok=True)
            stats['uncategorized'].append(pdf.filename)
        
        # Create confidence-based filename
        confidence_str = f"{int(pdf.confidence_score * 100):02d}"
        new_filename = f"[{confidence_str}%] {pdf.filename}"
        new_path = target_path / new_filename
        
        # Copy file (overwrite if exists)
        try:
            shutil.copy2(original_file, new_path)
            stats['organized'] += 1
            
            # Display progress
            if specific_procedure:
                print(f"  ✓ {pdf.filename[:35]:<35} → {specific_procedure}/{new_filename[:25]}")
            else:
                print(f"  • {pdf.filename[:35]:<35} → {category_name}/{new_filename[:25]}")
            
            # Also copy high-quality PDFs to special folder
            if pdf.confidence_score >= 0.85:
                high_quality_path = base_path / "_High_Quality_PDFs"
                high_quality_path.mkdir(exist_ok=True)
                
                if specific_procedure:
                    hq_filename = f"[{confidence_str}%] {specific_procedure} - {pdf.filename}"
                else:
                    hq_filename = new_filename
                    
                high_quality_file = high_quality_path / hq_filename
                shutil.copy2(original_file, high_quality_file)
                
        except Exception as e:
            print(f"  ✗ Error organizing {pdf.filename}: {e}")
    
    # Display statistics
    print(f"\n📊 Organization Summary")
    print("="*60)
    print(f"✅ Successfully organized: {stats['organized']} PDFs")
    print(f"\n📁 By Specific Procedure:")
    for proc, count in sorted(stats['by_procedure'].items(), key=lambda x: x[1], reverse=True):
        print(f"  • {proc:<30} {count:>3} PDFs")
    
    if stats['uncategorized']:
        print(f"\n⚠️  Uncategorized ({len(stats['uncategorized'])} PDFs):")
        for filename in stats['uncategorized'][:5]:
            print(f"  • {filename}")
        if len(stats['uncategorized']) > 5:
            print(f"  ... and {len(stats['uncategorized']) - 5} more")
    
    return stats


def create_procedure_index():
    """Create an enhanced HTML index organized by specific procedures."""
    base_path = Path("agent_output/organized_pdfs")
    
    # Get PDF metadata from database
    engine = create_engine('sqlite:///./data/agent_collector.db')
    with Session(engine) as session:
        pdfs = session.query(PDFDocument).order_by(
            PDFDocument.confidence_score.desc()
        ).all()
    
    # Group PDFs by specific procedure
    pdfs_by_procedure = {}
    for pdf in pdfs:
        procedure = identify_specific_procedure(pdf.filename)
        if not procedure:
            procedure = "Other Procedures"
        
        if procedure not in pdfs_by_procedure:
            pdfs_by_procedure[procedure] = []
        pdfs_by_procedure[procedure].append(pdf)
    
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Post-Op PDFs by Procedure</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #2d3748; 
            margin: 0 0 10px 0;
        }
        .subtitle {
            color: #718096;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 5px;
        }
        .procedure-section {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }
        h2 { 
            color: #2d3748;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .pdf-grid {
            display: grid;
            gap: 10px;
        }
        .pdf-item { 
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 8px;
            transition: background 0.2s;
        }
        .pdf-item:hover {
            background: #e9ecef;
        }
        .confidence { 
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.9em;
        }
        .high { background: #d4edda; color: #155724; }
        .medium { background: #fff3cd; color: #856404; }
        .low { background: #f8d7da; color: #721c24; }
        .filename { 
            color: #4c51bf;
            text-decoration: none;
            flex: 1;
            margin-right: 10px;
        }
        .filename:hover { text-decoration: underline; }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            background: #edf2f7;
            color: #4a5568;
            border-radius: 4px;
            font-size: 0.85em;
            margin-left: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Post-Operative Care PDFs</h1>
            <div class="subtitle">Organized by Specific Procedures with Confidence Scores</div>
            """
    
    # Add statistics
    total_pdfs = len(pdfs)
    avg_confidence = sum(p.confidence_score for p in pdfs) / total_pdfs if total_pdfs else 0
    high_quality = sum(1 for p in pdfs if p.confidence_score >= 0.85)
    procedures_count = len(pdfs_by_procedure)
    
    html_content += f"""
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{total_pdfs}</div>
                    <div class="stat-label">Total PDFs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{procedures_count}</div>
                    <div class="stat-label">Procedures</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{avg_confidence:.0%}</div>
                    <div class="stat-label">Avg Confidence</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{high_quality}</div>
                    <div class="stat-label">High Quality</div>
                </div>
            </div>
        </div>
    """
    
    # Add PDFs by procedure
    for procedure in sorted(pdfs_by_procedure.keys()):
        procedure_pdfs = sorted(pdfs_by_procedure[procedure], 
                               key=lambda x: x.confidence_score, 
                               reverse=True)
        
        html_content += f"""
        <div class="procedure-section">
            <h2>{procedure} <span class="badge">{len(procedure_pdfs)} PDFs</span></h2>
            <div class="pdf-grid">
        """
        
        for pdf in procedure_pdfs:
            confidence_class = 'high' if pdf.confidence_score >= 0.85 else 'medium' if pdf.confidence_score >= 0.65 else 'low'
            confidence_str = f"{int(pdf.confidence_score * 100)}%"
            
            # Determine file path
            category_map = {
                'orthopedic': 'Orthopedic Surgery',
                'cardiac': 'Cardiac Surgery',
                'general_surgery': 'General Surgery',
                'neurological': 'Neurosurgery',
                'urological': 'Urology',
                'gynecological': 'Gynecological Surgery',
                'ent': 'ENT Surgery',
                'ophthalmic': 'Ophthalmology',
                'plastic_surgery': 'Plastic Surgery',
                'dental': 'Oral Surgery',
                'vascular': 'Vascular Surgery',
                'gastrointestinal': 'GI Surgery',
                'thoracic': 'Thoracic Surgery',
                'pediatric': 'Pediatric Surgery',
                'unknown': 'Uncategorized'
            }
            
            category_name = category_map.get(pdf.procedure_type, 'Uncategorized')
            if procedure != "Other Procedures":
                pdf_path = f"{sanitize_folder_name(category_name)}/{sanitize_folder_name(procedure)}/[{int(pdf.confidence_score * 100):02d}%] {pdf.filename}"
            else:
                pdf_path = f"{sanitize_folder_name(category_name)}/[{int(pdf.confidence_score * 100):02d}%] {pdf.filename}"
            
            html_content += f"""
                <div class="pdf-item">
                    <a href="{pdf_path}" class="filename">{pdf.filename[:60]}</a>
                    <span class="confidence {confidence_class}">{confidence_str}</span>
                </div>
            """
        
        html_content += """
            </div>
        </div>
        """
    
    html_content += """
    </div>
</body>
</html>
"""
    
    # Save index file
    index_path = base_path / "procedure_index.html"
    with open(index_path, 'w') as f:
        f.write(html_content)
    
    print(f"\n📄 Created procedure index: {index_path}")
    return index_path


def main():
    """Main function to organize PDFs by specific procedures."""
    print("\n" + "="*60)
    print("🗂️  ENHANCED PDF ORGANIZATION BY PROCEDURE")
    print("="*60)
    
    # Organize PDFs by specific procedures
    stats = organize_pdfs_by_procedure()
    
    # Create procedure-based index
    if stats and stats['organized'] > 0:
        index_path = create_procedure_index()
        print(f"\n✨ Enhanced organization complete!")
        print(f"   View by procedure: open {index_path}")
    
    print("="*60)


if __name__ == "__main__":
    main()