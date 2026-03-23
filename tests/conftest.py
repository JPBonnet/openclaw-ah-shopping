"""Shared test fixtures for ah-shopping tests."""

import json
import pytest
from pathlib import Path


@pytest.fixture
def sample_product() -> dict:
    """A realistic AH product dict as returned by the API."""
    return {
        "webshopId": "123456",
        "hqId": 789,
        "title": "AH Kipstukjes naturel",
        "brand": "AH",
        "price": 4.99,
        "bonusPrice": 3.99,
        "unitSize": "450 g",
        "unitPriceDescription": "€8.87 per kg",
        "isBonus": True,
        "isStapelBonus": False,
        "isInfiniteBonus": False,
        "discountLabels": [{"defaultDescription": "25% korting"}],
        "availableOnline": True,
        "isOrderable": True,
        "orderAvailabilityStatus": "IN_ASSORTMENT",
        "mainCategory": "Vlees, kip, vis, vega",
        "subCategory": "Kipfilet en kipstukjes",
        "shopType": "REGULAR",
        "nutriscore": "A",
        "nix18": False,
        "propertyIcons": [],
        "descriptionFull": "",
        "descriptionHighlights": "",
        "isSponsored": False,
        "isPreviouslyBought": False,
        "minBestBeforeDays": None,
        "images": [],
        "image": "",
    }


@pytest.fixture
def sample_product_no_bonus() -> dict:
    """A product without bonus."""
    return {
        "webshopId": "654321",
        "title": "Perla Huisblend filterkoffie",
        "brand": "Perla",
        "price": 3.49,
        "bonusPrice": None,
        "unitSize": "250 g",
        "unitPriceDescription": "€13.96 per kg",
        "isBonus": False,
        "availableOnline": True,
        "nutriscore": "",
        "discountLabels": [],
    }


@pytest.fixture
def sample_preferences() -> dict:
    """Test preferences matching the project's preferences.json structure."""
    return {
        "family": {
            "members": [
                {"name": "JP", "age": 30, "gender": "male", "activity_level": "moderate", "pregnant": False},
                {"name": "Inidri", "age": 30, "gender": "female", "activity_level": "moderate", "pregnant": True},
                {"name": "Roux", "age": 3, "gender": "male", "activity_level": "active", "pregnant": False},
            ],
            "default_servings": 2,
        },
        "budget": {"max_weekly_euros": 150, "prefer_bonus": True},
        "brand_preferences": {
            "brand_scores": {"Perla": 15, "AH": 10},
            "avoid_brands": [],
        },
        "protein_preferences": {
            "avoid": ["kipfilet"],
            "prefer": ["kipstukjes", "kippendijen"],
        },
        "dietary": {
            "avoid_ingredients": ["koriander", "cilantro"],
            "allergies": [],
        },
    }


@pytest.fixture
def sample_recipe() -> dict:
    """A sample recipe for testing."""
    return {
        "name": "Spaghetti Bolognese",
        "description": "Klassieke Italiaanse pasta met gehaktsaus",
        "cuisine": "Italiaans",
        "method": "kookplaat",
        "protein": "rund",
        "season": "all",
        "difficulty": "easy",
        "servings": 4,
        "prep_time_min": 10,
        "cook_time_min": 25,
        "ingredients": [
            {"item": "spaghetti", "quantity": 500, "unit": "g"},
            {"item": "rundergehakt", "quantity": 500, "unit": "g"},
            {"item": "uien", "quantity": 2, "unit": "stuks"},
            {"item": "knoflook", "quantity": 2, "unit": "teentjes"},
            {"item": "tomatenblokjes", "quantity": 400, "unit": "g"},
        ],
        "calories_per_serving": 580,
        "protein_g": 32,
        "carbs_g": 65,
        "fat_g": 18,
        "tags": ["budget", "comfort", "kid-friendly"],
    }


@pytest.fixture
def sample_recipes() -> list[dict]:
    """Multiple sample recipes for filtering tests."""
    return [
        {
            "name": "Stamppot boerenkool",
            "cuisine": "Nederlands",
            "method": "kookplaat",
            "protein": "varken",
            "season": "winter",
            "difficulty": "easy",
            "servings": 4,
            "prep_time_min": 15,
            "cook_time_min": 25,
            "calories_per_serving": 520,
            "protein_g": 28,
            "carbs_g": 55,
            "fat_g": 20,
            "tags": ["comfort", "budget"],
            "ingredients": [
                {"item": "boerenkool", "quantity": 500, "unit": "g"},
                {"item": "aardappelen", "quantity": 1000, "unit": "g"},
                {"item": "rookworst", "quantity": 1, "unit": "stuks"},
            ],
        },
        {
            "name": "Griekse salade",
            "cuisine": "Mediterraan",
            "method": "kookplaat",
            "protein": "vegetarisch",
            "season": "zomer",
            "difficulty": "easy",
            "servings": 2,
            "prep_time_min": 10,
            "cook_time_min": 0,
            "calories_per_serving": 320,
            "protein_g": 12,
            "carbs_g": 18,
            "fat_g": 24,
            "tags": ["healthy", "quick"],
            "ingredients": [
                {"item": "komkommer", "quantity": 1, "unit": "stuks"},
                {"item": "tomaten", "quantity": 3, "unit": "stuks"},
                {"item": "feta", "quantity": 200, "unit": "g"},
            ],
        },
        {
            "name": "Nasi goreng",
            "cuisine": "Aziatisch",
            "method": "wok",
            "protein": "kip",
            "season": "all",
            "difficulty": "easy",
            "servings": 4,
            "prep_time_min": 15,
            "cook_time_min": 15,
            "calories_per_serving": 480,
            "protein_g": 26,
            "carbs_g": 58,
            "fat_g": 16,
            "tags": ["quick", "kid-friendly"],
            "ingredients": [
                {"item": "rijst", "quantity": 400, "unit": "g"},
                {"item": "kipstukjes", "quantity": 300, "unit": "g"},
                {"item": "sojasaus", "quantity": 2, "unit": "el"},
            ],
        },
    ]
