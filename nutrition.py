#!/usr/bin/env python3
"""Nutrition tracking and calorie calculations for the family."""

import argparse
import json
import math
import sys
from dataclasses import dataclass, field


# ── Activity level multipliers (Harris-Benedict / Mifflin-St Jeor) ───
ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# ── Macro split targets (percentage of total calories) ───────────────
MACRO_SPLIT = {
    "protein_pct": 0.20,  # 20% of calories from protein
    "carbs_pct": 0.50,    # 50% of calories from carbs
    "fat_pct": 0.30,      # 30% of calories from fat
}

# ── Calories per gram of macronutrient ───────────────────────────────
CALS_PER_G_PROTEIN = 4
CALS_PER_G_CARBS = 4
CALS_PER_G_FAT = 9

# ── Toddler calorie estimates (age in years -> kcal/day) ────────────
# Based on Dutch Voedingscentrum guidelines
TODDLER_CALORIES: dict[int, dict[str, int]] = {
    1: {"male": 950, "female": 900},
    2: {"male": 1050, "female": 1000},
    3: {"male": 1150, "female": 1100},
    4: {"male": 1250, "female": 1200},
    5: {"male": 1350, "female": 1300},
    6: {"male": 1500, "female": 1400},
}

# ── Child calorie estimates (7-17) ──────────────────────────────────
CHILD_CALORIES: dict[int, dict[str, int]] = {
    7:  {"male": 1600, "female": 1500},
    8:  {"male": 1650, "female": 1550},
    9:  {"male": 1750, "female": 1650},
    10: {"male": 1850, "female": 1700},
    11: {"male": 1950, "female": 1800},
    12: {"male": 2100, "female": 1900},
    13: {"male": 2250, "female": 2000},
    14: {"male": 2400, "female": 2100},
    15: {"male": 2550, "female": 2200},
    16: {"male": 2700, "female": 2250},
    17: {"male": 2800, "female": 2300},
}

# ── Pregnancy extra calories by trimester ────────────────────────────
PREGNANCY_EXTRA_CALORIES = 300  # Average across trimesters (T2+T3)


@dataclass
class FamilyMember:
    """A family member with nutritional needs.

    Attributes:
        name: Display name.
        age: Age in years.
        gender: 'male' or 'female'.
        activity_level: One of 'sedentary', 'moderate', 'active', 'very_active'.
        weight_kg: Weight in kilograms (used for Mifflin-St Jeor). Estimated if 0.
        height_cm: Height in centimeters (used for Mifflin-St Jeor). Estimated if 0.
        pregnant: Whether currently pregnant (adds ~300 kcal/day).
    """

    name: str
    age: int
    gender: str
    activity_level: str = "moderate"
    weight_kg: float = 0
    height_cm: float = 0
    pregnant: bool = False

    def __post_init__(self) -> None:
        """Estimate weight and height if not provided, based on Dutch averages."""
        if self.weight_kg <= 0:
            self.weight_kg = self._estimate_weight()
        if self.height_cm <= 0:
            self.height_cm = self._estimate_height()

    def _estimate_weight(self) -> float:
        """Estimate weight based on age and gender (Dutch averages)."""
        if self.age <= 1:
            return 10.0
        elif self.age <= 3:
            return 12.0 + (self.age - 1) * 2
        elif self.age <= 6:
            return 16.0 + (self.age - 3) * 2.5
        elif self.age <= 12:
            return 23.0 + (self.age - 6) * 3.5
        elif self.age <= 17:
            base = 44.0 + (self.age - 12) * 5
            return base if self.gender == "male" else base - 5
        else:
            return 80.0 if self.gender == "male" else 65.0

    def _estimate_height(self) -> float:
        """Estimate height in cm based on age and gender (Dutch averages)."""
        if self.age <= 1:
            return 75.0
        elif self.age <= 3:
            return 80.0 + (self.age - 1) * 8
        elif self.age <= 6:
            return 96.0 + (self.age - 3) * 6
        elif self.age <= 12:
            return 114.0 + (self.age - 6) * 5.5
        elif self.age <= 17:
            base = 147.0 + (self.age - 12) * 6
            return base if self.gender == "male" else base - 5
        else:
            return 181.0 if self.gender == "male" else 167.0

    @property
    def daily_calories(self) -> int:
        """Calculate recommended daily calorie intake.

        Uses Mifflin-St Jeor equation for adults (18+).
        Uses age-based lookup tables for children and toddlers.
        Adds 300 kcal for pregnancy.
        """
        # Toddlers (1-6)
        if self.age <= 6:
            clamped_age = max(1, min(6, self.age))
            base = TODDLER_CALORIES.get(
                clamped_age, {"male": 1150, "female": 1100}
            )
            cals = base.get(self.gender, base["male"])
            return cals

        # Children (7-17)
        if self.age <= 17:
            clamped_age = max(7, min(17, self.age))
            base = CHILD_CALORIES.get(
                clamped_age, {"male": 2000, "female": 1800}
            )
            cals = base.get(self.gender, base["male"])
            return cals

        # Adults (18+) — Mifflin-St Jeor equation
        # Men:   BMR = 10 * weight(kg) + 6.25 * height(cm) - 5 * age - 5 + 161 (nee: +5)
        # Women: BMR = 10 * weight(kg) + 6.25 * height(cm) - 5 * age - 161
        if self.gender == "male":
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + 5
        else:
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age - 161

        multiplier = ACTIVITY_MULTIPLIERS.get(self.activity_level, 1.55)
        total = bmr * multiplier

        if self.pregnant:
            total += PREGNANCY_EXTRA_CALORIES

        return round(total)

    @property
    def daily_protein_g(self) -> int:
        """Recommended daily protein in grams.

        Calculated as 20% of daily calories, divided by 4 kcal/g.
        Children under 6 get a minimum of 1.1g per kg body weight.
        Pregnant women get a 25g bonus.
        """
        if self.age <= 6:
            return round(max(self.weight_kg * 1.1, 13))

        base = round(self.daily_calories * MACRO_SPLIT["protein_pct"] / CALS_PER_G_PROTEIN)
        if self.pregnant:
            base += 25
        return base

    @property
    def daily_carbs_g(self) -> int:
        """Recommended daily carbs in grams.

        Calculated as 50% of daily calories, divided by 4 kcal/g.
        """
        return round(self.daily_calories * MACRO_SPLIT["carbs_pct"] / CALS_PER_G_CARBS)

    @property
    def daily_fat_g(self) -> int:
        """Recommended daily fat in grams.

        Calculated as 30% of daily calories, divided by 9 kcal/g.
        """
        return round(self.daily_calories * MACRO_SPLIT["fat_pct"] / CALS_PER_G_FAT)


def load_family_from_preferences(path: str = "preferences.json") -> list[FamilyMember]:
    """Load family members from preferences.json.

    Expected format in preferences.json under 'family' key:
    [
        {"name": "JP", "age": 30, "gender": "male", "activity_level": "moderate"},
        {"name": "Inidri", "age": 30, "gender": "female", "activity_level": "moderate", "pregnant": true},
        {"name": "Roux", "age": 3, "gender": "male", "activity_level": "active"}
    ]

    Falls back to hardcoded family if file not found or missing 'family' key.

    Args:
        path: Path to preferences JSON file.

    Returns:
        List of FamilyMember instances.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        family_raw = data.get("family", [])
        family_data = family_raw.get("members", family_raw) if isinstance(family_raw, dict) else family_raw
        if family_data:
            return [
                FamilyMember(
                    name=m["name"],
                    age=m.get("age", 30),
                    gender=m.get("gender", "male"),
                    activity_level=m.get("activity_level", "moderate"),
                    weight_kg=m.get("weight_kg", 0),
                    height_cm=m.get("height_cm", 0),
                    pregnant=m.get("pregnant", False),
                )
                for m in family_data
            ]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    # Fallback: default family from project spec
    return [
        FamilyMember(name="JP", age=30, gender="male", activity_level="moderate"),
        FamilyMember(
            name="Inidri", age=30, gender="female",
            activity_level="moderate", pregnant=True,
        ),
        FamilyMember(name="Roux", age=3, gender="male", activity_level="active"),
    ]


def calculate_meal_nutrition(recipe: dict, servings_consumed: int = 1) -> dict:
    """Calculate nutrition for a meal from recipe data.

    Looks for nutrition info in the recipe dict under keys like
    'nutrition', 'calories', 'protein_g', etc. Also supports a
    'nutrition_per_serving' sub-dict.

    Args:
        recipe: Recipe dict, may contain nutrition data.
        servings_consumed: Number of servings eaten (default 1).

    Returns:
        Dict with keys: calories, protein_g, carbs_g, fat_g (per serving * servings_consumed).
    """
    # Try structured nutrition data
    nutrition = recipe.get("nutrition_per_serving", recipe.get("nutrition", {}))

    if isinstance(nutrition, dict) and nutrition:
        calories = nutrition.get("calories", nutrition.get("kcal", 0))
        protein = nutrition.get("protein_g", nutrition.get("protein", 0))
        carbs = nutrition.get("carbs_g", nutrition.get("carbs", 0))
        fat = nutrition.get("fat_g", nutrition.get("fat", 0))
    else:
        # Try top-level keys (support both 'calories' and 'calories_per_serving')
        calories = recipe.get("calories_per_serving", recipe.get("calories", recipe.get("kcal", 0)))
        protein = recipe.get("protein_g", 0)
        carbs = recipe.get("carbs_g", 0)
        fat = recipe.get("fat_g", 0)

    # Estimate from ingredients if no nutrition data provided
    if calories == 0 and "ingredients" in recipe:
        calories, protein, carbs, fat = _estimate_from_ingredients(
            recipe["ingredients"], recipe.get("servings", 4)
        )

    return {
        "name": recipe.get("name", recipe.get("title", "Unknown")),
        "calories": round(calories * servings_consumed),
        "protein_g": round(protein * servings_consumed),
        "carbs_g": round(carbs * servings_consumed),
        "fat_g": round(fat * servings_consumed),
        "servings_consumed": servings_consumed,
    }


def _estimate_from_ingredients(ingredients: list, servings: int) -> tuple[float, float, float, float]:
    """Rough calorie estimation from ingredient list when no nutrition data is available.

    This is a very rough estimate based on common Dutch ingredients.
    Returns per-serving values: (calories, protein_g, carbs_g, fat_g).
    """
    # Simple lookup for common ingredients (per typical recipe portion)
    ROUGH_ESTIMATES: dict[str, tuple[float, float, float, float]] = {
        # (kcal, protein, carbs, fat) per typical recipe quantity
        "kip": (165, 31, 0, 3.6),
        "kipfilet": (165, 31, 0, 3.6),
        "kipstukjes": (165, 31, 0, 3.6),
        "rundergehakt": (250, 26, 0, 15),
        "gehakt": (250, 26, 0, 15),
        "varkenshaas": (143, 26, 0, 3.5),
        "zalm": (208, 20, 0, 13),
        "vis": (150, 25, 0, 5),
        "garnalen": (85, 18, 0, 1),
        "ei": (78, 6, 0.6, 5),
        "eieren": (156, 12, 1.2, 10),
        "rijst": (130, 2.7, 28, 0.3),
        "pasta": (131, 5, 25, 1.1),
        "spaghetti": (131, 5, 25, 1.1),
        "aardappelen": (77, 2, 17, 0.1),
        "aardappel": (77, 2, 17, 0.1),
        "brood": (79, 3, 15, 1),
        "melk": (42, 3.4, 5, 1),
        "kaas": (113, 7, 0.4, 9),
        "broccoli": (34, 2.8, 7, 0.4),
        "spinazie": (23, 2.9, 3.6, 0.4),
        "tomaten": (18, 0.9, 3.9, 0.2),
        "paprika": (31, 1, 6, 0.3),
        "ui": (40, 1.1, 9, 0.1),
        "uien": (40, 1.1, 9, 0.1),
        "knoflook": (5, 0.2, 1, 0),
        "wortel": (41, 0.9, 10, 0.2),
        "courgette": (17, 1.2, 3, 0.3),
        "pompoen": (26, 1, 6.5, 0.1),
        "boerenkool": (49, 4.3, 9, 0.9),
        "spruitjes": (43, 3.4, 9, 0.3),
    }

    total_cal = 0.0
    total_prot = 0.0
    total_carb = 0.0
    total_fat = 0.0

    for ing in ingredients:
        name = ""
        if isinstance(ing, str):
            name = ing.lower()
        elif isinstance(ing, dict):
            name = ing.get("item", ing.get("name", "")).lower()

        for key, (cal, prot, carb, fat) in ROUGH_ESTIMATES.items():
            if key in name:
                total_cal += cal
                total_prot += prot
                total_carb += carb
                total_fat += fat
                break

    if servings > 0:
        return (
            total_cal / servings,
            total_prot / servings,
            total_carb / servings,
            total_fat / servings,
        )
    return (total_cal, total_prot, total_carb, total_fat)


def calculate_daily_nutrition(meals: list[dict]) -> dict:
    """Calculate total nutrition for a day's meals.

    Args:
        meals: List of meal nutrition dicts (as returned by calculate_meal_nutrition).

    Returns:
        Dict with total calories, protein_g, carbs_g, fat_g and meal details.
    """
    total_cal = 0
    total_prot = 0
    total_carb = 0
    total_fat = 0

    for meal in meals:
        total_cal += meal.get("calories", 0)
        total_prot += meal.get("protein_g", 0)
        total_carb += meal.get("carbs_g", 0)
        total_fat += meal.get("fat_g", 0)

    return {
        "calories": total_cal,
        "protein_g": total_prot,
        "carbs_g": total_carb,
        "fat_g": total_fat,
        "meal_count": len(meals),
        "meals": meals,
    }


def calculate_weekly_nutrition(weekly_meals: dict[str, list[dict]]) -> dict:
    """Calculate weekly nutrition totals and averages.

    Args:
        weekly_meals: Dict mapping day name (e.g. 'maandag') to list of meal
                     nutrition dicts for that day.

    Returns:
        Dict with daily breakdown, weekly totals, and daily averages.
    """
    daily_results: dict[str, dict] = {}
    week_cal = 0
    week_prot = 0
    week_carb = 0
    week_fat = 0
    day_count = 0

    for day, meals in weekly_meals.items():
        daily = calculate_daily_nutrition(meals)
        daily_results[day] = daily
        week_cal += daily["calories"]
        week_prot += daily["protein_g"]
        week_carb += daily["carbs_g"]
        week_fat += daily["fat_g"]
        day_count += 1

    avg_divisor = max(day_count, 1)

    return {
        "days": daily_results,
        "weekly_totals": {
            "calories": week_cal,
            "protein_g": week_prot,
            "carbs_g": week_carb,
            "fat_g": week_fat,
        },
        "daily_averages": {
            "calories": round(week_cal / avg_divisor),
            "protein_g": round(week_prot / avg_divisor),
            "carbs_g": round(week_carb / avg_divisor),
            "fat_g": round(week_fat / avg_divisor),
        },
        "day_count": day_count,
    }


def compare_to_recommendations(daily_totals: dict, member: FamilyMember) -> dict:
    """Compare actual intake to recommended for a family member.

    Args:
        daily_totals: Dict with calories, protein_g, carbs_g, fat_g.
        member: FamilyMember to compare against.

    Returns:
        Dict with surplus/deficit for each macro and percentage of target.
    """
    rec_cal = member.daily_calories
    rec_prot = member.daily_protein_g
    rec_carb = member.daily_carbs_g
    rec_fat = member.daily_fat_g

    actual_cal = daily_totals.get("calories", 0)
    actual_prot = daily_totals.get("protein_g", 0)
    actual_carb = daily_totals.get("carbs_g", 0)
    actual_fat = daily_totals.get("fat_g", 0)

    def _pct(actual: float, recommended: float) -> int:
        """Calculate percentage of recommended intake."""
        if recommended <= 0:
            return 0
        return round(actual / recommended * 100)

    return {
        "member": member.name,
        "calories": {
            "actual": actual_cal,
            "recommended": rec_cal,
            "diff": actual_cal - rec_cal,
            "pct": _pct(actual_cal, rec_cal),
        },
        "protein_g": {
            "actual": actual_prot,
            "recommended": rec_prot,
            "diff": actual_prot - rec_prot,
            "pct": _pct(actual_prot, rec_prot),
        },
        "carbs_g": {
            "actual": actual_carb,
            "recommended": rec_carb,
            "diff": actual_carb - rec_carb,
            "pct": _pct(actual_carb, rec_carb),
        },
        "fat_g": {
            "actual": actual_fat,
            "recommended": rec_fat,
            "diff": actual_fat - rec_fat,
            "pct": _pct(actual_fat, rec_fat),
        },
    }


def format_nutrition_summary(weekly: dict, family: list[FamilyMember]) -> str:
    """Format nutrition summary for Telegram (markdown).

    Shows per-person deficit/surplus vs recommended intake.

    Args:
        weekly: Weekly nutrition data as returned by calculate_weekly_nutrition.
        family: List of FamilyMember instances.

    Returns:
        Markdown-formatted string suitable for Telegram.
    """
    lines: list[str] = []
    lines.append("*Voeding weekoverzicht*\n")

    avg = weekly["daily_averages"]
    lines.append(
        f"Gemiddeld per dag: {avg['calories']} kcal | "
        f"{avg['protein_g']}g eiwit | "
        f"{avg['carbs_g']}g koolh | "
        f"{avg['fat_g']}g vet\n"
    )

    # Per-day breakdown
    for day, data in weekly.get("days", {}).items():
        meal_names = [m.get("name", "?") for m in data.get("meals", [])]
        lines.append(
            f"_{day}_: {data['calories']} kcal "
            f"({', '.join(meal_names)})"
        )

    lines.append("")

    # Per-member comparison
    lines.append("*Per persoon (dag gemiddelde vs aanbevolen):*\n")
    for member in family:
        comparison = compare_to_recommendations(avg, member)

        cal = comparison["calories"]
        diff_sign = "+" if cal["diff"] >= 0 else ""
        status = "OK" if abs(cal["pct"] - 100) <= 15 else ("te veel" if cal["diff"] > 0 else "te weinig")

        lines.append(
            f"*{member.name}* ({member.age}j, {'zwanger' if member.pregnant else member.gender}):"
        )
        lines.append(
            f"  Calorie: {cal['actual']}/{cal['recommended']} kcal "
            f"({diff_sign}{cal['diff']}, {cal['pct']}%) - _{status}_"
        )

        prot = comparison["protein_g"]
        lines.append(
            f"  Eiwit: {prot['actual']}/{prot['recommended']}g ({prot['pct']}%)"
        )

        carb = comparison["carbs_g"]
        lines.append(
            f"  Koolh: {carb['actual']}/{carb['recommended']}g ({carb['pct']}%)"
        )

        fat = comparison["fat_g"]
        lines.append(
            f"  Vet: {fat['actual']}/{fat['recommended']}g ({fat['pct']}%)"
        )
        lines.append("")

    return "\n".join(lines)


def calculate_member_portion(member: FamilyMember, adult_servings: float = 1.0) -> float:
    """Calculate portion size for a family member relative to an adult serving.

    Toddlers (age <= 5) get 50% of an adult serving.
    Children (6-12) get 75% of an adult serving.
    Adults and teens get full servings.

    Args:
        member: The family member.
        adult_servings: Base adult serving count.

    Returns:
        Adjusted serving size.
    """
    if member.age <= 5:
        return adult_servings * 0.5
    elif member.age <= 12:
        return adult_servings * 0.75
    return adult_servings


def check_calorie_warnings(
    recipe: dict,
    family: list[FamilyMember],
    threshold_pct: float = 0.40,
) -> list[dict]:
    """Check if a dinner exceeds a percentage of daily intake for any family member.

    Args:
        recipe: Recipe dict with nutrition data.
        family: List of FamilyMember instances.
        threshold_pct: Warning threshold as fraction of daily calories (default 40%).

    Returns:
        List of warning dicts with member name, meal calories, daily calories,
        and percentage. Empty list if no warnings.
    """
    meal = calculate_meal_nutrition(recipe, servings_consumed=1)
    meal_cals = meal["calories"]
    warnings: list[dict] = []

    for member in family:
        portion = calculate_member_portion(member)
        member_cals = round(meal_cals * portion)
        daily = member.daily_calories
        if daily > 0:
            pct = member_cals / daily
            if pct > threshold_pct:
                warnings.append({
                    "member": member.name,
                    "meal_name": meal["name"],
                    "meal_calories": member_cals,
                    "daily_calories": daily,
                    "percentage": round(pct * 100, 1),
                    "warning": (
                        f"{member.name}: dinner is {round(pct * 100)}% of daily intake "
                        f"({member_cals}/{daily} kcal)"
                    ),
                })

    return warnings


def calculate_weekly_calorie_budget(
    recipes: list[dict],
    family: list[FamilyMember],
    num_dinners: int = 5,
) -> dict:
    """Track weekly calorie budget across dinners for each family member.

    Sums calories for the given dinner recipes and compares to weekly needs
    (dinner is assumed to be ~35% of daily intake, so weekly dinner budget
    = daily_calories * 0.35 * num_dinners).

    Args:
        recipes: List of recipe dicts (one per dinner).
        family: List of FamilyMember instances.
        num_dinners: Number of dinners in the week (default 5).

    Returns:
        Dict with per-member weekly budget comparison.
    """
    results: list[dict] = []

    for member in family:
        portion = calculate_member_portion(member)
        total_dinner_cals = 0
        for recipe in recipes[:num_dinners]:
            meal = calculate_meal_nutrition(recipe, servings_consumed=1)
            total_dinner_cals += round(meal["calories"] * portion)

        weekly_daily_total = member.daily_calories * num_dinners
        dinner_budget = round(weekly_daily_total * 0.35)

        results.append({
            "member": member.name,
            "total_dinner_calories": total_dinner_cals,
            "weekly_dinner_budget": dinner_budget,
            "diff": total_dinner_cals - dinner_budget,
            "pct": round(total_dinner_cals / dinner_budget * 100) if dinner_budget > 0 else 0,
            "status": (
                "over budget" if total_dinner_cals > dinner_budget * 1.15
                else "under budget" if total_dinner_cals < dinner_budget * 0.85
                else "on track"
            ),
        })

    return {
        "num_dinners": min(num_dinners, len(recipes)),
        "members": results,
    }


def format_meal_card(
    recipe: dict,
    family: list[FamilyMember],
) -> str:
    """Format a Telegram-style nutrition card for a single meal.

    Shows per-person portion-adjusted calories and macro breakdown,
    plus any calorie warnings.

    Args:
        recipe: Recipe dict with nutrition data.
        family: List of FamilyMember instances.

    Returns:
        Telegram-formatted markdown string.
    """
    meal = calculate_meal_nutrition(recipe, servings_consumed=1)
    warnings = check_calorie_warnings(recipe, family)
    warning_members = {w["member"] for w in warnings}

    lines: list[str] = []
    name = meal["name"]
    lines.append(f"*{name}*")
    lines.append(
        f"Per portie: {meal['calories']} kcal | "
        f"{meal['protein_g']}g eiwit | "
        f"{meal['carbs_g']}g koolh | "
        f"{meal['fat_g']}g vet"
    )
    lines.append("")

    for member in family:
        portion = calculate_member_portion(member)
        adj_cals = round(meal["calories"] * portion)
        adj_prot = round(meal["protein_g"] * portion)
        adj_carb = round(meal["carbs_g"] * portion)
        adj_fat = round(meal["fat_g"] * portion)
        pct = round(adj_cals / member.daily_calories * 100) if member.daily_calories > 0 else 0

        warn_icon = " ⚠️" if member.name in warning_members else ""
        portion_label = f" ({round(portion * 100)}%)" if portion != 1.0 else ""

        lines.append(
            f"*{member.name}*{portion_label}: "
            f"{adj_cals} kcal ({pct}% dagelijks){warn_icon} | "
            f"{adj_prot}g E | {adj_carb}g K | {adj_fat}g V"
        )

    if warnings:
        lines.append("")
        for w in warnings:
            lines.append(f"⚠️ {w['warning']}")

    return "\n".join(lines)


def _load_recipes(path: str) -> list[dict]:
    """Load recipes from JSON file.

    Args:
        path: Path to recipes JSON file.

    Returns:
        List of recipe dicts.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("recipes", [])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Nutrition tracking and calorie calculations"
    )
    parser.add_argument(
        "--recipes", default="recipes.json", help="Path to recipes JSON file"
    )
    parser.add_argument(
        "--preferences", default="preferences.json",
        help="Path to preferences JSON file with family data",
    )
    parser.add_argument(
        "--week", action="store_true",
        help="Calculate weekly nutrition (expects weekmenu format)",
    )
    parser.add_argument(
        "--telegram", action="store_true",
        help="Format output for Telegram (markdown)",
    )
    parser.add_argument(
        "--family-only", action="store_true",
        help="Show family member recommendations only",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    family = load_family_from_preferences(args.preferences)

    # Show family recommendations only
    if args.family_only:
        if args.json:
            family_data = [
                {
                    "name": m.name,
                    "age": m.age,
                    "gender": m.gender,
                    "pregnant": m.pregnant,
                    "daily_calories": m.daily_calories,
                    "daily_protein_g": m.daily_protein_g,
                    "daily_carbs_g": m.daily_carbs_g,
                    "daily_fat_g": m.daily_fat_g,
                }
                for m in family
            ]
            json.dump(family_data, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            print("Aanbevolen dagelijkse inname per gezinslid:\n")
            for m in family:
                pregnant_str = " (zwanger)" if m.pregnant else ""
                print(f"  {m.name} ({m.age}j, {m.gender}{pregnant_str}):")
                print(f"    Calorieen: {m.daily_calories} kcal")
                print(f"    Eiwit:     {m.daily_protein_g}g")
                print(f"    Koolh:     {m.daily_carbs_g}g")
                print(f"    Vet:       {m.daily_fat_g}g")
                print()
        sys.exit(0)

    # Load recipes
    try:
        recipes = _load_recipes(args.recipes)
    except FileNotFoundError:
        print(f"Error: recipes file not found: {args.recipes}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {args.recipes}: {e}", file=sys.stderr)
        sys.exit(1)

    if args.week:
        # Expect weekmenu format: {"maandag": [...], "dinsdag": [...], ...}
        # or {"weekmenu": {"maandag": {...}, ...}}
        # Try to build weekly meals from recipes
        try:
            with open(args.recipes, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            raw = {}

        weekmenu = raw.get("weekmenu", raw if isinstance(raw, dict) and not isinstance(raw.get("recipes"), list) else {})

        if not weekmenu or "recipes" in weekmenu:
            # Fall back: treat all recipes as a single week, one per day
            days = [
                "maandag", "dinsdag", "woensdag", "donderdag",
                "vrijdag", "zaterdag", "zondag",
            ]
            weekmenu = {}
            for i, recipe in enumerate(recipes[:7]):
                day = days[i % 7]
                meal = calculate_meal_nutrition(recipe)
                weekmenu[day] = [meal]

        else:
            # Parse weekmenu structure
            parsed_menu: dict[str, list[dict]] = {}
            for day, day_data in weekmenu.items():
                if isinstance(day_data, dict):
                    # Single recipe for the day
                    parsed_menu[day] = [calculate_meal_nutrition(day_data)]
                elif isinstance(day_data, list):
                    parsed_menu[day] = [calculate_meal_nutrition(r) for r in day_data]
            weekmenu = parsed_menu

        weekly = calculate_weekly_nutrition(weekmenu)

        if args.telegram:
            print(format_nutrition_summary(weekly, family))
        elif args.json:
            json.dump(weekly, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            print("Weekoverzicht voeding:\n")
            for day, data in weekly["days"].items():
                meals_str = ", ".join(
                    m.get("name", "?") for m in data.get("meals", [])
                )
                print(f"  {day}: {data['calories']} kcal ({meals_str})")

            avg = weekly["daily_averages"]
            print(f"\nGemiddeld per dag: {avg['calories']} kcal | "
                  f"{avg['protein_g']}g eiwit | {avg['carbs_g']}g koolh | "
                  f"{avg['fat_g']}g vet\n")

            print("Vergelijking met aanbevolen inname:\n")
            for m in family:
                comp = compare_to_recommendations(avg, m)
                cal = comp["calories"]
                diff_sign = "+" if cal["diff"] >= 0 else ""
                print(
                    f"  {m.name}: {cal['actual']}/{cal['recommended']} kcal "
                    f"({diff_sign}{cal['diff']}, {cal['pct']}%)"
                )
    else:
        # Calculate per-recipe nutrition
        meal_data = [calculate_meal_nutrition(r) for r in recipes]
        daily = calculate_daily_nutrition(meal_data)

        if args.json:
            json.dump(daily, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            print(f"Voeding voor {len(recipes)} gerecht(en):\n")
            for meal in meal_data:
                print(
                    f"  {meal['name']}: {meal['calories']} kcal | "
                    f"{meal['protein_g']}g eiwit | {meal['carbs_g']}g koolh | "
                    f"{meal['fat_g']}g vet"
                )

            print(f"\n{'─' * 60}")
            print(
                f"Totaal: {daily['calories']} kcal | "
                f"{daily['protein_g']}g eiwit | {daily['carbs_g']}g koolh | "
                f"{daily['fat_g']}g vet\n"
            )

            print("Vergelijking met aanbevolen dagelijkse inname:\n")
            for m in family:
                comp = compare_to_recommendations(daily, m)
                cal = comp["calories"]
                diff_sign = "+" if cal["diff"] >= 0 else ""
                print(
                    f"  {m.name}: {cal['actual']}/{cal['recommended']} kcal "
                    f"({diff_sign}{cal['diff']}, {cal['pct']}%)"
                )
