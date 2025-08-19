# PostOp PDF Collector - System Documentation

## 🎯 Purpose
An intelligent system that automatically collects, analyzes, and organizes post-operative care instruction PDFs for surgical procedures. The system uses AI-powered agents to search the web, evaluate PDF quality and relevance, and maintain a comprehensive database of post-op care instructions. Additionally performs deep content analysis to extract specific care tasks, categorize them, and generate structured datasets for healthcare applications.

## 🏗️ Architecture Overview

### Core Components

```
postop-pdf-collector/
├── agent_interface.py          # AI agent orchestrator with Google search
├── smart_collector.py          # Intelligent targeted collection by procedure
├── web_dashboard.py            # FastAPI backend with WebSocket support
├── dashboard_live.html         # Real-time monitoring dashboard
├── organize_pdfs.py            # Basic PDF organization script
├── organize_pdfs_enhanced.py   # Advanced organization by specific procedures
├── procedure_database.json     # Comprehensive US surgical procedures database
├── analysis/                   # PDF content analysis system
│   ├── scripts/
│   │   ├── pdf_analyzer_simple.py      # Pattern-based task extraction
│   │   └── enhance_descriptions.py     # Enhanced description extractor
│   └── outputs/
│       ├── clean_final/                # Cleaned dataset results
│       └── postop_care_analysis.csv    # Full task analysis
├── identify_non_patient_pdfs.py        # Classifier for non-patient materials
├── archive_non_patient_pdfs.py         # Archive management for non-patient PDFs
├── run_clean_analysis.py               # Run analysis on patient-only PDFs
└── postop_collector/           # Core library modules
    ├── analyzer/               # PDF analysis and confidence scoring
    ├── collector/              # Web scraping and downloading
    ├── storage/                # Database and file management
    └── config/                 # Configuration and settings
```

### Data Flow
1. **Search Phase**: Agent queries Google for procedure-specific PDFs
2. **Collection Phase**: Downloads and validates PDFs
3. **Analysis Phase**: AI analyzes content for relevance and quality
4. **Organization Phase**: Categorizes by procedure with confidence scores
5. **Content Extraction**: Pattern-based extraction of care tasks and instructions
6. **Quality Control**: Identification and archiving of non-patient materials
7. **Storage Phase**: SQLite database + organized file structure + CSV datasets

### Key Technologies
- **Backend**: Python, FastAPI, SQLAlchemy, asyncio
- **Frontend**: HTML5, JavaScript, WebSocket for real-time updates
- **AI/ML**: Google Gemini API for content analysis
- **Search**: Google Custom Search API
- **Storage**: SQLite database + filesystem organization

## 📊 Database Schema

### PDFDocument Table
- `id`: Primary key
- `url`: Source URL
- `filename`: Local filename
- `procedure_type`: Category (orthopedic, cardiac, etc.)
- `specific_procedure`: Extracted procedure name
- `confidence_score`: 0.0-1.0 relevance score
- `quality_assessment`: high/medium/low
- `content_hash`: SHA-256 for deduplication
- `collected_at`: Timestamp
- `metadata`: JSON field for additional data

## 🚀 Recent Work Completed (August 19, 2024)

### 1. Live Dashboard Integration
- ✅ Connected `dashboard_live.html` to real backend API
- ✅ Replaced mock data with actual collection status
- ✅ Added WebSocket support for real-time updates
- ✅ Implemented polling for collection statistics
- ✅ Added "Clear Terminal" functionality

### 2. PDF Organization Enhancement
- ✅ Added confidence percentages to all PDF filenames `[XX%]`
- ✅ Created procedure-specific subfolders (e.g., "Total Knee Replacement")
- ✅ Implemented pattern matching for 40+ specific procedures
- ✅ Generated `_High_Quality_PDFs` folder for ≥85% confidence
- ✅ Created enhanced HTML index with procedure grouping

### 3. Deep Content Analysis Implementation
- ✅ Extracted **4,371 patient care tasks** from PDFs
- ✅ Enhanced task descriptions to average **243 characters** (3x improvement)
- ✅ Discovered **12 new task categories** beyond predefined ones
- ✅ Identified and archived **44 non-patient PDFs** (guidelines, research papers)
- ✅ Created cleaned dataset with **232 patient-only PDFs**
- ✅ Generated comprehensive CSV datasets for analysis

### 4. Current Statistics (Post-Cleaning)
- **232 patient instruction PDFs** (cleaned dataset)
- **4,371 care tasks** extracted with enhanced descriptions
- **275 procedure overviews** documented
- **75% average confidence** score
- **16 task categories** including newly discovered ones

## 🎮 How to Use

### Start the Web Server
```bash
python3 web_dashboard.py
# Dashboard available at http://localhost:8001
```

### Run Smart Collection
```bash
# Targeted collection for specific procedures
python3 smart_collector.py --action systematic --rounds 3 --pdfs 20
```

### Organize Existing PDFs
```bash
# Basic organization with confidence scores
python3 organize_pdfs.py

# Enhanced organization by specific procedures
python3 organize_pdfs_enhanced.py
```

### View Organized PDFs
```bash
open agent_output/organized_pdfs/procedure_index.html
```

### Run Deep Content Analysis
```bash
# Analyze all PDFs and extract care tasks
python3 run_full_analysis.py

# Enhanced extraction with fuller descriptions
python3 analysis/scripts/enhance_descriptions.py

# Identify and archive non-patient PDFs
python3 identify_non_patient_pdfs.py
python3 archive_non_patient_pdfs.py

# Run analysis on cleaned patient-only dataset
python3 run_clean_analysis.py
```

### View Analysis Results
```bash
# View extracted care tasks
open analysis/outputs/clean_final/patient_care_tasks_final.csv

# View procedure overviews
open analysis/outputs/clean_final/procedure_overviews_final.csv
```

## 📋 Outstanding Tasks & Improvements

### High Priority
- [ ] **Real-time Progress Updates**: Enhance WebSocket to show individual PDF analysis in dashboard
- [ ] **Duplicate Detection**: Implement content-based deduplication before downloading
- [ ] **API Rate Limiting**: Add backoff strategy for Google Search API limits
- [ ] **Error Recovery**: Implement checkpoint/resume for interrupted collections

### Medium Priority
- [ ] **Procedure Auto-Detection**: Use NLP to extract procedure names from PDF content
- [ ] **Multi-language Support**: Collect Spanish language post-op instructions
- [ ] **Source Ranking**: Prioritize trusted medical institutions (Mayo, Cleveland Clinic, etc.)
- [ ] **Export Functionality**: Generate procedure-specific PDF bundles for distribution

### Low Priority
- [ ] **Analytics Dashboard**: Add charts showing coverage gaps and collection trends
- [ ] **User Accounts**: Multi-user support with personalized collections
- [ ] **Mobile App**: iOS/Android app for viewing collected PDFs
- [ ] **Cloud Backup**: Automatic backup to S3/Google Drive

### Quality Improvements
- [ ] **Content Validation**: Verify PDFs contain actual post-op instructions
- [ ] **Freshness Check**: Prioritize recently updated PDFs (check publication dates)
- [ ] **Completeness Score**: Analyze if PDFs cover all essential recovery topics
- [ ] **Readability Analysis**: Score PDFs on patient-friendliness

## 🔧 Configuration

### Environment Variables (.env)
```bash
GOOGLE_API_KEY="your-api-key"
GOOGLE_SEARCH_ENGINE_ID="your-search-engine-id"
GEMINI_API_KEY="your-gemini-key"
MAX_CONCURRENT_DOWNLOADS=5
CONFIDENCE_THRESHOLD=0.6
```

### Key Files
- `data/agent_collector.db` - SQLite database
- `agent_output/pdfs/` - Raw downloaded PDFs
- `agent_output/organized_pdfs/` - Organized by procedure
- `agent_output/archived_non_patient_pdfs/` - Non-patient materials archive
- `analysis/outputs/clean_final/` - Final cleaned analysis results
  - `patient_care_tasks_final.csv` - All extracted care tasks
  - `procedure_overviews_final.csv` - Procedure summaries
  - `discovered_categories_final.csv` - New task categories found
  - `category_frequency_final.json` - Task distribution data
- `data/collection_state.json` - Collection progress tracking
- `data/collection_history.json` - Historical run data
- `pdf_analysis_plan.md` - Comprehensive analysis planning document

## 🐛 Known Issues

1. **Memory Usage**: Large PDF collections (>1000) may cause memory issues
2. **API Limits**: Google Search API has 100 queries/day limit (free tier)
3. **PDF Parsing**: Some scanned PDFs fail text extraction
4. **Procedure Matching**: ~40% of PDFs remain uncategorized by specific procedure

## 📈 Performance Metrics

- **Collection Speed**: ~20-30 PDFs per minute
- **Analysis Accuracy**: 75% average confidence score
- **Categorization Success**: 60% matched to specific procedures
- **Storage Efficiency**: ~200MB per 100 PDFs

## 🔐 Security Considerations

- API keys stored in environment variables
- No PHI/PII collected from PDFs
- Local storage only (no cloud transmission)
- Content hash prevents duplicate storage

## 🚦 Testing Commands

```bash
# Test agent interface
python3 -c "from agent_interface import AgentInterface; import asyncio; asyncio.run(AgentInterface().test_connection())"

# Check database
python3 show_pdf_stats.py

# View collection history
python3 view_pdfs.py

# Test web server
curl http://localhost:8001/api/status
```

## 📝 Notes for Future Development

1. **Scalability**: Consider PostgreSQL for >10,000 PDFs
2. **Caching**: Implement Redis for search result caching
3. **ML Enhancement**: Fine-tune BERT model for procedure classification
4. **Compliance**: Ensure HIPAA compliance before any cloud deployment
5. **Monitoring**: Add OpenTelemetry for production monitoring

---

*Last Updated: August 19, 2024*
*Primary Developer: Michael Evans*
*AI Assistant: Claude (Anthropic)*

## 📊 Content Analysis Achievements

### Task Extraction Results
- **4,371 patient care tasks** extracted from 232 cleaned PDFs
- **Average 19 tasks per PDF** with enhanced descriptions
- **243 character average** task description length (3x improvement)
- **16 distinct task categories** including:
  - Activity Restrictions (516 tasks)
  - Medication Management (451 tasks)
  - Diet & Nutrition (379 tasks)
  - Wound Care (340 tasks)
  - Follow-up Care (228 tasks)
  - Plus 11 more categories including newly discovered ones

### Data Quality Improvements
- **Pattern-based extraction** using 10+ regex patterns for comprehensive capture
- **Multi-sentence context** preservation for complete instructions
- **Dynamic category discovery** identifying new care areas not in predefined list
- **Non-patient material filtering** removing clinical guidelines and research papers
- **Enhanced description extraction** capturing full context up to 3 sentences

### Analysis Outputs
All analysis results available in `analysis/outputs/clean_final/`:
- Complete care task dataset with procedure references
- Procedure overviews with summaries
- Category frequency analysis
- Discovered categories documentation