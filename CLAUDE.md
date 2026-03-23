# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python toolkit for Albert Heijn grocery automation: weekly meal planning, smart product matching, nutrition tracking, and one-click cart building via koopknop deep links.

## Running

```bash
pip install -r requirements.txt          # requests + pytest
python3 ah_koopknop.py                   # Basic cart builder (uses config.json)
python3 meal_cart.py --ingredients list.json  # Full smart pipeline
python3 seasonal.py                      # Seasonal recipe suggestions
python3 nutrition.py --recipes recipes.json   # Nutrition tracking
python3 order_history.py --summary       # Order history
pytest tests/ -v                         # Run tests (65 tests)
```

## Architecture

Flat structure, Python files at root:

- **`ah_koopknop.py`** — Entry point. Loads items from JSON, searches via `AHApi`, builds koopknop URL.
- **`ah_api.py`** — AH mobile API client. Anonymous auth, search, bonus, product details.
- **`ah_bonus.py`** — Fetch and display current AH bonus/discount products.
- **`product_matcher.py`** — Intelligent product search with fuzzy matching, brand preferences, scoring, and caching.
- **`meal_cart.py`** — Full pipeline: ingredients → product matching → cart URL.
- **`seasonal.py`** — Season detection, recipe filtering, seasonal ingredients.
- **`nutrition.py`** — Calorie/macro tracking, family recommendations (Mifflin-St Jeor).
- **`order_history.py`** — Order tracking, spending trends, low-stock detection.

Data files:
- **`recipes.json`** — 67 Dutch-friendly recipes with full nutrition data.
- **`preferences.json`** — Family preferences (brands, dietary, budget, equipment).
- **`matched_products.json`** — Product match cache (auto-generated).
- **`order_history.json`** — Order history (auto-generated).

## Family Context

- **JP** (30M, moderate activity) — no kipfilet, prefer kipstukjes/dijen
- **Inidri** (30F, pregnant, moderate activity) — no fish
- **Roux** (3yr toddler) — kid-friendly portions
- **Budget**: max €150/week
- **Equipment**: NO OVEN — airfryer, kookplaat, wok, stoofpot, magnetron only
- **Brands**: Perla coffee, AH huismerk preferred
- **Dietary**: NO koriander in any recipe

## Shopping List Format (config.json)

```json
{
  "items": [
    { "name": "kipstukjes", "quantity": 1 },
    { "name": "rundergehakt", "quantity": 2 }
  ]
}
```

## Key Design Decisions

- Replaced Selenium/Playwright (blocked by CloudFlare) with API + koopknop URL approach
- Own lightweight AH API client (`ah_api.py`) — no external dependencies beyond `requests`
- Product matcher uses fuzzy matching + brand preference scoring + caching
- Recipes database: NO oven, NO koriander, NO kipfilet
- Nutrition uses Mifflin-St Jeor equation with pregnancy/toddler adjustments
