import os
import re
import argparse
import asyncio
import logging
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pyppeteer import launch

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUTPUT_DIR = "output"
NAV_TIMEOUT_MS = 30_000   # 30 seconds (Pyppeteer uses milliseconds)

async def fetch_links_with_pyppeteer(url):
    """
    Use Pyppeteer to dynamically load the page and fetch links after dismissing cookie warnings.
    """
    try:
        browser = await launch(headless=True)
        page = await browser.newPage()
        # If setDefaultNavigationTimeout() is not async in your Pyppeteer install, remove await:
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
            logging.warning("No cookie banner found or failed to dismiss it: %s", e)

        # Extract all anchor tags
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        links = {
            urljoin(url, a["href"])
            for a in soup.find_all("a", href=True)
            if "#" not in a["href"]
        }
        await browser.close()

        logging.info(f"Found {len(links)} links on {url}")
        return links
    except Exception as e:
        logging.error(f"Failed to fetch links from {url}: {e}")
        return set()

async def save_as_pdf(page_url, output_path):
    """
    Render a page into a PDF using Pyppeteer, with a built-in timeout.
    """
    try:
        # We'll wrap in asyncio.wait_for to skip pages that get stuck
        await asyncio.wait_for(_save_as_pdf_task(page_url, output_path), timeout=40)
    except asyncio.TimeoutError:
        logging.error(f"Timeout while saving PDF for {page_url}. Skipping.")

async def _save_as_pdf_task(page_url, output_path):
    """
    Helper task for saving the PDF that can be awaited with a timeout.
    """
    browser = await launch(headless=True)
    try:
        page = await browser.newPage()
        # Again, remove 'await' if your Pyppeteer doesn't support it:
        page.setDefaultNavigationTimeout(NAV_TIMEOUT_MS)

        await page.goto(page_url, {"waitUntil": "networkidle2"})
        await page.pdf({"path": output_path, "format": "A4"})
        logging.info(f"Saved PDF: {output_path}")
    except Exception as e:
        logging.error(f"Failed to save PDF for {page_url}: {e}")
    finally:
        await browser.close()

def save_as_text(page_url, output_path):
    """
    Fetch a page and save its text content.
    """
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        text_content = soup.get_text(separator="\n")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        logging.info(f"Saved text: {output_path}")
    except Exception as e:
        logging.error(f"Failed to save text for {page_url}: {e}")

async def process_link(sem, link, index, output_format, delay):
    """
    Process a single link in PDF or text format,
    skipping if file already exists, then waiting for a delay.
    """
    async with sem:
        title = re.sub(r'[\\/*?:"<>|]', "_", link.split("/")[-1][:50]) or f"link-{index}"
        filename = f"{title}.{output_format}"
        output_path = os.path.join(OUTPUT_DIR, filename)

        if os.path.isfile(output_path):
            logging.info(f"Skipping existing file: {output_path}")
        else:
            logging.info(f"Processing {link} -> {output_path}")
            if output_format == "pdf":
                await save_as_pdf(link, output_path)
            else:
                save_as_text(link, output_path)
        
        # Delay after processing this link
        await asyncio.sleep(delay)

async def scrape_section(base_url, output_format, test_mode=False, delay=1.0):
    """
    Main scraping function to gather links and process them dynamically.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        links = await fetch_links_with_pyppeteer(base_url)
        if not links:
            logging.warning("No links found. Exiting.")
            return

        if test_mode:
            # Process only the first link
            first_link = next(iter(links))
            await process_link(asyncio.Semaphore(1), first_link, 1, output_format, delay)
            return

        # Use limited concurrency (e.g., 2) to avoid overwhelm
        sem = asyncio.Semaphore(2)
        tasks = [
            asyncio.ensure_future(process_link(sem, link, i, output_format, delay))
            for i, link in enumerate(links, start=1)
        ]
        await asyncio.gather(*tasks)
    except Exception as e:
        logging.error(f"Error during scrape: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a section into PDFs or text files.")
    parser.add_argument("--base_url", default="https://docs.workato.com/projects.html", help="Base URL to scrape")
    parser.add_argument("--output_format", choices=["pdf", "text"], default="pdf", help="Output file format")
    parser.add_argument("--test", action="store_true", help="Test mode (process only one link)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay (in seconds) between downloads.")
    args = parser.parse_args()

    asyncio.get_event_loop().run_until_complete(
        scrape_section(args.base_url, args.output_format, args.test, args.delay)
    )
