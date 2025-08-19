#!/usr/bin/env python3
"""Display PDF confidence scores in a simple format."""

from postop_collector.storage.metadata_db import MetadataDB
from postop_collector.config.settings import Settings
from postop_collector.core.models import ProcedureType

def show_confidence():
    # Initialize database
    settings = Settings()
    db = MetadataDB(
        database_url=settings.database_url,
        environment=settings.environment
    )
    
    print("\n" + "="*70)
    print("📊 PDF CONFIDENCE SCORES")
    print("="*70)
    
    # Get statistics
    stats = db.get_statistics()
    print(f"\n📈 Overall Statistics:")
    print(f"  • Total PDFs: {stats['total_pdfs']}")
    print(f"  • Average Confidence: {stats['average_confidence']:.2%}")
    print(f"  • Storage Used: {stats['total_storage_bytes'] / (1024*1024):.1f} MB")
    
    # Get PDFs by procedure type and show confidence
    print(f"\n📋 PDFs by Procedure Type (with confidence):")
    print("-" * 70)
    
    all_pdfs = []
    for proc_type in ProcedureType:
        pdfs = db.get_pdfs_by_procedure_type(
            proc_type,
            min_confidence=0.0,  # Get all
            limit=100
        )
        for pdf in pdfs:
            all_pdfs.append((pdf.confidence_score, pdf.procedure_type, pdf.filename))
    
    # Sort by confidence (highest first)
    all_pdfs.sort(reverse=True)
    
    # Display in a simple table format
    print(f"{'Confidence':<12} {'Type':<20} {'Filename':<38}")
    print("-" * 70)
    
    for confidence, proc_type, filename in all_pdfs:
        # Truncate filename if too long
        display_name = filename[:35] + "..." if len(filename) > 38 else filename
        
        # Color code based on confidence
        if confidence >= 0.8:
            quality = "⭐⭐⭐"  # High
        elif confidence >= 0.6:
            quality = "⭐⭐"    # Medium
        else:
            quality = "⭐"      # Low
            
        print(f"{confidence:>6.2%} {quality:<5} {proc_type:<20} {display_name:<38}")
    
    # Show breakdown by quality level
    high = sum(1 for c, _, _ in all_pdfs if c >= 0.8)
    medium = sum(1 for c, _, _ in all_pdfs if 0.6 <= c < 0.8)
    low = sum(1 for c, _, _ in all_pdfs if c < 0.6)
    
    print("\n" + "="*70)
    print("📊 Quality Distribution:")
    print(f"  ⭐⭐⭐ High (≥80%):   {high} PDFs")
    print(f"  ⭐⭐  Medium (60-79%): {medium} PDFs")
    print(f"  ⭐   Low (<60%):     {low} PDFs")
    print("="*70 + "\n")

if __name__ == "__main__":
    show_confidence()