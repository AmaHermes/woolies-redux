#!/usr/bin/env python3
"""Dump nav HTML to inspect structure."""
import time, re
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/127.0.0.0')
    page.goto('https://www.woolworths.co.za/cat/Food/_/N-1z13sk5', timeout=60000, wait_until='domcontentloaded')
    time.sleep(6)
    h = page.content()
    # find Pantry (1644) etc
    for kw in ['Pantry', 'Bakery', 'Frozen', 'Soup Shop', 'Promotions']:
        # locate the keyword and print 600 chars around it
        idx = h.find(kw)
        if idx > 0:
            print(f"\n=== {kw} (at {idx}) ===")
            print(h[max(0,idx-400):idx+400])
            print()
    browser.close()
