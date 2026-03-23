# AH Shopping — Smart Grocery Automation for Albert Heijn

Automated weekly meal planning, smart product matching, and one-click cart building for Albert Heijn (AH).

## Features

- **Weekly Meal Planning** — 50+ recipe database with seasonal filtering
- **Smart Product Matcher** — Fuzzy matching, brand preferences, bonus prioritization, product caching
- **One-Click Cart** — Build AH koopknop deep links to add all items at once
- **Nutrition Tracking** — Per-meal and weekly calorie/macro tracking for the whole family
- **Seasonal Support** — Season-aware recipe filtering and ingredient suggestions
- **Order History** — Track spending trends, detect frequently bought items
- **Family Preferences** — Dietary restrictions, brand preferences, budget limits

## Quick Start

```bash
pip install -r requirements.txt    # Only dependency: requests (+ pytest for tests)
python3 ah_koopknop.py             # Basic cart builder
python3 meal_cart.py --ingredients list.json  # Full pipeline
```

## Architecture

```
ah_koopknop.py      — Entry point: search items, build koopknop URL
ah_api.py           — AH mobile API client (anonymous auth, search, bonus, details)
ah_bonus.py         — Fetch and display current AH bonus/discount products
product_matcher.py  — Intelligent product search with scoring + caching
meal_cart.py        — Ingredients → resolved products → cart URL pipeline
seasonal.py         — Season detection, recipe filtering, seasonal ingredients
nutrition.py        — Calorie/macro tracking, family recommendations
order_history.py    — Order tracking, spending trends, low-stock detection
recipes.json        — 50+ Dutch-friendly recipes database
preferences.json    — Family preferences, brands, dietary, budget
```

## Usage

### Build a Cart from Shopping List

```bash
python3 ah_koopknop.py --items config.json
```

### Smart Ingredient Resolution

```bash
python3 meal_cart.py --ingredients shopping_list.json
python3 meal_cart.py --ingredients shopping_list.json --json
python3 meal_cart.py --ingredients shopping_list.json --save-plan plan.json
```

### Search for a Product

```bash
python3 product_matcher.py "500g kipstukjes"
python3 product_matcher.py --ingredients ingredients.json --json
```

### View Current Bonus Products

```bash
python3 ah_bonus.py              # Human-readable
python3 ah_bonus.py --summary    # Compact (for LLM context)
python3 ah_bonus.py --json       # Full JSON
```

### Seasonal Recipes

```bash
python3 seasonal.py                        # Current season recipes
python3 seasonal.py --season winter        # Winter recipes
python3 seasonal.py --cuisine Italiaans    # Filter by cuisine
python3 seasonal.py --protein kip          # Filter by protein
python3 seasonal.py --method airfryer      # Filter by cooking method
```

### Nutrition Tracking

```bash
python3 nutrition.py --recipes recipes.json          # Show recipe nutrition
python3 nutrition.py --recipes recipes.json --week    # Weekly summary
python3 nutrition.py --recipes recipes.json --telegram # Telegram-formatted
```

### Order History

```bash
python3 order_history.py --add plan.json   # Record an order
python3 order_history.py --trend           # Spending trends
python3 order_history.py --top             # Most bought items
python3 order_history.py --low-stock       # Items running low
python3 order_history.py --summary         # Full summary
```

## Shopping List Format

`config.json`:
```json
{
  "items": [
    { "name": "kipstukjes", "quantity": 1 },
    { "name": "rundergehakt", "quantity": 2 },
    { "name": "Perla filterkoffie", "quantity": 1 }
  ]
}
```

## Ingredients Format

```json
{
  "ingredients": [
    {"item": "spaghetti", "quantity": 500, "unit": "g"},
    {"item": "rundergehakt", "quantity": 500, "unit": "g"},
    {"item": "uien", "quantity": 3, "unit": "stuks"}
  ]
}
```

## Product Matching

The product matcher scores candidates on:
- **Relevance** (30 pts) — Fuzzy string matching (token overlap + bigram similarity)
- **Price efficiency** (25 pts) — Unit price comparison
- **Bonus** (20 pts) — Current AH bonus products get priority
- **Quantity fit** (15 pts) — Minimal waste from package sizes
- **Nutriscore** (10 pts) — Healthier products score higher
- **Brand preference** (15 pts) — Preferred brands (Perla, AH huismerk) get bonus

Features:
- Loads brand preferences from `preferences.json`
- Caches matched products in `matched_products.json`
- Filters out avoided ingredients (kipfilet, koriander)
- Skips pantry items (zout, peper, olijfolie, etc.)

## Family Preferences

`preferences.json` tracks:
- Family members with dietary needs (JP, Inidri, Roux)
- Brand preferences (Perla coffee, AH huismerk default)
- Protein preferences (no kipfilet, prefer kipstukjes/dijen)
- Dietary restrictions (no koriander, Inidri no fish)
- Budget (max €150/week)
- Equipment (no oven, airfryer + kookplaat)

## Recipe Database

`recipes.json` contains 50+ recipes with:
- Multiple cuisines (Nederlands, Italiaans, Aziatisch, Mexicaans, Indiaas, Mediterraan)
- Cooking methods (airfryer, kookplaat, wok, stoofpot, magnetron)
- Seasonal tags (lente, zomer, herfst, winter)
- Full nutritional info (calories, protein, carbs, fat)
- Smart tags (budget, quick, comfort, healthy, kid-friendly)

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## How the Koopknop URL Works

1. Log into https://www.ah.nl in your browser
2. Copy the generated URL
3. Paste in address bar — all items are added to cart instantly
4. Proceed to checkout

URL format: `https://www.ah.nl/mijnlijst/add-multiple?p=<id>:<qty>&p=<id>:<qty>`

## API

Uses the AH mobile app API directly (no external dependencies beyond `requests`):
- Anonymous token auth (no login required)
- Product search with filters
- Bonus/discount product listing
- Full product details with nutrition and allergens
