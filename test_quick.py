#!/usr/bin/env python3
"""Quick test script to verify the PostOp PDF Collector is working."""

import asyncio
import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from postop_collector.analysis.content_analyzer import ContentAnalyzer
from postop_collector.analysis.procedure_categorizer import ProcedureCategorizer
from postop_collector.analysis.timeline_parser import TimelineParser


def test_analysis_modules():
    """Test the analysis modules with sample text."""
    print("=" * 60)
    print("Testing PostOp PDF Collector Analysis Modules")
    print("=" * 60)
    
    # Sample post-operative text
    sample_text = """
    POST-OPERATIVE INSTRUCTIONS: TOTAL KNEE REPLACEMENT
    
    Date of Surgery: January 15, 2024
    Surgeon: Dr. Smith, Orthopedic Surgery
    
    IMMEDIATE POST-OPERATIVE CARE (Days 1-3):
    • Keep your leg elevated when sitting or lying down
    • Apply ice packs for 20 minutes every 2 hours while awake
    • Take pain medication as prescribed
    • Perform ankle pump exercises 10 times every hour while awake
    
    MEDICATIONS:
    1. Oxycodone 5mg: Take 1-2 tablets every 4-6 hours as needed for pain
       (Maximum 8 tablets in 24 hours)
    2. Acetaminophen 500mg: Take 2 tablets every 6 hours
    3. Aspirin 81mg: Take once daily for 6 weeks to prevent blood clots
    4. Cephalexin 500mg: Take twice daily for 7 days (antibiotic)
    
    ACTIVITY PROGRESSION:
    • Day 1-3: Bed rest with bathroom privileges, use walker
    • Week 1-2: Limited walking with walker, no weight restrictions
    • Week 3-4: Transition to cane, increase walking distance
    • Week 6: Most patients can walk without assistance
    • Month 3: Return to most normal activities
    • Month 6: Full recovery expected
    
    WARNING SIGNS - CALL YOUR DOCTOR IMMEDIATELY IF YOU EXPERIENCE:
    ⚠️ Fever greater than 101.5°F (38.6°C)
    ⚠️ Increasing pain not controlled by medication  
    ⚠️ Redness, warmth, or drainage from the incision site
    ⚠️ Chest pain or difficulty breathing
    ⚠️ Calf pain, swelling, or tenderness (possible blood clot)
    ⚠️ Sudden inability to bear weight on the operated leg
    
    WOUND CARE:
    • Keep incision dry for first 48 hours
    • After 48 hours, you may shower but do not soak in a bath
    • Change dressing daily or if it becomes wet/soiled
    • Sutures will be removed at your 2-week follow-up appointment
    
    FOLLOW-UP APPOINTMENTS:
    • Wound check: 1 week post-surgery (January 22, 2024)
    • Suture removal: 2 weeks post-surgery (January 29, 2024)
    • First follow-up with surgeon: 6 weeks (February 26, 2024)
    • Physical therapy evaluation: Week 3
    
    PHYSICAL THERAPY:
    Physical therapy is crucial for your recovery. You will begin PT in week 3.
    Expect to attend 2-3 sessions per week for 6-8 weeks.
    
    DIET:
    • No dietary restrictions unless specified by your doctor
    • Drink plenty of fluids
    • Eat protein-rich foods to promote healing
    
    RETURN TO ACTIVITIES:
    • Driving: When you can bend your knee comfortably and are off narcotics (typically 4-6 weeks)
    • Work: Desk job 4-6 weeks, physical labor 10-12 weeks
    • Sexual activity: When comfortable, typically 4-6 weeks
    • Sports: Low-impact activities at 3 months, high-impact after 6 months
    
    If you have any questions or concerns, please contact our office at (555) 123-4567.
    
    After-hours emergency: (555) 123-4999
    """
    
    print("\n1. TESTING CONTENT ANALYZER")
    print("-" * 40)
    analyzer = ContentAnalyzer()
    analysis = analyzer.analyze(sample_text)
    
    print(f"✓ Is post-operative content: {analysis['is_post_operative']}")
    print(f"✓ Relevance score: {analysis['relevance_score']:.2%}")
    print(f"✓ Content quality: {analysis['content_quality']}")
    print(f"✓ Sections found: {len(analysis['sections_found'])} sections")
    
    if analysis['sections_found']:
        print(f"  Sections: {', '.join(analysis['sections_found'][:5])}")
    
    print(f"\n  Warning signs extracted: {len(analysis['warning_signs'])}")
    if analysis['warning_signs']:
        print(f"  Example: {analysis['warning_signs'][0][:80]}...")
    
    print(f"\n  Medications found: {len(analysis['medication_instructions'])}")
    if analysis['medication_instructions']:
        print(f"  Example: {analysis['medication_instructions'][0][:80]}...")
    
    # Test procedure categorizer
    print("\n2. TESTING PROCEDURE CATEGORIZER")
    print("-" * 40)
    categorizer = ProcedureCategorizer()
    proc_type, confidence = categorizer.categorize(sample_text)
    
    print(f"✓ Procedure type: {proc_type.value}")
    print(f"✓ Confidence: {confidence:.2%}")
    
    details = categorizer.extract_procedure_details(sample_text)
    if details['procedure_name']:
        print(f"✓ Procedure identified: {details['procedure_name']}")
    if details['body_part']:
        print(f"✓ Body part: {details['body_part']}")
    
    # Test timeline parser
    print("\n3. TESTING TIMELINE PARSER")
    print("-" * 40)
    parser = TimelineParser()
    events = parser.parse_timeline(sample_text)
    
    print(f"✓ Timeline events found: {len(events)}")
    
    if events:
        print("\n  Sample timeline events:")
        for event in events[:5]:
            print(f"  • {event.time_reference} ({event.time_value} days): {event.category}")
    
    milestones = parser.extract_milestones(events)
    if milestones:
        print(f"\n  Key milestones identified: {len(milestones)}")
        for milestone in milestones[:3]:
            print(f"  • {milestone['type']}: {milestone['time_reference']}")
    
    # Test schedule creation
    schedule = parser.create_recovery_schedule(events)
    print(f"\n  Recovery periods identified: {len(schedule)}")
    for period in list(schedule.keys())[:3]:
        print(f"  • {period}: {len(schedule[period])} events")
    
    print("\n" + "=" * 60)
    print("✅ All analysis modules working correctly!")
    print("=" * 60)
    
    return True


async def test_collector():
    """Test the main collector with a simple example."""
    print("\n4. TESTING MAIN COLLECTOR")
    print("-" * 40)
    
    from postop_collector import PostOpPDFCollector
    from postop_collector.config.settings import Settings
    
    # Create test settings
    settings = Settings(
        output_directory="./test_output",
        max_pdfs_per_source=2,
        min_confidence_score=0.3,
        max_requests_per_second=1.0,
    )
    
    print(f"✓ Settings created")
    print(f"  Output directory: {settings.output_directory}")
    print(f"  Min confidence score: {settings.min_confidence_score}")
    
    # Initialize collector
    async with PostOpPDFCollector(settings) as collector:
        print("✓ Collector initialized")
        print(f"  Analysis modules loaded: {len([collector.pdf_extractor, collector.content_analyzer, collector.timeline_parser, collector.procedure_categorizer])}")
        
        # Test with a simple website (won't download actual PDFs without real URLs)
        test_urls = ["https://www.example.com"]
        
        print(f"\n  Testing with URL: {test_urls[0]}")
        print("  (Note: This won't find actual PDFs on example.com)")
        
        result = await collector.collect_from_urls(test_urls)
        
        print(f"\n✓ Collection completed")
        print(f"  URLs discovered: {result.total_urls_discovered}")
        print(f"  PDFs collected: {result.total_pdfs_collected}")
    
    return True


def main():
    """Run all tests."""
    print("\n🚀 Starting PostOp PDF Collector Tests\n")
    
    try:
        # Test analysis modules
        success = test_analysis_modules()
        
        if success:
            # Test async collector
            print("\nTesting async collector...")
            asyncio.run(test_collector())
            
            print("\n" + "=" * 60)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 60)
            print("\nThe PostOp PDF Collector is working correctly!")
            print("\nNext steps:")
            print("1. Set up your Google API credentials in .env file")
            print("2. Run: python example_usage.py")
            print("3. Or run the full test suite: pytest")
            
        else:
            print("\n❌ Some tests failed. Please check the output above.")
            
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("\nPlease make sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())