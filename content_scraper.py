import os
import logging
import asyncio
import requests
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from bs4 import BeautifulSoup

from browser_pool import BrowserPool
from retry_utils import async_retry_decorator
from utils import hash_file, hash_bytes, hash_text, sanitize_filename, create_headers, ensure_dir

class ContentScraper:
    """
    Scrapes content from webpages and saves it as PDF or text files.
    """
    
    def __init__(
        self, 
        browser_pool: BrowserPool,
        output_dir: str = "output",
        nav_timeout_ms: int = 30_000,
        pdf_options: Dict[str, Any] = None
    ):
        """
        Initialize the content scraper.
        
        Args:
            browser_pool: Pool of browser instances to use
            output_dir: Directory to save scraped content
            nav_timeout_ms: Navigation timeout in milliseconds
            pdf_options: Options to pass to Pyppeteer's page.pdf()
        """
        self.browser_pool = browser_pool
        self.output_dir = output_dir
        self.nav_timeout_ms = nav_timeout_ms
        self.pdf_options = pdf_options or {"format": "A4"}
        
        # Ensure output directory exists
        ensure_dir(output_dir)
    
    async def scrape_url(
        self, 
        url: str, 
        output_format: str = "pdf", 
        index: int = 0,
        custom_filename: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Scrape content from a URL and save it in the specified format.
        
        Args:
            url: URL to scrape
            output_format: Format to save content as ("pdf" or "text")
            index: Numerical index for filename generation
            custom_filename: Optional custom filename to use
            
        Returns:
            Tuple of (success: bool, output_path: str)
        """
        # Generate output filename
        if custom_filename:
            filename = custom_filename
        else:
            filename = sanitize_filename(url, index)
            
        output_path = os.path.join(self.output_dir, f"{filename}.{output_format}")
        
        logging.info(f"Processing {url} -> {output_path}")
        
        # Process based on requested format
        if output_format == "pdf":
            success = await self.save_as_pdf(url, output_path)
        else:
            success = await self.save_as_text(url, output_path)
            
        return success, output_path
    
    @async_retry_decorator(
        retries=2,
        base_delay=2.0,
        retry_on_exceptions=(Exception,),
        retry_on_status_codes=[429, 503, 500, 403]
    )
    async def save_as_pdf(self, url: str, output_path: str) -> bool:
        """
        Save a webpage as PDF with content comparison.
        
        Args:
            url: URL to save as PDF
            output_path: Path to save the PDF
            
        Returns:
            Boolean indicating success
        """
        pdf_bytes = await self._generate_pdf_bytes(url)
        if not pdf_bytes:
            return False
            
        # Hash the new content
        new_hash = hash_bytes(pdf_bytes)
        
        # Check if file exists and compare content
        if os.path.isfile(output_path):
            existing_hash = hash_file(output_path)
            if existing_hash == new_hash:
                logging.info(f"PDF content is identical. Skipping: {output_path}")
                return True
            else:
                logging.info(f"PDF content differs. Overwriting: {output_path}")
                
        # Save the new PDF
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        logging.info(f"Saved PDF: {output_path}")
        return True
    
    async def _generate_pdf_bytes(self, url: str) -> Optional[bytes]:
        """
        Generate PDF bytes from a URL without saving to disk.
        
        Args:
            url: URL to render as PDF
            
        Returns:
            PDF content as bytes, or None on failure
        """
        browser = await self.browser_pool.get_browser()
        pdf_bytes = None
        
        try:
            page = await browser.newPage()
            page.setDefaultNavigationTimeout(self.nav_timeout_ms)
            
            # Set headers with random user agent
            await page.setExtraHTTPHeaders(create_headers())
            
            # Navigate to the URL and wait for content to load
            await page.goto(url, {"waitUntil": "domcontentloaded"})
            
            # Wait a bit for any JavaScript to execute
            await asyncio.sleep(2)
            
            # Generate PDF
            pdf_bytes = await page.pdf(self.pdf_options)
            
        except Exception as e:
            logging.error(f"Failed to generate PDF for {url}: {e}")
            raise  # Re-raise for retry decorator
            
        finally:
            # Close the page and release the browser back to the pool
            try:
                if page:
                    await page.close()
            except Exception:
                pass
                
            await self.browser_pool.release_browser(browser)
            
        return pdf_bytes
    
    @async_retry_decorator(
        retries=2,
        base_delay=2.0,
        retry_on_exceptions=(Exception,),
        retry_on_status_codes=[429, 503, 500, 403]
    )
    async def save_as_text(self, url: str, output_path: str) -> bool:
        """
        Save a webpage as text with content comparison.
        
        Args:
            url: URL to save as text
            output_path: Path to save the text
            
        Returns:
            Boolean indicating success
        """
        # Use requests to fetch the content
        try:
            headers = create_headers()
            response = await asyncio.to_thread(
                requests.get, url, headers=headers, timeout=10
            )
            response.raise_for_status()
            
            # Extract and clean text content
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Remove script and style elements
            for element in soup(["script", "style", "meta", "link"]):
                element.extract()
                
            # Get text content with preserved structure
            text_content = soup.get_text(separator="\n")
            
            # Remove excessive newlines
            text_content = "\n".join(line for line in text_content.split("\n") if line.strip())
            
            # Hash the new content
            new_hash = hash_text(text_content)
            
            # Check if file exists and compare content
            if os.path.isfile(output_path):
                existing_hash = hash_file(output_path)
                if existing_hash == new_hash:
                    logging.info(f"Text content is identical. Skipping: {output_path}")
                    return True
                else:
                    logging.info(f"Text content differs. Overwriting: {output_path}")
            
            # Save the new text
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text_content)
            logging.info(f"Saved text: {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save text for {url}: {e}")
            raise  # Re-raise for retry decorator