"""Main PostOp PDF Collector implementation."""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

from ..analysis.content_analyzer import ContentAnalyzer
from ..analysis.pdf_extractor import PDFTextExtractor
from ..analysis.procedure_categorizer import ProcedureCategorizer
from ..analysis.timeline_parser import TimelineParser
from ..config.settings import Settings
from ..storage.metadata_db import MetadataDB
from ..utils.rate_limiter import RateLimiter
from .models import CollectionResult, ContentQuality, PDFMetadata

logger = logging.getLogger(__name__)


class PostOpPDFCollector:
    """Collects and analyzes post-operative instruction PDFs from various sources."""

    def __init__(self, settings: Optional[Settings] = None, use_database: bool = True):
        """Initialize the collector with configuration settings.
        
        Args:
            settings: Configuration settings
            use_database: Whether to use database for persistence (default: True)
        """
        self.settings = settings or Settings()
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(
            max_requests=self.settings.max_requests_per_second
        )
        self.collected_urls: Set[str] = set()
        self.output_dir = Path(self.settings.output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.output_dir / "metadata.json"
        self._load_existing_metadata()
        
        # Initialize database if enabled
        self.use_database = use_database
        self.db: Optional[MetadataDB] = None
        self.collection_run_id: Optional[str] = None
        if self.use_database:
            db_url = self.settings.database_url if hasattr(self.settings, 'database_url') else None
            self.db = MetadataDB(database_url=db_url, environment=self.settings.environment)
        
        # Initialize analysis modules
        self.pdf_extractor = PDFTextExtractor(enable_ocr=self.settings.enable_ocr)
        self.content_analyzer = ContentAnalyzer()
        self.timeline_parser = TimelineParser()
        self.procedure_categorizer = ProcedureCategorizer()

    def _load_existing_metadata(self) -> None:
        """Load existing metadata to avoid duplicate downloads."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    self.collected_urls = set(data.get("collected_urls", []))
                    logger.info(f"Loaded {len(self.collected_urls)} existing URLs")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
                self.collected_urls = set()

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = ClientTimeout(total=self.settings.request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        # Close database connection if enabled
        if self.use_database and self.db:
            self.db.close()

    async def search_google(self, query: str, num_results: int = 10) -> List[str]:
        """
        Search Google for relevant URLs using Custom Search API.
        
        Args:
            query: Search query string
            num_results: Number of results to return
            
        Returns:
            List of URLs from search results
        """
        if not self.settings.google_api_key or not self.settings.google_search_engine_id:
            logger.warning("Google API credentials not configured")
            return []

        urls = []
        params = {
            "key": self.settings.google_api_key,
            "cx": self.settings.google_search_engine_id,
            "q": query,
            "num": min(num_results, 10),  # API limit
        }

        try:
            async with self.session.get(
                "https://www.googleapis.com/customsearch/v1", params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data.get("items", []):
                        urls.append(item["link"])
                else:
                    logger.error(f"Google search failed: {response.status}")
        except Exception as e:
            logger.error(f"Error during Google search: {e}")

        return urls

    async def discover_pdfs_from_website(self, base_url: str) -> List[str]:
        """
        Crawl a website to discover PDF links.
        
        Args:
            base_url: Base URL of the website to crawl
            
        Returns:
            List of discovered PDF URLs
        """
        pdf_urls = []
        visited = set()
        to_visit = [base_url]
        domain = urlparse(base_url).netloc

        while to_visit and len(visited) < self.settings.max_pages_per_site:
            url = to_visit.pop(0)
            if url in visited:
                continue

            visited.add(url)
            await self.rate_limiter.acquire()

            try:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        continue

                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        continue

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find PDF links
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        full_url = urljoin(url, href)
                        
                        if full_url.lower().endswith(".pdf"):
                            pdf_urls.append(full_url)
                        elif urlparse(full_url).netloc == domain and full_url not in visited:
                            to_visit.append(full_url)

            except Exception as e:
                logger.debug(f"Error crawling {url}: {e}")

        return pdf_urls

    async def download_pdf(self, url: str) -> Optional[bytes]:
        """
        Download PDF content from URL.
        
        Args:
            url: URL of the PDF to download
            
        Returns:
            PDF content as bytes or None if download failed
        """
        if url in self.collected_urls:
            logger.debug(f"Skipping already collected URL: {url}")
            return None

        await self.rate_limiter.acquire()

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    # Verify it's actually a PDF
                    if content.startswith(b"%PDF"):
                        return content
                    else:
                        logger.warning(f"URL {url} does not contain PDF content")
                else:
                    logger.warning(f"Failed to download {url}: {response.status}")
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")

        return None

    async def analyze_pdf(self, pdf_content: bytes, url: str) -> Optional[PDFMetadata]:
        """
        Analyze PDF content and extract metadata.
        
        Args:
            pdf_content: PDF content as bytes
            url: Source URL of the PDF
            
        Returns:
            PDFMetadata object with extracted information or None if analysis fails
        """
        # Calculate file hash
        file_hash = hashlib.sha256(pdf_content).hexdigest()
        
        # Generate filename
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name or f"{file_hash[:8]}.pdf"
        
        # Save PDF to disk
        file_path = self.output_dir / "pdfs" / filename
        file_path.parent.mkdir(exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(pdf_content)
        
        try:
            # Extract text from PDF
            extraction_result = self.pdf_extractor.extract_text_from_bytes(pdf_content)
            text_content = extraction_result.get("text_content", "")
            
            # Clean the extracted text
            cleaned_text = self.pdf_extractor.clean_text(text_content)
            
            # Analyze content for post-operative relevance
            content_analysis = self.content_analyzer.analyze(cleaned_text)
            
            # Skip if not post-operative content and quality threshold not met
            if not content_analysis["is_post_operative"]:
                confidence = content_analysis["relevance_score"]
                if confidence < self.settings.min_confidence_score:
                    logger.info(f"Skipping {url}: Low relevance score ({confidence:.2f})")
                    return None
            
            # Parse timeline information
            timeline_events = self.timeline_parser.parse_timeline(cleaned_text)
            timeline_summary = self.timeline_parser.generate_timeline_summary(timeline_events)
            
            # Categorize procedure type
            procedure_type, proc_confidence = self.procedure_categorizer.categorize(cleaned_text)
            procedure_details = self.procedure_categorizer.extract_procedure_details(cleaned_text)
            
            # Determine content quality
            quality_map = {
                "high": ContentQuality.HIGH,
                "medium": ContentQuality.MEDIUM,
                "low": ContentQuality.LOW,
            }
            content_quality = quality_map.get(
                content_analysis.get("content_quality", "low"),
                ContentQuality.UNASSESSED
            )
            
            # Calculate overall confidence score
            confidence_score = self.content_analyzer.calculate_confidence_score(content_analysis)
            
            # Create metadata with analysis results
            metadata = PDFMetadata(
                url=url,
                filename=filename,
                file_path=str(file_path),
                file_hash=file_hash,
                file_size=len(pdf_content),
                source_domain=parsed_url.netloc,
                download_timestamp=datetime.utcnow(),
                # Content from analysis
                text_content=cleaned_text[:5000],  # Limit stored text
                confidence_score=confidence_score,
                procedure_type=procedure_type,
                content_quality=content_quality,
                # Extracted information
                timeline_elements=[event.description for event in timeline_events[:10]],
                medication_instructions=content_analysis.get("medication_instructions", [])[:10],
                warning_signs=content_analysis.get("warning_signs", [])[:10],
                follow_up_instructions=[],  # Can be extracted if needed
                # Additional metadata
                language="en",  # Can be detected if needed
                page_count=extraction_result.get("page_count", 0),
                has_images=extraction_result.get("has_images", False),
                has_tables=extraction_result.get("has_tables", False),
            )
            
            logger.info(
                f"Analyzed {url}: {procedure_type.value} "
                f"(confidence: {confidence_score:.2f}, quality: {content_quality.value})"
            )
            
            # Save to database if enabled
            if self.use_database and self.db:
                try:
                    pdf_id = self.db.save_pdf_metadata(metadata)
                    # Save detailed analysis results
                    if timeline_events:
                        self.db.save_analysis_result(
                            pdf_id=pdf_id,
                            analysis_type="timeline",
                            results={"events": [e.__dict__ for e in timeline_events]},
                            confidence=confidence_score,
                        )
                    if procedure_details:
                        self.db.save_analysis_result(
                            pdf_id=pdf_id,
                            analysis_type="procedure",
                            results=procedure_details,
                            confidence=proc_confidence,
                        )
                except Exception as e:
                    logger.error(f"Failed to save to database: {e}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error analyzing PDF from {url}: {e}")
            # Return basic metadata even if analysis fails
            return PDFMetadata(
                url=url,
                filename=filename,
                file_path=str(file_path),
                file_hash=file_hash,
                file_size=len(pdf_content),
                source_domain=parsed_url.netloc,
                download_timestamp=datetime.utcnow(),
                text_content="",
                confidence_score=0.0,
            )

    async def collect_from_search_queries(
        self, queries: List[str]
    ) -> CollectionResult:
        """
        Collect PDFs based on search queries.
        
        Args:
            queries: List of search queries
            
        Returns:
            CollectionResult with collected PDFs and statistics
        """
        all_metadata = []
        total_urls_found = 0
        
        for query in queries:
            logger.info(f"Searching for: {query}")
            
            # Get search results
            search_urls = await self.search_google(query)
            total_urls_found += len(search_urls)
            
            # Process each search result
            for url in search_urls:
                # Check if URL is a PDF
                if url.lower().endswith(".pdf"):
                    content = await self.download_pdf(url)
                    if content:
                        metadata = await self.analyze_pdf(content, url)
                        if metadata:
                            all_metadata.append(metadata)
                            self.collected_urls.add(url)
                else:
                    # Crawl website for PDFs
                    pdf_urls = await self.discover_pdfs_from_website(url)
                    for pdf_url in pdf_urls[:self.settings.max_pdfs_per_source]:
                        content = await self.download_pdf(pdf_url)
                        if content:
                            metadata = await self.analyze_pdf(content, pdf_url)
                            if metadata:
                                all_metadata.append(metadata)
                                self.collected_urls.add(pdf_url)

        # Save metadata
        self._save_metadata(all_metadata)

        return CollectionResult(
            total_pdfs_collected=len(all_metadata),
            total_urls_discovered=total_urls_found,
            metadata_list=all_metadata,
            collection_timestamp=datetime.utcnow(),
        )

    async def collect_from_urls(self, urls: List[str]) -> CollectionResult:
        """
        Collect PDFs from specific URLs.
        
        Args:
            urls: List of URLs to collect from
            
        Returns:
            CollectionResult with collected PDFs and statistics
        """
        all_metadata = []
        
        for url in urls:
            if url.lower().endswith(".pdf"):
                # Direct PDF download
                content = await self.download_pdf(url)
                if content:
                    metadata = await self.analyze_pdf(content, url)
                    all_metadata.append(metadata)
                    self.collected_urls.add(url)
            else:
                # Crawl website for PDFs
                pdf_urls = await self.discover_pdfs_from_website(url)
                for pdf_url in pdf_urls[:self.settings.max_pdfs_per_source]:
                    content = await self.download_pdf(pdf_url)
                    if content:
                        metadata = await self.analyze_pdf(content, pdf_url)
                        all_metadata.append(metadata)
                        self.collected_urls.add(pdf_url)

        # Save metadata
        self._save_metadata(all_metadata)

        return CollectionResult(
            total_pdfs_collected=len(all_metadata),
            total_urls_discovered=len(urls),
            metadata_list=all_metadata,
            collection_timestamp=datetime.utcnow(),
        )

    def _save_metadata(self, metadata_list: List[PDFMetadata]) -> None:
        """Save metadata to JSON file."""
        existing_data = {}
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    existing_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading existing metadata: {e}")

        # Update metadata
        existing_data["collected_urls"] = list(self.collected_urls)
        existing_data["last_updated"] = datetime.utcnow().isoformat()
        existing_data["total_pdfs"] = len(self.collected_urls)
        
        # Add new metadata
        if "pdfs" not in existing_data:
            existing_data["pdfs"] = []
        
        for metadata in metadata_list:
            existing_data["pdfs"].append(metadata.dict())

        # Save to file
        with open(self.metadata_file, "w") as f:
            json.dump(existing_data, f, indent=2, default=str)

    async def run_collection(
        self,
        search_queries: Optional[List[str]] = None,
        direct_urls: Optional[List[str]] = None,
    ) -> CollectionResult:
        """
        Run the collection process.
        
        Args:
            search_queries: List of search queries to use
            direct_urls: List of direct URLs to collect from
            
        Returns:
            Combined CollectionResult from all sources
        """
        all_metadata = []
        total_urls = 0
        
        # Start collection run in database if enabled
        if self.use_database and self.db:
            self.collection_run_id = self.db.create_collection_run(
                search_queries=search_queries,
                direct_urls=direct_urls,
                config={
                    "max_pdfs_per_source": self.settings.max_pdfs_per_source,
                    "quality_threshold": self.settings.min_confidence_score,
                }
            )

        if search_queries:
            result = await self.collect_from_search_queries(search_queries)
            all_metadata.extend(result.metadata_list)
            total_urls += result.total_urls_discovered

        if direct_urls:
            result = await self.collect_from_urls(direct_urls)
            all_metadata.extend(result.metadata_list)
            total_urls += result.total_urls_discovered

        final_result = CollectionResult(
            total_pdfs_collected=len(all_metadata),
            total_urls_discovered=total_urls,
            metadata_list=all_metadata,
            collection_timestamp=datetime.utcnow(),
        )
        
        # Save collection result to database if enabled
        if self.use_database and self.db and self.collection_run_id:
            try:
                self.db.save_collection_result(self.collection_run_id, final_result)
            except Exception as e:
                logger.error(f"Failed to save collection result to database: {e}")
        
        return final_result