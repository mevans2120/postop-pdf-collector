#!/usr/bin/env python3
"""Display PDF collection statistics with confidence scores."""

from postop_collector.storage.metadata_db import MetadataDB
from postop_collector.config.settings import Settings
from tabulate import tabulate
import os

def show_pdf_stats():
    # Initialize database
    settings = Settings()
    db = MetadataDB(
        database_url=settings.database_url,
        environment=settings.environment
    )
    
    # Get all PDFs sorted by confidence
    all_pdfs = sorted(db.get_all_pdfs(), key=lambda x: x.confidence_score, reverse=True)
    
    if not all_pdfs:
        print("No PDFs in database yet.")
        return
    
    # Prepare data for table
    table_data = []
    for pdf in all_pdfs:
        # Check if file exists
        file_exists = "✓" if os.path.exists(pdf.file_path) else "✗"
        
        # Truncate filename if too long
        filename = pdf.filename[:40] + "..." if len(pdf.filename) > 40 else pdf.filename
        
        table_data.append([
            filename,
            pdf.procedure_type,
            f"{pdf.confidence_score:.2f}",
            pdf.content_quality,
            f"{pdf.file_size / 1024:.0f} KB",
            file_exists
        ])
    
    # Print statistics
    print("\n" + "="*80)
    print("📊 PDF COLLECTION STATISTICS")
    print("="*80)
    
    # Summary stats
    total_pdfs = len(all_pdfs)
    avg_confidence = sum(p.confidence_score for p in all_pdfs) / total_pdfs if total_pdfs > 0 else 0
    high_quality = sum(1 for p in all_pdfs if p.confidence_score >= 0.8)
    medium_quality = sum(1 for p in all_pdfs if 0.6 <= p.confidence_score < 0.8)
    low_quality = sum(1 for p in all_pdfs if p.confidence_score < 0.6)
    
    print(f"\n📈 Summary:")
    print(f"  • Total PDFs: {total_pdfs}")
    print(f"  • Average Confidence: {avg_confidence:.2%}")
    print(f"  • High Quality (≥80%): {high_quality} PDFs")
    print(f"  • Medium Quality (60-79%): {medium_quality} PDFs")
    print(f"  • Low Quality (<60%): {low_quality} PDFs")
    
    # Procedure type breakdown
    print(f"\n🏥 Procedure Types:")
    proc_types = {}
    for pdf in all_pdfs:
        proc_types[pdf.procedure_type] = proc_types.get(pdf.procedure_type, 0) + 1
    
    for proc_type, count in sorted(proc_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {proc_type}: {count} PDFs")
    
    # Detailed table
    print(f"\n📋 PDF Details (sorted by confidence):")
    print("-" * 80)
    
    headers = ["Filename", "Procedure Type", "Confidence", "Quality", "Size", "File"]
    print(tabulate(table_data, headers=headers, tablefmt="simple"))
    
    # Show top medications and warnings if available
    print("\n💊 Sample Extracted Content:")
    for pdf in all_pdfs[:3]:  # Show top 3
        if pdf.medication_instructions or pdf.warning_signs:
            print(f"\n  📄 {pdf.filename[:50]}:")
            if pdf.medication_instructions:
                meds = pdf.medication_instructions[:3]
                print(f"     Medications: {', '.join(meds[:3])}")
            if pdf.warning_signs:
                warnings = pdf.warning_signs[:2]
                print(f"     Warnings: {', '.join(warnings[:2])}")
    
    print("\n" + "="*80)
    print("💡 Tip: PDFs with confidence ≥ 0.6 are considered good quality")
    print("="*80 + "\n")

if __name__ == "__main__":
    show_pdf_stats()