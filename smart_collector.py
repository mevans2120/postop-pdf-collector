#!/usr/bin/env python3
"""Smart PDF Collector that systematically collects PDFs for all US surgical procedures."""

import asyncio
import json
import random
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from agent_interface import AgentInterface
from postop_collector.storage.metadata_db import MetadataDB
from postop_collector.config.settings import Settings


class SmartPDFCollector:
    """Intelligent collector that targets specific procedures systematically."""
    
    def __init__(self):
        """Initialize the smart collector."""
        self.agent = AgentInterface()
        self.procedure_db = self.load_procedure_database()
        self.collection_state = self.load_collection_state()
        
    def load_procedure_database(self) -> Dict:
        """Load the procedure database."""
        with open('procedure_database.json', 'r') as f:
            return json.load(f)
    
    def load_collection_state(self) -> Dict:
        """Load or create collection state tracking."""
        state_file = Path('data/collection_state.json')
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        return {
            'procedures_collected': {},
            'last_category': None,
            'collection_rounds': 0
        }
    
    def save_collection_state(self):
        """Save collection state."""
        with open('data/collection_state.json', 'w') as f:
            json.dump(self.collection_state, f, indent=2)
    
    def get_next_procedures_to_collect(self, count: int = 5) -> List[Dict]:
        """Get the next procedures that need PDFs."""
        procedures_needed = []
        
        # First, prioritize common procedures
        for proc in self.procedure_db['priority_procedures']:
            if self.collection_state['procedures_collected'].get(proc, 0) < 3:
                procedures_needed.append({
                    'name': proc,
                    'priority': 'high',
                    'current_count': self.collection_state['procedures_collected'].get(proc, 0)
                })
        
        # Then add procedures with low coverage
        for category, data in self.procedure_db['surgical_procedures'].items():
            for proc in data['procedures']:
                current_count = self.collection_state['procedures_collected'].get(proc, 0)
                if current_count < 2:  # Need at least 2 PDFs per procedure
                    procedures_needed.append({
                        'name': proc,
                        'category': category,
                        'priority': 'normal',
                        'current_count': current_count
                    })
        
        # Sort by current count (ascending) and priority
        procedures_needed.sort(key=lambda x: (x['current_count'], x.get('priority', 'normal')))
        
        return procedures_needed[:count]
    
    def generate_smart_queries(self, procedures: List[Dict]) -> List[str]:
        """Generate intelligent search queries for procedures."""
        queries = []
        hospitals = self.procedure_db['search_strategy']['include_hospital_names']
        modifiers = self.procedure_db['common_search_modifiers']
        
        for proc in procedures:
            proc_name = proc['name']
            
            # Basic query
            queries.append(f'"{proc_name}" post operative care instructions pdf')
            
            # Add hospital-specific query for high priority
            if proc.get('priority') == 'high' and hospitals:
                hospital = random.choice(hospitals)
                queries.append(f'"{proc_name}" {hospital} recovery instructions pdf')
            
            # Add a modifier query
            modifier = random.choice(modifiers[:3])
            queries.append(f'"{proc_name}" {modifier}')
        
        # Limit queries
        max_queries = self.procedure_db['search_strategy']['max_queries_per_run']
        return queries[:max_queries]
    
    async def collect_targeted_pdfs(self, max_pdfs: int = 30) -> Dict:
        """Collect PDFs targeting specific procedures."""
        print("\n" + "="*70)
        print("🎯 SMART PDF COLLECTION")
        print("="*70)
        
        # Get procedures that need PDFs
        target_procedures = self.get_next_procedures_to_collect(5)
        
        if not target_procedures:
            print("✅ All procedures have sufficient PDFs!")
            return {'status': 'complete'}
        
        print("\n📋 Target Procedures:")
        for proc in target_procedures:
            print(f"  • {proc['name']} (current: {proc['current_count']} PDFs)")
        
        # Generate smart queries
        queries = self.generate_smart_queries(target_procedures)
        
        print(f"\n🔍 Search Queries ({len(queries)}):")
        for i, query in enumerate(queries[:5], 1):
            print(f"  {i}. {query[:60]}...")
        
        # Run collection
        print("\n⏳ Starting collection...")
        result = await self.agent.collect_pdfs(
            search_queries=queries,
            max_pdfs=max_pdfs,
            quality_threshold=0.6
        )
        
        # Update collection state
        self.collection_state['collection_rounds'] += 1
        for proc in target_procedures:
            current = self.collection_state['procedures_collected'].get(proc['name'], 0)
            # Estimate PDFs collected per procedure
            estimated_new = result['pdfs_collected'] // len(target_procedures)
            self.collection_state['procedures_collected'][proc['name']] = current + max(1, estimated_new)
        
        self.save_collection_state()
        
        # Show results
        print(f"\n✅ Collection Complete:")
        print(f"  • PDFs collected: {result['pdfs_collected']}")
        print(f"  • Success rate: {result['success_rate']:.1%}")
        print(f"  • Average confidence: {result['average_confidence']:.1%}")
        
        return result
    
    def show_coverage_report(self):
        """Show coverage report for all procedures."""
        print("\n" + "="*70)
        print("📊 PROCEDURE COVERAGE REPORT")
        print("="*70)
        
        total_procedures = sum(
            len(data['procedures']) 
            for data in self.procedure_db['surgical_procedures'].values()
        )
        
        covered_procedures = len(self.collection_state['procedures_collected'])
        
        print(f"\n📈 Overall Statistics:")
        print(f"  • Total procedures in database: {total_procedures}")
        print(f"  • Procedures with PDFs: {covered_procedures}")
        print(f"  • Coverage: {covered_procedures/total_procedures:.1%}")
        print(f"  • Collection rounds: {self.collection_state['collection_rounds']}")
        
        # Show by category
        print(f"\n📋 Coverage by Category:")
        print("-" * 70)
        
        for category, data in self.procedure_db['surgical_procedures'].items():
            procedures = data['procedures']
            covered = sum(1 for p in procedures if p in self.collection_state['procedures_collected'])
            pdfs = sum(self.collection_state['procedures_collected'].get(p, 0) for p in procedures)
            
            coverage = covered / len(procedures) if procedures else 0
            print(f"  {data['category']:<30} {covered:>3}/{len(procedures):<3} procedures ({coverage:>5.1%}) - {pdfs} PDFs")
        
        # Show gaps
        print(f"\n⚠️  Procedures Needing PDFs:")
        gaps = []
        for category, data in self.procedure_db['surgical_procedures'].items():
            for proc in data['procedures']:
                count = self.collection_state['procedures_collected'].get(proc, 0)
                if count == 0:
                    gaps.append(proc)
        
        if gaps:
            for proc in gaps[:10]:  # Show first 10
                print(f"  • {proc}")
            if len(gaps) > 10:
                print(f"  ... and {len(gaps)-10} more")
        else:
            print("  None - all procedures have at least 1 PDF!")
        
        print("="*70)
    
    async def run_systematic_collection(self, rounds: int = 5, pdfs_per_round: int = 20):
        """Run systematic collection over multiple rounds."""
        print(f"\n🚀 Starting Systematic Collection")
        print(f"   Rounds: {rounds}")
        print(f"   PDFs per round: {pdfs_per_round}")
        
        for round_num in range(1, rounds + 1):
            print(f"\n\n{'='*70}")
            print(f"📍 ROUND {round_num} of {rounds}")
            print(f"{'='*70}")
            
            result = await self.collect_targeted_pdfs(pdfs_per_round)
            
            if result.get('status') == 'complete':
                print("\n🎉 All procedures have sufficient coverage!")
                break
            
            # Show progress
            self.show_coverage_report()
            
            if round_num < rounds:
                print(f"\n⏰ Waiting 30 seconds before next round...")
                await asyncio.sleep(30)
        
        print(f"\n\n{'='*70}")
        print("✅ SYSTEMATIC COLLECTION COMPLETE")
        self.show_coverage_report()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart PDF Collector for Surgical Procedures")
    parser.add_argument('--action', choices=['collect', 'coverage', 'systematic'],
                       default='coverage', help='Action to perform')
    parser.add_argument('--rounds', type=int, default=3, help='Number of collection rounds')
    parser.add_argument('--pdfs', type=int, default=20, help='PDFs per round')
    
    args = parser.parse_args()
    
    collector = SmartPDFCollector()
    
    if args.action == 'collect':
        await collector.collect_targeted_pdfs(args.pdfs)
    elif args.action == 'coverage':
        collector.show_coverage_report()
    elif args.action == 'systematic':
        await collector.run_systematic_collection(args.rounds, args.pdfs)


if __name__ == "__main__":
    asyncio.run(main())