#!/usr/bin/env python3
"""
Targeted collection script for missing procedures
"""
import asyncio
import os
from pathlib import Path
from postop_collector import PostOpPDFCollector
from postop_collector.config.settings import Settings

async def collect_missing_procedures():
    """Collect PDFs for specific missing procedures"""
    
    # High-priority missing procedures grouped by category
    missing_procedures = {
        "Orthopedic": [
            "Carpal Tunnel Release post operative instructions",
            "Achilles Tendon Repair recovery guide",
            "Bunion Surgery aftercare",
            "Tennis Elbow Surgery post op care",
            "Trigger Finger Release recovery",
            "Ankle Fracture Repair rehabilitation",
            "Meniscus Repair post surgery",
            "Shoulder Arthroscopy recovery",
            "Fracture Fixation aftercare"
        ],
        "Urology": [
            "Bladder Surgery post operative care",
            "Circumcision aftercare instructions",
            "Hydrocele Repair recovery",
            "Nephrectomy post op instructions",
            "Penile Implant surgery aftercare",
            "Bladder Sling recovery guide",
            "Ureteroscopy post procedure care"
        ],
        "ENT": [
            "Cochlear Implant post surgery care",
            "Laryngoscopy recovery instructions",
            "Vocal Cord Surgery aftercare",
            "Turbinate Reduction post op",
            "Stapedectomy recovery guide",
            "Thyroid Surgery post operative care"
        ],
        "Neurosurgery": [
            "Laminectomy post operative instructions",
            "Microdiscectomy recovery guide",
            "VP Shunt Placement aftercare",
            "Nerve Decompression post surgery",
            "Aneurysm Clipping recovery",
            "Chiari Decompression post op care",
            "Lumbar Puncture aftercare"
        ],
        "Vascular": [
            "AV Fistula Creation post op care",
            "Peripheral Artery Bypass recovery",
            "Endovascular Repair aftercare",
            "Vein Stripping post operative instructions"
        ],
        "Cardiac": [
            "Heart Transplant recovery guide",
            "ICD Implantation aftercare",
            "Mitral Valve Repair post op",
            "TAVR Procedure recovery instructions"
        ],
        "GI Surgery": [
            "Colostomy care instructions",
            "ERCP post procedure care",
            "Gastrostomy Tube aftercare",
            "Nissen Fundoplication recovery",
            "Intestinal Resection post op"
        ]
    }
    
    # Initialize settings and collector
    settings = Settings(
        output_directory="./agent_output",
        max_pdfs_per_source=5,
        min_confidence_score=0.6,
        database_url="sqlite:///./data/agent_collector.db",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        google_search_engine_id=os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
    )
    
    collector = PostOpPDFCollector(settings=settings)
    
    print("=" * 70)
    print("STARTING TARGETED COLLECTION FOR MISSING PROCEDURES")
    print("=" * 70)
    
    total_searches = sum(len(procs) for procs in missing_procedures.values())
    search_count = 0
    collected_count = 0
    
    for category, procedures in missing_procedures.items():
        print(f"\n📁 Collecting {category} procedures ({len(procedures)} searches)...")
        
        for procedure in procedures:
            search_count += 1
            print(f"\n[{search_count}/{total_searches}] Searching: {procedure}")
            
            try:
                # Search Google for PDFs
                query = f"{procedure} PDF patient education filetype:pdf"
                urls = await collector.search_google(query, num_results=5)
                
                if urls:
                    print(f"  ✓ Found {len(urls)} potential PDFs")
                    
                    # Process each URL
                    for url in urls[:3]:  # Limit to top 3 per search
                        try:
                            result = await collector.collect_pdf(url)
                            if result and result.confidence_score >= 0.6:
                                collected_count += 1
                                print(f"  ✓ Collected [{int(result.confidence_score*100)}%]: {url[:60]}...")
                            elif result:
                                print(f"  ⚠️  Low confidence [{int(result.confidence_score*100)}%]: {url[:60]}...")
                        except Exception as e:
                            print(f"  ✗ Failed: {str(e)[:50]}")
                else:
                    print(f"  ⚠️  No results found")
                    
                # Brief delay to respect rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"  ✗ Search error: {str(e)}")
                await asyncio.sleep(5)  # Longer delay on error
    
    print("\n" + "=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)
    print(f"Processed {search_count} searches across {len(missing_procedures)} categories")
    print(f"Successfully collected {collected_count} PDFs")
    print("\nRun 'python3 organize_pdfs_enhanced.py' to organize new PDFs")
    print("Run 'python3 analyze_coverage.py' to see updated coverage stats")

if __name__ == "__main__":
    asyncio.run(collect_missing_procedures())