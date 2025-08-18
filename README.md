# PostOp PDF Collector

A Python package for collecting and analyzing post-operative instruction PDFs from various medical sources.

## Features

- **Automated PDF Discovery**: Search and collect PDFs from multiple sources
- **Web Crawling**: Discover PDFs from medical websites
- **Advanced PDF Analysis**: 
  - Text extraction with multiple methods (pdfplumber, PyPDF2, OCR-ready)
  - Content relevance scoring
  - Automatic procedure type classification
  - Timeline and recovery schedule extraction
  - Medication instruction parsing
  - Warning sign identification
- **Intelligent Filtering**: Only collect relevant post-operative content
- **Metadata Management**: Track collected PDFs with comprehensive metadata
- **Rate Limiting**: Respectful crawling with configurable rate limits
- **Configuration Management**: Environment-based configuration with validation

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/postop-pdf-collector.git
cd postop-pdf-collector

# Install in development mode
pip install -e .

# Or install with all dependencies
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from postop_collector import PostOpPDFCollector
from postop_collector.config.settings import Settings

async def main():
    # Configure settings
    settings = Settings(
        output_directory="./collected_pdfs",
        max_pdfs_per_source=10,
        google_api_key="your_api_key",  # Optional
        google_search_engine_id="your_engine_id"  # Optional
    )
    
    # Create collector
    async with PostOpPDFCollector(settings) as collector:
        # Collect from search queries
        result = await collector.run_collection(
            search_queries=[
                "post operative care instructions pdf",
                "surgery recovery guide pdf",
                "cardiac surgery aftercare pdf"
            ],
            direct_urls=[
                "http://hospital.example.com/patient-resources",
                "http://clinic.example.com/post-op-care.pdf"
            ]
        )
        
        # Print results
        print(f"Collected {result.total_pdfs_collected} PDFs")
        print(f"Success rate: {result.success_rate:.2%}")
        print(f"By procedure type: {result.by_procedure_type}")
        print(f"By source: {result.by_source_domain}")

# Run the collector
asyncio.run(main())
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
# API Keys
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Output Configuration
OUTPUT_DIRECTORY=./output
MAX_PDFS_PER_SOURCE=10
MAX_PAGES_PER_SITE=50

# Rate Limiting
MAX_REQUESTS_PER_SECOND=2.0
REQUEST_TIMEOUT=30

# Quality Control
MIN_CONFIDENCE_SCORE=0.5
MIN_TEXT_LENGTH=100

# Logging
LOG_LEVEL=INFO
LOG_FILE=collector.log
```

### Programmatic Configuration

```python
from postop_collector.config.settings import Settings

settings = Settings(
    output_directory="/path/to/output",
    max_pdfs_per_source=20,
    max_requests_per_second=1.0,
    min_confidence_score=0.7
)
```

## Project Structure

```
postop_collector/
├── core/
│   ├── collector.py          # Main collector implementation
│   └── models.py             # Pydantic data models
├── analysis/                  # ✅ Phase 2 Complete
│   ├── pdf_extractor.py      # PDF text extraction
│   ├── content_analyzer.py   # Content analysis & relevance scoring
│   ├── timeline_parser.py    # Timeline extraction
│   └── procedure_categorizer.py # Procedure classification
├── discovery/
│   ├── search_api.py         # Search API integration (Phase 3)
│   └── web_crawler.py        # Web crawling logic (Phase 3)
├── storage/
│   ├── file_manager.py       # File operations (Phase 3)
│   └── metadata_db.py        # Database operations (Phase 3)
├── config/
│   └── settings.py           # Configuration management
└── utils/
    └── rate_limiter.py       # Rate limiting utilities
```

## REST API

The project includes a comprehensive REST API built with FastAPI:

```bash
# Start the API server
python run_api.py

# API will be available at:
# - http://localhost:8000
# - Documentation: http://localhost:8000/docs
# - Alternative docs: http://localhost:8000/redoc
```

### Key API Endpoints

- `GET /health` - Health check
- `GET /api/v1/pdfs/` - List PDFs with filters
- `POST /api/v1/collection/start` - Start new collection
- `POST /api/v1/search/` - Search PDFs
- `GET /api/v1/statistics/` - Get statistics

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for full API documentation.

## Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Or use the deployment script
./deploy.sh production up

# Stop services
./deploy.sh production down

# View logs
./deploy.sh production logs
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=postop_collector

# Run specific test file
pytest tests/test_collector.py

# Test API endpoints
pytest tests/test_api.py

# Test database operations
pytest tests/test_database.py
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Format code
black postop_collector tests

# Sort imports
isort postop_collector tests

# Type checking
mypy postop_collector

# Linting
flake8 postop_collector tests
```

## Roadmap

### Phase 1: Foundation (Current)
- ✅ Basic package structure
- ✅ Core collector implementation
- ✅ Configuration management
- ✅ Basic testing framework
- ✅ Rate limiting

### Phase 2: Analysis Integration (Completed ✅)
- ✅ PDF text extraction with PyPDF2/pdfplumber
- ✅ Advanced content analysis
- ✅ Confidence scoring
- ✅ Timeline extraction
- ✅ Medication instruction parsing
- ✅ Procedure categorization
- ✅ Warning sign extraction
- ✅ Content quality assessment

### Phase 3: Production Features (Completed ✅)
- ✅ Database persistence (SQLite/PostgreSQL)
- ✅ REST API endpoints with FastAPI
- ✅ Docker deployment configuration
- [ ] Monitoring and alerting
- [ ] CI/CD pipeline

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.