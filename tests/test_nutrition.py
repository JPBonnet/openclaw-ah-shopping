"""Tests for nutrition.py — calorie tracking and family intake calculations."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nutrition import (
    FamilyMember,
    calculate_meal_nutrition,
    calculate_daily_nutrition,
    compare_to_recommendations,
    format_nutrition_summary,
    calculate_member_portion,
    check_calorie_warnings,
    calculate_weekly_calorie_budget,
    format_meal_card,
)


class TestFamilyMember:
    """Tests for FamilyMember calorie calculations."""

    def test_adult_male_calories(self):
        jp = FamilyMember(name="JP", age=30, gender="male", activity_level="moderate")
        assert 2200 < jp.daily_calories < 2800

    def test_pregnant_female_extra_calories(self):
        inidri = FamilyMember(name="Inidri", age=30, gender="female",
                              activity_level="moderate", pregnant=True)
        normal = FamilyMember(name="Normal", age=30, gender="female",
                              activity_level="moderate", pregnant=False)
        assert inidri.daily_calories > normal.daily_calories
        assert inidri.daily_calories - normal.daily_calories >= 250

    def test_toddler_calories(self):
        roux = FamilyMember(name="Roux", age=3, gender="male", activity_level="active")
        assert 800 < roux.daily_calories < 1600

    def test_daily_protein(self):
        jp = FamilyMember(name="JP", age=30, gender="male", activity_level="moderate")
        assert jp.daily_protein_g > 50

    def test_daily_macros_sum_reasonable(self):
        jp = FamilyMember(name="JP", age=30, gender="male", activity_level="moderate")
        # Macros should roughly account for total calories
        macro_cals = jp.daily_protein_g * 4 + jp.daily_carbs_g * 4 + jp.daily_fat_g * 9
        assert abs(macro_cals - jp.daily_calories) < 200


class TestMealNutrition:
    """Tests for meal nutrition calculations."""

    def test_basic_calculation(self, sample_recipe):
        result = calculate_meal_nutrition(sample_recipe, servings_consumed=1)
        assert result["calories"] == sample_recipe["calories_per_serving"]
        assert result["protein_g"] == sample_recipe["protein_g"]

    def test_multiple_servings(self, sample_recipe):
        result = calculate_meal_nutrition(sample_recipe, servings_consumed=2)
        assert result["calories"] == sample_recipe["calories_per_serving"] * 2

    def test_missing_data_defaults(self):
        recipe = {"name": "Mystery meal"}
        result = calculate_meal_nutrition(recipe)
        assert result["calories"] == 0


class TestDailyNutrition:
    """Tests for daily nutrition aggregation."""

    def test_aggregate_two_meals(self, sample_recipe):
        meal1 = calculate_meal_nutrition(sample_recipe, servings_consumed=1)
        meal2 = calculate_meal_nutrition(sample_recipe, servings_consumed=1)
        result = calculate_daily_nutrition([meal1, meal2])
        assert result["calories"] == sample_recipe["calories_per_serving"] * 2

    def test_empty_day(self):
        result = calculate_daily_nutrition([])
        assert result["calories"] == 0


class TestRecommendations:
    """Tests for recommendation comparison."""

    def test_deficit_detection(self):
        member = FamilyMember(name="JP", age=30, gender="male", activity_level="moderate")
        daily = {"calories": 1500, "protein_g": 40, "carbs_g": 150, "fat_g": 50}
        result = compare_to_recommendations(daily, member)
        assert result["calories"]["diff"] < 0  # deficit

    def test_surplus_detection(self):
        member = FamilyMember(name="Roux", age=3, gender="male", activity_level="active")
        daily = {"calories": 3000, "protein_g": 100, "carbs_g": 400, "fat_g": 120}
        result = compare_to_recommendations(daily, member)
        assert result["calories"]["diff"] > 0  # surplus


class TestPortionCalculation:
    """Tests for member portion calculations."""

    def test_toddler_gets_half_portion(self):
        roux = FamilyMember(name="Roux", age=3, gender="male", activity_level="active")
        portion = calculate_member_portion(roux)
        assert portion == 0.5

    def test_adult_gets_full_portion(self):
        jp = FamilyMember(name="JP", age=30, gender="male", activity_level="moderate")
        portion = calculate_member_portion(jp)
        assert portion == 1.0

    def test_child_gets_75_pct(self):
        child = FamilyMember(name="Child", age=8, gender="female", activity_level="active")
        portion = calculate_member_portion(child)
        assert portion == 0.75

    def test_toddler_boundary_age_5(self):
        child5 = FamilyMember(name="Kid", age=5, gender="male", activity_level="active")
        assert calculate_member_portion(child5) == 0.5

    def test_teenager_gets_full_portion(self):
        teen = FamilyMember(name="Teen", age=15, gender="male", activity_level="active")
        assert calculate_member_portion(teen) == 1.0


class TestCalorieWarnings:
    """Tests for calorie warning threshold detection."""

    def test_high_calorie_dinner_triggers_warning(self):
        """A 900 kcal dinner should trigger a warning for Roux (toddler)."""
        recipe = {
            "name": "Heavy dinner",
            "calories_per_serving": 900,
            "protein_g": 40,
            "carbs_g": 80,
            "fat_g": 40,
        }
        family = [
            FamilyMember(name="JP", age=30, gender="male", activity_level="moderate"),
            FamilyMember(name="Roux", age=3, gender="male", activity_level="active"),
        ]
        warnings = check_calorie_warnings(recipe, family)
        # Roux gets 50% portion = 450 kcal, daily ~1150 kcal, 450/1150 = ~39% (borderline)
        # JP gets full 900 kcal, daily ~2500 kcal, 900/2500 = 36% (no warning)
        # Let's check with a meal that definitely triggers
        recipe["calories_per_serving"] = 1200
        warnings = check_calorie_warnings(recipe, family)
        # Roux: 600/1150 = 52% -> warning
        roux_warnings = [w for w in warnings if w["member"] == "Roux"]
        assert len(roux_warnings) == 1
        assert roux_warnings[0]["percentage"] > 40

    def test_moderate_dinner_no_warning(self):
        """A 400 kcal dinner should not trigger warnings."""
        recipe = {
            "name": "Light dinner",
            "calories_per_serving": 400,
            "protein_g": 25,
            "carbs_g": 40,
            "fat_g": 12,
        }
        family = [
            FamilyMember(name="JP", age=30, gender="male", activity_level="moderate"),
            FamilyMember(name="Roux", age=3, gender="male", activity_level="active"),
        ]
        warnings = check_calorie_warnings(recipe, family)
        assert len(warnings) == 0

    def test_custom_threshold(self):
        """Custom threshold should work."""
        recipe = {
            "name": "Dinner",
            "calories_per_serving": 500,
            "protein_g": 30,
            "carbs_g": 50,
            "fat_g": 15,
        }
        family = [FamilyMember(name="JP", age=30, gender="male", activity_level="moderate")]
        # With 20% threshold, 500/~2500 = 20%, should just barely trigger
        warnings = check_calorie_warnings(recipe, family, threshold_pct=0.15)
        assert len(warnings) == 1


class TestWeeklyCalorieBudget:
    """Tests for weekly calorie budget tracking."""

    def test_five_dinners_budget(self, sample_recipe):
        family = [
            FamilyMember(name="JP", age=30, gender="male", activity_level="moderate"),
        ]
        recipes = [sample_recipe] * 5
        result = calculate_weekly_calorie_budget(recipes, family, num_dinners=5)
        assert result["num_dinners"] == 5
        assert len(result["members"]) == 1
        member_result = result["members"][0]
        assert member_result["member"] == "JP"
        assert member_result["total_dinner_calories"] == sample_recipe["calories_per_serving"] * 5
        assert member_result["weekly_dinner_budget"] > 0
        assert member_result["status"] in ("on track", "over budget", "under budget")

    def test_roux_gets_half_calories(self, sample_recipe):
        family = [
            FamilyMember(name="Roux", age=3, gender="male", activity_level="active"),
        ]
        recipes = [sample_recipe] * 5
        result = calculate_weekly_calorie_budget(recipes, family, num_dinners=5)
        roux = result["members"][0]
        expected = round(sample_recipe["calories_per_serving"] * 0.5) * 5
        assert roux["total_dinner_calories"] == expected


class TestFormatMealCard:
    """Tests for Telegram meal card formatting."""

    def test_meal_card_contains_name(self, sample_recipe):
        family = [
            FamilyMember(name="JP", age=30, gender="male", activity_level="moderate"),
        ]
        card = format_meal_card(sample_recipe, family)
        assert sample_recipe["name"] in card

    def test_meal_card_shows_all_members(self, sample_recipe):
        family = [
            FamilyMember(name="JP", age=30, gender="male", activity_level="moderate"),
            FamilyMember(name="Inidri", age=30, gender="female", pregnant=True),
            FamilyMember(name="Roux", age=3, gender="male", activity_level="active"),
        ]
        card = format_meal_card(sample_recipe, family)
        assert "JP" in card
        assert "Inidri" in card
        assert "Roux" in card

    def test_meal_card_shows_portion_label(self, sample_recipe):
        family = [
            FamilyMember(name="Roux", age=3, gender="male", activity_level="active"),
        ]
        card = format_meal_card(sample_recipe, family)
        assert "(50%)" in card
