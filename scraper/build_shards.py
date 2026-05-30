#!/usr/bin/env python3
"""Shard products by L1 category, recipes alphabetically. Emit manifest.json."""
import json, os, re, hashlib
from urllib.parse import unquote
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'scraper')
OUT = os.path.join(ROOT, 'docs', 'data')

def slug(s):
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "other"

def derive_cat(p):
    url = p.get('pdp_url', '') or ''
    m = re.search(r'/prod/Food/([^/]+)/', url)
    if m:
        return unquote(m.group(1)).replace('-', ' ').strip()
    return 'Other'

def main():
    os.makedirs(os.path.join(OUT, 'products'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'recipes'), exist_ok=True)

    # --- PRODUCTS ---
    prods = json.load(open(os.path.join(SRC, 'products.json')))
    by_cat = defaultdict(list)
    for p in prods:
        cat = derive_cat(p)
        # Strip pdp_url to save bytes — derive from sku if needed
        slim = {
            's': p.get('sku'),
            'n': p.get('name'),
            'p': p.get('price'),
            'u': p.get('unit'),
            'i': p.get('image'),
            'b': p.get('brand'),
        }
        by_cat[cat].append(slim)

    prod_shards = []
    for cat, items in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        sl = slug(cat)
        path = os.path.join(OUT, 'products', f'{sl}.json')
        json.dump(items, open(path, 'w'), separators=(',', ':'), ensure_ascii=False)
        prod_shards.append({
            'cat': cat,
            'slug': sl,
            'file': f'data/products/{sl}.json',
            'count': len(items),
            'bytes': os.path.getsize(path),
        })

    # --- RECIPES (alpha buckets) ---
    recs = json.load(open(os.path.join(SRC, 'recipes.json')))
    BUCKETS = [
        ('a-c', lambda c: 'a' <= c <= 'c'),
        ('d-g', lambda c: 'd' <= c <= 'g'),
        ('h-l', lambda c: 'h' <= c <= 'l'),
        ('m-p', lambda c: 'm' <= c <= 'p'),
        ('q-s', lambda c: 'q' <= c <= 's'),
        ('t-z', lambda c: 't' <= c <= 'z'),
        ('other', lambda c: True),  # fallback
    ]
    by_bucket = defaultdict(list)
    for r in recs:
        title = (r.get('title') or '').strip().lower()
        first = title[:1] if title else ''
        bucket = 'other'
        for name, fn in BUCKETS[:-1]:
            if fn(first):
                bucket = name
                break
        slim = {
            'i': r.get('id'),
            't': r.get('title'),
            'a': r.get('author'),
            'im': r.get('image'),
            'ing': r.get('ingredients', []),
            'st': r.get('steps', []),
        }
        by_bucket[bucket].append(slim)

    rec_shards = []
    for bucket, items in by_bucket.items():
        path = os.path.join(OUT, 'recipes', f'{bucket}.json')
        json.dump(items, open(path, 'w'), separators=(',', ':'), ensure_ascii=False)
        rec_shards.append({
            'bucket': bucket,
            'file': f'data/recipes/{bucket}.json',
            'count': len(items),
            'bytes': os.path.getsize(path),
        })

    # --- MANIFEST ---
    manifest = {
        'version': '1',
        'generated': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
        'products': {
            'total': sum(s['count'] for s in prod_shards),
            'shards': prod_shards,
        },
        'recipes': {
            'total': sum(s['count'] for s in rec_shards),
            'shards': rec_shards,
        },
    }
    json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=2, ensure_ascii=False)

    # Summary
    print(f"Products: {manifest['products']['total']} across {len(prod_shards)} shards")
    print(f"Recipes:  {manifest['recipes']['total']} across {len(rec_shards)} shards")
    total_bytes = sum(s['bytes'] for s in prod_shards) + sum(s['bytes'] for s in rec_shards)
    print(f"Total payload: {total_bytes/1024:.1f} KB ({total_bytes/1024/1024:.2f} MB)")
    print(f"\nLargest product shards:")
    for s in sorted(prod_shards, key=lambda x: -x['bytes'])[:5]:
        print(f"  {s['bytes']/1024:>6.1f} KB  {s['count']:>4} items  {s['cat']}")
    print(f"\nRecipe buckets:")
    for s in rec_shards:
        print(f"  {s['bytes']/1024:>6.1f} KB  {s['count']:>4} items  {s['bucket']}")

if __name__ == '__main__':
    main()
