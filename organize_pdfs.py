#!/usr/bin/env python3
"""Organize PDFs into procedure-based folder structure."""

import os
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from postop_collector.storage.database import PDFDocument
import json


def sanitize_folder_name(name: str) -> str:
    """Sanitize procedure name for use as folder name."""
    # Remove/replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


def create_folder_structure():
    """Create organized folder structure based on procedure types."""
    base_path = Path("agent_output/organized_pdfs")
    
    # Load procedure database
    with open('procedure_database.json', 'r') as f:
        proc_db = json.load(f)
    
    # Create main categories
    categories = {
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
    
    print("\n📁 Creating Folder Structure")
    print("="*60)
    
    for category_key, category_name in categories.items():
        category_path = base_path / sanitize_folder_name(category_name)
        category_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {category_path}")
        
        # Create subfolders for specific procedures if we have them in the database
        if category_key in proc_db['surgical_procedures']:
            procedures = proc_db['surgical_procedures'][category_key]['procedures']
            for proc in procedures[:5]:  # Create folders for first 5 procedures
                proc_path = category_path / sanitize_folder_name(proc)
                proc_path.mkdir(exist_ok=True)
    
    # Create a special folder for high-quality PDFs
    high_quality_path = base_path / "_High_Quality_PDFs"
    high_quality_path.mkdir(exist_ok=True)
    print(f"✓ Created: {high_quality_path}")
    
    return base_path


def organize_existing_pdfs():
    """Organize existing PDFs into the new folder structure."""
    base_path = Path("agent_output/organized_pdfs")
    original_path = Path("agent_output/pdfs")
    
    if not original_path.exists():
        print("No PDFs to organize.")
        return
    
    # Get PDF metadata from database
    engine = create_engine('sqlite:///./data/agent_collector.db')
    with Session(engine) as session:
        pdfs = session.query(PDFDocument).all()
    
    print(f"\n📂 Organizing {len(pdfs)} PDFs")
    print("="*60)
    
    organized_count = 0
    for pdf in pdfs:
        original_file = original_path / pdf.filename
        if not original_file.exists():
            continue
        
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
        category_path.mkdir(parents=True, exist_ok=True)
        
        # Create confidence-based filename
        confidence_str = f"{int(pdf.confidence_score * 100):02d}"
        new_filename = f"[{confidence_str}%] {pdf.filename}"
        new_path = category_path / new_filename
        
        # Copy file
        shutil.copy2(original_file, new_path)
        organized_count += 1
        print(f"  • {pdf.filename[:40]:<40} → {category_name}/{new_filename[:30]}")
        
        # Also copy high-quality PDFs to special folder
        if pdf.confidence_score >= 0.80:
            high_quality_path = base_path / "_High_Quality_PDFs"
            high_quality_file = high_quality_path / new_filename
            shutil.copy2(original_file, high_quality_file)
    
    print(f"\n✅ Organized {organized_count} PDFs")
    return organized_count


def create_index_file():
    """Create an index HTML file for easy browsing."""
    base_path = Path("agent_output/organized_pdfs")
    
    # Get PDF metadata from database
    engine = create_engine('sqlite:///./data/agent_collector.db')
    with Session(engine) as session:
        pdfs = session.query(PDFDocument).order_by(
            PDFDocument.procedure_type,
            PDFDocument.confidence_score.desc()
        ).all()
    
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Post-Op PDF Collection</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #2c3e50; }
        h2 { color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; }
        .category { margin: 20px 0; }
        .pdf-item { 
            margin: 10px 0; 
            padding: 10px; 
            background: #f8f9fa; 
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
        }
        .confidence { 
            font-weight: bold; 
            padding: 2px 8px; 
            border-radius: 3px; 
        }
        .high { background: #d4edda; color: #155724; }
        .medium { background: #fff3cd; color: #856404; }
        .low { background: #f8d7da; color: #721c24; }
        .stats { 
            background: #e3f2fd; 
            padding: 15px; 
            border-radius: 5px; 
            margin: 20px 0;
        }
        .filename { color: #007bff; text-decoration: none; }
        .filename:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>📚 Post-Operative PDF Collection</h1>
    """
    
    # Add statistics
    total_pdfs = len(pdfs)
    avg_confidence = sum(p.confidence_score for p in pdfs) / total_pdfs if total_pdfs else 0
    high_quality = sum(1 for p in pdfs if p.confidence_score >= 0.8)
    
    html_content += f"""
    <div class="stats">
        <h3>📊 Collection Statistics</h3>
        <p>Total PDFs: <strong>{total_pdfs}</strong></p>
        <p>Average Confidence: <strong>{avg_confidence:.1%}</strong></p>
        <p>High Quality (≥80%): <strong>{high_quality}</strong></p>
        <p>Categories Covered: <strong>{len(set(p.procedure_type for p in pdfs))}</strong></p>
    </div>
    """
    
    # Group PDFs by procedure type
    from collections import defaultdict
    pdfs_by_type = defaultdict(list)
    for pdf in pdfs:
        pdfs_by_type[pdf.procedure_type].append(pdf)
    
    # Add PDFs by category
    for proc_type in sorted(pdfs_by_type.keys()):
        category_pdfs = pdfs_by_type[proc_type]
        html_content += f"""
        <div class="category">
            <h2>{proc_type.replace('_', ' ').title()} ({len(category_pdfs)} PDFs)</h2>
        """
        
        for pdf in category_pdfs:
            confidence_class = 'high' if pdf.confidence_score >= 0.8 else 'medium' if pdf.confidence_score >= 0.6 else 'low'
            confidence_str = f"{int(pdf.confidence_score * 100)}%"
            
            # Create relative path to PDF
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
            pdf_filename = f"[{int(pdf.confidence_score * 100):02d}%] {pdf.filename}"
            pdf_path = f"{sanitize_folder_name(category_name)}/{pdf_filename}"
            
            html_content += f"""
            <div class="pdf-item">
                <a href="{pdf_path}" class="filename">{pdf.filename[:60]}</a>
                <span class="confidence {confidence_class}">{confidence_str}</span>
            </div>
            """
        
        html_content += "</div>"
    
    html_content += """
</body>
</html>
"""
    
    # Save index file
    index_path = base_path / "index.html"
    with open(index_path, 'w') as f:
        f.write(html_content)
    
    print(f"\n📄 Created index file: {index_path}")
    return index_path


def main():
    """Main function to organize PDFs."""
    print("\n" + "="*60)
    print("🗂️  PDF ORGANIZATION SYSTEM")
    print("="*60)
    
    # Create folder structure
    base_path = create_folder_structure()
    
    # Organize existing PDFs
    organized = organize_existing_pdfs()
    
    # Create index file
    if organized > 0:
        index_path = create_index_file()
        print(f"\n✨ Organization complete!")
        print(f"   View organized PDFs at: {base_path}")
        print(f"   Open index: open {index_path}")
    
    print("="*60)


if __name__ == "__main__":
    main()