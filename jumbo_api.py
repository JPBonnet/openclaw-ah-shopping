"""
Jumbo API — Jumbo product search
==================================
Direct implementation without supermarktconnector dependency.
Uses the Jumbo mobile API (no authentication required).
"""

import requests

_JUMBO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:102.0) Gecko/20100101 Firefox/102.0"
}

_API_VERSION = "v17"
_SEARCH_URL = f"https://mobileapi.jumbo.com/{_API_VERSION}/search"


class JumboApi:
    """Lightweight Jumbo product search client."""

    def search(self, query: str, size: int = 10) -> list[dict]:
        """
        Search for products by name.
        Returns list of product dicts with: id, title, price, quantity.
        """
        resp = requests.get(
            _SEARCH_URL,
            headers=_JUMBO_HEADERS,
            params={"q": query, "offset": 0, "limit": size},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("products", {}).get("data", [])

    def get_price(self, product: dict) -> float:
        """Extract price as float from product dict."""
        try:
            return float(product["prices"]["price"]["amount"]) / 100
        except (KeyError, TypeError, ValueError):
            return 0.0
