#!/usr/bin/env python3
"""
Product Matcher — Intelligent AH product search with scoring
==============================================================
Searches Albert Heijn for ingredients and scores candidates on relevance,
price efficiency, bonus status, quantity fit, nutriscore, and brand preference.

Features:
- Fuzzy string matching for better product resolution
- Brand preference scoring from preferences.json
- Product match caching (matched_products.json)
- Preference-aware filtering (avoid kipfilet, koriander, etc.)

Usage:
    python3 product_matcher.py "500g spaghetti"
    python3 product_matcher.py --ingredients ingredients.json
    python3 product_matcher.py --ingredients ingredients.json --json
"""

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from ah_api import AHApi


# ── Skip terms (reused from ah_koopknop.py) ─────────────
SKIP_TERMS = ["maaltijdmix", "honig mix", "babyvoeding", "aanbieding pakket", "mix pakket"]

# ── Pantry items (don't need to buy) ────────────────────
PANTRY_ITEMS = {
    "zout", "peper", "zwarte peper", "olijfolie", "olie", "boter",
    "suiker", "bloem", "bakpoeder", "kaneel", "paprikapoeder",
    "knoflookpoeder", "oregano", "basilicum", "tijm", "laurierblad",
    "azijn", "sojasaus", "ketjap", "sambal", "mosterd",
}

# ── Unit aliases for Dutch cooking terms ────────────────
UNIT_ALIASES = {
    "blik": {"g": 400},
    "blikje": {"g": 400},
    "bus": {"g": 400},
    "pak": {"g": 500},
    "zak": {"g": 500},
    "fles": {"ml": 500},
    "teentje": {"g": 3},
    "teentjes": {"g": 3},
    "teen": {"g": 3},
    "eetlepel": {"ml": 15},
    "el": {"ml": 15},
    "theelepel": {"ml": 5},
    "tl": {"ml": 5},
    "snuf": {"g": 1},
    "snufje": {"g": 1},
    "takje": {"g": 2},
    "takjes": {"g": 2},
    "plak": {"g": 20},
    "plakken": {"g": 20},
    "schijf": {"g": 30},
    "schijfje": {"g": 30},
    "hand": {"g": 30},
    "handvol": {"g": 30},
    "bosje": {"g": 25},
    "stuk": {"stuks": 1},
    "stuks": {"stuks": 1},
}

# ── Nutriscore points ──────────────────────────────────
NUTRISCORE_POINTS = {"A": 10, "B": 8, "C": 6, "D": 3, "E": 0}

# ── Cache file for previously matched products ─────────
CACHE_FILE = "matched_products.json"

# ── Preferences file ───────────────────────────────────
PREFERENCES_FILE = "preferences.json"


def load_preferences(path: str = PREFERENCES_FILE) -> dict:
    """Load user preferences from preferences.json. Returns empty dict if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_cache(path: str = CACHE_FILE) -> dict[str, dict]:
    """Load previously matched products from cache file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache: dict[str, dict], path: str = CACHE_FILE) -> None:
    """Save matched products cache to file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _get_avoid_terms(prefs: dict) -> list[str]:
    """Extract terms to avoid from preferences (protein + dietary)."""
    avoid = []
    protein_prefs = prefs.get("protein_preferences", {})
    avoid.extend(protein_prefs.get("avoid", []))
    dietary = prefs.get("dietary", {})
    avoid.extend(dietary.get("avoid_ingredients", []))
    return [t.lower() for t in avoid]


def _get_brand_scores(prefs: dict) -> dict[str, int]:
    """Extract brand preference scores from preferences."""
    brand_prefs = prefs.get("brand_preferences", {})
    return brand_prefs.get("brand_scores", {})


def parse_ingredient(text: str) -> dict:
    """
    Parse ingredient string like '500g spaghetti', '2 uien', '1 blik tomaten'.
    Returns {"item": str, "quantity": float, "unit": str}.
    """
    text = text.strip()

    # Try: "500g spaghetti", "200ml melk"
    m = re.match(r"(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l|cl|dl)\b\s+(.+)", text, re.IGNORECASE)
    if m:
        qty = float(m.group(1).replace(",", "."))
        unit = m.group(2).lower()
        item = m.group(3).strip()
        return {"item": item, "quantity": qty, "unit": unit}

    # Try: "2 blik tomaten", "1 teentje knoflook"
    m = re.match(r"(\d+(?:[.,]\d+)?)\s+(\w+)\s+(.+)", text, re.IGNORECASE)
    if m:
        qty = float(m.group(1).replace(",", "."))
        maybe_unit = m.group(2).lower()
        item = m.group(3).strip()
        if maybe_unit in UNIT_ALIASES:
            alias = UNIT_ALIASES[maybe_unit]
            real_unit = list(alias.keys())[0]
            real_qty = qty * alias[real_unit]
            return {"item": item, "quantity": real_qty, "unit": real_unit}
        # Not a known unit — it's part of the item name
        return {"item": f"{maybe_unit} {item}", "quantity": qty, "unit": "stuks"}

    # Try: "3 uien", "1 komkommer"
    m = re.match(r"(\d+(?:[.,]\d+)?)\s+(.+)", text, re.IGNORECASE)
    if m:
        qty = float(m.group(1).replace(",", "."))
        item = m.group(2).strip()
        return {"item": item, "quantity": qty, "unit": "stuks"}

    # Just a name
    return {"item": text, "quantity": 1, "unit": "stuks"}


def _parse_unit_size(unit_size: str) -> tuple[float, str]:
    """Parse unitSize like '500 g', '1 l', '6 stuks' into (value, unit)."""
    if not unit_size:
        return 0, ""
    m = re.match(r"(\d+(?:[.,]\d+)?)\s*(\w+)", unit_size.strip())
    if m:
        val = float(m.group(1).replace(",", "."))
        unit = m.group(2).lower()
        return val, unit
    return 0, ""


def _normalize_to_grams(qty: float, unit: str) -> float | None:
    """Convert quantity to grams for comparison. Returns None if not convertible."""
    unit = unit.lower()
    if unit in ("g", "gram"):
        return qty
    if unit in ("kg", "kilo"):
        return qty * 1000
    if unit in ("ml", "milliliter"):
        return qty  # ~1g per ml for most foods
    if unit in ("l", "liter"):
        return qty * 1000
    if unit in ("cl",):
        return qty * 10
    if unit in ("dl",):
        return qty * 100
    return None


def _fuzzy_similarity(s1: str, s2: str) -> float:
    """
    Calculate fuzzy similarity between two strings (0-1).
    Uses a combination of token overlap and character-level bigram similarity.
    """
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if not s1 or not s2:
        return 0.0

    # Token overlap component
    t1 = set(s1.split())
    t2 = set(s2.split())
    if t1 and t2:
        token_sim = len(t1 & t2) / max(len(t1), 1)
    else:
        token_sim = 0.0

    # Bigram similarity component (handles typos, partial matches)
    def bigrams(s: str) -> set[str]:
        return {s[i:i+2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}

    b1 = bigrams(s1.replace(" ", ""))
    b2 = bigrams(s2.replace(" ", ""))
    if b1 or b2:
        bigram_sim = 2 * len(b1 & b2) / (len(b1) + len(b2))
    else:
        bigram_sim = 0.0

    # Substring bonus: if query is contained in title
    substring_bonus = 0.3 if s1 in s2 else 0.0

    return min(1.0, token_sim * 0.5 + bigram_sim * 0.3 + substring_bonus * 0.2)


def _token_overlap(query: str, title: str) -> float:
    """Calculate token overlap score (0-1) between query and title."""
    q_tokens = set(query.lower().split())
    t_tokens = set(title.lower().split())
    if not q_tokens:
        return 0
    return len(q_tokens & t_tokens) / len(q_tokens)


def score_product(product: dict, query: str, needed_qty: float,
                  needed_unit: str, prefer_bonus: bool = True,
                  brand_scores: dict[str, int] | None = None) -> dict:
    """
    Score a product candidate (0-115 raw, normalized display).
    Returns dict with total score and breakdown.
    """
    title = product.get("title", "")
    brand = product.get("brand", "")
    scores = {}

    # 1. Relevance (30 pts) — fuzzy match (weighted: token overlap + bigram)
    fuzzy = _fuzzy_similarity(query, title)
    token = _token_overlap(query, title)
    relevance = max(fuzzy, token)
    scores["relevance"] = round(relevance * 30)

    # 2. Price efficiency (25 pts)
    unit_price_desc = product.get("unitPriceDescription", "")
    price_score = 12  # default middle score
    m = re.search(r"€?\s*(\d+[.,]\d+)", unit_price_desc)
    if m:
        unit_price = float(m.group(1).replace(",", "."))
        price_score = max(0, min(25, round(25 - unit_price * 2)))
    scores["price_efficiency"] = price_score

    # 3. Bonus (20 pts)
    if product.get("isBonus") and prefer_bonus:
        scores["bonus"] = 20
    else:
        scores["bonus"] = 0

    # 4. Quantity fit (15 pts)
    pkg_val, pkg_unit = _parse_unit_size(product.get("unitSize", ""))
    needed_g = _normalize_to_grams(needed_qty, needed_unit)
    pkg_g = _normalize_to_grams(pkg_val, pkg_unit)

    packs_needed = 1
    if needed_g and pkg_g and pkg_g > 0:
        packs_needed = max(1, math.ceil(needed_g / pkg_g))
        waste_ratio = (packs_needed * pkg_g - needed_g) / (packs_needed * pkg_g)
        scores["quantity_fit"] = round(15 * (1 - waste_ratio))
    elif needed_unit == "stuks":
        packs_needed = max(1, math.ceil(needed_qty))
        scores["quantity_fit"] = 10  # neutral
    else:
        scores["quantity_fit"] = 8  # can't compare, give middle-ish

    # 5. Nutriscore (10 pts)
    ns = product.get("nutriscore", "").upper()
    scores["nutriscore"] = NUTRISCORE_POINTS.get(ns, 5)

    # 6. Brand preference (15 pts bonus)
    scores["brand"] = 0
    if brand_scores and brand:
        for brand_name, brand_pts in brand_scores.items():
            if brand_name.lower() in brand.lower() or brand.lower() in brand_name.lower():
                scores["brand"] = min(15, brand_pts)
                break

    total = sum(scores.values())

    return {
        "score": total,
        "breakdown": scores,
        "packs_needed": packs_needed,
    }


def find_best_product(api: AHApi, item: str, quantity: float = 1,
                      unit: str = "stuks", prefer_bonus: bool = True,
                      prefs: dict | None = None,
                      use_cache: bool = True) -> dict | None:
    """
    Search AH for an ingredient and return the best scored match.
    Returns dict with product info + score, or None.

    Uses preferences for brand scoring and avoid-list filtering.
    Checks cache for previously matched products.
    """
    if prefs is None:
        prefs = load_preferences()

    # Check pantry
    if item.lower().strip() in PANTRY_ITEMS:
        return {"pantry": True, "item": item}

    avoid_terms = _get_avoid_terms(prefs)
    brand_scores = _get_brand_scores(prefs)

    # Check cache
    cache_key = f"{item.lower().strip()}|{quantity}|{unit}"
    if use_cache:
        cache = load_cache()
        if cache_key in cache:
            cached = cache[cache_key]
            # Return cached result if less than 7 days old (or no timestamp)
            return cached

    products = api.search(query=item, size=15)

    best = None
    best_score = -1

    for p in products:
        title = p.get("title", "").lower()

        # Skip bad matches
        if any(skip in title for skip in SKIP_TERMS):
            continue
        if not p.get("webshopId"):
            continue
        if not p.get("availableOnline", True):
            continue

        # Skip products containing avoided terms
        if any(avoid in title for avoid in avoid_terms):
            continue

        result = score_product(p, item, quantity, unit, prefer_bonus, brand_scores)

        if result["score"] > best_score:
            best_score = result["score"]
            best = {
                "webshopId": p["webshopId"],
                "title": p["title"],
                "brand": p.get("brand", ""),
                "price": p.get("price", 0),
                "bonusPrice": p.get("bonusPrice"),
                "isBonus": p.get("isBonus", False),
                "unitSize": p.get("unitSize", ""),
                "nutriscore": p.get("nutriscore", ""),
                "discountLabels": p.get("discountLabels", []),
                "score": result["score"],
                "breakdown": result["breakdown"],
                "packs_needed": result["packs_needed"],
                "query": item,
                "quantity": quantity,
                "unit": unit,
            }

    # Save to cache
    if best and use_cache:
        cache = load_cache()
        cache[cache_key] = best
        save_cache(cache)

    return best


def print_match(match: dict) -> None:
    """Print a single product match result."""
    if match.get("pantry"):
        print(f"  {match['item']} — pantry item (skip)")
        return

    bonus = " BONUS" if match.get("isBonus") else ""
    bp = match.get("bonusPrice")
    price_str = f"€{bp:.2f} (was €{match['price']:.2f})" if bp else f"€{match['price']:.2f}"
    packs = match["packs_needed"]
    packs_str = f" x{packs}" if packs > 1 else ""

    print(f"  {match['query']} -> {match['title']} [{match['unitSize']}]")
    print(f"    {price_str}{packs_str}{bonus} | score: {match['score']}/100")
    print(f"    breakdown: {match['breakdown']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product Matcher — Intelligent AH product search")
    parser.add_argument("ingredient", nargs="?", help="Single ingredient (e.g. '500g spaghetti')")
    parser.add_argument("--ingredients", help="JSON file with ingredients list")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-bonus", action="store_true", help="Don't prefer bonus products")
    parser.add_argument("--no-cache", action="store_true", help="Don't use product cache")
    args = parser.parse_args()

    if not args.ingredient and not args.ingredients:
        parser.print_help()
        sys.exit(1)

    api = AHApi()
    prefer_bonus = not args.no_bonus
    prefs = load_preferences()

    if args.ingredient:
        parsed = parse_ingredient(args.ingredient)
        match = find_best_product(api, parsed["item"], parsed["quantity"],
                                  parsed["unit"], prefer_bonus, prefs,
                                  use_cache=not args.no_cache)
        if args.json:
            json.dump(match, sys.stdout, indent=2, ensure_ascii=False)
            print()
        elif match:
            print_match(match)
        else:
            print(f"  No match found for: {args.ingredient}")

    elif args.ingredients:
        with open(args.ingredients, "r", encoding="utf-8") as f:
            data = json.load(f)

        ingredients = data if isinstance(data, list) else data.get("ingredients", [])
        results = []

        for ing in ingredients:
            if isinstance(ing, str):
                parsed = parse_ingredient(ing)
            else:
                parsed = {
                    "item": ing.get("item", ing.get("name", "")),
                    "quantity": ing.get("quantity", 1),
                    "unit": ing.get("unit", "stuks"),
                }

            match = find_best_product(api, parsed["item"], parsed["quantity"],
                                      parsed["unit"], prefer_bonus, prefs,
                                      use_cache=not args.no_cache)
            if match:
                results.append(match)
            else:
                results.append({"item": parsed["item"], "not_found": True})

        if args.json:
            json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            for r in results:
                if r.get("not_found"):
                    print(f"  {r['item']} — NOT FOUND")
                else:
                    print_match(r)
