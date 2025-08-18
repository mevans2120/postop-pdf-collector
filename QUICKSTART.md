# Quick Start Guide - PostOp PDF Collector

## 🚀 Testing What We've Built

### Step 1: Install Dependencies

First, make sure you have Python 3.8+ installed, then install the required packages:

```bash
cd postop-pdf-collector

# Install core dependencies
pip install aiohttp pydantic beautifulsoup4 python-dotenv

# Install PDF processing libraries
pip install PyPDF2 pdfplumber pymupdf Pillow

# Install test dependencies (optional)
pip install pytest pytest-asyncio pytest-cov
```

Or simply install everything:
```bash
pip install -r requirements.txt
```

### Step 2: Quick Test - No Setup Required!

Run the quick test script to verify everything is working:

```bash
python test_quick.py
```

This will:
- ✅ Test all analysis modules with sample text
- ✅ Verify the content analyzer is working
- ✅ Test procedure categorization
- ✅ Check timeline extraction
- ✅ Initialize the main collector

Expected output:
```
🚀 Starting PostOp PDF Collector Tests

Testing PostOp PDF Collector Analysis Modules
============================================================

1. TESTING CONTENT ANALYZER
✓ Is post-operative content: True
✓ Relevance score: 85%
✓ Content quality: high
...

🎉 ALL TESTS PASSED!
```

### Step 3: Test with Sample Text Analysis

Run the analysis example with built-in sample text:

```bash
python example_analysis.py
```

This demonstrates:
- PDF text analysis
- Procedure classification
- Timeline extraction
- Medication parsing
- Warning sign identification

### Step 4: Run the Full Test Suite

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=postop_collector

# Run specific test file
pytest tests/test_analysis.py -v

# Run with output
pytest -s
```

### Step 5: Test with Real PDFs (Optional)

#### Option A: Test with Local PDFs

1. Create a sample_pdfs directory:
```bash
mkdir sample_pdfs
```

2. Add any PDF files to test
3. Create a test script:

```python
import asyncio
from pathlib import Path
from postop_collector.analysis.pdf_extractor import PDFTextExtractor
from postop_collector.analysis.content_analyzer import ContentAnalyzer

async def test_local_pdf():
    extractor = PDFTextExtractor()
    analyzer = ContentAnalyzer()
    
    pdf_path = Path("sample_pdfs/your_pdf.pdf")
    
    # Extract text
    result = extractor.extract_text_from_file(pdf_path)
    print(f"Extracted {len(result['text_content'])} characters")
    
    # Analyze content
    analysis = analyzer.analyze(result['text_content'])
    print(f"Is post-op: {analysis['is_post_operative']}")
    print(f"Relevance: {analysis['relevance_score']:.2%}")

asyncio.run(test_local_pdf())
```

#### Option B: Test with Web Collection

1. Create a `.env` file (optional, for Google Search):
```env
# Copy from .env.example
OUTPUT_DIRECTORY=./test_output
MAX_PDFS_PER_SOURCE=2
MIN_CONFIDENCE_SCORE=0.5
```

2. Run a test collection:

```python
import asyncio
from postop_collector import PostOpPDFCollector
from postop_collector.config.settings import Settings

async def test_collection():
    settings = Settings(
        output_directory="./test_output",
        max_pdfs_per_source=2,
        min_confidence_score=0.5
    )
    
    async with PostOpPDFCollector(settings) as collector:
        # Test with medical websites
        result = await collector.collect_from_urls([
            "https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies",
            "https://www.mayoclinic.org/tests-procedures"
        ])
        
        print(f"Collected {result.total_pdfs_collected} PDFs")
        
        # Show what was found
        for metadata in result.metadata_list:
            print(f"- {metadata.filename}")
            print(f"  Procedure: {metadata.procedure_type.value}")
            print(f"  Confidence: {metadata.confidence_score:.2%}")

asyncio.run(test_collection())
```

## 📊 Understanding Test Results

### What the Tests Verify

1. **Content Analysis Tests**
   - Correctly identifies post-operative content
   - Extracts warning signs and medications
   - Calculates relevance scores

2. **Procedure Categorization Tests**
   - Identifies procedure types (orthopedic, cardiac, etc.)
   - Extracts procedure details

3. **Timeline Parser Tests**
   - Extracts recovery timeline events
   - Identifies key milestones
   - Creates recovery schedules

4. **Integration Tests**
   - PDF text extraction works
   - All modules integrate correctly
   - Metadata is properly created

## 🔍 Debugging Common Issues

### Import Errors
```bash
# If you get import errors, make sure you're in the right directory:
cd postop-pdf-collector

# And that the package is installed:
pip install -e .
```

### Missing Dependencies
```bash
# If pdfplumber fails:
pip install pdfplumber

# If PyMuPDF fails:
pip install pymupdf
```

### Permission Errors
```bash
# Make sure output directory is writable:
mkdir -p output
chmod 755 output
```

## 📈 Performance Testing

Test with multiple PDFs:

```python
import time
import asyncio
from postop_collector.analysis.content_analyzer import ContentAnalyzer

def performance_test():
    analyzer = ContentAnalyzer()
    
    # Test with increasingly large texts
    for size in [100, 1000, 10000]:
        text = "post-operative care " * size
        
        start = time.time()
        result = analyzer.analyze(text)
        elapsed = time.time() - start
        
        print(f"Size {size}: {elapsed:.3f} seconds")

performance_test()
```

## ✅ Verification Checklist

- [ ] `python test_quick.py` runs without errors
- [ ] All analysis modules return expected results
- [ ] Timeline extraction identifies events correctly
- [ ] Procedure categorization works
- [ ] Content relevance scoring is accurate
- [ ] PDF metadata is properly created

## 🎯 Next Steps

Once testing is complete:

1. **Configure Google Search API** (optional):
   - Get API key from Google Cloud Console
   - Add to `.env` file
   - Test search functionality

2. **Collect Real PDFs**:
   - Run `python example_usage.py`
   - Check `output/` directory for results

3. **Analyze Results**:
   - Review `metadata.json` for collected PDFs
   - Check confidence scores and classifications

4. **Customize Settings**:
   - Adjust `MIN_CONFIDENCE_SCORE` for stricter filtering
   - Modify `MAX_PDFS_PER_SOURCE` for more/fewer PDFs
   - Enable OCR with `ENABLE_OCR=true` (requires tesseract)

## 💡 Tips

- Start with the quick test to verify installation
- Use sample text before trying real PDFs
- Check logs for detailed analysis information
- Lower confidence threshold initially to see more results
- Increase gradually to improve quality

Happy testing! 🎉