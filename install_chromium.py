#!/usr/bin/env python3
"""
Script to download and install Chromium for pyppeteer.
"""

import asyncio
from pyppeteer.chromium_downloader import download_chromium

print("Downloading Chromium for pyppeteer...")
download_chromium()
print("Chromium download complete.")