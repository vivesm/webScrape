import os
import re
import asyncio
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pyppeteer import launch

BASE_URL = "https://help.okta.com/wf/en-us/content/topics/workflows/execute/flow-api-endpoint.htm"
OUTPUT_DIR = "js_rendered_pdfs"

def get_links(url):
    """Return a set of help.okta.com links from a given page URL."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        links = {
            urljoin(url, a["href"])
            for a in soup.find_all("a", href=True)
            if "help.okta.com" in urljoin(url, a["href"])
        }
        return links
    except Exception as e:
        print(f"Failed to get links from {url}: {e}")
        return set()

def get_page_title(url):
    """Fetch the page title, sanitize it, and return."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        title = soup.title.string.strip() if soup.title else "untitled"
        # Replace illegal filename characters with underscores
        title = re.sub(r'[\\/*?:"<>|]', '_', title)
        # Limit length if desired
        return title[:80]
    except Exception as e:
        print(f"Failed to get page title from {url}: {e}")
        return "untitled"

async def save_as_pdf(page_url, output_path):
    """Render the page_url in a headless browser and save it as PDF."""
    try:
        browser = await launch(headless=True)
        page = await browser.newPage()
        await page.goto(page_url, {"waitUntil": "networkidle2"})
        await page.pdf({"path": output_path, "format": "A4"})
        await browser.close()
        print(f"Saved PDF: {output_path}")
    except Exception as e:
        print(f"Failed to save PDF for {page_url}: {e}")

async def scrape_3_levels(test_mode=False):
    """Scrape links up to 3 levels deep, optionally in test mode."""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Level 1
        first_level = get_links(BASE_URL)

        # Level 2
        second_level = set()
        for link1 in first_level:
            second_level |= get_links(link1)

        # Level 3
        third_level = set()
        for link2 in second_level:
            third_level |= get_links(link2)

        # Combine all links and remove duplicates
        all_links = list(first_level | second_level | third_level)

        # Generate PDFs with page titles as file names
        for i, link in enumerate(all_links, start=1):
            page_title = get_page_title(link)
            pdf_filename = f"{page_title}.pdf"
            pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

            print(f"Rendering: {link}")
            await save_as_pdf(link, pdf_path)

            # Break early if we're in test mode (only 1 PDF)
            if test_mode:
                break

            # 1-second delay between downloads
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error during scraping: {e}")

if __name__ == "__main__":
    # Pass True to run in test mode; otherwise pass False or omit
    asyncio.get_event_loop().run_until_complete(scrape_3_levels(test_mode=False))
