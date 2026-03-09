#!/usr/bin/env python3
"""
Meal Cart — Ingredients to AH Koopknop Cart URL
=================================================
Takes a JSON shopping list (as produced by the OpenClaw agent),
resolves all products via AH API with scoring, and builds the koopknop URL.

Usage:
    python3 meal_cart.py --ingredients shopping_list.json
    python3 meal_cart.py --ingredients shopping_list.json --save-plan plan.json
    python3 meal_cart.py --ingredients shopping_list.json --json

Input format:
    {
      "ingredients": [
        {"item": "spaghetti", "quantity": 500, "unit": "g"},
        {"item": "rundergehakt", "quantity": 500, "unit": "g"},
        {"item": "uien", "quantity": 3, "unit": "stuks"}
      ]
    }
"""

import argparse
import json
import sys
from ah_api import AHApi
from ah_koopknop import build_koopknop_url
from product_matcher import find_best_product, parse_ingredient


def resolve_ingredients(api: AHApi, ingredients: list[dict],
                        prefer_bonus: bool = True) -> dict:
    """
    Resolve a list of ingredients to AH products.
    Returns dict with matched products, pantry items, not found, and stats.
    """
    matched = []
    pantry = []
    not_found = []
    total_price = 0.0
    total_without_bonus = 0.0

    for ing in ingredients:
        if isinstance(ing, str):
            parsed = parse_ingredient(ing)
        else:
            parsed = {
                "item": ing.get("item", ing.get("name", "")),
                "quantity": ing.get("quantity", 1),
                "unit": ing.get("unit", "stuks"),
            }

        match = find_best_product(
            api, parsed["item"], parsed["quantity"], parsed["unit"], prefer_bonus
        )

        if not match:
            not_found.append(parsed["item"])
            continue

        if match.get("pantry"):
            pantry.append(match["item"])
            continue

        packs = match["packs_needed"]
        effective_price = match.get("bonusPrice") or match["price"]
        line_total = effective_price * packs
        regular_total = match["price"] * packs
        total_price += line_total
        total_without_bonus += regular_total

        matched.append(match)

    return {
        "matched": matched,
        "pantry": pantry,
        "not_found": not_found,
        "total_price": total_price,
        "total_without_bonus": total_without_bonus,
        "bonus_savings": total_without_bonus - total_price,
    }


def print_results(result: dict):
    """Print matched products and cart URL."""
    matched = result["matched"]
    pantry = result["pantry"]
    not_found = result["not_found"]

    print(f"Matched {len(matched)} products:\n")

    for m in matched:
        bonus = " BONUS" if m.get("isBonus") else ""
        bp = m.get("bonusPrice")
        price_str = f"€{bp:.2f} (was €{m['price']:.2f})" if bp else f"€{m['price']:.2f}"
        packs = m["packs_needed"]
        packs_str = f" x{packs}" if packs > 1 else ""
        print(f"  {m['query']} -> {m['title']} [{m['unitSize']}] {price_str}{packs_str}{bonus}")

    if pantry:
        print(f"\nPantry items (already at home): {', '.join(pantry)}")
    if not_found:
        print(f"\nNot found: {', '.join(not_found)}")

    print(f"\n{'─'*60}")
    print(f"Total: €{result['total_price']:.2f}")
    if result["bonus_savings"] > 0:
        print(f"Bonus savings: €{result['bonus_savings']:.2f}")
        print(f"Without bonus: €{result['total_without_bonus']:.2f}")

    # Build koopknop URL
    cart_items = []
    for m in matched:
        cart_items.append({
            "webshopId": m["webshopId"],
            "qty": m["packs_needed"],
        })

    if cart_items:
        url = build_koopknop_url(cart_items)
        print(f"\n{'─'*60}")
        print(f"Koopknop URL ({len(cart_items)} products):\n")
        print(url)
    else:
        print("\nNo products to add to cart.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meal Cart — Ingredients to AH cart URL")
    parser.add_argument("--ingredients", required=True, help="JSON file with ingredients")
    parser.add_argument("--save-plan", help="Save full plan with matches to JSON file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    with open(args.ingredients, "r", encoding="utf-8") as f:
        data = json.load(f)

    ingredients = data if isinstance(data, list) else data.get("ingredients", [])

    api = AHApi()
    result = resolve_ingredients(api, ingredients)

    if args.json:
        # Build URL for JSON output too
        cart_items = [{"webshopId": m["webshopId"], "qty": m["packs_needed"]}
                      for m in result["matched"]]
        output = {
            **result,
            "koopknop_url": build_koopknop_url(cart_items) if cart_items else None,
        }
        json.dump(output, sys.stdout, indent=2, ensure_ascii=False, default=str)
        print()
    else:
        print_results(result)

    if args.save_plan:
        cart_items = [{"webshopId": m["webshopId"], "qty": m["packs_needed"]}
                      for m in result["matched"]]
        plan = {
            **result,
            "koopknop_url": build_koopknop_url(cart_items) if cart_items else None,
        }
        with open(args.save_plan, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nPlan saved to: {args.save_plan}")
