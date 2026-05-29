#!/bin/bash
# Full overnight scrape: discover IDs across cmp200000-cmp215000, then extract all.
cd ~/Projects/woolies-cookbook/scraper

echo "=== PHASE 1: DISCOVERY ==="
echo "Probing cmp200000–cmp215000 (15,000 IDs)…"
/usr/bin/python3 discover.py 200000 215000 4

echo ""
echo "=== PHASE 2: EXTRACTION ==="
/usr/bin/python3 extract.py 4

echo ""
echo "=== DONE ==="
echo "Recipes: $(jq length recipes.json)"
echo "IDs probed: 15000"
