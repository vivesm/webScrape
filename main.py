#!/usr/bin/env python3
"""
WebScrape - Main Application Entry Point
=======================================

This is the main entry point for the WebScrape application, a powerful web scraping
tool that can extract content from websites, save it in various formats, and process
it for RAG (Retrieval Augmented Generation) applications.

This script:
1. Parses command-line arguments
2. Sets up logging
3. Initializes and runs the web scraper
4. Optionally processes scraped content for RAG

Usage:
-----
```bash
# Basic usage
python main.py --base_url https://example.com --output_format text

# With RAG processing
python main.py --base_url https://example.com --rag --chunk_size 500

# Test mode with just a single link
python main.py --base_url https://example.com --test
```

See the README.md file for full documentation of all command-line options.

Author: WebScrape Team
License: MIT
"""

import os
import asyncio
import argparse
import logging
from typing import List, Optional

from web_scraper import WebScraper
from rag_processor import RAGProcessor

# Setup logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("scraper.log")  # File output
    ]
)

async def main():
    """
    Parse command line arguments and run the web scraper.
    
    This function is the main entry point of the application. It:
    1. Sets up the argument parser with all available options
    2. Initializes the web scraper with the specified configuration
    3. Runs the scraping process
    4. Optionally processes the scraped content for RAG
    
    The function is async to allow for non-blocking I/O operations,
    which is important for web scraping tasks.
    """
    # Create argument parser with all available options
    parser = argparse.ArgumentParser(
        description="WebScrape - A powerful web scraping tool with RAG processing capabilities",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter  # Show defaults in help
    )
    
    # =====================================================================
    # Base scraping options
    # =====================================================================
    parser.add_argument(
        "--base_url", 
        default="https://docs.workato.com/projects.html", 
        help="Base URL to scrape links from"
    )
    parser.add_argument(
        "--output_format", 
        choices=["pdf", "text"], 
        default="text", 
        help="Output file format (pdf or text)"
    )
    
    # =====================================================================
    # Scraping behavior options
    # =====================================================================
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Test mode (process only a few links)"
    )
    parser.add_argument(
        "--test_count", 
        type=int, 
        default=2, 
        help="Number of links to process in test mode"
    )
    parser.add_argument(
        "--delay", 
        type=float, 
        default=1.0, 
        help="Delay (in seconds) between processing each link"
    )
    parser.add_argument(
        "--concurrency", 
        type=int, 
        default=2, 
        help="Number of concurrent browsers to use (higher values use more memory)"
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=30, 
        help="Navigation timeout in seconds before giving up on a page"
    )
    parser.add_argument(
        "--max_depth", 
        type=int, 
        default=1, 
        help="Maximum link depth to crawl (1 = only links on the start page)"
    )
    
    # =====================================================================
    # Output and filtering options
    # =====================================================================
    parser.add_argument(
        "--output_dir", 
        default="output", 
        help="Directory to save scraped content"
    )
    parser.add_argument(
        "--same_domain_only", 
        action="store_true", 
        help="Only follow links from the same domain as the base URL"
    )
    parser.add_argument(
        "--include", 
        action="append", 
        help="Regex pattern to include URLs (can be used multiple times)"
    )
    parser.add_argument(
        "--exclude", 
        action="append", 
        help="Regex pattern to exclude URLs (can be used multiple times)"
    )
    
    # =====================================================================
    # RAG (Retrieval Augmented Generation) processing options
    # =====================================================================
    parser.add_argument(
        "--rag", 
        action="store_true",
        help="Process scraped content for RAG (Retrieval Augmented Generation)"
    )
    parser.add_argument(
        "--rag_dir", 
        default="rag_data",
        help="Directory to store RAG-processed data"
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=1000,
        help="Size of text chunks for RAG processing (in characters)"
    )
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=200,
        help="Overlap between text chunks for RAG processing (in characters)"
    )
    
    # =====================================================================
    # Performance options
    # =====================================================================
    parser.add_argument(
        "--streaming", 
        action="store_true",
        help="Use streaming processor for better performance (text mode only)"
    )
    parser.add_argument(
        "--stream_buffer",
        type=int,
        default=1024,
        help="Size of streaming buffer in KB (default: 1024)"
    )
    
    # Parse the arguments
    args = parser.parse_args()
    
    try:
        # Log the start of the scraping process with configuration summary
        logging.info(f"Starting web scraping from {args.base_url}")
        logging.info(f"Configuration: max_depth={args.max_depth}, domain_only={args.same_domain_only}, concurrency={args.concurrency}")
        logging.info(f"Saving {args.output_format} files to {args.output_dir}/")
        
        # Print a user-friendly summary of what will happen
        print(f"\n{'='*60}")
        print(f"WebScrape Starting")
        print(f"{'='*60}")
        print(f"URL: {args.base_url}")
        print(f"Max Depth: {args.max_depth} {'(base URL only)' if args.max_depth == 0 else ''}")
        print(f"Same Domain Only: {'Yes' if args.same_domain_only else 'No'}")
        print(f"Output Format: {args.output_format}")
        print(f"Streaming Mode: {'Enabled' if args.streaming else 'Disabled'}")
        if args.rag:
            print(f"RAG Processing: Enabled (chunks of {args.chunk_size} chars with {args.chunk_overlap} overlap)")
        print(f"{'='*60}\n")
        
        # Initialize the web scraper with the specified configuration
        scraper = WebScraper(
            output_dir=args.output_dir,
            max_browsers=args.concurrency,
            nav_timeout_ms=args.timeout * 1000,  # Convert to milliseconds
            same_domain_only=args.same_domain_only,
            exclude_patterns=args.exclude,
            include_patterns=args.include,
            delay=args.delay,
            max_depth=args.max_depth
        )
        
        # Initialize the browser pool (creates browser instances)
        await scraper.initialize()
        
        # Check if streaming mode is enabled
        if args.streaming and args.output_format == "text":
            # Import and use streaming processor
            from streaming_processor import StreamingProcessor
            
            logging.info(f"Using streaming processor for better performance")
            # Convert buffer size from KB to bytes
            buffer_size = args.stream_buffer * 1024
            
            stream_processor = StreamingProcessor(
                output_dir=args.output_dir,
                output_format=args.output_format,
                max_parallel=args.concurrency,
                buffer_size=buffer_size
            )
            
            # Extract links first
            links = []
            if args.test:
                # In test mode, process a limited number of URLs
                logging.info(f"Test mode enabled: processing up to {args.test_count} links")
                # Extract all links first
                all_links = await scraper._extract_all_links_to_depth(
                    base_url=args.base_url,
                    max_depth=args.max_depth
                )
                # Select a subset of links for testing
                links = [args.base_url]  # Always include base URL
                if len(all_links) > 1:
                    # Add additional links up to test_count
                    additional_links = all_links[:min(args.test_count - 1, len(all_links) - 1)]
                    links.extend(additional_links)
                logging.info(f"Selected {len(links)} links for test mode")
            else:
                # Extract links up to the specified depth
                links = await scraper._extract_all_links_to_depth(
                    base_url=args.base_url,
                    max_depth=args.max_depth
                )
            
            # Process links using streaming processor
            output_files = await stream_processor.process_urls(links)
        else:
            # Use regular scraper
            output_files = await scraper.scrape(
                base_url=args.base_url,
                output_format=args.output_format,
                test_mode=args.test,
                test_count=args.test_count
            )
        
        # Output a summary of the scraping process
        logging.info(f"Scraping completed. Saved {len(output_files)} files to {args.output_dir}/")
        
        # Print a user-friendly summary of results
        print(f"\n{'='*60}")
        print(f"WebScrape Complete")
        print(f"{'='*60}")
        print(f"Files saved: {len(output_files)}")
        print(f"Output directory: {args.output_dir}/")
        if len(output_files) > 0:
            print(f"Example files:")
            for file in output_files[:3]:
                print(f"  - {os.path.basename(file)}")
            if len(output_files) > 3:
                print(f"  - ...and {len(output_files) - 3} more")
        print(f"{'='*60}")
        
        # Process for RAG if requested and we have output files
        if args.rag and output_files:
            logging.info(f"Starting RAG processing with chunk size {args.chunk_size} and overlap {args.chunk_overlap}...")
            
            # Initialize the RAG processor
            rag_processor = RAGProcessor(
                input_dir=args.output_dir,
                output_dir=args.rag_dir,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap
            )
            
            # Process the directory containing the scraped files
            stats = await rag_processor.process_directory()
            
            # Output a summary of the RAG processing
            logging.info(f"RAG processing completed: {stats['processed_files']} files processed")
            logging.info(f"Generated {stats['total_chunks']} text chunks for RAG")
            logging.info(f"RAG data saved to {args.rag_dir}/")
            
            # Print user-friendly RAG summary
            print(f"\n{'='*60}")
            print(f"RAG Processing Complete")
            print(f"{'='*60}")
            print(f"Files processed: {stats['processed_files']}")
            print(f"Chunks generated: {stats['total_chunks']}")
            print(f"Chunk size: {args.chunk_size} characters with {args.chunk_overlap} overlap")
            print(f"Output directory: {args.rag_dir}/")
            print(f"{'='*60}")
            
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        logging.info("Process interrupted by user. Shutting down...")
    except Exception as e:
        # Log any unhandled exceptions
        logging.error(f"Error during execution: {e}", exc_info=True)
        return 1
    
    return 0
    
if __name__ == "__main__":
    # Run the main async function with the asyncio event loop
    exit_code = asyncio.run(main())
    exit(exit_code)  # Return the exit code to the shell