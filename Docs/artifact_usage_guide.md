# Artifact Usage Guide for Claude Code Development

## Previously Created Artifacts Overview

I've created two key artifacts that will be extremely valuable for your Claude Code development:

### 1. **Post-Op PDF Collection Pipeline** (Primary Implementation)
**Artifact ID:** `postop_pdf_collector`  
**Type:** Complete Python implementation  
**Value:** ⭐⭐⭐⭐⭐ (Essential)

### 2. **PDF Text Extraction & Analysis** (Enhancement Module)
**Artifact ID:** `pdf_text_extractor`  
**Type:** Advanced analysis components  
**Value:** ⭐⭐⭐⭐⭐ (Essential)

## Recommended Usage Strategy with Claude Code

### Phase 1: Foundation with Primary Artifact

#### Start with the Core Collector
```bash
# Begin your Claude Code session
cd postop-pdf-collector
claude "I have a complete PDF collection pipeline implementation that I'd like to adapt and enhance. Let me share the existing code structure."

# Copy the main collector code
# Then continue:
claude "This is the foundation code I want to build upon. Please:
1. Refactor this into a proper Python package structure
2. Add proper error handling and logging
3. Implement the missing PDF text extraction integration
4. Add configuration management with environment variables
5. Create proper async context management"
```

#### Key Adaptations Needed:
```python
# Original has placeholder comments like:
# text_content = extract_pdf_text(content)  # Implement separately

# Claude Code should implement:
async def extract_pdf_text(self, pdf_content: bytes) -> str:
    """Extract text using the PDF analysis components"""
    analyzer = PDFTextAnalyzer()
    # Implementation from the second artifact
```

### Phase 2: Integration with Analysis Module

#### Enhance with Advanced Analysis
```bash
claude "Now I want to integrate the advanced PDF text analysis capabilities. Here's the analysis module I have:"

# Share the PDFTextAnalyzer code
# Then continue:
claude "Please integrate this analysis system into our main collector:
1. Replace the placeholder text extraction with this robust system
2. Integrate the confidence scoring into our PDFMetadata class
3. Add the timeline extraction to our analysis pipeline
4. Implement the advanced procedure categorization
5. Create proper data models using Pydantic"
```

#### Integration Points:
```python
# In the main collector, enhance the download_and_analyze_pdf method:
async def download_and_analyze_pdf(self, pdf_url: str) -> PDFMetadata:
    # ... existing download code ...
    
    # Enhanced with analysis module
    analyzer = PDFTextAnalyzer()
    analysis_results = analyzer.analyze_pdf_content(file_path)
    
    metadata = PDFMetadata(
        url=pdf_url,
        filename=filename,
        source_domain=domain,
        file_size=len(content),
        text_content=analysis_results["text_content"],
        confidence_score=analysis_results["confidence_score"],
        procedure_type=max(analysis_results["procedure_categories"].items(), key=lambda x: x[1])[0],
        timeline_elements=analysis_results["timeline_elements"],
        medication_instructions=analysis_results["medication_instructions"],
        warning_signs=analysis_results["warning_signs"]
    )
```

## Specific Claude Code Commands for Implementation

### Initial Setup and Structure
```bash
# Create the project structure
claude "Transform this single-file implementation into a professional Python package:

postop_collector/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── collector.py          # Main PostOpPDFCollector class
│   └── models.py             # Pydantic data models
├── discovery/
│   ├── __init__.py
│   ├── search_api.py         # Google Custom Search integration
│   └── web_crawler.py        # Website crawling logic
├── analysis/
│   ├── __init__.py
│   ├── pdf_extractor.py      # PDF text extraction
│   ├── content_analyzer.py   # Content analysis and classification
│   └── timeline_parser.py    # Timeline extraction
├── storage/
│   ├── __init__.py
│   ├── file_manager.py       # File system operations
│   └── metadata_db.py        # Database operations
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration management
└── utils/
    ├── __init__.py
    ├── rate_limiter.py       # Rate limiting utilities
    └── logging_config.py     # Logging setup

Split the existing code into these modules logically."
```

### Enhanced Error Handling
```bash
claude "Add comprehensive error handling throughout the codebase:
1. Create custom exception classes for different error types
2. Implement retry logic with exponential backoff
3. Add circuit breaker pattern for unreliable sources
4. Create proper logging with structured data
5. Add health checks and monitoring endpoints"
```

### Configuration Management
```bash
claude "Replace hardcoded values with proper configuration management:
1. Use Pydantic for configuration models with validation
2. Support environment variables and config files
3. Add different profiles (development, staging, production)
4. Include validation for API keys and required settings
5. Create a configuration wizard for initial setup"
```

### Testing Framework
```bash
claude "Create a comprehensive testing framework:
1. Unit tests for each module with high coverage
2. Integration tests for the full pipeline
3. Mock services for external APIs (Google Search, websites)
4. Test fixtures with sample PDFs of different types
5. Performance tests for large-scale collection
6. Add test data generators for different scenarios"
```

## Key Enhancements to Add with Claude Code

### 1. Production-Ready Features
```bash
claude "Add production-ready features to make this enterprise-grade:
1. Database migrations for metadata storage
2. API endpoints for external integration
3. Authentication and authorization
4. Rate limiting with Redis backend
5. Monitoring and alerting integration
6. Docker deployment with docker-compose
7. CI/CD pipeline with GitHub Actions"
```

### 2. Advanced PDF Processing
```bash
claude "Enhance the PDF processing capabilities:
1. OCR support for scanned documents using Tesseract
2. Image extraction and analysis from PDFs
3. Table extraction for structured data
4. Multi-language support detection
5. PDF quality assessment metrics
6. Handling of password-protected PDFs"
```

### 3. Machine Learning Integration
```bash
claude "Add machine learning capabilities:
1. Train classification models on collected data
2. Implement active learning for improving accuracy
3. Add clustering for discovering new procedure types
4. Create embeddings for semantic similarity
5. Implement anomaly detection for content quality
6. Add recommendation system for related procedures"
```

### 4. Monitoring and Analytics
```bash
claude "Build comprehensive monitoring and analytics:
1. Real-time dashboards for collection status
2. Quality metrics and trend analysis
3. Source reliability scoring and blacklisting
4. Performance profiling and optimization suggestions
5. Cost tracking for API usage
6. Alerting for collection failures or quality drops"
```

## Development Workflow Integration

### Daily Development Cycle
1. **Morning Standup with Claude:**
   ```bash
   claude --continue "Review yesterday's progress, current pipeline status, and plan today's development priorities"
   ```

2. **Feature Development:**
   ```bash
   claude "Implement [specific feature] following our established patterns and integrating with the existing collector and analyzer modules"
   ```

3. **Code Review:**
   ```bash
   claude "Review this implementation for:
   - Code quality and consistency with our patterns
   - Performance implications
   - Error handling completeness
   - Test coverage
   - Documentation needs"
   ```

4. **Testing and Validation:**
   ```bash
   claude "Create tests for the new functionality and run a small-scale collection to validate the implementation"
   ```

### Custom Project Commands

Create these slash commands in `.claude/commands/`:

#### `/integrate-analyzer`
```markdown
Integrate the PDF text analyzer module with the main collector:
1. Update the download_and_analyze_pdf method
2. Enhance the PDFMetadata model with new fields
3. Update database schema if needed
4. Add proper error handling for analysis failures
5. Create tests for the integrated functionality
```

#### `/optimize-performance`
```markdown
Optimize the collection pipeline performance:
1. Profile the current implementation
2. Identify bottlenecks in PDF processing
3. Implement caching for repeated operations
4. Optimize database queries and batch operations
5. Add monitoring for performance metrics
```

#### `/validate-collection`
```markdown
Validate a collection run:
1. Check collection success rates by source
2. Analyze content quality metrics
3. Identify any classification errors
4. Generate quality report with recommendations
5. Update source reliability scores
```

## Migration Strategy from Artifacts

### Step 1: Foundation Migration
1. Copy the main collector class as starting point
2. Refactor into modular architecture
3. Add proper Python packaging
4. Implement configuration management
5. Add basic testing framework

### Step 2: Analysis Integration
1. Integrate the PDFTextAnalyzer class
2. Enhance data models with analysis results
3. Update the collection pipeline
4. Add comprehensive error handling
5. Create integration tests

### Step 3: Production Enhancement
1. Add database persistence
2. Implement API endpoints
3. Add monitoring and logging
4. Create deployment configuration
5. Build documentation and examples

This approach leverages the solid foundation of the existing artifacts while using Claude Code's capabilities to build a production-ready, enterprise-grade system for your post-operative instruction collection needs.