#!/usr/bin/env python3
"""
Test Script for WebScrape
========================

This script performs a basic test of the web scraping functionality
by scraping a public website and verifying that the content is saved correctly.
It tests both text and PDF output formats, as well as RAG processing.

Usage:
    python test_scraper.py

This script will create temporary directories for testing and clean them up
when finished unless the --keep flag is specified.
"""

import os
import sys
import asyncio
import argparse
import tempfile
import shutil
import logging
from pathlib import Path

# Import the scraper components
from web_scraper import WebScraper
from rag_processor import RAGProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Use a public website that's stable and allows scraping
TEST_URL = "https://httpbin.org/"

async def test_text_scraping(output_dir):
    """Test scraping content in text format."""
    logging.info("Testing text scraping...")
    
    # Create scraper
    scraper = WebScraper(
        output_dir=output_dir,
        max_browsers=1,
        nav_timeout_ms=30000,
        same_domain_only=True
    )
    
    # Initialize and run scraper
    await scraper.initialize()
    output_files = await scraper.scrape(
        base_url=TEST_URL,
        output_format="text",
        test_mode=True  # Only process one link for test
    )
    
    # Verify results
    if not output_files:
        logging.error("❌ Text scraping failed: No files were saved")
        return False
        
    logging.info(f"✅ Text scraping successful: {len(output_files)} files saved")
    return True

async def test_pdf_scraping(output_dir):
    """Test scraping content in PDF format."""
    logging.info("Testing PDF scraping...")
    
    # Create scraper
    scraper = WebScraper(
        output_dir=output_dir,
        max_browsers=1,
        nav_timeout_ms=30000,
        same_domain_only=True
    )
    
    # Initialize and run scraper
    await scraper.initialize()
    output_files = await scraper.scrape(
        base_url=TEST_URL,
        output_format="pdf",
        test_mode=True  # Only process one link for test
    )
    
    # Verify results
    if not output_files:
        logging.error("❌ PDF scraping failed: No files were saved")
        return False
        
    logging.info(f"✅ PDF scraping successful: {len(output_files)} files saved")
    return True

async def test_rag_processing(input_dir, rag_dir):
    """Test RAG processing of scraped content."""
    logging.info("Testing RAG processing...")
    
    # Make sure we have files to process
    input_files = list(Path(input_dir).glob("*.*"))
    if not input_files:
        logging.error("❌ RAG processing setup failed: No input files found")
        return False
        
    # Log the files we found
    logging.info(f"Found {len(input_files)} files to process: {[f.name for f in input_files]}")
    
    # Debug: Create a simple test file to ensure we have content
    test_file_path = Path(input_dir) / "test_content.txt"
    with open(test_file_path, "w") as f:
        f.write("""
        # Test Document
        
        This is a test document for RAG processing.
        
        ## Section 1
        
        This section contains some text that will be chunked.
        The chunking algorithm should break this into smaller pieces.
        
        ## Section 2
        
        More content for testing the RAG processor.
        This should generate multiple chunks for testing.
        
        ## Conclusion
        
        The test document is now complete.
        """)
    
    logging.info(f"Created test file: {test_file_path}")
    
    # Create RAG processor
    processor = RAGProcessor(
        input_dir=input_dir,
        output_dir=rag_dir,
        chunk_size=200,  # Smaller chunks for test
        chunk_overlap=50
    )
    
    # Process the content
    stats = await processor.process_directory()
    
    # Verify results
    if stats["total_chunks"] == 0:
        logging.error("❌ RAG processing failed: No chunks were generated")
        return False
        
    logging.info(f"✅ RAG processing successful: {stats['total_chunks']} chunks generated")
    
    # List the generated files
    rag_files = list(Path(rag_dir).glob("*.json"))
    logging.info(f"Generated {len(rag_files)} RAG files: {[f.name for f in rag_files][:5]}...")
    
    return True

async def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(description="Test the WebScrape functionality")
    parser.add_argument("--keep", action="store_true", help="Keep test directories")
    args = parser.parse_args()
    
    # Create temporary directories for testing
    base_dir = tempfile.mkdtemp(prefix="webscrape_test_")
    text_dir = os.path.join(base_dir, "text_output")
    pdf_dir = os.path.join(base_dir, "pdf_output")
    rag_dir = os.path.join(base_dir, "rag_output")
    
    os.makedirs(text_dir)
    os.makedirs(pdf_dir)
    os.makedirs(rag_dir)
    
    logging.info(f"Created test directories in {base_dir}")
    
    try:
        # Run tests
        text_success = await test_text_scraping(text_dir)
        pdf_success = await test_pdf_scraping(pdf_dir)
        
        # Only test RAG if at least one scraping test succeeded
        rag_success = False
        if text_success:
            rag_success = await test_rag_processing(text_dir, rag_dir)
        
        # Summarize results
        logging.info("\n" + "="*50)
        logging.info("TEST SUMMARY")
        logging.info("="*50)
        logging.info(f"Text scraping: {'✅ PASS' if text_success else '❌ FAIL'}")
        logging.info(f"PDF scraping: {'✅ PASS' if pdf_success else '❌ FAIL'}")
        logging.info(f"RAG processing: {'✅ PASS' if rag_success else '❌ FAIL'}")
        logging.info("="*50)
        
        if all([text_success, pdf_success, rag_success]):
            logging.info("🎉 All tests passed successfully!")
            return 0
        else:
            logging.error("Some tests failed. See details above.")
            return 1
            
    finally:
        # Clean up test directories
        if not args.keep:
            shutil.rmtree(base_dir)
            logging.info(f"Cleaned up test directories")
        else:
            logging.info(f"Test directories preserved at {base_dir}")

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))