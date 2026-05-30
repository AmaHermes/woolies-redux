#!/usr/bin/env python3
"""Dump one card's HTML to inspect structure."""
import time, re
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/127.0.0.0', viewport={'width': 1280, 'height': 800})
    page.goto('https://www.woolworths.co.za/cat/Food/Soup-Shop/_/N-1ass4io?Nrpp=60', timeout=45000, wait_until='domcontentloaded')
    page.wait_for_selector('.product-list__item', timeout=25000, state='attached')
    # Scroll to bottom to trigger lazy-loaded product links/images
    for _ in range(8):
        page.evaluate('window.scrollBy(0, 800)')
        time.sleep(0.4)
    time.sleep(2)
    h = page.content()
    # Check what classes/elements wrap product cards
    all_prods = list(re.finditer(r'href="(/prod/[^"]+/_/A-\d+)"', h))
    cards_class = re.findall(r'class="product-list__item"', h)
    print(f"\nproduct-list__item cards: {len(cards_class)}")
    print(f"total /prod/ A-id links: {len(all_prods)}")
    # Find the first product-list__item block
    m = re.search(r'<div class="product-list__item"', h)
    if m:
        # find matching closing tag by depth
        start = m.start()
        end = start + 7000  # just take 7KB
        print(f"\n--- First product-list__item block (7KB) ---")
        print(h[start:end][:6500])
    browser.close()
