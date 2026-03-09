#!/usr/bin/env python3
"""
AH Koopknop — Albert Heijn Cart Automation via Deep Link
=========================================================
Uses the AH mobile API (via supermarktconnector) to search products,
then builds an add-multiple koopknop URL to add all items to cart at once.

Usage:
    python ah_koopknop.py                    # Use default items in config.json
    python ah_koopknop.py --items boodschappen.json  # Custom items file

How it works:
    1. Search AH product API for each item
    2. Get webshopId (numeric) for best match
    3. Build URL: https://www.ah.nl/mijnlijst/add-multiple?p=<id>:<qty>&p=<id>:<qty>
    4. Print URL (copy-paste in browser, or use browser relay)
"""

import json
import sys
import argparse
from supermarktconnector.ah import AHConnector


# ──────────────────────────────────────────
# Config
# ──────────────────────────────────────────

DEFAULT_ITEMS_FILE = "config.json"

# Terms to skip in product search results (bad matches)
SKIP_TERMS = ["maaltijdmix", "honig mix", "babyvoeding", "aanbieding pakket", "mix pakket"]


# ──────────────────────────────────────────
# Product search
# ──────────────────────────────────────────

def search_product(connector: AHConnector, query: str, size: int = 6) -> dict | None:
    """
    Search for a product and return the best match.
    Returns dict with webshopId, title, price, isBonus — or None if not found.
    """
    try:
        results = connector.search_products(query=query, size=size)
        products = results.get("products", [])

        for product in products:
            title = product.get("title", "").lower()

            # Skip bad matches
            if any(skip in title for skip in SKIP_TERMS):
                continue

            web_id = product.get("webshopId")
            if not web_id:
                continue

            return {
                "webshopId": str(web_id),
                "title": product.get("title", ""),
                "price": product.get("priceBeforeBonus") or product.get("price", 0),
                "isBonus": product.get("isBonus", False),
            }

        return None  # No suitable match found

    except Exception as e:
        print(f"   ⚠️  API error for '{query}': {e}")
        return None


# ──────────────────────────────────────────
# URL builder
# ──────────────────────────────────────────

def build_koopknop_url(items: list[dict]) -> str:
    """
    Build AH add-multiple koopknop URL.
    items: list of {"webshopId": "12345", "qty": 1}
    """
    params = "&".join(f"p={item['webshopId']}:{item['qty']}" for item in items)
    return f"https://www.ah.nl/mijnlijst/add-multiple?{params}"


# ──────────────────────────────────────────
# Main workflow
# ──────────────────────────────────────────

def run(items_file: str = DEFAULT_ITEMS_FILE):
    """Main workflow: search products, build URL, print result."""

    # Load items
    try:
        with open(items_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        items = config.get("items", [])
    except FileNotFoundError:
        print(f"❌ Items file not found: {items_file}")
        sys.exit(1)

    if not items:
        print("❌ No items found in config.")
        sys.exit(1)

    print(f"🛒 Searching AH for {len(items)} items...\n")

    connector = AHConnector()
    found = []
    not_found = []
    total_price = 0.0

    for item in items:
        name = item.get("name", "")
        qty = item.get("quantity", 1)

        result = search_product(connector, name)

        if result:
            bonus_tag = " 🏷️ BONUS" if result["isBonus"] else ""
            price = result["price"] * qty
            total_price += price
            print(f"   ✅ {name} → {result['title']} (€{result['price']:.2f} x{qty}){bonus_tag}")
            found.append({"webshopId": result["webshopId"], "qty": qty, "name": name})
        else:
            print(f"   ❌ {name} → NOT FOUND")
            not_found.append(name)

    print(f"\n{'─'*60}")
    print(f"✅ Found:     {len(found)}/{len(items)} items")
    print(f"❌ Not found: {len(not_found)} items" + (f": {', '.join(not_found)}" if not_found else ""))
    print(f"💶 Est. total: €{total_price:.2f}")

    if not found:
        print("\n❌ No items found, cannot build URL.")
        sys.exit(1)

    url = build_koopknop_url(found)

    print(f"\n{'─'*60}")
    print("🔗 Koopknop URL (click to add all items to cart):\n")
    print(url)
    print(f"\n💡 Open this URL in your AH browser (logged in) to add all {len(found)} items at once.")

    return url


# ──────────────────────────────────────────
# CLI
# ──────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AH Koopknop — Build add-to-cart URL from shopping list")
    parser.add_argument("--items", default=DEFAULT_ITEMS_FILE, help="Path to items JSON file (default: config.json)")
    args = parser.parse_args()

    run(items_file=args.items)
