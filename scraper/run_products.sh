#!/bin/bash
# Full product scrape — all Food categories, polite, resumable.
set -e
cd ~/Projects/woolies-cookbook/scraper

# Clear any half-done test run
rm -f products.json products_progress.json

echo "=== STARTED: $(date) ==="
/usr/bin/python3 products.py 2>&1
echo "=== FINISHED: $(date) ==="

PRODUCT_COUNT=$(/usr/bin/python3 -c "import json; print(len(json.load(open('products.json'))))")
echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ PRODUCTS SCRAPED: $PRODUCT_COUNT"
echo "═══════════════════════════════════════════"
