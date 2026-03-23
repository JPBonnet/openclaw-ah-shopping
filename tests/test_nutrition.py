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
