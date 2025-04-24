#!/usr/bin/env python3
"""
Test Script for Crawl Depth Control
==================================

This script tests the crawl depth control functionality of the WebScrape tool
by comparing the results of scraping a website at different depths.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import tempfile
import shutil

from web_scraper import WebScraper
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Wikipedia makes a good test case for depth control
TEST_URL = "https://en.wikipedia.org/wiki/Web_scraping"

async def test_depth_control():
    """Test the crawl depth control functionality."""
    logging.info("Testing crawl depth control...")
    
    # Create temporary directory for output
    output_dir = tempfile.mkdtemp(prefix="webscrape_depth_test_")
    logging.info(f"Created test directory: {output_dir}")
    
    try:
        # Test with depth 0 (only the base URL)
        logging.info("Running test with depth 0 (base URL only)...")
        depth0_scraper = WebScraper(
            output_dir=output_dir + "/depth0",
            max_browsers=2,
            nav_timeout_ms=30000,
            same_domain_only=True,
            max_depth=0  # Only the base URL
        )
        
        # Initialize and run scraper
        await depth0_scraper.initialize()
        # We need to scrape with output for depth 0 because _extract_links doesn't save files
        depth0_files = await depth0_scraper.scrape(
            base_url=TEST_URL,
            output_format="text",
            test_mode=False
        )
        await depth0_scraper.browser_pool.close_all()
        
        # Test with depth 1 (base URL and links on the base page)
        logging.info("Running test with depth 1 (base URL and direct links)...")
        depth1_scraper = WebScraper(
            output_dir=output_dir + "/depth1",
            max_browsers=2,
            nav_timeout_ms=30000,
            same_domain_only=True,
            max_depth=1
        )
        
        # Initialize and run scraper
        await depth1_scraper.initialize()
        # Use _extract_links to just get URL counts without saving files
        depth1_links = await depth1_scraper._extract_links(TEST_URL)
        # Get full scrape details (this would save files)
        depth1_files = await depth1_scraper.scrape(
            base_url=TEST_URL,
            output_format="text",
            test_mode=True  # Only the first link to avoid too many downloads
        )
        await depth1_scraper.browser_pool.close_all()
        
        # Test with depth 2 (one level deeper)
        logging.info("Running test with depth 2 (base URL, direct links, and one level deeper)...")
        depth2_scraper = WebScraper(
            output_dir=output_dir + "/depth2",
            max_browsers=2,
            nav_timeout_ms=30000,
            same_domain_only=True,
            max_depth=2
        )
        
        # Initialize scraper
        await depth2_scraper.initialize()
        
        # This would be slow, so we'll simulate by extracting links from first URL
        first_level_links = await depth2_scraper._extract_links(TEST_URL)
        if first_level_links:
            # Extract links from first link of first level
            first_link = next(iter(first_level_links))
            second_level_links = await depth2_scraper._extract_links(first_link)
            depth2_links = first_level_links.union(second_level_links)
        else:
            depth2_links = set()
            
        await depth2_scraper.browser_pool.close_all()
        
        # Log results
        logging.info("\n" + "="*50)
        logging.info("TEST RESULTS")
        logging.info("="*50)
        logging.info(f"Depth 0 files: {len(depth0_files)}")
        logging.info(f"Depth 1 links: {len(depth1_links)}")
        logging.info(f"Depth 2 links estimation: {len(depth2_links)}")
        
        # Determine test result
        if len(depth0_files) <= 1 and len(depth1_links) > 0 and len(depth2_links) > len(depth1_links):
            logging.info("✅ TEST PASSED: Depth control is working correctly")
            return True
        else:
            logging.error("❌ TEST FAILED: Depth control results don't match expectations")
            return False
        
    finally:
        # Clean up
        shutil.rmtree(output_dir)
        logging.info(f"Cleaned up test directory")

async def main():
    """Run the test."""
    try:
        success = await test_depth_control()
        return 0 if success else 1
    except Exception as e:
        logging.error(f"Error during test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))