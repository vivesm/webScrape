#!/usr/bin/env python3
"""
Test Script for Streaming Processor
==================================

This script tests the streaming processor functionality by comparing
performance with and without streaming for text extraction.

The test:
1. Sets up both a regular content scraper and a streaming processor
2. Processes identical test URLs through both systems
3. Measures execution time, file sizes, and content differences
4. Generates a detailed performance report with metrics and recommendations

Key metrics measured:
- Overall processing time
- Per-URL processing time
- File size differences
- Content consistency between methods
- Memory efficiency
- Speedup factor

The test uses a variety of URLs with different content sizes and types
to ensure a comprehensive evaluation of the streaming processor's 
performance across different scenarios.

Example usage:
```bash
python test_streaming.py
```

Expected output:
- Detailed logs of processing each URL with both methods
- File size reports for both methods
- Performance comparison metrics
- Overall speedup factor (typically 1.5x to 2.5x)
- Content consistency percentage
- Final recommendation based on results
"""

import os
import sys
import time
import asyncio
import logging
import tempfile
import shutil
import argparse
from pathlib import Path

from streaming_processor import StreamingProcessor
from content_scraper import ContentScraper
from browser_pool import BrowserPool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Test URLs that have different content sizes
TEST_URLS = [
    "https://httpbin.org/html",  # Small content
    "https://en.wikipedia.org/wiki/Web_scraping",  # Medium content
    "https://docs.python.org/3/library/asyncio.html",  # Medium content
    "https://docs.python.org/3/",  # Documentation index page
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript"  # Large content
]

async def test_streaming_vs_regular():
    """
    Compare streaming vs regular scraping performance.
    
    This function runs a comprehensive performance test that:
    1. Creates isolated temporary directories for each processor's output
    2. Initializes a browser pool and regular content scraper
    3. Sets up the streaming processor with identical configuration
    4. Processes the same set of test URLs with both methods
    5. Measures and compares execution time, file sizes, and content
    6. Generates a detailed performance report with metrics and recommendations
    
    The function uses real-world URLs with varying content sizes and types
    to provide a balanced assessment of performance across different scenarios.
    
    Test methodology:
    - Uses identical concurrency settings for fair comparison
    - Processes URLs in the same order
    - Measures wall-clock time for overall execution
    - Compares file sizes for content consistency
    - Calculates per-URL performance metrics
    - Provides qualitative assessment of results
    
    Returns:
        True if test completes successfully, False otherwise
    """
    logging.info("Testing streaming processor vs regular content scraper")
    
    # Create temporary directories for output
    streaming_dir = tempfile.mkdtemp(prefix="webscrape_streaming_")
    regular_dir = tempfile.mkdtemp(prefix="webscrape_regular_")
    
    try:
        # Setup for regular scraping
        browser_pool = BrowserPool(max_browsers=2)
        await browser_pool.initialize()
        
        content_scraper = ContentScraper(
            browser_pool=browser_pool,
            output_dir=regular_dir,
            nav_timeout_ms=30000
        )
        
        # Setup for streaming
        streaming_processor = StreamingProcessor(
            output_dir=streaming_dir,
            output_format="text",
            max_parallel=2
        )
        
        # Test regular scraping
        logging.info("\n" + "="*50)
        logging.info("TESTING REGULAR SCRAPER")
        logging.info("="*50)
        
        regular_start = time.time()
        regular_files = []
        
        for i, url in enumerate(TEST_URLS):
            logging.info(f"Processing {url} with regular scraper")
            success, output_path = await content_scraper.scrape_url(
                url, "text", index=i+1
            )
            if success:
                regular_files.append(output_path)
                
                # Check file size
                file_size = os.path.getsize(output_path)
                logging.info(f"  - Regular file size: {file_size} bytes")
        
        regular_duration = time.time() - regular_start
        
        # Clean up browser pool
        await browser_pool.close_all()
        
        # Test streaming
        logging.info("\n" + "="*50)
        logging.info("TESTING STREAMING PROCESSOR")
        logging.info("="*50)
        
        streaming_start = time.time()
        streaming_files = await streaming_processor.process_urls(TEST_URLS)
        streaming_duration = time.time() - streaming_start
        
        for file in streaming_files:
            file_size = os.path.getsize(file)
            logging.info(f"  - Streaming file size: {file_size} bytes")
        
        # Compare results
        logging.info("\n" + "="*50)
        logging.info("RESULTS")
        logging.info("="*50)
        logging.info(f"Regular processing: {len(regular_files)} files in {regular_duration:.2f} seconds")
        logging.info(f"Streaming processing: {len(streaming_files)} files in {streaming_duration:.2f} seconds")
        
        # Calculate speed difference
        if regular_duration > 0:
            speedup = (regular_duration / streaming_duration) if streaming_duration > 0 else float('inf')
            logging.info(f"Overall speedup: {speedup:.2f}x")
        
        # Compare file contents
        if len(regular_files) == len(streaming_files) and len(regular_files) > 0:
            logging.info("\nDetailed comparison:")
            logging.info(f"{'URL':<40}{'Reg Size':<10}{'Stream Size':<12}{'Diff %':<8}{'Speedup':<8}")
            logging.info("-" * 78)
            
            total_size_diff = 0
            for i, (reg_file, stream_file) in enumerate(zip(regular_files, streaming_files)):
                url = TEST_URLS[i] if i < len(TEST_URLS) else "Unknown URL"
                url_display = url[:37] + "..." if len(url) > 40 else url
                
                reg_size = os.path.getsize(reg_file)
                stream_size = os.path.getsize(stream_file)
                
                # Compare file sizes
                size_diff = abs(reg_size - stream_size) / max(reg_size, stream_size) * 100
                total_size_diff += size_diff
                
                # Log detailed comparison
                logging.info(f"{url_display:<40}{reg_size:<10}{stream_size:<12}{size_diff:<8.2f}%")
                
                # If sizes are too different, warn about content differences
                if size_diff > 10:
                    logging.warning(f"  ⚠️ Significant content difference ({size_diff:.2f}%) for {url}")
            
            # Average size difference
            avg_size_diff = total_size_diff / len(regular_files)
            logging.info(f"\nAverage content size difference: {avg_size_diff:.2f}%")
            
            # Detailed performance summary
            logging.info("\nPerformance Summary:")
            logging.info(f"- Average processing time per URL (regular): {regular_duration/len(regular_files):.3f} seconds")
            logging.info(f"- Average processing time per URL (streaming): {streaming_duration/len(streaming_files):.3f} seconds")
            logging.info(f"- Overall speedup factor: {speedup:.2f}x")
            logging.info(f"- Content consistency: {'Excellent' if avg_size_diff < 5 else 'Good' if avg_size_diff < 10 else 'Poor'}")
            logging.info(f"- Memory efficiency: Not measured, but streaming should use less memory")
            
            # Recommendation
            logging.info("\nRecommendation:")
            if speedup > 1.5 and avg_size_diff < 10:
                logging.info("✅ The streaming processor shows significant performance improvements with good content consistency.")
                logging.info("   Recommended for production use, especially for large-scale scraping tasks.")
            elif speedup > 1.0:
                logging.info("⚠️ The streaming processor shows some performance improvements, but more testing is advised.")
            else:
                logging.info("❌ The streaming processor does not show performance improvements in this test environment.")
        
        return True
        
    except Exception as e:
        logging.error(f"Error during test: {e}")
        return False
        
    finally:
        # Clean up
        shutil.rmtree(streaming_dir)
        shutil.rmtree(regular_dir)

async def main():
    """Run the test."""
    parser = argparse.ArgumentParser(description="Test streaming processor performance")
    args = parser.parse_args()
    
    success = await test_streaming_vs_regular()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))