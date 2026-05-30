#!/usr/bin/env python3
"""One-off test: scrape Soup Shop only to verify extraction."""
import sys, json
sys.path.insert(0, '.')
from pathlib import Path
import products as P

# Override category list with just one
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/127.0.0.0',
        viewport={'width': 1280, 'height': 800},
    )
    page = ctx.new_page()
    products_dict = {}
    log = open('/tmp/test.log', 'w')
    P.scrape_category(page, 'Soup Shop', 'Food/Soup-Shop/_/N-1ass4io', products_dict, log)
    log.close()
    browser.close()

print(f"\n✅ Extracted {len(products_dict)} products")
print("\nFirst 5:")
for i, (sku, p) in enumerate(list(products_dict.items())[:5]):
    print(f"  {p['name'][:50]:<50} R{p['price']:.2f}  {p['unit']}  SKU={sku}")
    if p.get('image'): print(f"    img: {p['image'][:80]}")
