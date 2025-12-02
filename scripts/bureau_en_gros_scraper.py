#!/usr/bin/env python
import os
import csv
import json
import time
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

# URL de base pour les liquidations Bureau en Gros / Staples
# ⚠️ À ADAPTER si tu as une URL spécifique (magasin, langue, etc.)
BASE_URL = "https://www.staples.ca/a/search"

session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8",
        "Referer": "https://www.staples.ca/",
        "Connection": "keep-alive",
    }
)


def fetch_page(page: int, max_retries: int = 3, delay: int = 5) -> str:
    """Télécharge le HTML d'une page de liquidation."""
    params = {
        "language": "fr",
        "initiative": "clearance",
        "page": page,
    }

    last_status = None

    for attempt in range(1, max_retries + 1):
        print(f"[INFO] Fetch page {page} (attempt {attempt}/{max_retries})…")
        resp = session.get(BASE_URL, params=params, timeout=30)
        last_status = resp.status_code

        if resp.status_code == 200:
            return resp.text

        if resp.status_code in (403, 429):
            print(
                f"[WARN] HTTP {resp.status_code} on page {page}, retrying after {delay * attempt} s…"
            )
            time.sleep(delay * attempt)
            continue

        print(f"[ERROR] HTTP {resp.status_code} on page {page}: {resp.text[:300]}")
        return ""

    print(f"[ERROR] Blocked on page {page} with status {last_status} after {max_retries} attempts.")
    return ""


def normalize_price(text: str):
    """Nettoie un prix du type 'CA$ 19,99' -> 19.99 (float)."""
    if not text:
        return None
    text = text.replace("CA$", "").replace("$", "")
    text = text.replace(" ", "").replace("\u00a0", "")
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_products(html: str) -> List[Dict]:
    """Parse le HTML et extrait les produits de liquidation."""
    soup = BeautifulSoup(html, "html.parser")

    tiles = soup.select("div.product-tile.js-product-tile")
    products: List[Dict] = []

    for tile in tiles:
        # Titre
        title_el = tile.select_one(".product-tile__title")
        title = title_el.get_text(strip=True) if title_el else ""

        # Lien produit
        link_el = tile.select_one("a.product-tile__image-link, a.product-tile__title-link")
        url = link_el["href"] if link_el and link_el.has_attr("href") else ""

        # Prix actuel
        price_el = tile.select_one(".product-pricing__price")
        price_text = price_el.get_text(strip=True) if price_el else ""
        current_price = normalize_price(price_text)

        # Prix original (barré)
        original_el = tile.select_one(
            ".product-pricing__list-price, .product-pricing__original-price"
        )
        original_text = original_el.get_text(strip=True) if original_el else ""
        original_price = normalize_price(original_text)

        # SKU
        sku_el = tile.select_one("[data-product-sku]")
        sku = sku_el["data-product-sku"] if sku_el and sku_el.has_attr("data-product-sku") else ""

        # Image
        img_el = tile.select_one("img.product-tile__image")
        image_url = img_el["src"] if img_el and img_el.has_attr("src") else ""

        # Rabais %
        discount_percent = None
        if original_price and current_price and original_price > 0:
            discount_percent = round((1 - current_price / original_price) * 100, 2)

        products.append(
            {
                "title": title,
                "url": url,
                "sku": sku,
                "current_price": current_price,
                "original_price": original_price,
                "discount_percent": discount_percent,
                "image_url": image_url,
            }
        )

    print(f"[INFO] Parsed {len(products)} products on page")
    return products


def scrape_all_pages(max_pages: int = 20, delay: float = 1.5) -> List[Dict]:
    """Scrape plusieurs pages jusqu'à ce qu'il n'y ait plus de produits."""
    all_products: List[Dict] = []

    for page in range(1, max_pages + 1):
        print(f"[INFO] Scraping page {page}/{max_pages}")
        html = fetch_page(page)

        if not html:
            print(f"[WARN] Empty or blocked page at {page}, stopping pagination.")
            break

        products = parse_products(html)

        if not products:
            print(f"[INFO] No products found on page {page}, stopping pagination.")
            break

        print(f"[INFO] Found {len(products)} products on page {page}")
        all_products.extend(products)
        time.sleep(delay)

    print(f"[INFO] Total products scraped: {len(all_products)}")
    return all_products


def save_outputs(products: List[Dict], output_dir: str = "artifacts"):
    """Sauvegarde les résultats en JSON et CSV dans artifacts/."""
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "bureau_en_gros_liquidations.json")
    csv_path = os.path.join(output_dir, "bureau_en_gros_liquidations.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    if products:
        fieldnames = list(products[0].keys())
    else:
        fieldnames = [
            "title",
            "url",
            "sku",
            "current_price",
            "original_price",
            "discount_percent",
            "image_url",
        ]

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in products:
            writer.writerow(p)

    print(f"[INFO] Saved JSON -> {json_path}")
    print(f"[INFO] Saved CSV  -> {csv_path}")


def main():
    max_pages_env = os.getenv("BUREAU_EN_GROS_MAX_PAGES")
    max_pages = int(max_pages_env) if max_pages_env else 20

    products = scrape_all_pages(max_pages=max_pages)
    save_outputs(products)


if __name__ == "__main__":
    main()
