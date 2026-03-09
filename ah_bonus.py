#!/usr/bin/env python3
"""
AH Bonus — Dump current Albert Heijn bonus/discount products
=============================================================
CLI tool that fetches all current AH bonus products and outputs them
in various formats for human or LLM consumption.

Usage:
    python3 ah_bonus.py                # Human-readable, grouped by category
    python3 ah_bonus.py --json         # Full JSON output
    python3 ah_bonus.py --summary      # Compact summary for LLM context
"""

import argparse
import json
import sys
from collections import defaultdict
from ah_api import AHApi


def fetch_bonus_products() -> list[dict]:
    """Fetch all current bonus products from AH."""
    api = AHApi()
    return api.get_all_bonus()


def _format_labels(labels: list) -> str:
    """Format discount labels (list of dicts or strings) into a string."""
    parts = []
    for lbl in labels:
        if isinstance(lbl, dict):
            parts.append(lbl.get("defaultDescription", ""))
        else:
            parts.append(str(lbl))
    return " | ".join(filter(None, parts))


def print_grouped(products: list[dict]):
    """Print bonus products grouped by main category (human-readable)."""
    by_category = defaultdict(list)
    for p in products:
        cat = p.get("mainCategory") or "Overig"
        by_category[cat].append(p)

    print(f"AH Bonus deze week: {len(products)} producten\n")

    for cat in sorted(by_category):
        items = by_category[cat]
        print(f"── {cat} ({len(items)}) ──")
        for p in items:
            title = p["title"]
            unit = p.get("unitSize", "")
            price = p.get("price", 0)
            bonus_price = p.get("bonusPrice")
            label_str = _format_labels(p.get("discountLabels", []))

            if bonus_price is not None:
                price_str = f"€{bonus_price:.2f} (was €{price:.2f})"
            elif label_str:
                price_str = f"€{price:.2f} {label_str}"
            else:
                price_str = f"€{price:.2f}"

            print(f"  {title} [{unit}] — {price_str}")
        print()


def print_summary(products: list[dict]):
    """Print compact summary for LLM context window."""
    by_category = defaultdict(list)
    for p in products:
        cat = p.get("mainCategory") or "Overig"
        by_category[cat].append(p)

    print(f"# AH Bonus deze week ({len(products)} producten)\n")

    for cat in sorted(by_category):
        items = by_category[cat]
        print(f"## {cat}")
        for p in items:
            title = p["title"]
            unit = p.get("unitSize", "")
            bonus_price = p.get("bonusPrice")
            price = p.get("price", 0)
            labels = p.get("discountLabels", [])

            parts = [title]
            if unit:
                parts.append(unit)

            if bonus_price is not None:
                parts.append(f"€{bonus_price:.2f} (was €{price:.2f})")
            elif labels:
                parts.append(f"€{price:.2f} {_format_labels(labels)}")
            else:
                parts.append(f"€{price:.2f}")

            if p.get("isStapelBonus"):
                parts.append("[stapelkorting]")

            print(f"- {' | '.join(parts)}")
        print()


def print_json(products: list[dict]):
    """Print full JSON output."""
    json.dump(products, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AH Bonus — Current discount products")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="Full JSON output")
    group.add_argument("--summary", action="store_true", help="Compact summary for LLM context")
    args = parser.parse_args()

    products = fetch_bonus_products()

    if args.json:
        print_json(products)
    elif args.summary:
        print_summary(products)
    else:
        print_grouped(products)
