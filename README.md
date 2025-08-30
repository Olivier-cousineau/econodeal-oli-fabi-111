
# EconoDeal – Professional Landing (FR/EN)

Deploy-ready static site (GitHub Pages / Vercel).

## Features
- Bilingual UI (FR/EN) via simple toggle.
- Loads normalized data from `data/walmart_clean.json` and `data/toysrus_clean.json`.
- Filters: store, category, min % off, search.
- Links to **Amazon**, **eBay**, and **Keepa** searches for each product.
- RONA gallery page included in `pages/rona_gallery.html` (copied from your upload).

## Local Dev
Open `index.html` directly, or serve locally (recommended):
```bash
python -m http.server 8000
# then open http://localhost:8000
```

## GitHub Pages
1. Create a new repo (e.g., `econodeal-landing`).
2. Upload all files from this zip to the root of the repo.
3. Enable **Pages** (Settings → Pages → Deploy from branch → `main` / `/root`).
4. Your site will be live at `https://<user>.github.io/econodeal-landing/`.

## Keepa / Amazon API
- Current build uses **search links** (no API keys needed).
- To embed Keepa charts per product later, add an ASIN field to items and call your backend or Keepa API from the client; avoid exposing keys in the frontend.
