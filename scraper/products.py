#!/usr/bin/env python3
"""
Scrape ALL Woolworths SA Food products via Playwright.

Strategy:
1. Visit each Food sub-category page (Pantry, Bakery, Frozen, Meat, etc.)
2. Wait for the PLP grid to render (JS-loaded after first paint)
3. Paginate through using ?No= offsets until exhausted
4. For each product card, extract: name, price, unit, image URL, PDP URL, SKU
5. Save incrementally to products.json — resumable

Polite: 1 worker, 2s pauses between pages, identifiable UA.
"""
import json, re, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "https://www.woolworths.co.za"
HERE = Path(__file__).parent
OUT = HERE / "products.json"
PROGRESS = HERE / "products_progress.json"
LOG = HERE / "products.log"

# Categories loaded from categories.json (produced by discover_categories.py)
def load_categories():
    cats_file = HERE / "categories.json"
    if not cats_file.exists():
        raise SystemExit(f"❌ Run discover_categories.py first to create {cats_file}")
    return json.loads(cats_file.read_text())

# Filter rules — what we DON'T want
SKIP_LABELS = {
    'Promotions',          # cross-category, duplicates everything
    'Toiletries & Health', # not food
    'Household', 'Cleaning', 'Pets', 'Baby', 'Kids',  # non-food departments
    'Gift Cards', 'Wine & Bubbles', 'Flowers & Plants',
    'Eid',                 # seasonal/promo, mostly dupes
    'Weekend Hosting', 'Easy Winter Meals',  # promo curations, dupes
    'Woolies Favourites Shop', 'Supper Club', 'Local Favourites',  # promo curations
    'Winter Desserts',     # tiny + seasonal
}
PAGE_SIZE = 60  # Woolies max per page


def load_existing():
    if OUT.exists():
        try:
            data = json.loads(OUT.read_text())
            return {p['sku']: p for p in data if p.get('sku')}
        except Exception:
            return {}
    return {}


def save(products_dict):
    OUT.write_text(json.dumps(list(products_dict.values()), indent=2, ensure_ascii=False))


def load_progress():
    if PROGRESS.exists():
        try: return json.loads(PROGRESS.read_text())
        except: pass
    return {"completed_categories": []}


def save_progress(p):
    PROGRESS.write_text(json.dumps(p, indent=2))


def extract_from_card(card_html):
    """Parse a single product-list__item div into a dict.

    Cards have clean data attributes via Constructor.io:
      data-cnstrc-item-id="6009245795065"
      data-cnstrc-item-name="Our Best Ever Beef Bourguignon Style Soup 1 kg"
      data-cnstrc-item-price="199.99"
    """
    sku_m = re.search(r'data-cnstrc-item-id="([^"]+)"', card_html)
    name_m = re.search(r'data-cnstrc-item-name="([^"]+)"', card_html)
    price_m = re.search(r'data-cnstrc-item-price="([^"]+)"', card_html)
    if not (sku_m and name_m): return None
    sku = sku_m.group(1)
    name = name_m.group(1).replace('&amp;', '&').strip()
    try:
        price = float(price_m.group(1)) if price_m else None
    except ValueError:
        price = None
    # Image: img with src=… and alt=…
    img_m = re.search(r'class="product-card__img[^"]*"\s+alt="[^"]+"\s*width', card_html) or \
            re.search(r'<img[^>]+class="product-card__img[^"]*"[^>]+src="([^"]+)"', card_html) or \
            re.search(r'<img[^>]+src="(https://assets\.woolworthsstatic[^"]+)"', card_html)
    image = None
    img_src = re.search(r'<img[^>]+(?:data-src|src)="(https://[^"]+\.jpg[^"]*)"', card_html)
    if img_src:
        # Strip ?V=… cache-buster optionally? keep full URL — Woolies CDN
        image = img_src.group(1).replace('&amp;', '&')
    # PDP URL
    pdp_m = re.search(r'href="(/prod/[^"?]+/_/A-' + re.escape(sku) + r')', card_html)
    pdp_url = (BASE + pdp_m.group(1)) if pdp_m else None
    # Unit/size from name (e.g. "1 kg", "600 g", "500 ml")
    unit_m = re.search(r'(\d+(?:\.\d+)?\s*(?:kg|g|ml|l|pk|pack))(?:\s|$)', name, re.I)
    unit = unit_m.group(1) if unit_m else None
    # Brand from alt text if available (e.g. "Woolies Brands Chicken…")
    brand = None
    brand_m = re.search(r'alt="(Woolies\s+Brands|[A-Z][A-Za-z\s&]+?)\s+' + re.escape(name[:20]), card_html)
    if brand_m: brand = brand_m.group(1).strip()
    return {
        'sku': sku, 'name': name, 'price': price,
        'unit': unit, 'image': image, 'pdp_url': pdp_url,
        'brand': brand,
    }


def scrape_category(page, cat_label, cat_path, products_dict, log):
    url_base = f"{BASE}/cat/{cat_path}"
    log_line = f"\n=== {cat_label} ==="
    print(log_line); log.write(log_line + "\n"); log.flush()
    offset = 0
    same_count_streak = 0
    while True:
        url = f"{url_base}?No={offset}&Nrpp={PAGE_SIZE}"
        try:
            page.goto(url, timeout=45000, wait_until='domcontentloaded')
            # Wait for product card divs to be in the DOM
            page.wait_for_selector('.product-list__item', timeout=25000, state='attached')
            # Scroll to trigger lazy-loaded /prod/ links inside the cards
            for _ in range(8):
                page.evaluate('window.scrollBy(0, 800)')
                time.sleep(0.3)
            time.sleep(1.5)
        except Exception as e:
            msg = f"  ⚠️ page timeout at offset {offset}: {e}"
            print(msg); log.write(msg + "\n")
            break

        # Grab the HTML and split into cards by the product-list__item wrapper
        html = page.content()
        # Find each <div class="product-list__item" ...> and take 5KB
        cards = []
        for m in re.finditer(r'<div class="product-list__item"\s+data-cnstrc-item-id', html):
            start = m.start()
            end = min(len(html), start + 5000)
            cards.append(html[start:end])

        added = 0
        for card_html in cards:
            p = extract_from_card(card_html)
            if p and p['sku'] not in products_dict:
                products_dict[p['sku']] = p
                added += 1
        msg = f"  page offset={offset}: {len(cards)} cards parsed, {added} new (total: {len(products_dict)})"
        print(msg); log.write(msg + "\n"); log.flush()

        if added == 0:
            same_count_streak += 1
            if same_count_streak >= 2:
                msg = f"  → no new products 2 pages in a row, moving on"
                print(msg); log.write(msg + "\n")
                break
        else:
            same_count_streak = 0

        offset += PAGE_SIZE
        if offset > 5000:  # safety cap per category
            print("  → hit 5000 cap"); break
        save(products_dict)  # checkpoint every page
        time.sleep(2)


def main():
    all_cats = load_categories()
    cats_to_scrape = [c for c in all_cats if c['label'] not in SKIP_LABELS]
    expected_total = sum(c['count'] or 0 for c in cats_to_scrape)
    progress = load_progress()
    products = load_existing()
    print(f"📦 Starting product scrape")
    print(f"   {len(cats_to_scrape)} categories to scan (~{expected_total} expected SKUs, dedupe will reduce)")
    print(f"   {len(products)} already cached | {len(progress['completed_categories'])} categories done")

    log = LOG.open("a")
    log.write(f"\n\n##### RUN {time.strftime('%Y-%m-%d %H:%M:%S')} #####\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
        )
        page = context.new_page()

        for cat in cats_to_scrape:
            label, path = cat['label'], cat['path']
            if label in progress['completed_categories']:
                print(f"⏭  {label} — already done")
                continue
            try:
                # path is like /cat/Food/Pantry/_/N-1lw4dzx — strip the leading /cat/
                cat_path = path.replace('/cat/', '', 1)
                scrape_category(page, label, cat_path, products, log)
                progress['completed_categories'].append(label)
                save_progress(progress)
                save(products)
            except KeyboardInterrupt:
                print("\n⚠️ interrupted"); break
            except Exception as e:
                msg = f"❌ {label} failed: {e}"
                print(msg); log.write(msg + "\n")

        browser.close()
        log.close()

    print(f"\n🎉 Done. {len(products)} unique products in {OUT}")


if __name__ == "__main__":
    main()
