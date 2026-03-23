#!/usr/bin/env python3
"""Seasonal support for recipe filtering and ingredient availability."""

import argparse
import json
import sys
from datetime import date


# ── Dutch seasonal produce mapping ────────────────────────────
SEASONAL_INGREDIENTS: dict[str, list[str]] = {
    "lente": [
        "asperges", "radijs", "spinazie", "rabarber", "tuinbonen",
        "lente-ui", "prei", "sla", "rucola", "waterkers",
        "peterselie", "bieslook", "munt", "dille", "kervel",
        "aardbeien", "nieuwe aardappelen", "venkel", "artisjok",
        "postelein", "snijbiet", "lamsoor", "zeekraal",
        "witte asperges", "groene asperges", "eikenbladsla",
    ],
    "zomer": [
        "aardbeien", "frambozen", "bosbessen", "kersen", "perziken",
        "abrikozen", "pruimen", "meloenen", "watermeloen", "tomaten",
        "courgette", "aubergine", "paprika", "komkommer", "sperziebonen",
        "mais", "bonen", "doperwten", "bramen", "rode bessen",
        "zomerfruit", "sla", "rucola", "ijsbergsla", "radijs",
        "bosui", "venkel", "artisjok", "tuinbonen", "snijbonen",
        "postelein", "kruiden", "basilicum", "munt", "dille",
    ],
    "herfst": [
        "pompoen", "butternut", "flespompoen", "paddenstoelen",
        "kastanjes", "appels", "peren", "druiven", "vijgen",
        "rode kool", "witte kool", "spitskool", "bloemkool",
        "broccoli", "pastinaak", "knolselderij", "bietjes",
        "zoete aardappel", "mais", "walnoten", "hazelnoten",
        "cranberries", "prei", "boerenkool", "andijvie",
        "veldsla", "champignons", "eekhoorntjesbrood",
    ],
    "winter": [
        "boerenkool", "spruitjes", "winterwortel", "knolselderij",
        "pastinaak", "rode kool", "witte kool", "savooiekool",
        "prei", "aardappelen", "uien", "knoflook", "bietjes",
        "schorseneren", "raapjes", "witlof", "andijvie",
        "veldsla", "mandarijnen", "sinaasappels", "grapefruits",
        "clementines", "stoofperen", "cranberries", "pompoen",
        "champignons", "winterpostelein", "celeriac",
    ],
}


# ── Seasonal cooking suggestions ─────────────────────────────
SEASONAL_SUGGESTIONS: dict[str, dict] = {
    "lente": {
        "methods": ["stomen", "kort bakken", "grillen", "rauw"],
        "flavors": ["fris", "licht", "citroen", "kruiden", "lente-ui"],
        "proteins": ["lam", "kip", "vis", "garnalen", "ei"],
        "cuisines": ["Frans", "Italiaans", "Japans"],
        "description": (
            "Lente draait om verse, lichte smaken. Asperges zijn het "
            "seizoenshoogtepunt. Kies voor kort garen om frisheid te behouden."
        ),
    },
    "zomer": {
        "methods": ["grillen", "barbecue", "rauw", "salade", "koud"],
        "flavors": ["fris", "zomers", "mediterraan", "kruiden", "citrus"],
        "proteins": ["vis", "garnalen", "kip", "halloumi", "tofu"],
        "cuisines": ["Grieks", "Turks", "Mexicaans", "Thais"],
        "description": (
            "Zomer is het seizoen van de BBQ en frisse salades. Tomaten, "
            "courgette en paprika zijn op hun best. Houd gerechten licht."
        ),
    },
    "herfst": {
        "methods": ["stoven", "oven", "soep", "braden", "roosteren"],
        "flavors": ["hartig", "noten", "paddenstoelen", "warm", "zoet"],
        "proteins": ["rund", "varken", "wild", "kip", "eend"],
        "cuisines": ["Nederlands", "Frans", "Italiaans", "Brits"],
        "description": (
            "Herfst vraagt om stevige, verwarmende gerechten. Pompoensoep, "
            "stoofpotten en paddenstoelenrisotto passen perfect."
        ),
    },
    "winter": {
        "methods": ["stoven", "oven", "soep", "stamppot", "braden"],
        "flavors": ["hartig", "stevig", "warm", "kruiden", "kaas"],
        "proteins": ["rund", "varken", "kip", "worst", "spek"],
        "cuisines": ["Nederlands", "Frans", "Indonesisch", "Indiaas"],
        "description": (
            "Winter is het seizoen van stamppotten, erwtensoep en stoofvlees. "
            "Boerenkool, spruitjes en winterwortel zijn de sterren."
        ),
    },
}


def get_current_season(d: date | None = None) -> str:
    """Return current season in Dutch: lente, zomer, herfst, winter.

    Based on meteorological seasons:
    - Lente:  March, April, May
    - Zomer:  June, July, August
    - Herfst: September, October, November
    - Winter: December, January, February
    """
    if d is None:
        d = date.today()
    month = d.month
    if month in (3, 4, 5):
        return "lente"
    elif month in (6, 7, 8):
        return "zomer"
    elif month in (9, 10, 11):
        return "herfst"
    else:
        return "winter"


def get_seasonal_ingredients(season: str) -> list[str]:
    """Return list of ingredients that are in season.

    Args:
        season: One of 'lente', 'zomer', 'herfst', 'winter'.

    Returns:
        List of Dutch ingredient names available in that season.

    Raises:
        ValueError: If season is not recognized.
    """
    season = season.lower().strip()
    if season not in SEASONAL_INGREDIENTS:
        raise ValueError(
            f"Unknown season '{season}'. "
            f"Use one of: lente, zomer, herfst, winter"
        )
    return list(SEASONAL_INGREDIENTS[season])


def filter_recipes_by_season(
    recipes: list[dict], season: str | None = None
) -> list[dict]:
    """Filter recipes that match the current or given season.

    Recipes with season set to 'all' or 'alle' are always included.
    A recipe matches if its 'season' field equals the target season,
    or if any of its 'seasons' list entries match.

    Args:
        recipes: List of recipe dicts. Each may have a 'season' string
                 or 'seasons' list field.
        season: Target season. Defaults to the current season if None.

    Returns:
        List of recipes matching the season.
    """
    if season is None:
        season = get_current_season()
    season = season.lower().strip()

    filtered: list[dict] = []
    for recipe in recipes:
        recipe_season = recipe.get("season", "").lower().strip()
        recipe_seasons = [s.lower().strip() for s in recipe.get("seasons", [])]

        # Always include all-season recipes
        if recipe_season in ("all", "alle", ""):
            filtered.append(recipe)
            continue
        if "all" in recipe_seasons or "alle" in recipe_seasons:
            filtered.append(recipe)
            continue

        # Match specific season
        if recipe_season == season:
            filtered.append(recipe)
            continue
        if season in recipe_seasons:
            filtered.append(recipe)
            continue

    return filtered


def get_seasonal_suggestions(season: str) -> dict:
    """Return seasonal cooking suggestions including preferred methods and flavors.

    Args:
        season: One of 'lente', 'zomer', 'herfst', 'winter'.

    Returns:
        Dict with keys: methods, flavors, proteins, cuisines, description.

    Raises:
        ValueError: If season is not recognized.
    """
    season = season.lower().strip()
    if season not in SEASONAL_SUGGESTIONS:
        raise ValueError(
            f"Unknown season '{season}'. "
            f"Use one of: lente, zomer, herfst, winter"
        )
    return dict(SEASONAL_SUGGESTIONS[season])


def load_recipes(path: str = "recipes.json") -> list[dict]:
    """Load recipes from JSON file.

    Args:
        path: Path to JSON file. Expected format is either a list of recipe
              dicts, or a dict with a 'recipes' key containing the list.

    Returns:
        List of recipe dicts.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("recipes", [])


def _matches_filter(recipe: dict, key: str, value: str) -> bool:
    """Check if a recipe matches a filter on a given key.

    Handles both string and list fields.
    """
    value = value.lower().strip()
    field = recipe.get(key, "")
    if isinstance(field, str):
        return value in field.lower()
    if isinstance(field, list):
        return any(value in item.lower() for item in field)
    return False


def _print_recipe(recipe: dict) -> None:
    """Print a recipe summary."""
    name = recipe.get("name", recipe.get("title", "Unnamed"))
    season = recipe.get("season", "all")
    seasons = recipe.get("seasons", [])
    season_str = ", ".join(seasons) if seasons else season
    cuisine = recipe.get("cuisine", "")
    protein = recipe.get("protein", "")
    method = recipe.get("method", "")
    servings = recipe.get("servings", "")

    print(f"  {name}")
    parts = []
    if season_str:
        parts.append(f"seizoen: {season_str}")
    if cuisine:
        parts.append(f"keuken: {cuisine}")
    if protein:
        parts.append(f"eiwit: {protein}")
    if method:
        parts.append(f"methode: {method}")
    if servings:
        parts.append(f"porties: {servings}")
    if parts:
        print(f"    {' | '.join(parts)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seasonal recipe filtering and ingredient info"
    )
    parser.add_argument(
        "--season",
        choices=["lente", "zomer", "herfst", "winter"],
        help="Target season (default: current season)",
    )
    parser.add_argument("--cuisine", help="Filter recipes by cuisine")
    parser.add_argument("--protein", help="Filter recipes by protein")
    parser.add_argument("--method", help="Filter recipes by cooking method")
    parser.add_argument(
        "--recipes", default="recipes.json", help="Path to recipes JSON file"
    )
    parser.add_argument(
        "--ingredients-only",
        action="store_true",
        help="Only show seasonal ingredients",
    )
    parser.add_argument(
        "--suggestions",
        action="store_true",
        help="Show seasonal cooking suggestions",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    season = args.season or get_current_season()

    # Show ingredients only
    if args.ingredients_only:
        ingredients = get_seasonal_ingredients(season)
        if args.json:
            json.dump(
                {"season": season, "ingredients": ingredients},
                sys.stdout,
                indent=2,
                ensure_ascii=False,
            )
            print()
        else:
            print(f"Seizoensgroenten en fruit ({season}):\n")
            for ing in sorted(ingredients):
                print(f"  - {ing}")
        sys.exit(0)

    # Show suggestions
    if args.suggestions:
        suggestions = get_seasonal_suggestions(season)
        if args.json:
            json.dump(
                {"season": season, **suggestions},
                sys.stdout,
                indent=2,
                ensure_ascii=False,
            )
            print()
        else:
            print(f"Kooksuggesties voor {season}:\n")
            print(f"  {suggestions['description']}\n")
            print(f"  Bereidingswijzen: {', '.join(suggestions['methods'])}")
            print(f"  Smaken:           {', '.join(suggestions['flavors'])}")
            print(f"  Eiwitten:         {', '.join(suggestions['proteins'])}")
            print(f"  Keukens:          {', '.join(suggestions['cuisines'])}")
        sys.exit(0)

    # Filter recipes
    try:
        recipes = load_recipes(args.recipes)
    except FileNotFoundError:
        print(f"Error: recipes file not found: {args.recipes}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {args.recipes}: {e}", file=sys.stderr)
        sys.exit(1)

    filtered = filter_recipes_by_season(recipes, season)

    # Apply additional filters
    if args.cuisine:
        filtered = [r for r in filtered if _matches_filter(r, "cuisine", args.cuisine)]
    if args.protein:
        filtered = [r for r in filtered if _matches_filter(r, "protein", args.protein)]
    if args.method:
        filtered = [r for r in filtered if _matches_filter(r, "method", args.method)]

    if args.json:
        json.dump(
            {"season": season, "count": len(filtered), "recipes": filtered},
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
    else:
        print(f"Recepten voor {season} ({len(filtered)} gevonden):\n")
        if not filtered:
            print("  Geen recepten gevonden voor deze criteria.")
        else:
            for recipe in filtered:
                _print_recipe(recipe)
                print()

        # Also show seasonal ingredients
        ingredients = get_seasonal_ingredients(season)
        print(f"{'─' * 60}")
        print(f"Seizoensproducten ({season}): {', '.join(sorted(ingredients)[:10])}...")
