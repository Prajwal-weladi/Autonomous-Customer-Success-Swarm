"""
Command-line interface for Policy Scraper and RAG Integration

Usage:
    python -m app.agents.policy.app.rag.policy_cli [command] [options]

Commands:
    scrape              Scrape policies from URLs
    scrape-force        Force rescrape (ignore existing)
    load                Load previously saved policies
    process             Process policies into chunks
    validate            Validate chunks
    stats               Show statistics
    export              Export chunks for RAG service
    init-rag            Full pipeline (scrape + process + validate)
    help                Show this help message
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from app.agents.policy.app.rag.policy_scraper import (
    PolicyScraper,
    PolicyProcessor,
)
from app.agents.policy.app.rag.rag_integration import (
    RAGPolicyIntegration,
    initialize_rag_with_policies
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def print_header(text: str):
    """Print a formatted header."""
    width = 80
    print("\n" + "=" * width)
    print(text.center(width))
    print("=" * width)


def print_section(text: str):
    """Print a formatted section."""
    print(f"\n📌 {text}")
    print("-" * 60)


def cmd_scrape(args):
    """Scrape policies from URLs."""
    print_header("SCRAPING POLICIES FROM URLs")
    
    scraper = PolicyScraper()
    policies = scraper.scrape_all_policies()
    
    print_section("RESULTS")
    print(f"✅ Successfully scraped {len(policies)} policies")
    
    for policy_key, policy_doc in policies.items():
        print(f"\n📄 {policy_key.upper()}")
        print(f"   Domain: {policy_doc.policy_domain}")
        print(f"   Title: {policy_doc.title}")
        print(f"   Content length: {len(policy_doc.cleaned_content)} characters")
    
    print_section("SAVED LOCATIONS")
    print(f"Raw HTML: {scraper.raw_dir}")
    print(f"Cleaned Text: {scraper.cleaned_dir}")


def cmd_scrape_force(args):
    """Force rescrape all policies."""
    print_header("FORCE RESCRAPING ALL POLICIES")
    
    scraper = PolicyScraper()
    
    print_section("SCRAPING")
    policies = scraper.scrape_all_policies()
    
    print_section("RESULTS")
    print(f"✅ Successfully scraped {len(policies)} policies")


def cmd_load(args):
    """Load previously saved policies."""
    print_header("LOADING SAVED POLICIES")
    
    scraper = PolicyScraper()
    policies = scraper.load_all_policies()
    
    if not policies:
        print("❌ No saved policies found")
        return
    
    print_section("LOADED POLICIES")
    for policy_id, policy_doc in policies.items():
        print(f"\n📄 {policy_id}")
        print(f"   Domain: {policy_doc.policy_domain}")
        print(f"   Title: {policy_doc.title}")
        print(f"   Content length: {len(policy_doc.cleaned_content)} characters")
        print(f"   Source: {policy_doc.source_url}")


def cmd_process(args):
    """Process policies into chunks."""
    print_header("PROCESSING POLICIES INTO CHUNKS")
    
    scraper = PolicyScraper()
    processor = PolicyProcessor()
    
    print_section("LOADING POLICIES")
    policies = scraper.load_all_policies()
    
    if not policies:
        print("❌ No policies found to process")
        return
    
    print(f"✅ Loaded {len(policies)} policies")
    
    print_section("PROCESSING")
    chunks_dict = processor.process_policies(policies)
    
    total_chunks = sum(len(c) for c in chunks_dict.values())
    
    print_section("RESULTS")
    print(f"✅ Created {total_chunks} chunks")
    
    for policy_key, chunks in chunks_dict.items():
        print(f"\n  {policy_key}: {len(chunks)} chunks")
    
    print_section("SAVING")
    chunks_file = processor.save_chunks_to_json(chunks_dict, Path("app/agents/policy/data/chunks/chunks.json"))
    print(f"✅ Chunks saved to JSON")


def cmd_validate(args):
    """Validate chunks for RAG."""
    print_header("VALIDATING CHUNKS")
    
    integration = RAGPolicyIntegration()
    
    print_section("VALIDATION IN PROGRESS")
    result = integration.validate_chunks()
    
    print_section("RESULTS")
    if result["valid"]:
        print(f"✅ All {result['total_chunks']} chunks are valid")
    else:
        print(f"❌ Validation failed with {len(result['errors'])} errors")
        for error in result['errors'][:10]:  # Show first 10 errors
            print(f"   - {error}")
        if len(result['errors']) > 10:
            print(f"   ... and {len(result['errors']) - 10} more errors")
    
    if result['warnings']:
        print(f"\n⚠️ Warnings:")
        for warning in result['warnings']:
            print(f"   - {warning}")


def cmd_stats(args):
    """Show statistics."""
    print_header("POLICY STATISTICS")
    
    integration = RAGPolicyIntegration()
    stats = integration.get_policy_stats()
    
    print_section("OVERVIEW")
    print(f"Total Policies: {stats['total_policies']}")
    print(f"Total Chunks: {stats['total_chunks']}")
    
    print_section("CHUNKS BY DOMAIN")
    for domain, count in stats['chunks_by_domain'].items():
        print(f"  {domain}: {count} chunks")
    
    print_section("POLICIES BY DOMAIN")
    for domain, count in stats['policies_by_domain'].items():
        print(f"  {domain}: {count} policies")


def cmd_export(args):
    """Export chunks for RAG service."""
    print_header("EXPORTING CHUNKS FOR RAG")
    
    output_format = args.format if hasattr(args, 'format') else 'json'
    
    integration = RAGPolicyIntegration()
    
    print_section("EXPORTING")
    export_file = integration.export_chunks_for_rag(output_format=output_format)
    
    if export_file:
        print_section("RESULTS")
        print(f"✅ Exported to: {export_file}")
        
        # Show file size
        file_size = Path(export_file).stat().st_size
        print(f"File size: {file_size / 1024:.2f} KB")
    else:
        print("❌ Export failed")


def cmd_init_rag(args):
    """Initialize RAG with complete pipeline."""
    print_header("INITIALIZING RAG WITH POLICIES")
    
    force = args.force if hasattr(args, 'force') else False
    
    print_section("RUNNING PIPELINE")
    result = initialize_rag_with_policies(force_rescrape=force)
    
    print_section("RESULTS")
    if result["status"] == "success":
        print("✅ RAG initialization successful!")
        
        pipeline = result.get("pipeline", {})
        print(f"\n📊 Pipeline Results:")
        print(f"   Policies scraped: {pipeline.get('policies_scraped', 0)}")
        print(f"   Chunks created: {pipeline.get('chunks_created', 0)}")
        
        stats = result.get("statistics", {})
        print(f"\n📊 Statistics:")
        print(f"   Total policies: {stats.get('total_policies', 0)}")
        print(f"   Total chunks: {stats.get('total_chunks', 0)}")
        
        validation = result.get("validation", {})
        if validation.get('valid'):
            print(f"\n✅ Validation: All chunks are valid")
        else:
            print(f"\n⚠️ Validation: Found {len(validation.get('errors', []))} errors")
        
        print(f"\n💾 Chunks file: {result.get('chunks_file')}")
    else:
        print(f"❌ RAG initialization failed:")
        for error in result.get("errors", []):
            print(f"   - {error}")


def cmd_help(args):
    """Show help message."""
    print(__doc__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Policy Scraper and RAG Integration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python -m app.agents.policy.app.rag.policy_cli init-rag\n"
               "  python -m app.agents.policy.app.rag.policy_cli scrape\n"
               "  python -m app.agents.policy.app.rag.policy_cli validate\n"
               "  python -m app.agents.policy.app.rag.policy_cli stats\n"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # scrape command
    subparsers.add_parser(
        'scrape',
        help='Scrape policies from URLs'
    )
    
    # scrape-force command
    scrape_force_parser = subparsers.add_parser(
        'scrape-force',
        help='Force rescrape all policies'
    )
    scrape_force_parser.add_argument(
        '--force',
        action='store_true',
        help='Force rescrape'
    )
    
    # load command
    subparsers.add_parser(
        'load',
        help='Load previously saved policies'
    )
    
    # process command
    subparsers.add_parser(
        'process',
        help='Process policies into chunks'
    )
    
    # validate command
    subparsers.add_parser(
        'validate',
        help='Validate chunks for RAG'
    )
    
    # stats command
    subparsers.add_parser(
        'stats',
        help='Show statistics'
    )
    
    # export command
    export_parser = subparsers.add_parser(
        'export',
        help='Export chunks for RAG service'
    )
    export_parser.add_argument(
        '--format',
        choices=['json', 'jsonl'],
        default='json',
        help='Export format (default: json)'
    )
    
    # init-rag command
    init_parser = subparsers.add_parser(
        'init-rag',
        help='Initialize RAG (complete pipeline)'
    )
    init_parser.add_argument(
        '--force',
        action='store_true',
        help='Force rescrape all policies'
    )
    
    # help command
    subparsers.add_parser(
        'help',
        help='Show help message'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Command mapping
    commands = {
        'scrape': cmd_scrape,
        'scrape-force': cmd_scrape_force,
        'load': cmd_load,
        'process': cmd_process,
        'validate': cmd_validate,
        'stats': cmd_stats,
        'export': cmd_export,
        'init-rag': cmd_init_rag,
        'help': cmd_help,
    }
    
    # Execute command
    if not args.command or args.command not in commands:
        cmd_help(args)
        return
    
    try:
        commands[args.command](args)
    except Exception as e:
        logger.error(f"Error executing command '{args.command}': {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
