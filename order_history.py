#!/usr/bin/env python3
"""Order history tracking -- what was ordered, when, and spending trends."""

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

HISTORY_FILE = "order_history.json"


def load_history(path: str = HISTORY_FILE) -> list[dict]:
    """Load order history from JSON. Returns empty list if file doesn't exist.

    Args:
        path: Path to the history JSON file.

    Returns:
        List of order dicts, each with keys: date, items, total,
        bonus_savings, notes.
    """
    p = Path(path)
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return data.get("orders", [])
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history: list[dict], path: str = HISTORY_FILE) -> None:
    """Save order history to JSON.

    Args:
        history: List of order dicts to save.
        path: Path to write the history JSON file.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False, default=str)


def add_order(
    items: list[dict],
    total: float,
    bonus_savings: float = 0,
    notes: str = "",
    path: str = HISTORY_FILE,
) -> dict:
    """Add a new order to history. Returns the new order entry.

    Each order is stored as:
    {
        "date": "2026-03-23",
        "items": [{"name": "...", "price": 1.99, "quantity": 1, "is_bonus": false}],
        "total": 45.50,
        "bonus_savings": 5.20,
        "notes": ""
    }

    Args:
        items: List of item dicts with name, price, quantity, is_bonus.
        total: Total order amount in euros.
        bonus_savings: Amount saved via bonus deals.
        notes: Optional notes about the order.
        path: Path to the history JSON file.

    Returns:
        The newly created order dict.
    """
    history = load_history(path)

    order = {
        "date": date.today().isoformat(),
        "items": [
            {
                "name": item.get("name", item.get("title", "")),
                "price": item.get("price", 0),
                "quantity": item.get("quantity", item.get("qty", 1)),
                "is_bonus": item.get("is_bonus", item.get("isBonus", False)),
            }
            for item in items
        ],
        "total": round(total, 2),
        "bonus_savings": round(bonus_savings, 2),
        "notes": notes,
    }

    history.append(order)
    save_history(history, path)
    return order


def _parse_order_date(order: dict) -> date:
    """Parse the date from an order dict.

    Handles ISO format strings and already-parsed date objects.

    Args:
        order: Order dict with a 'date' key.

    Returns:
        A date object.
    """
    d = order.get("date", "")
    if isinstance(d, date):
        return d
    try:
        return date.fromisoformat(str(d)[:10])
    except (ValueError, TypeError):
        return date.today()


def get_spending_trend(history: list[dict], weeks: int = 8) -> list[dict]:
    """Get weekly spending over last N weeks.

    Groups orders by ISO week and returns spending per week.

    Args:
        history: List of order dicts.
        weeks: Number of weeks to look back (default 8).

    Returns:
        List of dicts with keys: week_start, week_end, total, bonus_savings,
        order_count, sorted chronologically.
    """
    if not history:
        return []

    cutoff = date.today() - timedelta(weeks=weeks)
    weekly: dict[str, dict] = {}

    for order in history:
        order_date = _parse_order_date(order)
        if order_date < cutoff:
            continue

        # Get ISO week start (Monday)
        week_start = order_date - timedelta(days=order_date.weekday())
        week_key = week_start.isoformat()

        if week_key not in weekly:
            weekly[week_key] = {
                "week_start": week_start.isoformat(),
                "week_end": (week_start + timedelta(days=6)).isoformat(),
                "total": 0.0,
                "bonus_savings": 0.0,
                "order_count": 0,
            }

        weekly[week_key]["total"] += order.get("total", 0)
        weekly[week_key]["bonus_savings"] += order.get("bonus_savings", 0)
        weekly[week_key]["order_count"] += 1

    # Round totals
    for w in weekly.values():
        w["total"] = round(w["total"], 2)
        w["bonus_savings"] = round(w["bonus_savings"], 2)

    return sorted(weekly.values(), key=lambda w: w["week_start"])


def get_most_bought(history: list[dict], top_n: int = 15) -> list[dict]:
    """Get most frequently bought items.

    Counts how many orders each item appears in (not total quantity).

    Args:
        history: List of order dicts.
        top_n: Number of top items to return (default 15).

    Returns:
        List of dicts with keys: name, count, total_quantity, total_spent,
        avg_price, bonus_pct, sorted by count descending.
    """
    item_stats: dict[str, dict] = {}

    for order in history:
        seen_in_order: set[str] = set()
        for item in order.get("items", []):
            name = item.get("name", "").lower().strip()
            if not name:
                continue

            if name not in item_stats:
                item_stats[name] = {
                    "name": name,
                    "count": 0,
                    "total_quantity": 0,
                    "total_spent": 0.0,
                    "bonus_count": 0,
                }

            qty = item.get("quantity", 1)
            price = item.get("price", 0)
            is_bonus = item.get("is_bonus", False)

            if name not in seen_in_order:
                item_stats[name]["count"] += 1
                seen_in_order.add(name)

            item_stats[name]["total_quantity"] += qty
            item_stats[name]["total_spent"] += price * qty
            if is_bonus:
                item_stats[name]["bonus_count"] += 1

    results = []
    for stats in item_stats.values():
        count = stats["count"]
        results.append({
            "name": stats["name"],
            "count": count,
            "total_quantity": stats["total_quantity"],
            "total_spent": round(stats["total_spent"], 2),
            "avg_price": round(stats["total_spent"] / max(stats["total_quantity"], 1), 2),
            "bonus_pct": round(stats["bonus_count"] / max(count, 1) * 100),
        })

    results.sort(key=lambda x: x["count"], reverse=True)
    return results[:top_n]


def get_average_weekly_spend(history: list[dict]) -> float:
    """Calculate average weekly spend.

    Determines the span from the first to the last order and divides
    total spending by the number of weeks in that span.

    Args:
        history: List of order dicts.

    Returns:
        Average weekly spend in euros. Returns 0.0 if no history.
    """
    if not history:
        return 0.0

    dates = [_parse_order_date(o) for o in history]
    totals = [o.get("total", 0) for o in history]

    min_date = min(dates)
    max_date = max(dates)
    total_spent = sum(totals)

    span_days = (max_date - min_date).days
    if span_days <= 0:
        return round(total_spent, 2)

    weeks = max(span_days / 7, 1)
    return round(total_spent / weeks, 2)


def detect_low_stock(
    history: list[dict], frequency_threshold: float = 0.7
) -> list[str]:
    """Detect items that are bought frequently and may be running low.

    If an item appears in more than frequency_threshold fraction of all
    orders, it is considered a staple that should be restocked.

    Args:
        history: List of order dicts.
        frequency_threshold: Fraction of orders an item must appear in
                            to be considered a staple (default 0.7 = 70%).

    Returns:
        List of item names that appear in more than the threshold
        percentage of orders, sorted by frequency descending.
    """
    if not history:
        return []

    total_orders = len(history)
    item_order_count: Counter[str] = Counter()

    for order in history:
        seen: set[str] = set()
        for item in order.get("items", []):
            name = item.get("name", "").lower().strip()
            if name and name not in seen:
                item_order_count[name] += 1
                seen.add(name)

    staples = [
        name
        for name, count in item_order_count.most_common()
        if count / total_orders >= frequency_threshold
    ]

    return staples


def format_history_summary(history: list[dict]) -> str:
    """Format order history summary for display.

    Includes total orders, spending stats, top items, and low-stock alerts.

    Args:
        history: List of order dicts.

    Returns:
        Formatted summary string.
    """
    if not history:
        return "Geen bestelgeschiedenis gevonden."

    lines: list[str] = []
    lines.append(f"Bestelgeschiedenis: {len(history)} bestellingen\n")

    # Date range
    dates = [_parse_order_date(o) for o in history]
    lines.append(f"Periode: {min(dates).isoformat()} tot {max(dates).isoformat()}")

    # Total spending
    total_spent = sum(o.get("total", 0) for o in history)
    total_bonus = sum(o.get("bonus_savings", 0) for o in history)
    lines.append(f"Totaal uitgegeven: EUR {total_spent:.2f}")
    if total_bonus > 0:
        lines.append(f"Totaal bonusbesparing: EUR {total_bonus:.2f}")

    # Average weekly spend
    avg_weekly = get_average_weekly_spend(history)
    lines.append(f"Gemiddeld per week: EUR {avg_weekly:.2f}")

    # Spending trend (last 8 weeks)
    trend = get_spending_trend(history, weeks=8)
    if trend:
        lines.append(f"\nUitgaven per week (laatste {len(trend)} weken):")
        for week in trend:
            bonus_str = ""
            if week["bonus_savings"] > 0:
                bonus_str = f" (bonus: EUR {week['bonus_savings']:.2f})"
            lines.append(
                f"  {week['week_start']} - {week['week_end']}: "
                f"EUR {week['total']:.2f}{bonus_str} "
                f"({week['order_count']} bestelling(en))"
            )

    # Top items
    top = get_most_bought(history, top_n=10)
    if top:
        lines.append(f"\nMeest gekocht (top {len(top)}):")
        for item in top:
            bonus_str = f" ({item['bonus_pct']}% bonus)" if item["bonus_pct"] > 0 else ""
            lines.append(
                f"  {item['name']}: {item['count']}x besteld, "
                f"EUR {item['avg_price']:.2f} gem. prijs{bonus_str}"
            )

    # Low stock alerts
    low_stock = detect_low_stock(history)
    if low_stock:
        lines.append(f"\nMogelijk bijna op (koop je bijna elke keer):")
        for name in low_stock:
            lines.append(f"  - {name}")

    return "\n".join(lines)


def _load_items_from_file(path: str) -> tuple[list[dict], float, float]:
    """Load items from a JSON file for adding to history.

    Supports multiple formats:
    - meal_cart output: {"matched": [...], "total_price": X, "bonus_savings": Y}
    - Simple list: [{"name": "...", "price": X, "quantity": N}]
    - Config format: {"items": [...]}

    Args:
        path: Path to JSON file with items.

    Returns:
        Tuple of (items, total, bonus_savings).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        items = data
        total = sum(
            i.get("price", 0) * i.get("quantity", 1) for i in items
        )
        return items, total, 0.0

    # meal_cart / product_matcher output
    if "matched" in data:
        items = []
        for m in data["matched"]:
            items.append({
                "name": m.get("title", m.get("query", "")),
                "price": m.get("bonusPrice") or m.get("price", 0),
                "quantity": m.get("packs_needed", 1),
                "is_bonus": m.get("isBonus", False),
            })
        return (
            items,
            data.get("total_price", sum(i["price"] * i["quantity"] for i in items)),
            data.get("bonus_savings", 0),
        )

    # Config format
    if "items" in data:
        items = data["items"]
        total = sum(
            i.get("price", 0) * i.get("quantity", 1) for i in items
        )
        return items, total, 0.0

    return [], 0.0, 0.0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Order history tracking and spending trends"
    )
    parser.add_argument(
        "--add", metavar="FILE",
        help="Add order from JSON file (meal_cart output or item list)",
    )
    parser.add_argument(
        "--notes", default="", help="Notes for the order (use with --add)",
    )
    parser.add_argument(
        "--trend", action="store_true", help="Show weekly spending trend",
    )
    parser.add_argument(
        "--weeks", type=int, default=8,
        help="Number of weeks for trend (default 8)",
    )
    parser.add_argument(
        "--top", action="store_true", help="Show most bought items",
    )
    parser.add_argument(
        "--top-n", type=int, default=15,
        help="Number of top items to show (default 15)",
    )
    parser.add_argument(
        "--low-stock", action="store_true",
        help="Show items that may be running low",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.7,
        help="Frequency threshold for low-stock detection (default 0.7)",
    )
    parser.add_argument(
        "--summary", action="store_true", help="Show full history summary",
    )
    parser.add_argument(
        "--history-file", default=HISTORY_FILE,
        help=f"Path to history file (default {HISTORY_FILE})",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    history_path = args.history_file

    # Add order
    if args.add:
        try:
            items, total, bonus_savings = _load_items_from_file(args.add)
        except FileNotFoundError:
            print(f"Error: file not found: {args.add}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in {args.add}: {e}", file=sys.stderr)
            sys.exit(1)

        if not items:
            print("Error: no items found in file", file=sys.stderr)
            sys.exit(1)

        order = add_order(items, total, bonus_savings, args.notes, history_path)

        if args.json:
            json.dump(order, sys.stdout, indent=2, ensure_ascii=False, default=str)
            print()
        else:
            print(f"Bestelling toegevoegd: {len(order['items'])} producten, "
                  f"EUR {order['total']:.2f}")
            if order["bonus_savings"] > 0:
                print(f"Bonusbesparing: EUR {order['bonus_savings']:.2f}")
        sys.exit(0)

    history = load_history(history_path)

    if not history and not args.add:
        print("Geen bestelgeschiedenis gevonden.", file=sys.stderr)
        print(
            f"Gebruik --add FILE om een bestelling toe te voegen aan {history_path}.",
            file=sys.stderr,
        )
        sys.exit(0)

    # Spending trend
    if args.trend:
        trend = get_spending_trend(history, weeks=args.weeks)
        if args.json:
            json.dump(trend, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            if not trend:
                print("Geen bestellingen in de afgelopen weken.")
            else:
                print(f"Uitgaven per week (laatste {args.weeks} weken):\n")
                for week in trend:
                    bonus_str = ""
                    if week["bonus_savings"] > 0:
                        bonus_str = f" (bonus: EUR {week['bonus_savings']:.2f})"
                    print(
                        f"  {week['week_start']} - {week['week_end']}: "
                        f"EUR {week['total']:.2f}{bonus_str} "
                        f"({week['order_count']} bestelling(en))"
                    )
        sys.exit(0)

    # Top items
    if args.top:
        top = get_most_bought(history, top_n=args.top_n)
        if args.json:
            json.dump(top, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            print(f"Meest gekocht (top {args.top_n}):\n")
            for i, item in enumerate(top, 1):
                bonus_str = f" ({item['bonus_pct']}% bonus)" if item["bonus_pct"] > 0 else ""
                print(
                    f"  {i:2}. {item['name']}: {item['count']}x besteld, "
                    f"{item['total_quantity']} stuks, "
                    f"EUR {item['avg_price']:.2f} gem.{bonus_str}"
                )
        sys.exit(0)

    # Low stock
    if args.low_stock:
        low_stock = detect_low_stock(history, frequency_threshold=args.threshold)
        if args.json:
            json.dump(low_stock, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            if not low_stock:
                print("Geen producten gevonden die mogelijk bijna op zijn.")
            else:
                print(
                    f"Producten in >{args.threshold * 100:.0f}% van bestellingen "
                    f"(mogelijk bijna op):\n"
                )
                for name in low_stock:
                    print(f"  - {name}")
        sys.exit(0)

    # Default: full summary
    if args.summary or not any([args.trend, args.top, args.low_stock, args.add]):
        if args.json:
            summary_data = {
                "total_orders": len(history),
                "total_spent": round(sum(o.get("total", 0) for o in history), 2),
                "total_bonus_savings": round(
                    sum(o.get("bonus_savings", 0) for o in history), 2
                ),
                "avg_weekly_spend": get_average_weekly_spend(history),
                "trend": get_spending_trend(history),
                "top_items": get_most_bought(history),
                "low_stock": detect_low_stock(history),
            }
            json.dump(summary_data, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            print(format_history_summary(history))
