#!/usr/bin/env python3
"""
Discover Woolworths SA recipe IDs.

Strategy: Woolies' /recipes is React-rendered, so we can't directly crawl an index.
BUT — each individual recipe page HAS the data inline. And recipe IDs follow a
predictable pattern: cmpNNNNNN (6-digit IDs from ~200000 to ~210000+).

We brute-force probe the ID space at a polite rate. For each ID that returns
a real recipe page (not 404), we record it. This is the cheapest + most
complete discovery method.

Output: ~/Projects/woolies-cookbook/scraper/discovered_ids.json
"""
import json, sys, time, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from urllib3.exceptions import NotOpenSSLWarning
import warnings
warnings.filterwarnings('ignore', category=NotOpenSSLWarning)

BASE = "https://www.woolworths.co.za"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
}
OUT = Path(__file__).parent / "discovered_ids.json"
LOG = Path(__file__).parent / "discover.log"


def probe(cmp_id: int):
    """Return (cmp_id, title) if it's a real recipe, else (cmp_id, None)."""
    # The slug doesn't matter — Woolies serves the recipe based on the trailing A-cmpNNNNNN.
    # We use a generic URL pattern that we know works.
    url = f"{BASE}/content/recipe/_/A-cmp{cmp_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            return cmp_id, None, r.status_code
        # Quick check: does this look like a recipe page?
        h = r.text
        # Quick check: does this look like a recipe page?
        # Valid recipes have <h1> with title + "recipeData" inline state.
        # 404s/dimension-search return 200 but no <h1>.
        if 'recipeData' not in h:
            return cmp_id, None, 'no_recipeData'
        import re
        m = re.search(r'<h1[^>]*>([^<]+)</h1>', h)
        if not m:
            return cmp_id, None, 'no_h1'
        title = m.group(1).strip()
        if not title or 'Oh no' in title or 'Moved' in title:
            return cmp_id, None, 'bad_title'
        # Final URL has the real slug
        final_url = r.url
        return cmp_id, title, final_url
    except Exception as e:
        return cmp_id, None, f"err:{type(e).__name__}"


def load_existing():
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {"ids": {}, "checked_range": []}


def save(state):
    OUT.write_text(json.dumps(state, indent=2))


def main():
    # Known good range from sitemap samples: 207000-208000+
    # Spread: cmp207873 (Easter eggs), cmp207519 (BBQ buns), cmp207693 (giant ribs), cmp207641 (lamb chops)
    # Probe a wider band to capture older + newer recipes
    state = load_existing()
    already = set(int(k) for k in state["ids"].keys())

    # Range to probe — start aggressive
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    end   = int(sys.argv[2]) if len(sys.argv) > 2 else 210000
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4  # be polite

    to_probe = [i for i in range(start, end + 1) if i not in already]
    print(f"📍 Probing IDs {start}–{end} ({len(to_probe)} new, {len(already)} already known)")
    print(f"   workers={workers}, polite delay between batches")

    found = 0
    checked = 0
    log_f = LOG.open("a")
    log_f.write(f"\n=== Run {time.strftime('%Y-%m-%d %H:%M:%S')} range={start}-{end} ===\n")

    try:
        # Process in chunks so we can save progress + sleep
        chunk_size = 50
        for i in range(0, len(to_probe), chunk_size):
            chunk = to_probe[i:i + chunk_size]
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(probe, cid): cid for cid in chunk}
                for fut in as_completed(futures):
                    cid, title, info = fut.result()
                    checked += 1
                    if title:
                        state["ids"][str(cid)] = {
                            "title": title,
                            "url": info if isinstance(info, str) and info.startswith('http') else None,
                            "found_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                        }
                        found += 1
                        msg = f"  ✓ cmp{cid}: {title[:60]}"
                        print(msg)
                        log_f.write(msg + "\n")
                        log_f.flush()
            # Save every chunk
            save(state)
            print(f"  …{checked}/{len(to_probe)} checked, {found} new found this run, {len(state['ids'])} total known. Sleeping 2s…")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted. Progress saved.")
    finally:
        save(state)
        log_f.close()

    print(f"\n🎉 Done. {len(state['ids'])} total recipes discovered.")
    print(f"   Output: {OUT}")


if __name__ == "__main__":
    main()
