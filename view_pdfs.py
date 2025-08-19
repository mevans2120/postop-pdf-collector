#!/usr/bin/env python3
"""View all PDFs with their confidence scores and details."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from postop_collector.storage.database import PDFDocument
import os

def view_pdfs():
    # Check both database locations
    databases = [
        ('agent_collector.db', './data/agent_collector.db'),
        ('collector.db', './data/collector.db')
    ]
    
    for db_name, db_path in databases:
        if not os.path.exists(db_path):
            continue
            
        engine = create_engine(f'sqlite:///{db_path}')
        with Session(engine) as session:
            pdfs = session.query(PDFDocument).all()
            
            if not pdfs:
                continue
                
            print(f"\n{'='*80}")
            print(f"📊 PDFs in {db_name}: {len(pdfs)} documents")
            print(f"{'='*80}")
            
            # Sort by confidence
            pdfs_sorted = sorted(pdfs, key=lambda x: x.confidence_score, reverse=True)
            
            # Calculate stats
            avg_confidence = sum(p.confidence_score for p in pdfs) / len(pdfs)
            high_quality = sum(1 for p in pdfs if p.confidence_score >= 0.8)
            medium_quality = sum(1 for p in pdfs if 0.6 <= p.confidence_score < 0.8)
            low_quality = sum(1 for p in pdfs if p.confidence_score < 0.6)
            
            print(f"\n📈 Statistics:")
            print(f"  • Average Confidence: {avg_confidence:.1%}")
            print(f"  • High Quality (≥80%): {high_quality} PDFs")
            print(f"  • Medium Quality (60-79%): {medium_quality} PDFs")
            print(f"  • Low Quality (<60%): {low_quality} PDFs")
            
            print(f"\n📋 PDF List (sorted by confidence):")
            print(f"{'='*80}")
            print(f"{'Score':<8} {'Quality':<10} {'Type':<18} {'Filename'}")
            print(f"{'-'*80}")
            
            for pdf in pdfs_sorted:
                # Determine quality level
                if pdf.confidence_score >= 0.8:
                    quality = "⭐⭐⭐ High"
                elif pdf.confidence_score >= 0.6:
                    quality = "⭐⭐ Medium"
                else:
                    quality = "⭐ Low"
                
                # Truncate filename if needed
                filename = pdf.filename[:35] + "..." if len(pdf.filename) > 38 else pdf.filename
                
                print(f"{pdf.confidence_score:>6.0%}   {quality:<10} {pdf.procedure_type:<18} {filename}")
            
            # Show sample extracted content
            print(f"\n💊 Sample Extracted Content:")
            print(f"{'-'*80}")
            
            for pdf in pdfs_sorted[:3]:  # Top 3 PDFs
                print(f"\n📄 {pdf.filename[:50]} ({pdf.confidence_score:.0%}):")
                
                if pdf.medication_instructions:
                    meds = pdf.medication_instructions[:3] if isinstance(pdf.medication_instructions, list) else []
                    if meds:
                        print(f"   Medications: {', '.join(str(m) for m in meds[:2])}")
                
                if pdf.timeline_elements:
                    timeline = pdf.timeline_elements[:2] if isinstance(pdf.timeline_elements, list) else []
                    if timeline:
                        print(f"   Timeline: {', '.join(str(t) for t in timeline[:2])}")
                
                if pdf.warning_signs:
                    warnings = pdf.warning_signs[:2] if isinstance(pdf.warning_signs, list) else []
                    if warnings:
                        print(f"   Warnings: {', '.join(str(w) for w in warnings[:2])}")
            
            print(f"\n{'='*80}")

if __name__ == "__main__":
    view_pdfs()