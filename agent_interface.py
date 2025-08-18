#!/usr/bin/env python3
"""AI Agent Interface for PostOp PDF Collector

This module provides a simplified interface for AI agents (like Claude) to
autonomously collect and analyze post-operative PDFs.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from postop_collector import PostOpPDFCollector
from postop_collector.config.settings import Settings
from postop_collector.storage.metadata_db import MetadataDB
from postop_collector.core.models import ProcedureType


class AgentInterface:
    """Simplified interface for AI agents to operate the PostOp PDF Collector."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the agent interface.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.setup_logging()
        self.settings = self.create_settings()
        self.db = MetadataDB(
            database_url=self.settings.database_url,
            environment=self.settings.environment
        )
        self.logger = logging.getLogger(__name__)
        self.collection_history = []
    
    def setup_logging(self):
        """Setup logging for agent operations."""
        log_dir = Path("./agent_logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / f"agent_{datetime.now():%Y%m%d_%H%M%S}.log"),
                logging.StreamHandler()
            ]
        )
    
    def create_settings(self) -> Settings:
        """Create settings from configuration."""
        return Settings(
            output_directory=self.config.get("output_directory", "./agent_output"),
            max_pdfs_per_source=self.config.get("max_pdfs_per_source", 10),
            min_confidence_score=self.config.get("min_confidence_score", 0.6),
            database_url=self.config.get("database_url", "sqlite:///./data/agent_collector.db"),
            environment=self.config.get("environment", "production"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            google_search_engine_id=os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
        )
    
    async def collect_pdfs(
        self,
        search_queries: Optional[List[str]] = None,
        procedure_types: Optional[List[str]] = None,
        max_pdfs: int = 50,
        quality_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """Collect PDFs based on search criteria.
        
        Args:
            search_queries: List of search queries
            procedure_types: List of procedure types to focus on
            max_pdfs: Maximum number of PDFs to collect
            quality_threshold: Minimum quality score
            
        Returns:
            Collection results with statistics
        """
        # Generate search queries if not provided
        if not search_queries:
            search_queries = self.generate_search_queries(procedure_types)
        
        self.logger.info(f"Starting collection with queries: {search_queries}")
        
        # Create collector with custom settings
        settings = Settings(
            **self.settings.model_dump(),
            max_pdfs_per_source=min(max_pdfs // len(search_queries), 10),
            min_confidence_score=quality_threshold
        )
        
        async with PostOpPDFCollector(settings, use_database=True) as collector:
            result = await collector.run_collection(
                search_queries=search_queries,
                direct_urls=None
            )
            
            # Store collection history
            collection_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "queries": search_queries,
                "pdfs_collected": result.total_pdfs_collected,
                "urls_discovered": result.total_urls_discovered,
                "success_rate": result.success_rate,
                "average_confidence": result.average_confidence
            }
            self.collection_history.append(collection_record)
            
            self.logger.info(f"Collection completed: {result.total_pdfs_collected} PDFs collected")
            
            return {
                "status": "success",
                "pdfs_collected": result.total_pdfs_collected,
                "urls_discovered": result.total_urls_discovered,
                "success_rate": result.success_rate,
                "average_confidence": result.average_confidence,
                "by_procedure": result.by_procedure_type,
                "by_source": result.by_source_domain
            }
    
    def generate_search_queries(self, procedure_types: Optional[List[str]] = None) -> List[str]:
        """Generate search queries based on procedure types.
        
        Args:
            procedure_types: List of procedure types
            
        Returns:
            List of search queries
        """
        base_queries = [
            "post operative care instructions pdf",
            "surgery recovery guidelines pdf",
            "patient discharge instructions pdf",
            "post surgery care guide pdf",
            "surgical aftercare instructions pdf"
        ]
        
        if not procedure_types:
            return base_queries
        
        specific_queries = []
        for proc_type in procedure_types:
            specific_queries.extend([
                f"{proc_type} surgery post operative care pdf",
                f"{proc_type} procedure recovery instructions pdf",
                f"{proc_type} surgery aftercare guidelines pdf"
            ])
        
        return specific_queries[:10]  # Limit to 10 queries
    
    def analyze_collection(self) -> Dict[str, Any]:
        """Analyze the current collection of PDFs.
        
        Returns:
            Analysis results with insights
        """
        stats = self.db.get_statistics()
        
        # Get recent high-quality PDFs
        high_quality_pdfs = []
        for proc_type in ProcedureType:
            pdfs = self.db.get_pdfs_by_procedure_type(
                proc_type,
                min_confidence=0.8,
                limit=5
            )
            high_quality_pdfs.extend([{
                "filename": pdf.filename,
                "procedure_type": pdf.procedure_type.value,
                "confidence": pdf.confidence_score,
                "source": pdf.source_domain
            } for pdf in pdfs])
        
        # Identify gaps in collection
        gaps = []
        for proc_type in ProcedureType:
            count = stats["pdfs_by_procedure"].get(proc_type.value, 0)
            if count < 5:
                gaps.append({
                    "procedure_type": proc_type.value,
                    "current_count": count,
                    "recommended": 10
                })
        
        return {
            "total_pdfs": stats["total_pdfs"],
            "average_confidence": stats["average_confidence"],
            "storage_mb": stats["total_storage_bytes"] / (1024 * 1024),
            "pdfs_by_procedure": stats["pdfs_by_procedure"],
            "high_quality_pdfs": high_quality_pdfs[:10],
            "collection_gaps": gaps,
            "recommendations": self.generate_recommendations(stats, gaps)
        }
    
    def generate_recommendations(self, stats: Dict, gaps: List[Dict]) -> List[str]:
        """Generate recommendations for improving the collection.
        
        Args:
            stats: Current statistics
            gaps: Identified gaps in collection
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check for gaps
        if gaps:
            gap_types = [g["procedure_type"] for g in gaps]
            recommendations.append(
                f"Collect more PDFs for: {', '.join(gap_types[:3])}"
            )
        
        # Check quality
        if stats["average_confidence"] < 0.7:
            recommendations.append(
                "Focus on higher quality sources to improve average confidence"
            )
        
        # Check diversity
        if len(stats["pdfs_by_procedure"]) < 5:
            recommendations.append(
                "Diversify collection to cover more procedure types"
            )
        
        # Check recency
        recommendations.append(
            "Schedule regular collections to keep content up-to-date"
        )
        
        return recommendations
    
    def search_pdfs(
        self,
        query: str,
        procedure_type: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for specific PDFs in the collection.
        
        Args:
            query: Search query
            procedure_type: Optional procedure type filter
            min_confidence: Minimum confidence score
            
        Returns:
            List of matching PDFs
        """
        procedure_types = [ProcedureType(procedure_type)] if procedure_type else None
        
        results = self.db.search_pdfs(
            query=query,
            procedure_types=procedure_types,
            min_confidence=min_confidence,
            limit=20
        )
        
        return [{
            "filename": pdf.filename,
            "url": pdf.url,
            "procedure_type": pdf.procedure_type.value,
            "confidence": pdf.confidence_score,
            "source": pdf.source_domain,
            "timeline_elements": pdf.timeline_elements[:5],
            "medications": pdf.medication_instructions[:5],
            "warning_signs": pdf.warning_signs[:5]
        } for pdf in results]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent and collector.
        
        Returns:
            Status information
        """
        stats = self.db.get_statistics()
        
        # Get last collection info
        last_collection = None
        if self.collection_history:
            last_collection = self.collection_history[-1]
        
        return {
            "agent_status": "operational",
            "database_connected": True,
            "total_pdfs": stats["total_pdfs"],
            "total_collections": len(self.collection_history),
            "last_collection": last_collection,
            "storage_used_mb": stats["total_storage_bytes"] / (1024 * 1024),
            "average_confidence": stats["average_confidence"],
            "procedure_coverage": len(stats["pdfs_by_procedure"])
        }
    
    def schedule_collection(
        self,
        interval_hours: int = 24,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """Schedule periodic collections.
        
        Args:
            interval_hours: Hours between collections
            max_iterations: Maximum number of collections
            
        Returns:
            Schedule information
        """
        schedule = {
            "interval_hours": interval_hours,
            "max_iterations": max_iterations,
            "start_time": datetime.utcnow().isoformat(),
            "scheduled_runs": []
        }
        
        for i in range(max_iterations):
            run_time = datetime.utcnow() + timedelta(hours=interval_hours * i)
            schedule["scheduled_runs"].append({
                "iteration": i + 1,
                "scheduled_time": run_time.isoformat(),
                "search_focus": self.get_search_focus(i)
            })
        
        return schedule
    
    def get_search_focus(self, iteration: int) -> str:
        """Determine search focus for a given iteration.
        
        Args:
            iteration: Iteration number
            
        Returns:
            Search focus description
        """
        focuses = [
            "General post-operative care",
            "Orthopedic procedures",
            "Cardiac procedures",
            "Neurological procedures",
            "Gastrointestinal procedures",
            "Urological procedures",
            "Recent updates and guidelines",
            "Pediatric post-operative care",
            "Elderly patient care",
            "Complication management"
        ]
        return focuses[iteration % len(focuses)]
    
    async def run_autonomous_collection(
        self,
        duration_hours: int = 24,
        interval_minutes: int = 60
    ) -> Dict[str, Any]:
        """Run autonomous collection for a specified duration.
        
        Args:
            duration_hours: Total duration to run
            interval_minutes: Minutes between collection attempts
            
        Returns:
            Summary of all collections
        """
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=duration_hours)
        collections_performed = []
        
        self.logger.info(f"Starting autonomous collection for {duration_hours} hours")
        
        while datetime.utcnow() < end_time:
            # Analyze current state
            analysis = self.analyze_collection()
            
            # Determine what to collect based on gaps
            if analysis["collection_gaps"]:
                gap_types = [g["procedure_type"] for g in analysis["collection_gaps"][:3]]
                search_queries = self.generate_search_queries(gap_types)
            else:
                search_queries = self.generate_search_queries()
            
            # Perform collection
            try:
                result = await self.collect_pdfs(
                    search_queries=search_queries[:5],
                    max_pdfs=20,
                    quality_threshold=0.7
                )
                collections_performed.append(result)
                
                self.logger.info(f"Collection {len(collections_performed)} completed: {result['pdfs_collected']} PDFs")
                
            except Exception as e:
                self.logger.error(f"Collection failed: {e}")
            
            # Wait for next interval
            await asyncio.sleep(interval_minutes * 60)
        
        # Generate summary
        total_pdfs = sum(c.get("pdfs_collected", 0) for c in collections_performed)
        avg_success_rate = sum(c.get("success_rate", 0) for c in collections_performed) / len(collections_performed) if collections_performed else 0
        
        return {
            "duration_hours": duration_hours,
            "collections_performed": len(collections_performed),
            "total_pdfs_collected": total_pdfs,
            "average_success_rate": avg_success_rate,
            "collections": collections_performed,
            "final_statistics": self.db.get_statistics()
        }


# CLI interface for agents
async def main():
    """Main entry point for agent operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Agent Interface for PostOp PDF Collector")
    parser.add_argument("--action", choices=["collect", "analyze", "search", "status", "autonomous"],
                       default="status", help="Action to perform")
    parser.add_argument("--queries", nargs="+", help="Search queries for collection")
    parser.add_argument("--procedure-types", nargs="+", help="Procedure types to focus on")
    parser.add_argument("--max-pdfs", type=int, default=50, help="Maximum PDFs to collect")
    parser.add_argument("--duration", type=int, default=24, help="Duration for autonomous mode (hours)")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config and Path(args.config).exists():
        with open(args.config) as f:
            config = json.load(f)
    
    # Initialize agent
    agent = AgentInterface(config)
    
    # Execute action
    if args.action == "collect":
        result = await agent.collect_pdfs(
            search_queries=args.queries,
            procedure_types=args.procedure_types,
            max_pdfs=args.max_pdfs
        )
        print(json.dumps(result, indent=2))
    
    elif args.action == "analyze":
        result = agent.analyze_collection()
        print(json.dumps(result, indent=2))
    
    elif args.action == "search":
        if args.queries:
            results = agent.search_pdfs(args.queries[0])
            print(json.dumps(results, indent=2))
        else:
            print("Please provide a search query with --queries")
    
    elif args.action == "status":
        status = agent.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.action == "autonomous":
        result = await agent.run_autonomous_collection(
            duration_hours=args.duration,
            interval_minutes=30
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())