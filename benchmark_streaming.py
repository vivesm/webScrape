#!/usr/bin/env python3
"""
Streaming Processor Benchmark
============================

This tool benchmarks the streaming processor against the regular content scraper,
allowing for fine-tuning of performance parameters like buffer size.

It runs a series of benchmark tests with different configurations and provides
a detailed report on performance metrics.

Features:
- Compares streaming processor vs. regular content scraper performance
- Tests multiple buffer sizes to find optimal configuration
- Measures speedup factor and content consistency
- Generates detailed reports with performance metrics
- Supports regular and extended test sets with various content types
- Outputs both console summary and detailed JSON report

Usage:
```bash
# Basic usage with default buffer sizes
python benchmark_streaming.py

# Test specific buffer sizes (in KB)
python benchmark_streaming.py --buffer_sizes 256 512 1024 2048 4096

# Run extended benchmark with more test URLs
python benchmark_streaming.py --extended

# Custom output file for results
python benchmark_streaming.py --output my_benchmark_results.json
```

Output:
The tool produces a detailed JSON report with performance metrics for each
buffer size tested, including:
- Processing duration
- Average time per URL
- Content consistency percentage
- Speedup factor compared to regular scraper
- Optimal buffer size recommendation

The benchmark helps determine the optimal buffer size for different use cases,
balancing speed and memory usage based on your specific environment.
"""

import os
import asyncio
import logging
import tempfile
import argparse
import time
import json
from typing import Dict, List, Any, Tuple
from pathlib import Path

from browser_pool import BrowserPool
from content_scraper import ContentScraper
from streaming_processor import StreamingProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Test URLs for benchmarking
DEFAULT_TEST_URLS = [
    "https://httpbin.org/html",
    "https://en.wikipedia.org/wiki/Web_scraping",
    "https://docs.python.org/3/library/asyncio.html",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "https://github.com/about"
]

# Additional larger test URLs (use for extensive testing)
LARGE_TEST_URLS = [
    "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "https://docs.python.org/3/tutorial/index.html",
    "https://en.wikipedia.org/wiki/Web_browser",
    "https://developer.mozilla.org/en-US/docs/Web/HTTP",
    "https://en.wikipedia.org/wiki/Parsing"
]

async def benchmark_with_params(
    urls: List[str],
    buffer_sizes: List[int] = [256, 512, 1024, 2048, 4096],
    output_file: str = "benchmark_results.json"
) -> Dict[str, Any]:
    """
    Benchmark the streaming processor with different buffer sizes.
    
    This comprehensive benchmark function:
    1. Measures performance of the regular content scraper as a baseline
    2. Tests the streaming processor with multiple buffer sizes
    3. Calculates speedup factors and content consistency for each buffer size
    4. Determines the optimal buffer size based on performance
    5. Generates a detailed report with all metrics
    
    The function creates temporary directories for each test to ensure
    clean results and provides detailed logging throughout the process.
    
    Performance metrics measured:
    - Overall processing duration
    - Average time per URL
    - File size consistency between methods
    - Total output size
    - Speedup factor relative to baseline
    
    Args:
        urls: List of URLs to benchmark with varied content sizes and types
        buffer_sizes: List of buffer sizes in KB to test (default: 256 to 4096 KB)
        output_file: JSON file path to save detailed benchmark results
        
    Returns:
        Dictionary with comprehensive benchmark results containing:
        - timestamp: When the benchmark was run
        - urls_tested: Number of URLs tested
        - buffer_sizes: List of buffer sizes tested
        - baseline: Regular scraper performance metrics
        - results: List of streaming processor results for each buffer size
        - optimal: Details of the best-performing configuration
    """
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "urls_tested": len(urls),
        "buffer_sizes": buffer_sizes,
        "results": []
    }
    
    # Create a temporary directory for regular scraper output
    regular_dir = tempfile.mkdtemp(prefix="benchmark_regular_")
    
    # Run regular scraper first as baseline
    logging.info("=" * 60)
    logging.info("BENCHMARKING REGULAR CONTENT SCRAPER (BASELINE)")
    logging.info("=" * 60)
    
    # Setup browser pool and regular scraper
    browser_pool = BrowserPool(max_browsers=2)
    await browser_pool.initialize()
    
    content_scraper = ContentScraper(
        browser_pool=browser_pool,
        output_dir=regular_dir,
        nav_timeout_ms=30000
    )
    
    # Measure regular scraper performance
    regular_start = time.time()
    regular_files = []
    
    for i, url in enumerate(urls):
        logging.info(f"Processing with regular scraper: {url}")
        success, output_path = await content_scraper.scrape_url(
            url, "text", index=i+1
        )
        if success:
            regular_files.append(output_path)
    
    regular_duration = time.time() - regular_start
    
    # Clean up browser pool
    await browser_pool.close_all()
    
    # Calculate regular scraper metrics
    regular_size_total = sum(os.path.getsize(f) for f in regular_files)
    regular_avg_time = regular_duration / len(urls) if urls else 0
    
    # Save baseline results
    baseline = {
        "processor": "regular",
        "duration": regular_duration,
        "avg_time_per_url": regular_avg_time,
        "file_count": len(regular_files),
        "total_size": regular_size_total,
        "buffer_size": None  # Not applicable
    }
    results["baseline"] = baseline
    
    # Now test streaming processor with different buffer sizes
    for buffer_size in buffer_sizes:
        logging.info("=" * 60)
        logging.info(f"BENCHMARKING STREAMING PROCESSOR WITH {buffer_size}KB BUFFER")
        logging.info("=" * 60)
        
        # Create a temporary directory for this buffer size
        stream_dir = tempfile.mkdtemp(prefix=f"benchmark_stream_{buffer_size}kb_")
        
        # Configure streaming processor
        stream_processor = StreamingProcessor(
            output_dir=stream_dir,
            output_format="text",
            max_parallel=2,
            buffer_size=buffer_size * 1024  # Convert to bytes
        )
        
        # Measure streaming processor performance
        stream_start = time.time()
        stream_files = await stream_processor.process_urls(urls)
        stream_duration = time.time() - stream_start
        
        # Calculate metrics
        stream_size_total = sum(os.path.getsize(f) for f in stream_files)
        stream_avg_time = stream_duration / len(urls) if urls else 0
        
        # Check content consistency
        consistency = 0
        if regular_files and stream_files:
            # Get average size difference
            total_diff = 0
            for reg_file, stream_file in zip(regular_files, stream_files):
                reg_size = os.path.getsize(reg_file)
                stream_size = os.path.getsize(stream_file)
                diff = abs(reg_size - stream_size) / max(reg_size, stream_size)
                total_diff += diff
            
            consistency = 100 - (total_diff / len(regular_files) * 100)
            
        # Calculate speedup
        speedup = regular_duration / stream_duration if stream_duration > 0 else 0
        
        # Save results for this buffer size
        result = {
            "buffer_size": buffer_size,
            "duration": stream_duration,
            "avg_time_per_url": stream_avg_time,
            "file_count": len(stream_files),
            "total_size": stream_size_total,
            "speedup": speedup,
            "content_consistency": consistency
        }
        results["results"].append(result)
        
        # Clean up temporary directory
        # Keep files for now for comparison if needed
        # shutil.rmtree(stream_dir)
        
        logging.info(f"Buffer size {buffer_size}KB - Speedup: {speedup:.2f}x - Consistency: {consistency:.1f}%")
    
    # Find optimal buffer size
    if results["results"]:
        # Sort by speedup (higher is better)
        sorted_results = sorted(results["results"], key=lambda x: x["speedup"], reverse=True)
        optimal = sorted_results[0]
        
        logging.info("=" * 60)
        logging.info("BENCHMARK SUMMARY")
        logging.info("=" * 60)
        logging.info(f"Optimal buffer size: {optimal['buffer_size']}KB")
        logging.info(f"Speedup: {optimal['speedup']:.2f}x")
        logging.info(f"Content consistency: {optimal['content_consistency']:.1f}%")
        
        results["optimal"] = {
            "buffer_size": optimal["buffer_size"],
            "speedup": optimal["speedup"],
            "consistency": optimal["content_consistency"]
        }
    
    # Save results to file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"Benchmark results saved to {output_file}")
    
    return results

async def main():
    """Parse arguments and run benchmark."""
    parser = argparse.ArgumentParser(description="Streaming processor benchmark tool")
    parser.add_argument(
        "--buffer_sizes", 
        type=int, 
        nargs="+", 
        default=[256, 512, 1024, 2048, 4096],
        help="Buffer sizes in KB to test"
    )
    parser.add_argument(
        "--extended", 
        action="store_true",
        help="Run extended benchmark with more URLs"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="benchmark_results.json",
        help="Output file for benchmark results"
    )
    
    args = parser.parse_args()
    
    # Use extended URL set if requested
    urls = DEFAULT_TEST_URLS + LARGE_TEST_URLS if args.extended else DEFAULT_TEST_URLS
    
    # Run benchmark
    results = await benchmark_with_params(
        urls=urls,
        buffer_sizes=args.buffer_sizes,
        output_file=args.output
    )
    
    # Print summary
    print("\nStreaming Processor Benchmark Results:")
    print("-" * 80)
    print(f"URLs tested: {len(urls)}")
    print(f"Buffer sizes tested: {args.buffer_sizes}")
    print(f"Baseline (regular scraper): {results['baseline']['duration']:.2f} seconds")
    print(f"Optimal buffer size: {results['optimal']['buffer_size']}KB")
    print(f"Optimal speedup: {results['optimal']['speedup']:.2f}x")
    print(f"Content consistency: {results['optimal']['consistency']:.1f}%")
    print("-" * 80)
    print(f"Full results saved to: {args.output}")
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))