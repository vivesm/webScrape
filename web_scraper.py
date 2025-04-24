import asyncio
import logging
import signal
import sys
from typing import List, Set, Dict, Any, Optional
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from browser_pool import BrowserPool
from link_extractor import LinkExtractor
from content_scraper import ContentScraper
from utils import ensure_dir

class WebScraper:
    """
    Main web scraper class that coordinates link extraction and content scraping.
    """
    
    def __init__(
        self,
        output_dir: str = "output",
        max_browsers: int = 2,
        nav_timeout_ms: int = 30_000,
        same_domain_only: bool = False,
        exclude_patterns: List[str] = None,
        include_patterns: List[str] = None,
        pdf_options: Dict[str, Any] = None,
        delay: float = 1.0,
        max_depth: int = 1
    ):
        """
        Initialize the web scraper.
        
        Args:
            output_dir: Directory to save scraped content
            max_browsers: Maximum number of browser instances to use
            nav_timeout_ms: Navigation timeout in milliseconds
            same_domain_only: Whether to only extract links from the same domain
            exclude_patterns: List of regex patterns to exclude
            include_patterns: List of regex patterns to include
            pdf_options: Options to pass to Pyppeteer's page.pdf()
            delay: Delay between processing links in seconds
            max_depth: Maximum depth of links to follow (1 = only process links on the base page)
        """
        self.output_dir = output_dir
        self.max_browsers = max_browsers
        self.delay = delay
        self.max_depth = max_depth
        
        # Create components
        ensure_dir(output_dir)
        self.browser_pool = BrowserPool(max_browsers=max_browsers)
        self.link_extractor = LinkExtractor(
            browser_pool=self.browser_pool,
            nav_timeout_ms=nav_timeout_ms,
            same_domain_only=same_domain_only,
            exclude_patterns=exclude_patterns,
            include_patterns=include_patterns
        )
        self.content_scraper = ContentScraper(
            browser_pool=self.browser_pool,
            output_dir=output_dir,
            nav_timeout_ms=nav_timeout_ms,
            pdf_options=pdf_options
        )
        
        # For tracking visited URLs
        self.visited_urls = set()
        self.url_to_depth = {}
        
        # For clean shutdown
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_signal)
            
    def _handle_signal(self, signum, frame):
        """Handle termination signals by cleaning up resources."""
        logging.info("Received termination signal. Cleaning up...")
        asyncio.create_task(self._cleanup())
        sys.exit(1)
        
    async def _cleanup(self):
        """Clean up resources (especially browser instances)."""
        await self.browser_pool.close_all()
        
    async def scrape(
        self, 
        base_url: str, 
        output_format: str = "pdf", 
        test_mode: bool = False,
        test_count: int = 2
    ) -> List[str]:
        """
        Main scraping function to extract links and scrape content.
        
        Args:
            base_url: URL to extract links from
            output_format: Format to save content as ("pdf" or "text")
            test_mode: Whether to only process the first link (for testing)
            
        Returns:
            List of paths to scraped files
        """
        output_files = []
        
        try:
            logging.info(f"Starting scrape with max depth of {self.max_depth}")
            
            # Initialize with the base URL at depth 0
            self.visited_urls = set()
            self.url_to_depth = {base_url: 0}
            urls_by_depth = {0: [base_url]}
            
            # Process each depth level sequentially
            for current_depth in range(self.max_depth + 1):
                urls_at_this_depth = urls_by_depth.get(current_depth, [])
                
                if not urls_at_this_depth:
                    logging.info(f"No URLs to process at depth {current_depth}. Finished.")
                    break
                    
                logging.info(f"Processing {len(urls_at_this_depth)} URLs at depth {current_depth}")
                
                # Create progress bar for this depth level
                with logging_redirect_tqdm():
                    pbar_depth = tqdm(total=len(urls_at_this_depth), desc=f"Depth {current_depth}", position=0)
                
                for url in urls_at_this_depth:
                    if url in self.visited_urls:
                        continue
                    
                    # Mark as visited
                    self.visited_urls.add(url)
                    
                    # Extract links from this URL
                    links = await self.link_extractor.extract_links_from_url(url)
                    
                    # Store links for next depth level if not at max depth
                    if current_depth < self.max_depth:
                        # Register these links at the next depth level
                        for link in links:
                            if link not in self.visited_urls and link not in self.url_to_depth:
                                next_depth = current_depth + 1
                                self.url_to_depth[link] = next_depth
                                
                                # Initialize the next depth level if needed
                                if next_depth not in urls_by_depth:
                                    urls_by_depth[next_depth] = []
                                    
                                urls_by_depth[next_depth].append(link)
                    
                    # Process content of this URL (not needed for base URL in most cases)
                    if current_depth > 0 or current_depth == self.max_depth == 0:  # Special case for depth 0
                        # Test mode only processes limited URLs
                        if test_mode and len(output_files) >= test_count:
                            logging.info(f"Test mode: reached limit of {test_count} files")
                            continue
                            
                        success, output_path = await self.content_scraper.scrape_url(
                            url, output_format, index=len(output_files) + 1
                        )
                        if success:
                            output_files.append(output_path)
                        await asyncio.sleep(self.delay)  # Delay between requests
                        pbar_depth.update(1)
                        
                # Process URLs at this depth level concurrently (after link extraction)
                if links and current_depth < self.max_depth and not test_mode:
                    # Skip content processing if this is a test and we've processed something
                    if test_mode and output_files:
                        continue
                        
                    # Process content of links concurrently
                    sem = asyncio.Semaphore(self.max_browsers)
                    links_to_process = [link for link in links if link not in self.visited_urls]
                    
                    if links_to_process:
                        logging.info(f"Processing content of {len(links_to_process)} URLs from depth {current_depth}")
                        
                        async def process_with_semaphore(link, index):
                            async with sem:
                                # Mark as visited before processing to avoid duplicates
                                self.visited_urls.add(link)
                                
                                success, output_path = await self.content_scraper.scrape_url(
                                    link, output_format, index=index
                                )
                                if success:
                                    output_files.append(output_path)
                                await asyncio.sleep(self.delay)  # Delay between requests
                                pbar.update(1)
                                
                        # Create progress bar
                        pbar = tqdm(total=len(links_to_process), desc=f"Scraping depth {current_depth}")
                        
                        # Create tasks for all links
                        tasks = []
                        for i, link in enumerate(links_to_process, start=len(output_files) + 1):
                            task = asyncio.create_task(process_with_semaphore(link, i))
                            tasks.append(task)
                            
                        # Wait for all tasks to complete
                        await asyncio.gather(*tasks)
                        pbar.close()
                        
                # In test mode, only process the specified number of links
                if test_mode and len(output_files) >= test_count:
                    logging.info(f"Test mode: stopping after {test_count} files")
                    break
                    
                # Close progress bar for this depth
                pbar_depth.close()
                    
            logging.info(f"Completed scraping to max depth {self.max_depth}")
            stats = {depth: len(urls) for depth, urls in urls_by_depth.items()}
            logging.info(f"URL counts by depth: {stats}")
            
        except Exception as e:
            logging.error(f"Error during scrape: {e}")
        finally:
            # Clean up resources
            await self._cleanup()
            
        return output_files
        
    async def initialize(self):
        """Initialize the browser pool."""
        await self.browser_pool.initialize()
        
    async def _extract_links(self, url: str) -> Set[str]:
        """
        Extract links from a given URL without processing them.
        This is primarily used for testing domain restriction.
        
        Args:
            url: URL to extract links from
            
        Returns:
            Set of links found at the URL
        """
        return await self.link_extractor.extract_links_from_url(url)
        
    async def _extract_all_links_to_depth(self, base_url: str, max_depth: int) -> List[str]:
        """
        Extract all links up to a specified depth.
        
        This method is useful for extracting links for separate processing.
        It crawls the site structure similar to the scrape method but only
        extracts links without downloading or saving content.
        
        Args:
            base_url: Base URL to start from
            max_depth: Maximum depth to crawl
            
        Returns:
            List of all links found up to the specified depth
        """
        logging.info(f"Extracting links up to depth {max_depth} from {base_url}")
        
        all_links = set()
        visited = set()
        url_to_depth = {base_url: 0}
        urls_by_depth = {0: [base_url]}
        
        # Process each depth level sequentially
        for current_depth in range(max_depth + 1):
            urls_at_this_depth = urls_by_depth.get(current_depth, [])
            
            if not urls_at_this_depth:
                logging.info(f"No URLs to process at depth {current_depth}. Finished link extraction.")
                break
                
            logging.info(f"Extracting links from {len(urls_at_this_depth)} URLs at depth {current_depth}")
            
            # Create progress bar for this depth level
            with logging_redirect_tqdm():
                pbar_depth = tqdm(total=len(urls_at_this_depth), desc=f"Depth {current_depth}", position=0)
            
            # Process each URL at this depth
            for url in urls_at_this_depth:
                if url in visited:
                    pbar_depth.update(1)
                    continue
                
                # Mark as visited
                visited.add(url)
                all_links.add(url)  # Add to the total link collection
                
                # Extract links from this URL
                if current_depth < max_depth:  # No need to extract links at max depth
                    links = await self.link_extractor.extract_links_from_url(url)
                    
                    # Add links to next depth level
                    for link in links:
                        if link not in visited and link not in url_to_depth:
                            next_depth = current_depth + 1
                            url_to_depth[link] = next_depth
                            
                            # Initialize the next depth level if needed
                            if next_depth not in urls_by_depth:
                                urls_by_depth[next_depth] = []
                                
                            urls_by_depth[next_depth].append(link)
                
                pbar_depth.update(1)
            
            # Close progress bar for this depth
            pbar_depth.close()
        
        # Log statistics
        logging.info(f"Extracted {len(all_links)} unique links from {len(visited)} visited URLs")
        stats = {depth: len(urls) for depth, urls in urls_by_depth.items()}
        logging.info(f"URL counts by depth: {stats}")
        
        return list(all_links)