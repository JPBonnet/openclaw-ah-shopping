#!/usr/bin/env python3
"""
Supermarkt API — Dutch Supermarket Connectors (No External Dependencies)
========================================================================
Own implementation of Albert Heijn and Jumbo API connectors.
Replaces the 'supermarktconnector' library with zero external dependencies
beyond the standard 'requests' library.

Usage:
    from supermarkt_api import AHConnector, JumboConnector

    # Albert Heijn
    ah = AHConnector()
    results = ah.search_products("kipfilet", size=6)
    for p in results:
        print(p["title"], p["price"], p["webshopId"])

    # Jumbo
    jumbo = JumboConnector()
    results = jumbo.search_products("kipfilet", size=6)
    for p in results:
        print(p["title"], p["price"], p["id"])
"""

import requests
from typing import Iterator


# ══════════════════════════════════════════════════════════════
# Albert Heijn
# ══════════════════════════════════════════════════════════════

AH_HEADERS = {
    "Host": "api.ah.nl",
    "x-application": "AHWEBSHOP",
    "user-agent": "Appie/8.8.2 Model/phone Android/7.0-API24",
    "content-type": "application/json; charset=UTF-8",
}

AH_AUTH_URL = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
AH_SEARCH_URL = "https://api.ah.nl/mobile-services/product/search/v2"
AH_PRODUCT_URL = "https://api.ah.nl/mobile-services/product/detail/v4/fir/{}"
AH_BONUS_URL = "https://api.ah.nl/mobile-services/bonuspage/v1/metadata"


class AHConnector:
    """
    Albert Heijn product API connector.
    Uses anonymous token auth — no AH account needed.
    """

    def __init__(self):
        self._token = self._get_token()

    def _get_token(self) -> str:
        """Get anonymous access token from AH auth API."""
        response = requests.post(
            AH_AUTH_URL,
            headers=AH_HEADERS,
            json={"clientId": "appie"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def _auth_headers(self) -> dict:
        return {**AH_HEADERS, "Authorization": f"Bearer {self._token}"}

    def search_products(self, query: str, size: int = 10, page: int = 0) -> list[dict]:
        """
        Search AH products by query.
        Returns list of simplified product dicts:
            - webshopId: str (use in koopknop URL)
            - title: str
            - price: float
            - isBonus: bool
            - unitSize: str (e.g. "500 g")
        """
        response = requests.get(
            AH_SEARCH_URL,
            params={"sortOn": "RELEVANCE", "page": page, "size": size, "query": query},
            headers=self._auth_headers(),
            timeout=10,
        )
        response.raise_for_status()
        raw_products = response.json().get("products", [])
        return [self._normalize(p) for p in raw_products]

    def search_all_products(self, query: str, size: int = 50) -> Iterator[dict]:
        """Yield all pages of search results."""
        page = 0
        while True:
            response = requests.get(
                AH_SEARCH_URL,
                params={"sortOn": "RELEVANCE", "page": page, "size": size, "query": query},
                headers=self._auth_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            products = data.get("products", [])
            if not products:
                break
            yield from (self._normalize(p) for p in products)
            total_pages = data.get("page", {}).get("totalPages", 1)
            page += 1
            if page >= total_pages:
                break

    def get_product_details(self, webshop_id: int | str) -> dict:
        """Get full product details by webshopId."""
        response = requests.get(
            AH_PRODUCT_URL.format(webshop_id),
            headers=self._auth_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_bonus_products(self) -> list[dict]:
        """Get current bonus/sale products."""
        response = requests.get(
            AH_BONUS_URL,
            headers=self._auth_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize(p: dict) -> dict:
        """Normalize raw AH product to clean format."""
        price_raw = p.get("priceBeforeBonus") or p.get("price") or 0
        try:
            price = float(price_raw)
        except (ValueError, TypeError):
            price = 0.0

        return {
            "webshopId": str(p.get("webshopId", "")),
            "title": p.get("title", ""),
            "price": price,
            "isBonus": bool(p.get("isBonus", False)),
            "unitSize": p.get("unitSize", ""),
            "brand": p.get("brand", ""),
            "category": p.get("mainCategory", ""),
        }


# ══════════════════════════════════════════════════════════════
# Jumbo
# ══════════════════════════════════════════════════════════════

JUMBO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:102.0) Gecko/20100101 Firefox/102.0"
}

JUMBO_API_VERSION = "v17"
JUMBO_SEARCH_URL = f"https://mobileapi.jumbo.com/{JUMBO_API_VERSION}/search"
JUMBO_PRODUCT_URL = f"https://mobileapi.jumbo.com/{JUMBO_API_VERSION}/products/{{}}"
JUMBO_PROMOTIONS_URL = f"https://mobileapi.jumbo.com/{JUMBO_API_VERSION}/promotion-overview"


class JumboConnector:
    """
    Jumbo product API connector.
    No auth needed — public API.
    """

    def search_products(self, query: str, size: int = 10, page: int = 0) -> list[dict]:
        """
        Search Jumbo products by query.
        Returns list of simplified product dicts:
            - id: str
            - title: str
            - price: float
            - isBonus: bool (True if on promotion)
            - unitSize: str
        """
        response = requests.get(
            JUMBO_SEARCH_URL,
            headers=JUMBO_HEADERS,
            params={"offset": page * size, "limit": size, "q": query},
            timeout=10,
        )
        response.raise_for_status()
        raw_products = response.json().get("products", {}).get("data", [])
        return [self._normalize(p) for p in raw_products]

    def search_all_products(self, query: str, size: int = 30) -> Iterator[dict]:
        """Yield all pages of search results (max 30 per page — Jumbo API limit)."""
        size = min(size, 30)  # Jumbo caps at 30
        page = 0
        while True:
            response = requests.get(
                JUMBO_SEARCH_URL,
                headers=JUMBO_HEADERS,
                params={"offset": page * size, "limit": size, "q": query},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json().get("products", {})
            products = data.get("data", [])
            if not products:
                break
            yield from (self._normalize(p) for p in products)
            total = data.get("total", 0)
            page += 1
            if page * size >= total or page * size >= 30:  # Jumbo pagination limit
                break

    def get_product_details(self, product_id: str) -> dict:
        """Get full product details by Jumbo product ID."""
        response = requests.get(
            JUMBO_PRODUCT_URL.format(product_id),
            headers=JUMBO_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("product", {}).get("data", {})

    def get_promotions(self) -> list[dict]:
        """Get current Jumbo promotions/deals."""
        response = requests.get(
            JUMBO_PROMOTIONS_URL,
            headers=JUMBO_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("tabs", [])

    @staticmethod
    def _normalize(p: dict) -> dict:
        """Normalize raw Jumbo product to clean format."""
        price_info = p.get("prices", {})
        price_raw = price_info.get("price", {}).get("amount", 0)
        promo_price = price_info.get("promotionalPrice", {}).get("amount") if price_info.get("promotionalPrice") else None

        try:
            price = float(promo_price or price_raw) / 100  # Jumbo prices are in cents
        except (ValueError, TypeError):
            price = 0.0

        return {
            "id": str(p.get("id", "")),
            "title": p.get("title", ""),
            "price": price,
            "isBonus": bool(p.get("badgeName") or promo_price),
            "unitSize": p.get("quantityOptions", [{}])[0].get("unit", ""),
            "brand": p.get("brandName", ""),
            "category": "",
        }


# ══════════════════════════════════════════════════════════════
# Quick test
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from pprint import pprint

    print("=" * 50)
    print("🛒 Albert Heijn — zoeken naar 'kipfilet'")
    print("=" * 50)
    ah = AHConnector()
    ah_results = ah.search_products("kipfilet", size=3)
    for p in ah_results:
        bonus = " 🏷️ BONUS" if p["isBonus"] else ""
        print(f"  [{p['webshopId']}] {p['title']} — €{p['price']:.2f}{bonus}")

    print()
    print("=" * 50)
    print("🛒 Jumbo — zoeken naar 'kipfilet'")
    print("=" * 50)
    jumbo = JumboConnector()
    jumbo_results = jumbo.search_products("kipfilet", size=3)
    for p in jumbo_results:
        bonus = " 🏷️ BONUS" if p["isBonus"] else ""
        print(f"  [{p['id']}] {p['title']} — €{p['price']:.2f}{bonus}")
