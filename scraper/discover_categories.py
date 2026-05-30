#!/usr/bin/env python3
"""Discover Food category URLs by scraping the Food landing nav."""
import time, re, json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "categories.json"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/127.0.0.0')
    print("Loading /cat/Food...")
    page.goto('https://www.woolworths.co.za/cat/Food/_/N-1z13sk5', timeout=60000, wait_until='domcontentloaded')
    try:
        page.wait_for_selector('h4', timeout=20000)
    except Exception as e:
        print(f"warn: h4 wait timed out: {e}")
    time.sleep(5)
    h = page.content()
    # Extract <a href="..." >Label (count)</a>
    # Pattern: anchor with /cat/Food/SUBCAT/_/N-XXXX and the visible label text
    pattern = re.compile(r'class="nav-accordion__link"\s+href="([^"]+)">([^<]+?)\s*\((\d+)\)</a>')
    found = []
    seen = set()
    for m in pattern.finditer(h):
        href = m.group(1).replace('&amp;', '&').split('?')[0]
        label = m.group(2).replace('&amp;', '&').strip()
        count = int(m.group(3))
        if href in seen: continue
        seen.add(href)
        found.append({'path': href, 'label': label, 'count': count})
    print(f"\n📋 Found {len(found)} Food sub-categories:\n")
    for c in found:
        cnt = f"({c['count']})" if c['count'] else ""
        print(f"  {c['label']:<40} {cnt:>8}  {c['path']}")
    OUT.write_text(json.dumps(found, indent=2))
    print(f"\nSaved to {OUT}")
    browser.close()
