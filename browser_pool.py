"""
Browser Pool Module
==================

This module provides a resource management system for browser instances used in web scraping.
It maintains a pool of reusable browser instances to reduce the overhead of repeatedly
launching and closing browsers, significantly improving performance and resource usage.

Key Features:
- Dynamic browser instance management
- Concurrent access control with semaphores
- Health checking for browser instances
- Safe browser termination with process cleanup
- Automatic recovery from browser crashes

Usage Example:
-------------
```python
# Create a browser pool with maximum 3 concurrent browsers
pool = BrowserPool(max_browsers=3)

# Initialize the pool (optional, will auto-initialize if needed)
await pool.initialize()

# Get a browser from the pool
browser = await pool.get_browser()

# Use the browser...
page = await browser.newPage()
await page.goto('https://example.com')

# Return browser to the pool when done
await pool.release_browser(browser)

# Close all browsers when completely finished
await pool.close_all()
```

Dependencies:
- pyppeteer for browser automation
- asyncio for async/await functionality
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from pyppeteer import launch
from pyppeteer.browser import Browser
from contextlib import suppress
from pyppeteer.errors import NetworkError
from asyncio.exceptions import InvalidStateError

class BrowserPool:
    """
    Manages a pool of browser instances for more efficient resource usage.
    
    This class helps reduce the overhead of repeatedly launching and closing
    browser instances when processing multiple URLs. It manages browser lifecycle,
    health checking, and concurrent access to ensure optimal resource usage.
    
    The pool maintains two sets of browsers:
    1. available_browsers: Browsers ready to be used
    2. in_use_browsers: Browsers currently being used by tasks
    
    A semaphore limits the total number of concurrent browser instances.
    """
    
    def __init__(self, max_browsers: int = 2, browser_args: List[str] = None):
        """
        Initialize the browser pool.
        
        Args:
            max_browsers: Maximum number of browser instances to keep in the pool
                          Higher values improve concurrency but increase memory usage
            browser_args: List of command-line arguments to pass to the Chrome browser
                          Default includes security-related sandbox disabling for containers
        
        Note: 
            Browser instances are not created immediately. They are created when:
            1. initialize() is called explicitly, or
            2. get_browser() is called for the first time
        """
        # Configuration
        self.max_browsers = max_browsers
        self.browser_args = browser_args or ["--no-sandbox", "--disable-setuid-sandbox"]
        
        # Browser tracking collections
        self.available_browsers: Set[Browser] = set()  # Ready to use
        self.in_use_browsers: Set[Browser] = set()     # Currently in use
        
        # Concurrency control
        self.browser_semaphore = asyncio.Semaphore(max_browsers)
        
        # State tracking
        self.initialized = False
        
    async def initialize(self):
        """
        Initialize the browser pool by creating browser instances.
        
        This method creates the maximum number of browser instances upfront,
        which can be useful to reduce latency during initial scraping tasks.
        If the pool is already initialized, this method does nothing.
        
        Note:
            This method is optional. The pool will initialize lazily when needed.
        """
        # Prevent duplicate initialization
        if self.initialized:
            return
            
        # Create all browser instances
        for _ in range(self.max_browsers):
            browser = await self._create_browser()
            self.available_browsers.add(browser)
        
        self.initialized = True
        logging.info(f"Browser pool initialized with {self.max_browsers} instances")
    
    async def get_browser(self) -> Browser:
        """
        Acquire a browser from the pool or create a new one if needed.
        
        This method is the primary way to obtain a browser instance. It will:
        1. Wait for a semaphore slot to become available (if all are in use)
        2. Initialize the pool if it hasn't been initialized yet
        3. Take an available browser or create a new one if none are available
        4. Mark the browser as in-use
        
        Returns:
            A browser instance ready for use
            
        Note:
            Always pair this with a subsequent call to release_browser()
            to return the browser to the pool when done.
        """
        # Wait for a slot in the semaphore (limits concurrent browser usage)
        async with self.browser_semaphore:
            # Lazy initialization if needed
            if not self.initialized:
                await self.initialize()
                
            # Get an existing browser or create a new one
            if not self.available_browsers:
                browser = await self._create_browser()
            else:
                browser = self.available_browsers.pop()
            
            # Mark as in-use
            self.in_use_browsers.add(browser)
            return browser
    
    async def release_browser(self, browser: Browser):
        """
        Return a browser to the pool or close it if it's unhealthy.
        
        This method should be called after finishing work with a browser
        obtained via get_browser(). It performs health checks and:
        1. Closes any extra pages the browser has open
        2. Returns the browser to the available pool if healthy
        3. Replaces the browser with a new one if unhealthy
        4. Releases the semaphore to allow another task to use a browser
        
        Args:
            browser: The browser instance to release
            
        Note:
            Always call this method in a finally block to ensure browsers
            are properly returned to the pool, even if exceptions occur.
        """
        # Only process if this browser is actually from our pool
        if browser in self.in_use_browsers:
            self.in_use_browsers.remove(browser)
            
            # Check if browser is still healthy (has pages open)
            try:
                # Get all open pages
                pages = await browser.pages()
                
                # Close any extra pages (keep only the default page)
                if len(pages) > 1:  # More than just the default page
                    for page in pages[1:]:  # Close extra pages
                        await page.close()
                
                # Browser is healthy, return to available pool
                self.available_browsers.add(browser)
                
            except Exception as e:
                # Browser is unhealthy, replace it
                logging.warning(f"Unhealthy browser detected, creating new one: {e}")
                await self.safe_browser_close(browser)
                new_browser = await self._create_browser()
                self.available_browsers.add(new_browser)
            
            # Release semaphore to allow another task to use a browser
            self.browser_semaphore.release()
    
    async def _create_browser(self) -> Browser:
        """
        Create a new browser instance.
        
        This internal method handles the actual browser creation with
        configured arguments. It's used both during initialization and
        when replacing unhealthy browsers.
        
        Returns:
            A new browser instance configured with the pool's args
            
        Note:
            We use a headless browser by default for automation purposes.
            The browser_args can be customized during pool creation.
        """
        browser = await launch(
            headless=True,  # Run without visible UI
            args=self.browser_args  # Pass custom args (e.g., for containers)
        )
        return browser
    
    async def close_all(self):
        """
        Close all browser instances in the pool.
        
        This method should be called when the scraping job is complete
        to clean up all browser resources. It:
        1. Collects all browsers (both available and in-use)
        2. Safely closes each browser with process cleanup
        3. Clears the browser collections
        4. Resets the initialization flag
        
        Note:
            After calling this method, the pool will need to be
            reinitialized before use.
        """
        # Collect all browsers
        all_browsers = list(self.available_browsers) + list(self.in_use_browsers)
        
        # Create tasks to close each browser safely
        close_tasks = [self.safe_browser_close(browser) for browser in all_browsers]
        
        # Wait for all browsers to close
        if close_tasks:
            await asyncio.gather(*close_tasks)
            
        # Reset pool state
        self.available_browsers.clear()
        self.in_use_browsers.clear()
        self.initialized = False
        logging.info("All browsers in pool closed")
    
    async def safe_browser_close(self, browser: Browser):
        """
        Close a browser safely with timeout and process cleanup.
        
        This method handles browser shutdown with proper error handling:
        1. Attempts graceful close with timeout
        2. Falls back to process termination if graceful close fails
        
        Args:
            browser: The browser instance to close
            
        Note:
            This method is crucial for preventing process leaks, which
            can occur if browsers aren't closed properly.
        """
        try:
            # Try graceful close with timeout
            await asyncio.wait_for(browser.close(), timeout=5)
        except Exception:
            # Fallback to forceful termination
            logging.warning("Forcibly terminating Chrome process")
            if browser.process:
                # Suppress exceptions during kill to ensure cleanup continues
                with suppress(Exception):
                    browser.process.kill()