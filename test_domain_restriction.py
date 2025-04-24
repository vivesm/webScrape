#!/usr/bin/env python3
"""
Test Script for Domain Restriction Feature
==========================================

This script tests the domain restriction functionality of the WebScrape tool
by targeting a test website with external links and verifying that only 
links from the same domain are followed.
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

# Wikipedia makes a good test case because it has many links to external sites
TEST_URL = "https://en.wikipedia.org/wiki/Web_scraping"

async def test_domain_restriction():
    """Test the domain restriction functionality."""
    logging.info("Testing domain restriction...")
    
    # Create temporary directory for output
    output_dir = tempfile.mkdtemp(prefix="webscrape_domain_test_")
    logging.info(f"Created test directory: {output_dir}")
    
    try:
        # Test with domain restriction ON
        logging.info("Running test with domain restriction ON...")
        restricted_scraper = WebScraper(
            output_dir=output_dir + "/restricted",
            max_browsers=1,
            nav_timeout_ms=30000,
            same_domain_only=True  # Important: Domain restriction enabled
        )
        
        # Initialize and run scraper
        await restricted_scraper.initialize()
        # Just extract links, don't scrape content
        links_with_restriction = await restricted_scraper._extract_links(TEST_URL)
        await restricted_scraper.browser_pool.close_all()
        
        # Test with domain restriction OFF
        logging.info("Running test with domain restriction OFF...")
        unrestricted_scraper = WebScraper(
            output_dir=output_dir + "/unrestricted",
            max_browsers=1,
            nav_timeout_ms=30000,
            same_domain_only=False  # Important: Domain restriction disabled
        )
        
        # Initialize and run scraper
        await unrestricted_scraper.initialize()
        # Just extract links, don't scrape content
        links_without_restriction = await unrestricted_scraper._extract_links(TEST_URL)
        await unrestricted_scraper.browser_pool.close_all()
        
        # Check domains in both sets
        base_domain = urlparse(TEST_URL).netloc
        restricted_domains = {urlparse(link).netloc for link in links_with_restriction}
        unrestricted_domains = {urlparse(link).netloc for link in links_without_restriction}
        
        # Verify domain restriction worked
        external_in_restricted = [domain for domain in restricted_domains if domain != base_domain]
        external_in_unrestricted = [domain for domain in unrestricted_domains if domain != base_domain]
        
        # Log results
        logging.info("\n" + "="*50)
        logging.info("TEST RESULTS")
        logging.info("="*50)
        logging.info(f"Base domain: {base_domain}")
        logging.info(f"Links with restriction: {len(links_with_restriction)}")
        logging.info(f"Links without restriction: {len(links_without_restriction)}")
        logging.info(f"External domains with restriction: {len(external_in_restricted)}")
        logging.info(f"External domains without restriction: {len(external_in_unrestricted)}")
        
        # Determine test result
        if len(external_in_restricted) == 0 and len(links_with_restriction) > 0:
            logging.info("✅ TEST PASSED: Domain restriction successfully filtered out external links")
            return True
        else:
            domains_str = ", ".join(external_in_restricted[:5])
            logging.error(f"❌ TEST FAILED: Domain restriction didn't filter all external domains: {domains_str}...")
            return False
        
    finally:
        # Clean up
        shutil.rmtree(output_dir)
        logging.info(f"Cleaned up test directory")

async def main():
    """Run the test."""
    try:
        success = await test_domain_restriction()
        return 0 if success else 1
    except Exception as e:
        logging.error(f"Error during test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))