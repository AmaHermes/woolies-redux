# Woolies Cookbook 🍲🛒

A concept for a **future Woolies Dash app feature** — recipe-driven grocery shopping.

> *"You know what recipes you like for meals, so you know what ingredients you need.  
> Tap a dish → ingredients land in your Dash cart."*

## The pitch
Customers don't think in groceries — they think in **meals**. The current Dash app makes you build a cart item-by-item. This prototype reimagines the experience around the **cookbook**: save your favourite dishes once, then add their full ingredient list to your Dash cart with one tap.

**Why Woolies wins**: bigger basket sizes, higher conversion, stickier engagement. People come back to *plan their week*, not just refill staples.

## Prototype features
- 📖 **Recipe DB** — 10 SA-classic recipes pre-seeded; add your own. Persists in localStorage.
- 🔎 **Real search** — by recipe name, tag, *or ingredient* (e.g. search "chicken" → every recipe using it).
- 🧂 **Skip what you have** — tap an ingredient on the recipe screen to skip it before adding to cart.
- 🛒 **Cart aggregation** — when two recipes share an ingredient, the cart shows it once with a `×N` tag.
- ➕ **Add recipe form** — name, emoji, time, tags, ingredients (one per line).
- 📱 **Mobile-first** — designed as a phone app frame; full-screen on real mobile.

## Run it
```bash
open src/index.html
```

Or serve locally:
```bash
cd src && python3 -m http.server 8000
# → http://localhost:8000
```

## Stack
- Pure HTML/CSS/JS, single file, no build, no deps.
- localStorage for persistence.
- Inter from Google Fonts.

## Next moves
- Push `/src` to GitHub Pages (mirror the Solar Strike pattern).
- Real Woolies product API integration (price + SKU per ingredient → real basket value).
- "Plan my week" mode: drag 5 recipes onto Mon–Fri, get one weekly Dash order.
- Pantry tracker: skip ingredients you already own, system-wide.
- Share a cookbook with family members → merged shopping list.
