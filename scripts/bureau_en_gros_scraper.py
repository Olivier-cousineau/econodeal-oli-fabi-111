#!/usr/bin/env python3
"""Bureau en Gros clearance scraper.

Usage:
  python scripts/bureau_en_gros_scraper.py --url https://www.bureauengros.com/fr/clearance
  python scripts/bureau_en_gros_scraper.py --input fixtures/bureau_en_gros_liquidation.html

Outputs JSON and CSV files with normalized fields consumed by the landing page.
The scraper relies on JSON embedded in the page (e.g., Next.js `__NEXT_DATA__`).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


STORE_NAME = "Bureau en Gros"


@dataclass
class Product:
    name: str
    price: Optional[str]
    regular_price: Optional[str]
    product_url: Optional[str]
    image_url: Optional[str]
    category: Optional[str]
    availability: Optional[str]
    sku: Optional[str]
    store: str = STORE_NAME

    def to_mapping(self) -> Dict[str, Optional[str]]:
        return {
            "store": self.store,
            "category": self.category,
            "name": self.name,
            "price": self.price,
            "regular_price": self.regular_price,
            "product_url": self.product_url,
            "image_url": self.image_url,
            "sku": self.sku,
            "availability": self.availability,
        }


class BureauEnGrosScraper:
    def __init__(self, base_url: str = "https://www.bureauengros.com") -> None:
        self.base_url = base_url.rstrip("/")

    # --------------------------- HTTP / IO helpers ---------------------------
    def fetch_url(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (scraper)"})
        try:
            with urlopen(request, timeout=20) as resp:  # nosec: B310 - trusted target configured by user
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace")
        except HTTPError as exc:  # pragma: no cover - exercised only online
            raise RuntimeError(f"HTTP error {exc.code} for {url}") from exc
        except URLError as exc:  # pragma: no cover - exercised only online
            raise RuntimeError(f"Network error for {url}: {exc.reason}") from exc

    def load_source(self, url: Optional[str], input_path: Optional[Path]) -> str:
        if input_path:
            return Path(input_path).read_text(encoding="utf-8")
        if url:
            return self.fetch_url(url)
        raise ValueError("Provide either --url or --input")

    # -------------------------- Parsing / extraction -------------------------
    @staticmethod
    def _extract_json_strings(html: str) -> Iterable[str]:
        script_pattern = re.compile(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', re.S)
        next_data_pattern = re.compile(r"__NEXT_DATA__\s*=\s*({.*?})\s*<", re.S)
        preloaded_pattern = re.compile(r"__PRELOADED_STATE__\s*=\s*({.*?})\s*;", re.S)

        for regex in (script_pattern, next_data_pattern, preloaded_pattern):
            for match in regex.findall(html):
                yield match.strip()

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = re.sub(r"[^\d.,-]", "", value).replace(",", ".")
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _format_price(self, value: Any) -> Optional[str]:
        number = self._to_float(value)
        if number is None:
            return None
        return f"${number:.2f}"

    @staticmethod
    def _looks_like_product(obj: Any) -> bool:
        if not isinstance(obj, dict):
            return False
        has_name = any(k in obj for k in ("name", "title"))
        has_price = any(k in obj for k in ("salePrice", "offerPrice", "price", "currentPrice", "regularPrice", "listPrice"))
        return has_name and has_price

    def _find_product_nodes(self, obj: Any) -> Iterable[Dict[str, Any]]:
        if isinstance(obj, list):
            for item in obj:
                yield from self._find_product_nodes(item)
        elif isinstance(obj, dict):
            if self._looks_like_product(obj):
                yield obj
            for value in obj.values():
                yield from self._find_product_nodes(value)

    def _first_non_null(self, obj: Dict[str, Any], keys: Iterable[str]) -> Any:
        for key in keys:
            if key in obj and obj[key] not in (None, ""):
                return obj[key]
        return None

    def _normalize_product(self, raw: Dict[str, Any]) -> Optional[Product]:
        name = self._first_non_null(raw, ("name", "title"))
        if not name:
            return None

        price = self._format_price(self._first_non_null(raw, (
            "salePrice",
            "offerPrice",
            "price",
            "currentPrice",
            "activePrice",
        )))
        regular_price = self._format_price(self._first_non_null(raw, (
            "listPrice",
            "regularPrice",
            "wasPrice",
        )))

        sku = self._first_non_null(raw, ("sku", "id", "itemId", "partNumber"))
        product_url = self._first_non_null(raw, ("product_url", "productUrl", "url", "pdpUrl"))
        if isinstance(product_url, str) and product_url.startswith("/"):
            product_url = urljoin(self.base_url, product_url)

        image_candidates = self._first_non_null(raw, (
            "image",
            "imageUrl",
            "thumbnail",
            "primaryImage",
            "image_url",
            "images",
        ))
        image_url: Optional[str] = None
        if isinstance(image_candidates, list):
            image_url = image_candidates[0]
        else:
            image_url = image_candidates

        category = self._first_non_null(raw, ("category", "categoryPath", "categoryName"))
        if isinstance(category, list):
            category = " / ".join(str(c) for c in category)

        availability = self._first_non_null(raw, ("availability", "availabilityStatus", "stockMessage", "inventoryStatus"))

        return Product(
            name=str(name).strip(),
            price=price,
            regular_price=regular_price,
            product_url=product_url,
            image_url=image_url,
            category=category,
            availability=availability,
            sku=str(sku) if sku is not None else None,
        )

    def parse_products(self, html: str) -> List[Product]:
        products: List[Product] = []
        for block in self._extract_json_strings(html):
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue
            for raw in self._find_product_nodes(data):
                product = self._normalize_product(raw)
                if product:
                    products.append(product)

        # Deduplicate by SKU/name + price
        deduped: Dict[str, Product] = {}
        for item in products:
            key = item.sku or f"{item.name}|{item.price}"
            deduped[key] = item
        return list(deduped.values())

    # ------------------------------- Public API ------------------------------
    def scrape(self, url: Optional[str] = None, input_path: Optional[Path] = None) -> List[Product]:
        html = self.load_source(url=url, input_path=input_path)
        return self.parse_products(html)


def write_json(path: Path, products: List[Product]) -> None:
    payload = [p.to_mapping() for p in products]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, products: List[Product]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["store", "category", "name", "price", "regular_price", "product_url", "image_url", "sku", "availability"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for product in products:
            writer.writerow({k: v or "" for k, v in product.to_mapping().items()})


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape Bureau en Gros liquidation products.")
    parser.add_argument("--url", help="Page URL to scrape (liquidation / clearance).")
    parser.add_argument("--input", type=Path, help="Local HTML file to parse instead of fetching.")
    parser.add_argument("--json-out", type=Path, default=Path("data/bureau_en_gros_liquidations.json"), help="Path to write JSON output.")
    parser.add_argument("--csv-out", type=Path, default=Path("data/bureau_en_gros_liquidations.csv"), help="Path to write CSV output.")
    parser.add_argument("--base-url", default="https://www.bureauengros.com", help="Base URL used to resolve relative product links.")

    args = parser.parse_args(argv)
    scraper = BureauEnGrosScraper(base_url=args.base_url)

    products = scraper.scrape(url=args.url, input_path=args.input)
    if not products:
        print("No products extracted", file=sys.stderr)
        return 1

    write_json(args.json_out, products)
    write_csv(args.csv_out, products)

    print(f"Extracted {len(products)} products → {args.json_out} / {args.csv_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
