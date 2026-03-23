"""Tests for seasonal.py — season detection and recipe filtering."""

import pytest
from datetime import date
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from seasonal import (
    get_current_season,
    get_seasonal_ingredients,
    filter_recipes_by_season,
    get_seasonal_suggestions,
)


class TestSeasonDetection:
    """Tests for season detection."""

    def test_winter_december(self):
        assert get_current_season(date(2026, 12, 15)) == "winter"

    def test_winter_january(self):
        assert get_current_season(date(2026, 1, 15)) == "winter"

    def test_lente_march(self):
        assert get_current_season(date(2026, 3, 15)) == "lente"

    def test_zomer_july(self):
        assert get_current_season(date(2026, 7, 15)) == "zomer"

    def test_herfst_october(self):
        assert get_current_season(date(2026, 10, 15)) == "herfst"

    def test_default_uses_today(self):
        season = get_current_season()
        assert season in ("lente", "zomer", "herfst", "winter")


class TestSeasonalIngredients:
    """Tests for seasonal ingredient lists."""

    def test_winter_has_boerenkool(self):
        ingredients = get_seasonal_ingredients("winter")
        assert "boerenkool" in ingredients

    def test_zomer_has_aardbeien(self):
        ingredients = get_seasonal_ingredients("zomer")
        assert "aardbeien" in ingredients

    def test_lente_has_asperges(self):
        ingredients = get_seasonal_ingredients("lente")
        assert "asperges" in ingredients

    def test_herfst_has_pompoen(self):
        ingredients = get_seasonal_ingredients("herfst")
        assert "pompoen" in ingredients

    def test_unknown_season_raises_error(self):
        with pytest.raises(ValueError):
            get_seasonal_ingredients("unknown")


class TestRecipeFiltering:
    """Tests for recipe filtering by season."""

    def test_filter_winter(self, sample_recipes):
        result = filter_recipes_by_season(sample_recipes, "winter")
        names = [r["name"] for r in result]
        assert "Stamppot boerenkool" in names
        assert "Nasi goreng" in names  # 'all' season
        assert "Griekse salade" not in names

    def test_filter_zomer(self, sample_recipes):
        result = filter_recipes_by_season(sample_recipes, "zomer")
        names = [r["name"] for r in result]
        assert "Griekse salade" in names
        assert "Nasi goreng" in names  # 'all' season

    def test_all_season_always_included(self, sample_recipes):
        for season in ("lente", "zomer", "herfst", "winter"):
            result = filter_recipes_by_season(sample_recipes, season)
            names = [r["name"] for r in result]
            assert "Nasi goreng" in names


class TestSeasonalSuggestions:
    """Tests for seasonal cooking suggestions."""

    def test_suggestions_have_methods(self):
        suggestions = get_seasonal_suggestions("winter")
        assert "methods" in suggestions

    def test_winter_suggests_stoven(self):
        suggestions = get_seasonal_suggestions("winter")
        assert "stoven" in suggestions["methods"] or "stoofpot" in suggestions["methods"]

    def test_zomer_has_methods(self):
        suggestions = get_seasonal_suggestions("zomer")
        assert len(suggestions["methods"]) > 0
