"""Tests for meal_cart.py — ingredient resolution and cart building."""

import json
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from meal_cart import resolve_ingredients


class TestResolveIngredients:
    """Tests for the resolve_ingredients pipeline."""

    @patch("meal_cart.find_best_product")
    def test_matched_products(self, mock_find):
        mock_find.return_value = {
            "webshopId": "123",
            "title": "AH Spaghetti",
            "price": 1.29,
            "bonusPrice": None,
            "isBonus": False,
            "packs_needed": 1,
            "score": 75,
        }
        api = MagicMock()
        ingredients = [{"item": "spaghetti", "quantity": 500, "unit": "g"}]
        result = resolve_ingredients(api, ingredients)
        assert len(result["matched"]) == 1
        assert result["total_price"] > 0

    @patch("meal_cart.find_best_product")
    def test_pantry_items_skipped(self, mock_find):
        mock_find.return_value = {"pantry": True, "item": "zout"}
        api = MagicMock()
        ingredients = [{"item": "zout", "quantity": 1, "unit": "stuks"}]
        result = resolve_ingredients(api, ingredients)
        assert len(result["matched"]) == 0
        assert "zout" in result["pantry"]

    @patch("meal_cart.find_best_product")
    def test_not_found_items(self, mock_find):
        mock_find.return_value = None
        api = MagicMock()
        ingredients = [{"item": "rare_ingredient", "quantity": 1, "unit": "stuks"}]
        result = resolve_ingredients(api, ingredients)
        assert "rare_ingredient" in result["not_found"]

    @patch("meal_cart.find_best_product")
    def test_bonus_savings_calculated(self, mock_find):
        mock_find.return_value = {
            "webshopId": "456",
            "title": "AH Kipstukjes",
            "price": 5.00,
            "bonusPrice": 3.50,
            "isBonus": True,
            "packs_needed": 1,
            "score": 80,
        }
        api = MagicMock()
        ingredients = [{"item": "kipstukjes", "quantity": 1, "unit": "stuks"}]
        result = resolve_ingredients(api, ingredients)
        assert result["bonus_savings"] == 1.50

    @patch("meal_cart.find_best_product")
    def test_string_ingredient_format(self, mock_find):
        mock_find.return_value = {
            "webshopId": "789",
            "title": "AH Uien",
            "price": 1.00,
            "bonusPrice": None,
            "isBonus": False,
            "packs_needed": 1,
            "score": 60,
        }
        api = MagicMock()
        ingredients = ["3 uien"]
        result = resolve_ingredients(api, ingredients)
        assert len(result["matched"]) == 1

    @patch("meal_cart.find_best_product")
    def test_empty_list(self, mock_find):
        api = MagicMock()
        result = resolve_ingredients(api, [])
        assert result["matched"] == []
        assert result["total_price"] == 0.0
