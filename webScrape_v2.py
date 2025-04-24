import os
import re
import argparse
import asyncio
import logging
import requests
import hashlib
import tempfile
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pyppeteer import launch
from pyppeteer.errors import NetworkError
from asyncio.exceptions import InvalidStateError
from contextlib import suppress
import langdetect

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUTPUT_DIR = "output"
NAV_TIMEOUT_MS = 30_000   # 30 seconds (Pyppeteer uses milliseconds)

def filter_links(links):
    """
    Filter out unsupported or non-HTTP/HTTPS links.
    """
    valid_links = set()
    for link in links:
        if link.startswith("http://") or link.startswith("https://"):
            valid_links.add(link)
    return valid_links

def hash_file(file_path):
    """
    Calculate the SHA256 hash of a file for comparison.
    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        return None

def hash_bytes(data_bytes: bytes):
    """
    Hash raw byte content, e.g. for newly generated PDFs.
    """
    hasher = hashlib.sha256()
    hasher.update(data_bytes)
    return hasher.hexdigest()

def hash_text(text: str):
    """
    Hash text content.
    """
    hasher = hashlib.sha256()
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()

async def safe_browser_close(browser):
    """
    Try closing the browser gracefully with a short timeout,
    and force-kill if it gets stuck.
    """
    try:
        await asyncio.wait_for(browser.close(), timeout=10)
    except Exception:
        logging.warning("Forcibly terminating Chrome process.")
        if browser.process:
            browser.process.kill()

async def fetch_links_with_pyppeteer(url):
    """
    Use Pyppeteer to dynamically load the page and fetch links after dismissing cookie banners.
    """
    try:
        browser = await launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.newPage()
        page.setDefaultNavigationTimeout(NAV_TIMEOUT_MS)

        await page.goto(url, {"waitUntil": "domcontentloaded"})

        # Attempt to dismiss cookie banners if relevant
        try:
            await page.evaluate('''() => {
                const btns = [...document.querySelectorAll("button")];
                const acceptBtn = btns.find(b => b.innerText.includes("Accept"));
                if (acceptBtn) acceptBtn.click();
            }''')
            logging.info("Dismissed cookie banner.")
            await asyncio.sleep(1)
        except Exception as e:
            logging.warning(f"No cookie banner found or failed to dismiss it: {e}")

        # Extract all anchor tags
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        links = {
            urljoin(url, a["href"])
            for a in soup.find_all("a", href=True)
            if "#" not in a["href"]
        }

        await safe_browser_close(browser)

        links = filter_links(links)
        logging.info(f"Found {len(links)} links on {url}")
        return links
    except Exception as e:
        logging.error(f"Failed to fetch links from {url}: {e}")
        return set()

async def generate_pdf_bytes(page_url) -> bytes:
    """
    Generate PDF bytes from the given URL (no final file on disk).
    """
    browser = await launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
    pdf_bytes = b""
    try:
        page = await browser.newPage()
        page.setDefaultNavigationTimeout(NAV_TIMEOUT_MS)
        await page.goto(page_url, {"waitUntil": "domcontentloaded"})
        pdf_bytes = await page.pdf({"format": "A4"})
    except Exception as e:
        logging.error(f"Failed to generate PDF for {page_url}: {e}")
    finally:
        # Suppress noisy shutdown errors
        with suppress(InvalidStateError, NetworkError):
            await safe_browser_close(browser)

    return pdf_bytes

async def save_as_pdf(page_url, output_path):
    """
    Main function to handle the PDF creation with a timeout. 
    Compares PDF content if the file already exists.
    """
    try:
        await asyncio.wait_for(_save_pdf_with_comparison(page_url, output_path), timeout=40)
    except asyncio.TimeoutError:
        logging.error(f"Timeout while saving PDF for {page_url}. Skipping.")

async def _save_pdf_with_comparison(page_url, output_path):
    """
    Generate new PDF bytes, compare with existing file (if any),
    and only save if content is different.
    """
    # Generate PDF bytes in memory
    pdf_bytes = await generate_pdf_bytes(page_url)
    if not pdf_bytes:
        return  # Something went wrong

    new_hash = hash_bytes(pdf_bytes)

    # Check existing file
    if os.path.isfile(output_path):
        existing_hash = hash_file(output_path)
        if existing_hash == new_hash:
            logging.info(f"PDF content is identical. Skipping: {output_path}")
            return
        else:
            logging.info(f"PDF content differs. Overwriting: {output_path}")

    # If no file or hash differs, save the new PDF
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    logging.info(f"Saved PDF: {output_path}")

async def save_as_pdf_with_retry(page_url, output_path, retries=1):
    """
    Retry saving a PDF if it fails, but only once to skip quickly.
    """
    for attempt in range(retries):
        try:
            await save_as_pdf(page_url, output_path)
            return
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed for {page_url}: {e}")
    logging.error(f"Failed to save PDF after {retries} attempts: {page_url}")

def save_as_text_with_comparison(page_url, output_path, response=None):
    """
    Fetch page text content and compare with existing text if present.
    Optionally accepts a pre-fetched response object.
    """
    try:
        # Use provided response or fetch content
        if not response:
            response = requests.get(page_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
        
        new_text = response.text
        new_hash = hash_text(new_text)

        if os.path.isfile(output_path):
            existing_hash = hash_file(output_path)
            if existing_hash == new_hash:
                logging.info(f"Text content is identical. Skipping: {output_path}")
                return
            else:
                logging.info(f"Text content differs. Overwriting: {output_path}")

        # Save new text
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(new_text)
        logging.info(f"Saved text: {output_path}")

    except Exception as e:
        logging.error(f"Failed to save text for {page_url}: {e}")

async def process_link(sem, link, index, output_format, delay, language_filter=""):
    """
    Process a single link in PDF or text format with concurrency limiting.
    Includes language filtering if specified.
    """
    async with sem:
        # Generate a filename
        title_part = link.split("/")[-1][:50] or f"link-{index}"
        # Replace illegal filename characters
        title = re.sub(r'[\\/*?:"<>|]', "_", title_part)
        filename = f"{title}.{output_format}"
        output_path = os.path.join(OUTPUT_DIR, filename)

        logging.info(f"Processing {link} -> {output_path}")
        
        # If language filter is enabled, check content language first for text output
        if language_filter and output_format == "text":
            try:
                # Fetch content to detect language
                response = requests.get(link, headers=HEADERS, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Try to detect from HTML lang attribute first
                html_tag = soup.find('html')
                detected_lang = None
                
                if html_tag and html_tag.get('lang'):
                    # Extract the main language code from the lang attribute (e.g., 'en-US' -> 'en')
                    detected_lang = html_tag.get('lang').split('-')[0].lower()
                    logging.info(f"Language detected from HTML tag: {detected_lang}")
                
                # If no lang attribute or we need confirmation, detect from text content
                if not detected_lang or detected_lang != language_filter:
                    # Extract text for language detection
                    text_content = soup.get_text(separator=" ", strip=True)
                    if text_content:
                        # Only use a portion of the text for faster detection
                        sample_text = text_content[:1000]
                        detected_lang = detect_language(sample_text)
                        logging.info(f"Language detected from content: {detected_lang}")
                
                # Skip if language doesn't match the filter
                if detected_lang and detected_lang != language_filter:
                    logging.info(f"Skipping {link} because language '{detected_lang}' doesn't match filter '{language_filter}'")
                    return
                
                # If we couldn't detect the language but have a filter, process content anyway but warn
                if not detected_lang and language_filter:
                    logging.warning(f"Couldn't detect language for {link}, processing anyway with filter '{language_filter}'")
                
                # Save the content since we've already fetched it and it matches the filter
                save_as_text_with_comparison(link, output_path, response)
                
            except Exception as e:
                logging.error(f"Error checking language or processing {link}: {e}")
                return
        else:
            # Process without language filtering
            if output_format == "pdf":
                await save_as_pdf_with_retry(link, output_path)
            else:
                save_as_text_with_comparison(link, output_path)

        # Delay after processing
        await asyncio.sleep(delay)

def detect_language(text):
    """
    Detect the language of the provided text.
    Returns the language code (e.g., 'en', 'ja', etc.)
    """
    try:
        return langdetect.detect(text)
    except (langdetect.lang_detect_exception.LangDetectException, Exception) as e:
        logging.warning(f"Language detection failed: {e}")
        return None

async def scrape_section(base_url, output_format, test_mode=False, delay=1.0, test_count=2, language_filter=""):
    """
    Main scraping function: fetch links, process each, handle concurrency, etc.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        links = await fetch_links_with_pyppeteer(base_url)
        if not links:
            logging.warning("No links found. Exiting.")
            return

        # Log language filter if provided
        if language_filter:
            logging.info(f"Language filter enabled: Only processing content in '{language_filter}' language")

        if test_mode:
            # Process only a limited number of links in test mode
            test_links = list(links)[:test_count]
            logging.info(f"Test mode: Processing {len(test_links)} out of {len(links)} links")
            sem = asyncio.Semaphore(1)
            for i, link in enumerate(test_links, start=1):
                await process_link(sem, link, i, output_format, delay, language_filter)
            return

        sem = asyncio.Semaphore(2)
        tasks = [
            asyncio.ensure_future(process_link(sem, link, i, output_format, delay, language_filter))
            for i, link in enumerate(links, start=1)
        ]
        await asyncio.gather(*tasks)
    except Exception as e:
        logging.error(f"Error during scrape: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a section into PDFs or text files, with content comparison.")
    parser.add_argument("--base_url", default="https://docs.workato.com/projects.html", help="Base URL to scrape")
    parser.add_argument("--output_format", choices=["pdf", "text"], default="text", help="Output file format")
    parser.add_argument("--test", action="store_true", help="Test mode (process limited number of links)")
    parser.add_argument("--test_count", type=int, default=2, help="Number of pages to process in test mode")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay (in seconds) between downloads.")
    parser.add_argument("--language", type=str, default="", help="Filter content by language code (e.g., 'en' for English, 'ja' for Japanese, leave empty for all languages)")
    args = parser.parse_args()

    asyncio.get_event_loop().run_until_complete(
        scrape_section(args.base_url, args.output_format, args.test, args.delay, args.test_count, args.language)
    )
