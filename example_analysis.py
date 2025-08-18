"""Example demonstrating Phase 2 analysis features."""

import asyncio
import logging
from pathlib import Path

from postop_collector import PostOpPDFCollector
from postop_collector.analysis.content_analyzer import ContentAnalyzer
from postop_collector.analysis.pdf_extractor import PDFTextExtractor
from postop_collector.analysis.procedure_categorizer import ProcedureCategorizer
from postop_collector.analysis.timeline_parser import TimelineParser
from postop_collector.config.settings import Settings
from postop_collector.core.models import ProcedureType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def analyze_single_pdf():
    """Demonstrate analyzing a single PDF file."""
    print("\n=== Single PDF Analysis Example ===\n")
    
    # Initialize components
    extractor = PDFTextExtractor(enable_ocr=False)
    analyzer = ContentAnalyzer()
    timeline_parser = TimelineParser()
    categorizer = ProcedureCategorizer()
    
    # Example: Analyze a local PDF file
    pdf_path = Path("./sample_pdfs/knee_replacement.pdf")
    
    if pdf_path.exists():
        # Extract text
        print(f"Analyzing: {pdf_path}")
        extraction_result = extractor.extract_text_from_file(pdf_path)
        
        print(f"  Pages: {extraction_result['page_count']}")
        print(f"  Extraction method: {extraction_result['extraction_method']}")
        print(f"  Has tables: {extraction_result['has_tables']}")
        print(f"  Has images: {extraction_result['has_images']}")
        
        # Clean and analyze text
        text = extractor.clean_text(extraction_result['text_content'])
        
        # Content analysis
        print("\nContent Analysis:")
        content_result = analyzer.analyze(text)
        print(f"  Is post-operative: {content_result['is_post_operative']}")
        print(f"  Relevance score: {content_result['relevance_score']:.2f}")
        print(f"  Content quality: {content_result['content_quality']}")
        print(f"  Sections found: {', '.join(content_result['sections_found'][:5])}")
        
        # Procedure categorization
        print("\nProcedure Classification:")
        proc_type, confidence = categorizer.categorize(text)
        print(f"  Type: {proc_type.value}")
        print(f"  Confidence: {confidence:.2f}")
        
        details = categorizer.extract_procedure_details(text)
        if details['procedure_name']:
            print(f"  Procedure: {details['procedure_name']}")
        if details['body_part']:
            print(f"  Body part: {details['body_part']}")
        if details['surgical_approach']:
            print(f"  Approach: {details['surgical_approach']}")
        
        # Timeline extraction
        print("\nTimeline Information:")
        events = timeline_parser.parse_timeline(text)
        print(f"  Timeline events found: {len(events)}")
        
        if events:
            print("  Key milestones:")
            milestones = timeline_parser.extract_milestones(events)
            for milestone in milestones[:5]:
                print(f"    • {milestone['time_reference']}: {milestone['type']}")
        
        # Warning signs
        if content_result['warning_signs']:
            print("\nWarning Signs Extracted:")
            for sign in content_result['warning_signs'][:3]:
                print(f"  • {sign[:80]}...")
        
        # Medications
        if content_result['medication_instructions']:
            print("\nMedication Instructions:")
            for med in content_result['medication_instructions'][:3]:
                print(f"  • {med[:80]}...")
    else:
        print(f"Sample PDF not found at {pdf_path}")
        print("Creating a sample text for demonstration...")
        
        # Demo with sample text
        sample_text = """
        POST-OPERATIVE INSTRUCTIONS: TOTAL KNEE REPLACEMENT
        
        Your orthopedic surgeon has performed a total knee replacement surgery.
        These instructions will guide you through your recovery process.
        
        IMMEDIATE POST-OPERATIVE PERIOD (Days 1-3):
        - Rest with your leg elevated
        - Apply ice to reduce swelling
        - Take prescribed pain medications every 4-6 hours
        
        MEDICATIONS:
        - Oxycodone 5mg: Take 1-2 tablets every 4 hours as needed for pain
        - Aspirin 81mg: Take once daily for blood clot prevention
        - Antibiotics: Complete the full 7-day course
        
        ACTIVITY RESTRICTIONS:
        Week 1-2: Use walker, no weight bearing
        Week 3-4: Partial weight bearing with crutches
        Week 6: Full weight bearing as tolerated
        
        WARNING SIGNS - Call your doctor immediately if you experience:
        - Fever over 101°F
        - Increasing pain not controlled by medication
        - Redness, warmth, or drainage from the incision
        - Chest pain or shortness of breath
        - Calf pain or swelling
        
        FOLLOW-UP:
        - Suture removal: 10-14 days post-surgery
        - First follow-up: 2 weeks
        - Physical therapy begins: Week 3
        - Return to work: 6-8 weeks (office work)
        - Full recovery: 3-6 months
        """
        
        print("\nAnalyzing sample text...")
        
        # Analyze sample text
        content_result = analyzer.analyze(sample_text)
        print(f"\nContent Analysis:")
        print(f"  Is post-operative: {content_result['is_post_operative']}")
        print(f"  Relevance score: {content_result['relevance_score']:.2f}")
        print(f"  Content quality: {content_result['content_quality']}")
        
        # Categorize procedure
        proc_type, confidence = categorizer.categorize(sample_text)
        print(f"\nProcedure: {proc_type.value} (confidence: {confidence:.2f})")
        
        # Extract timeline
        events = timeline_parser.parse_timeline(sample_text)
        schedule = timeline_parser.create_recovery_schedule(events)
        
        print(f"\nRecovery Schedule:")
        for period, period_events in schedule.items():
            print(f"  {period.replace('_', ' ').title()}:")
            for event in period_events[:2]:
                print(f"    • {event.time_reference}: {event.category}")


async def demonstrate_collection_with_analysis():
    """Demonstrate the full collection pipeline with analysis."""
    print("\n=== Collection with Analysis Example ===\n")
    
    settings = Settings(
        output_directory="./output/analyzed",
        max_pdfs_per_source=3,
        min_confidence_score=0.5,  # Only keep relevant PDFs
        enable_ocr=False,
    )
    
    async with PostOpPDFCollector(settings) as collector:
        # Example URLs (these would need to be real URLs in practice)
        test_urls = [
            "https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies",
            "https://orthoinfo.aaos.org/en/recovery/",
        ]
        
        print("Starting collection with analysis...")
        print(f"Minimum confidence score: {settings.min_confidence_score}")
        print(f"URLs to process: {len(test_urls)}")
        
        result = await collector.collect_from_urls(test_urls)
        
        print(f"\nCollection Results:")
        print(f"  PDFs collected: {result.total_pdfs_collected}")
        print(f"  URLs discovered: {result.total_urls_discovered}")
        print(f"  Success rate: {result.success_rate:.1%}")
        
        if result.metadata_list:
            print(f"\nCollected PDFs by Procedure Type:")
            for proc_type, count in result.by_procedure_type.items():
                print(f"  {proc_type}: {count}")
            
            print(f"\nQuality Distribution:")
            quality_counts = {}
            for metadata in result.metadata_list:
                quality = metadata.content_quality.value
                quality_counts[quality] = quality_counts.get(quality, 0) + 1
            
            for quality, count in quality_counts.items():
                print(f"  {quality}: {count} PDFs")
            
            print(f"\nAverage confidence score: {result.average_confidence:.2f}")
            
            # Show sample of high-quality PDFs
            high_quality = [
                m for m in result.metadata_list 
                if m.confidence_score > 0.7
            ]
            
            if high_quality:
                print(f"\nHigh-Quality PDFs Found ({len(high_quality)}):")
                for pdf in high_quality[:3]:
                    print(f"  • {pdf.filename}")
                    print(f"    - Procedure: {pdf.procedure_type.value}")
                    print(f"    - Confidence: {pdf.confidence_score:.2f}")
                    print(f"    - Quality: {pdf.content_quality.value}")
                    if pdf.timeline_elements:
                        print(f"    - Timeline points: {len(pdf.timeline_elements)}")


async def analyze_by_procedure_type():
    """Demonstrate filtering and analyzing by procedure type."""
    print("\n=== Analysis by Procedure Type Example ===\n")
    
    settings = Settings(
        output_directory="./output/by_procedure",
        min_confidence_score=0.6,
    )
    
    # Target specific procedure types
    target_procedures = [
        ProcedureType.ORTHOPEDIC,
        ProcedureType.CARDIAC,
        ProcedureType.GENERAL,
    ]
    
    async with PostOpPDFCollector(settings) as collector:
        # Search queries tailored to specific procedures
        queries = [
            "knee replacement post operative instructions pdf",
            "cardiac surgery recovery guide pdf",
            "gallbladder surgery aftercare pdf",
        ]
        
        print(f"Searching for {len(target_procedures)} procedure types...")
        
        result = await collector.collect_from_search_queries(queries)
        
        # Organize by procedure type
        organized = {}
        for metadata in result.metadata_list:
            proc_type = metadata.procedure_type
            if proc_type not in organized:
                organized[proc_type] = []
            organized[proc_type].append(metadata)
        
        print(f"\nOrganized Results:")
        for proc_type in target_procedures:
            pdfs = organized.get(proc_type, [])
            print(f"\n{proc_type.value.upper()}:")
            print(f"  Found: {len(pdfs)} PDFs")
            
            if pdfs:
                # Analyze common elements
                all_timelines = []
                all_medications = []
                all_warnings = []
                
                for pdf in pdfs:
                    all_timelines.extend(pdf.timeline_elements)
                    all_medications.extend(pdf.medication_instructions)
                    all_warnings.extend(pdf.warning_signs)
                
                print(f"  Common elements across {proc_type.value} procedures:")
                print(f"    - Timeline points: {len(set(all_timelines))}")
                print(f"    - Medications mentioned: {len(set(all_medications))}")
                print(f"    - Warning signs: {len(set(all_warnings))}")


async def main():
    """Run all analysis examples."""
    print("=" * 60)
    print("PostOp PDF Collector - Phase 2 Analysis Features")
    print("=" * 60)
    
    # Run examples
    await analyze_single_pdf()
    
    # These examples would actually collect PDFs if given real URLs
    # await demonstrate_collection_with_analysis()
    # await analyze_by_procedure_type()
    
    print("\n" + "=" * 60)
    print("Analysis examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())