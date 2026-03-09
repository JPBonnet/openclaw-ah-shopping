"""
AH API — Albert Heijn product search
=====================================
Direct implementation without supermarktconnector dependency.
Uses the AH mobile app API (anonymous token, no login required).
"""

import requests

_AH_HEADERS = {
    "Host": "api.ah.nl",
    "x-application": "AHWEBSHOP",
    "user-agent": "Appie/8.8.2 Model/phone Android/7.0-API24",
    "content-type": "application/json; charset=UTF-8",
}

_AUTH_URL = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
_SEARCH_URL = "https://api.ah.nl/mobile-services/product/search/v2"


class AHApi:
    """Lightweight Albert Heijn product search client."""

    def __init__(self):
        self._token = self._get_token()

    def _get_token(self) -> str:
        """Get anonymous access token (no login required)."""
        resp = requests.post(_AUTH_URL, headers=_AH_HEADERS, json={"clientId": "appie"})
        resp.raise_for_status()
        return resp.json()["access_token"]

    def search(self, query: str, size: int = 10) -> list[dict]:
        """
        Search for products by name.
        Returns list of product dicts with: webshopId, title, price, isBonus.
        """
        resp = requests.get(
            _SEARCH_URL,
            headers={**_AH_HEADERS, "Authorization": f"Bearer {self._token}"},
            params={"sortOn": "RELEVANCE", "page": 0, "size": size, "query": query},
        )
        resp.raise_for_status()
        return resp.json().get("products", [])
