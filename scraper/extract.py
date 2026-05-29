#!/usr/bin/env python3
"""
Extract structured recipe data from Woolworths SA recipe pages.

Reads discovered_ids.json, fetches each recipe HTML, parses out:
  - title, author, image, hero URL
  - ingredients (list with quantities)
  - cooking steps
  - "BUY THE INGREDIENTS" — exact Woolworths SKUs with names

Output: recipes.json (one big array)
"""
import json, re, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import warnings
from urllib3.exceptions import NotOpenSSLWarning
warnings.filterwarnings('ignore', category=NotOpenSSLWarning)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Install: /usr/bin/python3 -m pip install --user beautifulsoup4 lxml")
    sys.exit(1)

BASE = "https://www.woolworths.co.za"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/127.0.0.0',
}
HERE = Path(__file__).parent
IDS = HERE / "discovered_ids.json"
OUT = HERE / "recipes.json"
PROGRESS = HERE / "extract_progress.json"


def fetch(cmp_id):
    url = f"{BASE}/content/recipe/_/A-cmp{cmp_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        return r.text
    except Exception:
        return None


def extract(cmp_id, html):
    soup = BeautifulSoup(html, 'lxml')
    out = {'id': f'cmp{cmp_id}', 'source_url': f'{BASE}/content/recipe/_/A-cmp{cmp_id}'}

    # Title
    h1 = soup.find('h1')
    if not h1: return None
    out['title'] = h1.get_text(strip=True)
    if not out['title'] or 'Oh no' in out['title']: return None

    # Author — find "Recipe By" row in a table
    author = None
    for td in soup.find_all('td'):
        prev = td.find_previous('td')
        if prev and 'Recipe By' in prev.get_text():
            author = td.get_text(strip=True)
            break
    out['author'] = author

    # Hero image — og:image meta
    og = soup.find('meta', property='og:image')
    out['image'] = og['content'] if og and og.get('content') else None

    # Ingredients — list under <h3>INGREDIENTS</h3>
    ingredients = []
    for h3 in soup.find_all('h3'):
        if 'INGREDIENT' in h3.get_text().upper():
            ul = h3.find_next('ul')
            if ul:
                ingredients = [li.get_text(strip=True) for li in ul.find_all('li')]
            break
    out['ingredients'] = ingredients

    # Steps — list under <h3>COOKING INSTRUCTIONS</h3> (or similar)
    steps = []
    for h3 in soup.find_all('h3'):
        t = h3.get_text().upper()
        if 'COOKING' in t or 'METHOD' in t or 'DIRECTIONS' in t or 'INSTRUCTIONS' in t:
            # Walk through next siblings, collecting <ol>/<ul> items
            ol = h3.find_next(['ol', 'ul'])
            if ol:
                steps = [li.get_text(strip=True) for li in ol.find_all('li')]
            break
    out['steps'] = steps

    # BUY THE INGREDIENTS — Woolworths SKUs
    products = []
    # Find the section after "BUY THE INGREDIENTS"
    buy_marker = soup.find(string=re.compile(r'BUY\s+THE\s+INGREDIENTS', re.I))
    if buy_marker:
        # Walk forward looking for product links
        parent = buy_marker.parent
        # Search next 30 siblings/descendants for /p/ links
        scope = parent
        for _ in range(8):
            if scope.parent:
                scope = scope.parent
            else:
                break
        for a in scope.find_all('a', href=True):
            href = a['href']
            if '/p/' in href:
                name = a.get_text(strip=True)
                if name and len(name) > 2:
                    full = href if href.startswith('http') else BASE + href
                    products.append({'name': name, 'url': full})
        # Dedupe by URL
        seen = set()
        products = [p for p in products if not (p['url'] in seen or seen.add(p['url']))]
    out['woolies_products'] = products

    # Filter: must have actual ingredients to qualify as a recipe
    if not ingredients:
        return None
    if len(ingredients) < 2:
        return None

    return out


def process_id(cmp_id):
    html = fetch(cmp_id)
    if not html: return cmp_id, None
    try:
        return cmp_id, extract(cmp_id, html)
    except Exception as e:
        return cmp_id, {'_error': str(e)}


def load_existing_recipes():
    if OUT.exists():
        return {r['id']: r for r in json.loads(OUT.read_text())}
    return {}


def main():
    if not IDS.exists():
        print(f"❌ {IDS} not found — run discover.py first")
        sys.exit(1)
    ids_data = json.loads(IDS.read_text())
    all_ids = sorted(int(k) for k in ids_data['ids'].keys())
    print(f"📖 {len(all_ids)} discovered IDs to extract")

    existing = load_existing_recipes()
    todo = [i for i in all_ids if f'cmp{i}' not in existing]
    print(f"   {len(existing)} already extracted, {len(todo)} new")

    if not todo:
        print("✅ All extracted!")
        return

    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    recipes = list(existing.values())
    new_count = 0
    fail_count = 0

    try:
        chunk = 30
        for i in range(0, len(todo), chunk):
            batch = todo[i:i + chunk]
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(process_id, cid): cid for cid in batch}
                for fut in as_completed(futures):
                    cid, rec = fut.result()
                    if rec and '_error' not in rec:
                        recipes.append(rec)
                        new_count += 1
                        prods = len(rec.get('woolies_products', []))
                        print(f"  ✓ cmp{cid}: {rec['title'][:50]:<50} | {len(rec['ingredients'])} ings, {prods} SKUs")
                    else:
                        fail_count += 1
            # Save progress
            OUT.write_text(json.dumps(recipes, indent=2, ensure_ascii=False))
            print(f"  …{i+len(batch)}/{len(todo)} done | +{new_count} ok, {fail_count} skip | total recipes: {len(recipes)}")
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted, progress saved.")
    finally:
        OUT.write_text(json.dumps(recipes, indent=2, ensure_ascii=False))

    print(f"\n🎉 {len(recipes)} total recipes in {OUT}")
    print(f"   {new_count} new this run, {fail_count} skipped (no ingredients found)")


if __name__ == "__main__":
    main()
