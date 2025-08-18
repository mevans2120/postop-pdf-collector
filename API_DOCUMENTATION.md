# PostOp PDF Collector REST API Documentation

## Overview

The PostOp PDF Collector provides a comprehensive REST API for managing PDF collections, searching documents, and analyzing post-operative instructions.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. In production, implement appropriate authentication mechanisms.

## Starting the API Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python run_api.py

# Or with custom settings
export API_HOST=0.0.0.0
export API_PORT=8080
export DATABASE_URL=postgresql://user:pass@localhost/postop
python run_api.py
```

## API Documentation

Interactive documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### Health Check

#### GET /health
Check API health and database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database_connected": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### PDF Management

#### GET /api/v1/pdfs/
List PDFs with optional filters.

**Query Parameters:**
- `procedure_type` (string): Filter by procedure type
- `min_confidence` (float): Minimum confidence score (0.0-1.0)
- `source_domain` (string): Filter by source domain
- `limit` (int): Maximum results (default: 50)
- `offset` (int): Pagination offset (default: 0)

**Response:**
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "has_more": true,
  "items": [
    {
      "id": 1,
      "url": "https://example.com/guide.pdf",
      "filename": "surgery-guide.pdf",
      "confidence_score": 0.85,
      "procedure_type": "orthopedic",
      "content_quality": "high",
      "source_domain": "example.com",
      "page_count": 12
    }
  ]
}
```

#### GET /api/v1/pdfs/{pdf_id}
Get detailed PDF metadata.

**Response:**
```json
{
  "id": 1,
  "url": "https://example.com/guide.pdf",
  "filename": "surgery-guide.pdf",
  "file_path": "/data/pdfs/surgery-guide.pdf",
  "file_hash": "abc123...",
  "file_size": 2048576,
  "confidence_score": 0.85,
  "procedure_type": "orthopedic",
  "content_quality": "high",
  "timeline_elements": ["Day 1-3: Rest", "Week 1-2: Light activity"],
  "medication_instructions": ["Take pain medication as needed"],
  "warning_signs": ["Fever above 101F", "Excessive bleeding"]
}
```

#### GET /api/v1/pdfs/{pdf_id}/download
Download the actual PDF file.

**Response:** Binary PDF file

#### GET /api/v1/pdfs/{pdf_id}/analysis
Get analysis results for a PDF.

**Query Parameters:**
- `analysis_type` (string): Filter by analysis type (timeline, medication, procedure)

**Response:**
```json
[
  {
    "id": 1,
    "analysis_type": "timeline",
    "results": {
      "events": [...]
    },
    "confidence": 0.9,
    "processing_time_ms": 250
  }
]
```

#### DELETE /api/v1/pdfs/{pdf_id}
Delete a PDF and its associated data.

### Collection Management

#### POST /api/v1/collection/start
Start a new PDF collection run.

**Request Body:**
```json
{
  "search_queries": ["post operative care", "surgery recovery"],
  "direct_urls": ["https://hospital.com/guides"],
  "max_pdfs": 20,
  "min_confidence": 0.6
}
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Collection started successfully",
  "status": "running"
}
```

#### GET /api/v1/collection/runs
List all collection runs.

**Response:**
```json
[
  {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "started_at": "2024-01-15T10:00:00Z",
    "completed_at": "2024-01-15T10:15:00Z",
    "total_pdfs_collected": 15,
    "total_urls_discovered": 50,
    "success_rate": 0.3,
    "average_confidence": 0.75
  }
]
```

#### GET /api/v1/collection/runs/{run_id}
Get details of a specific collection run.

#### POST /api/v1/collection/runs/{run_id}/stop
Stop an active collection run.

#### GET /api/v1/collection/active
Get list of currently active collection runs.

### Search

#### POST /api/v1/search/
Search PDFs by content.

**Request Body:**
```json
{
  "query": "knee surgery recovery",
  "procedure_types": ["orthopedic"],
  "min_confidence": 0.5,
  "limit": 20
}
```

**Response:**
```json
{
  "query": "knee surgery recovery",
  "total_results": 8,
  "results": [...],
  "search_time_ms": 125
}
```

#### GET /api/v1/search/cache
Get list of cached search queries.

#### DELETE /api/v1/search/cache
Clear all search cache entries.

### Statistics

#### GET /api/v1/statistics/
Get database statistics.

**Response:**
```json
{
  "total_pdfs": 250,
  "total_collection_runs": 15,
  "total_analysis_results": 750,
  "pdfs_by_procedure": {
    "orthopedic": 80,
    "cardiac": 45,
    "dental": 30
  },
  "pdfs_by_quality": {
    "high": 150,
    "medium": 75,
    "low": 25
  },
  "average_confidence": 0.72,
  "total_storage_mb": 512.5
}
```

#### GET /api/v1/statistics/summary
Get system summary with recent activity.

#### GET /api/v1/statistics/procedure-breakdown
Get detailed breakdown by procedure type.

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message",
  "detail": "Detailed error description",
  "status_code": 400
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Default: 100 requests per minute per IP
- Collection endpoints: 10 requests per minute

## Python Client Example

```python
import requests

class PostOpAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def search_pdfs(self, query, min_confidence=0.5):
        response = self.session.post(
            f"{self.base_url}/api/v1/search/",
            json={
                "query": query,
                "min_confidence": min_confidence
            }
        )
        return response.json()
    
    def start_collection(self, search_queries):
        response = self.session.post(
            f"{self.base_url}/api/v1/collection/start",
            json={"search_queries": search_queries}
        )
        return response.json()["run_id"]

# Usage
client = PostOpAPIClient()
results = client.search_pdfs("knee surgery")
run_id = client.start_collection(["post op care"])
```

## cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# List PDFs
curl "http://localhost:8000/api/v1/pdfs/?procedure_type=orthopedic&limit=10"

# Search PDFs
curl -X POST http://localhost:8000/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "knee surgery", "limit": 5}'

# Start collection
curl -X POST http://localhost:8000/api/v1/collection/start \
  -H "Content-Type: application/json" \
  -d '{"search_queries": ["post operative care"]}'

# Get statistics
curl http://localhost:8000/api/v1/statistics/
```

## WebSocket Support (Future)

Future versions will support WebSocket connections for real-time collection progress updates:
- `ws://localhost:8000/ws/collection/{run_id}`

## Environment Variables

Configure the API using environment variables:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql://user:pass@localhost/postop
ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/postop-api.log

# Collection Settings
MAX_PDFS_PER_SOURCE=20
MIN_CONFIDENCE_SCORE=0.6
MAX_REQUESTS_PER_SECOND=2.0
```

## Docker Deployment

```bash
# Build image
docker build -t postop-api .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db/postop \
  -v ./data:/app/data \
  postop-api
```

## Testing

Run API tests:

```bash
# Unit tests
pytest tests/test_api.py

# Integration tests
python example_api_client.py

# Load testing
locust -f tests/load_test.py --host=http://localhost:8000
```

## Security Considerations

For production deployment:

1. **Authentication**: Implement JWT or OAuth2
2. **HTTPS**: Use TLS certificates
3. **Rate Limiting**: Configure appropriate limits
4. **Input Validation**: Already implemented via Pydantic
5. **CORS**: Configure allowed origins
6. **Database Security**: Use connection pooling and prepared statements
7. **File Upload Limits**: Restrict PDF size and types
8. **API Keys**: Protect external API keys

## Performance

- Database queries are optimized with indexes
- Async operations for I/O-bound tasks
- Connection pooling for database
- Response caching for frequently accessed data
- Pagination for large result sets

## Monitoring

Recommended monitoring setup:
- Prometheus metrics endpoint: `/metrics`
- Health checks for uptime monitoring
- Log aggregation with ELK stack
- APM with DataDog or New Relic

## Support

For issues or questions:
- GitHub Issues: [project-repo]/issues
- Documentation: `/docs`
- API Status: `/health`