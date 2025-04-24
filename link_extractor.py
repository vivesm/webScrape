import asyncio
import logging
from typing import Set, Dict, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pyppeteer.page import Page

from browser_pool import BrowserPool
from retry_utils import async_retry_decorator
from utils import filter_links, create_headers

class LinkExtractor:
    """
    Extracts links from webpages using dynamic rendering with Pyppeteer.
    """
    
    def __init__(
        self, 
        browser_pool: BrowserPool,
        nav_timeout_ms: int = 30_000,
        same_domain_only: bool = False,
        exclude_patterns: List[str] = None,
        include_patterns: List[str] = None
    ):
        """
        Initialize the link extractor.
        
        Args:
            browser_pool: Pool of browser instances to use
            nav_timeout_ms: Navigation timeout in milliseconds
            same_domain_only: Whether to only include links from the same domain
            exclude_patterns: List of regex patterns to exclude
            include_patterns: List of regex patterns to include
        """
        self.browser_pool = browser_pool
        self.nav_timeout_ms = nav_timeout_ms
        self.same_domain_only = same_domain_only
        self.exclude_patterns = exclude_patterns
        self.include_patterns = include_patterns
    
    @async_retry_decorator(
        retries=3,
        base_delay=2.0,
        retry_on_exceptions=(Exception,),
        retry_on_status_codes=[429, 503, 500, 403]
    )
    async def extract_links_from_url(self, url: str) -> Set[str]:
        """
        Extract all links from a given URL using Pyppeteer for dynamic rendering.
        
        Args:
            url: URL to extract links from
            
        Returns:
            Set of extracted URLs
        """
        browser = await self.browser_pool.get_browser()
        links = set()
        
        try:
            # Parse the base URL to get the domain
            base_domain = urlparse(url).netloc
            if self.same_domain_only:
                logging.info(f"Domain restriction active. Only following links within: {base_domain}")
            
            # Create a new page for this extraction
            page = await browser.newPage()
            page.setDefaultNavigationTimeout(self.nav_timeout_ms)
            
            # Set headers with random user agent
            await page.setExtraHTTPHeaders(create_headers())
            
            # Navigate to the URL and wait for content to load
            await page.goto(url, {"waitUntil": "domcontentloaded"})
            
            # Try to dismiss cookie banners
            await self._try_dismiss_cookie_banners(page)
            
            # Extract links from the page
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            raw_links = {
                urljoin(url, a["href"])
                for a in soup.find_all("a", href=True)
                if "#" not in a["href"]  # Skip anchor links
            }
            
            logging.info(f"Found {len(raw_links)} raw links on page before filtering")
            
            # Filter links based on criteria
            links = filter_links(
                raw_links, 
                base_url=url, 
                exclude_patterns=self.exclude_patterns,
                include_patterns=self.include_patterns,
                same_domain_only=self.same_domain_only
            )
            
            if self.same_domain_only:
                # Double check that we only have links from the same domain
                for link in links:
                    link_domain = urlparse(link).netloc
                    if link_domain != base_domain:
                        logging.warning(f"Domain filter leakage detected: {link} (domain: {link_domain})")
            
            logging.info(f"Final result: {len(links)} valid links to process")
            
        except Exception as e:
            logging.error(f"Failed to extract links from {url}: {e}")
            raise  # Re-raise for the retry decorator
            
        finally:
            # Close the page and release the browser back to the pool
            try:
                if page:
                    await page.close()
            except Exception:
                pass
                
            await self.browser_pool.release_browser(browser)
            
        return links
    
    async def _try_dismiss_cookie_banners(self, page: Page) -> None:
        """
        Attempt to dismiss cookie consent banners on the page.
        
        Args:
            page: Pyppeteer page object
        """
        try:
            # Try common cookie banner patterns
            cookie_banner_selectors = [
                # Accept buttons
                "button[id*='cookie'][id*='accept'],button[class*='cookie'][class*='accept']",
                "button[id*='cookie'][id*='agree'],button[class*='cookie'][class*='agree']",
                "button[id*='accept-cookie'],button[class*='accept-cookie']",
                # Cookie banner close buttons
                "div[id*='cookie'] button[aria-label='Close'],div[class*='cookie'] button[aria-label='Close']",
                "div[id*='cookie'] .close,div[class*='cookie'] .close"
            ]
            
            # Try each selector
            for selector in cookie_banner_selectors:
                try:
                    accept_buttons = await page.querySelectorAll(selector)
                    if accept_buttons:
                        await accept_buttons[0].click()
                        logging.info("Dismissed cookie banner")
                        await asyncio.sleep(1)  # Wait for banner to disappear
                        return
                except Exception:
                    continue
                    
            # JavaScript fallback approach
            await page.evaluate('''() => {
                const btns = [...document.querySelectorAll("button")];
                const acceptBtn = btns.find(b => 
                    b.innerText.toLowerCase().includes("accept") || 
                    b.innerText.toLowerCase().includes("agree") ||
                    b.innerText.toLowerCase().includes("consent") ||
                    b.innerText.toLowerCase().includes("allow")
                );
                if (acceptBtn) acceptBtn.click();
            }''')
            
        except Exception as e:
            logging.warning(f"Failed to dismiss cookie banner: {e}")
            # Continue anyway - cookie banner dismissal is not critical