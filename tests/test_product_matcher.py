"""Tests for product_matcher.py — ingredient parsing, scoring, and matching."""

import json
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from product_matcher import (
    parse_ingredient,
    score_product,
    _parse_unit_size,
    _normalize_to_grams,
    _token_overlap,
    _fuzzy_similarity,
    _get_avoid_terms,
    _get_brand_scores,
    find_best_product,
    load_preferences,
    load_cache,
    save_cache,
    load_ingredient_aliases,
    resolve_alias,
    PANTRY_ITEMS,
    SKIP_TERMS,
)


class TestParseIngredient:
    """Tests for parse_ingredient function."""

    def test_grams_format(self):
        result = parse_ingredient("500g spaghetti")
        assert result == {"item": "spaghetti", "quantity": 500, "unit": "g"}

    def test_ml_format(self):
        result = parse_ingredient("200ml melk")
        assert result == {"item": "melk", "quantity": 200, "unit": "ml"}

    def test_kg_format(self):
        result = parse_ingredient("1.5kg aardappelen")
        assert result == {"item": "aardappelen", "quantity": 1.5, "unit": "kg"}

    def test_blik_unit(self):
        result = parse_ingredient("2 blik tomaten")
        assert result["item"] == "tomaten"
        assert result["quantity"] == 800  # 2 * 400g
        assert result["unit"] == "g"

    def test_teentje_unit(self):
        result = parse_ingredient("3 teentjes knoflook")
        assert result["item"] == "knoflook"
        assert result["quantity"] == 9  # 3 * 3g
        assert result["unit"] == "g"

    def test_stuks_format(self):
        result = parse_ingredient("3 uien")
        assert result == {"item": "uien", "quantity": 3, "unit": "stuks"}

    def test_unknown_unit_becomes_item(self):
        result = parse_ingredient("2 grote uien")
        assert result["item"] == "grote uien"
        assert result["quantity"] == 2
        assert result["unit"] == "stuks"

    def test_plain_name(self):
        result = parse_ingredient("spaghetti")
        assert result == {"item": "spaghetti", "quantity": 1, "unit": "stuks"}

    def test_comma_decimal(self):
        result = parse_ingredient("1,5kg gehakt")
        assert result["quantity"] == 1.5

    def test_eetlepel_alias(self):
        result = parse_ingredient("2 el olijfolie")
        assert result["quantity"] == 30  # 2 * 15ml
        assert result["unit"] == "ml"


class TestScoreProduct:
    """Tests for product scoring."""

    def test_bonus_product_gets_bonus_points(self, sample_product):
        result = score_product(sample_product, "kipstukjes", 450, "g", prefer_bonus=True)
        assert result["breakdown"]["bonus"] == 20

    def test_no_bonus_when_disabled(self, sample_product):
        result = score_product(sample_product, "kipstukjes", 450, "g", prefer_bonus=False)
        assert result["breakdown"]["bonus"] == 0

    def test_nutriscore_a_gets_max(self, sample_product):
        result = score_product(sample_product, "kipstukjes", 450, "g")
        assert result["breakdown"]["nutriscore"] == 10

    def test_brand_scoring(self, sample_product_no_bonus):
        brand_scores = {"Perla": 15, "AH": 10}
        result = score_product(sample_product_no_bonus, "koffie", 1, "stuks",
                               brand_scores=brand_scores)
        assert result["breakdown"]["brand"] == 15

    def test_brand_scoring_ah(self, sample_product):
        brand_scores = {"Perla": 15, "AH": 10}
        result = score_product(sample_product, "kipstukjes", 450, "g",
                               brand_scores=brand_scores)
        assert result["breakdown"]["brand"] == 10

    def test_packs_needed_calculation(self, sample_product):
        # Product is 450g, need 900g -> 2 packs
        result = score_product(sample_product, "kipstukjes", 900, "g")
        assert result["packs_needed"] == 2

    def test_score_is_positive(self, sample_product):
        result = score_product(sample_product, "kipstukjes", 450, "g")
        assert result["score"] > 0


class TestFuzzyMatching:
    """Tests for fuzzy string matching."""

    def test_exact_match(self):
        assert _fuzzy_similarity("spaghetti", "spaghetti") > 0.8

    def test_substring_match(self):
        assert _fuzzy_similarity("kipstukjes", "AH Kipstukjes naturel") > 0.3

    def test_no_match(self):
        assert _fuzzy_similarity("spaghetti", "bananen") < 0.3

    def test_empty_string(self):
        assert _fuzzy_similarity("", "anything") == 0.0


class TestPreferences:
    """Tests for preference loading and filtering."""

    def test_get_avoid_terms(self, sample_preferences):
        avoid = _get_avoid_terms(sample_preferences)
        assert "kipfilet" in avoid
        assert "koriander" in avoid

    def test_get_brand_scores(self, sample_preferences):
        scores = _get_brand_scores(sample_preferences)
        assert scores["Perla"] == 15
        assert scores["AH"] == 10

    def test_load_preferences_missing_file(self, tmp_path):
        result = load_preferences(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_pantry_detection(self):
        assert "zout" in PANTRY_ITEMS
        assert "spaghetti" not in PANTRY_ITEMS


class TestHelpers:
    """Tests for helper functions."""

    def test_parse_unit_size(self):
        assert _parse_unit_size("500 g") == (500, "g")
        assert _parse_unit_size("1 l") == (1, "l")
        assert _parse_unit_size("") == (0, "")

    def test_normalize_to_grams(self):
        assert _normalize_to_grams(1, "kg") == 1000
        assert _normalize_to_grams(500, "g") == 500
        assert _normalize_to_grams(1, "l") == 1000
        assert _normalize_to_grams(1, "stuks") is None

    def test_token_overlap(self):
        assert _token_overlap("kipstukjes naturel", "AH Kipstukjes naturel") == 1.0
        assert _token_overlap("spaghetti", "bananen") == 0.0


class TestCache:
    """Tests for product match caching."""

    def test_save_and_load_cache(self, tmp_path):
        cache_path = str(tmp_path / "test_cache.json")
        test_data = {"kipstukjes|450|g": {"title": "AH Kipstukjes", "score": 85}}
        save_cache(test_data, cache_path)
        loaded = load_cache(cache_path)
        assert loaded == test_data

    def test_load_empty_cache(self, tmp_path):
        result = load_cache(str(tmp_path / "nonexistent.json"))
        assert result == {}


class TestIngredientAliases:
    """Tests for ingredient alias resolution."""

    def test_load_aliases_from_file(self, tmp_path):
        alias_file = tmp_path / "test_aliases.json"
        alias_file.write_text(json.dumps({
            "kipstukjes": "AH scharrel kipfilet stukjes roerbak",
            "kipbouten": "AH scharrel kipdrumsticks",
        }), encoding="utf-8")
        aliases = load_ingredient_aliases(str(alias_file))
        assert aliases["kipstukjes"] == "AH scharrel kipfilet stukjes roerbak"
        assert aliases["kipbouten"] == "AH scharrel kipdrumsticks"

    def test_load_aliases_missing_file(self, tmp_path):
        result = load_ingredient_aliases(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_resolve_alias_exists(self):
        aliases = {
            "kipstukjes": "AH scharrel kipfilet stukjes roerbak",
            "kippendijen": "AH scharrel kipdijfilet",
        }
        assert resolve_alias("kipstukjes", aliases) == "AH scharrel kipfilet stukjes roerbak"
        assert resolve_alias("kippendijen", aliases) == "AH scharrel kipdijfilet"

    def test_resolve_alias_case_insensitive(self):
        aliases = {"kipstukjes": "AH scharrel kipfilet stukjes roerbak"}
        assert resolve_alias("Kipstukjes", aliases) == "AH scharrel kipfilet stukjes roerbak"

    def test_resolve_alias_not_found(self):
        aliases = {"kipstukjes": "AH scharrel kipfilet stukjes roerbak"}
        assert resolve_alias("spaghetti", aliases) == "spaghetti"

    def test_resolve_alias_strips_whitespace(self):
        aliases = {"kipstukjes": "AH scharrel kipfilet stukjes roerbak"}
        assert resolve_alias("  kipstukjes  ", aliases) == "AH scharrel kipfilet stukjes roerbak"


class TestPlantBasedFiltering:
    """Tests that plant-based products are filtered out when searching meat."""

    def test_skip_terms_include_plant_based(self):
        """SKIP_TERMS must contain plant-based indicators."""
        for term in ["plantaardig", "terra", "vivera", "vegan", "vegetarisch"]:
            assert term in SKIP_TERMS, f"'{term}' should be in SKIP_TERMS"

    def test_plant_based_product_skipped(self, sample_preferences):
        """A product with 'plantaardig' in title should be skipped."""
        plant_product = {
            "webshopId": "999",
            "title": "AH Terra Plantaardig gehakt",
            "brand": "AH Terra",
            "price": 2.99,
            "bonusPrice": None,
            "unitSize": "250 g",
            "unitPriceDescription": "€11.96 per kg",
            "isBonus": False,
            "availableOnline": True,
            "nutriscore": "A",
            "discountLabels": [],
        }
        title = plant_product["title"].lower()
        assert any(skip in title for skip in SKIP_TERMS)

    def test_vivera_product_skipped(self):
        """A product with 'vivera' in title should be skipped."""
        title = "Vivera Plantaardige Kipstukjes".lower()
        assert any(skip in title for skip in SKIP_TERMS)

    def test_real_meat_not_skipped(self):
        """Normal meat products should NOT be skipped."""
        title = "AH Scharrel kipfilet stukjes roerbak".lower()
        assert not any(skip in title for skip in SKIP_TERMS)


class TestAHHuismerkScoring:
    """Tests for AH huismerk title-based bonus scoring."""

    def test_ah_title_gets_brand_points(self):
        """Product with title starting 'AH ' should get brand points even without brand field match."""
        product = {
            "webshopId": "111",
            "title": "AH Scharrel kipfilet stukjes",
            "brand": "",
            "price": 4.99,
            "bonusPrice": None,
            "unitSize": "450 g",
            "unitPriceDescription": "€11.09 per kg",
            "isBonus": False,
            "availableOnline": True,
            "nutriscore": "A",
            "discountLabels": [],
        }
        brand_scores = {"AH": 10, "Perla": 15}
        result = score_product(product, "kipstukjes", 450, "g", brand_scores=brand_scores)
        assert result["breakdown"]["brand"] == 10

    def test_non_ah_title_no_bonus(self):
        """Product without 'AH ' prefix and no brand match should get 0 brand points."""
        product = {
            "webshopId": "222",
            "title": "Kipstukjes naturel",
            "brand": "",
            "price": 5.49,
            "bonusPrice": None,
            "unitSize": "450 g",
            "unitPriceDescription": "€12.20 per kg",
            "isBonus": False,
            "availableOnline": True,
            "nutriscore": "B",
            "discountLabels": [],
        }
        brand_scores = {"AH": 10, "Perla": 15}
        result = score_product(product, "kipstukjes", 450, "g", brand_scores=brand_scores)
        assert result["breakdown"]["brand"] == 0
