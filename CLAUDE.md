# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python CLI tool that generates Albert Heijn "koopknop" shopping cart deep links from a JSON shopping list. It searches for products via AH's mobile API and builds a URL that adds all items to a cart in one click.

## Running

```bash
pip install -r requirements.txt          # Only dependency: requests
python3 ah_koopknop.py                   # Uses default config.json
python3 ah_koopknop.py --items list.json # Custom shopping list
```

No build, test, or lint tooling exists.

## Architecture

Flat structure, four Python files at root:

- **`ah_koopknop.py`** — Entry point & orchestrator. Loads items from JSON, searches products via `AHApi`, filters bad matches, builds the koopknop URL (`https://www.ah.nl/mijnlijst/add-multiple?p=<id>:<qty>&...`).
- **`ah_api.py`** — Lightweight AH API client. Gets anonymous auth token from AH mobile API, searches products. Returns dicts with `webshopId`, `title`, `price`, `isBonus`.
- **`jumbo_api.py`** — Lightweight Jumbo API client. Public API, no auth needed.
- **`supermarkt_api.py`** — Full-featured multi-connector wrapper (`AHConnector`, `JumboConnector`) with pagination, bonus products, product details, and a `_normalize()` method for standardized output.

`ah_koopknop.py` uses `ah_api.py` directly (not `supermarkt_api.py`).

## Shopping List Format (config.json)

```json
{
  "items": [
    { "name": "kipfilet", "quantity": 1 },
    { "name": "rundergehakt", "quantity": 2 }
  ]
}
```

## Key Design Decisions

- Replaced Selenium/Playwright (blocked by CloudFlare) with API + koopknop URL approach
- Replaced `supermarktconnector` dependency with own lightweight API clients (`ah_api.py`, `jumbo_api.py`)
- Only external dependency is `requests`
- Product search in `ah_koopknop.py` filters out irrelevant results (maaltijdmix, babyvoeding, etc.)
