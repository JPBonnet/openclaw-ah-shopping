"""
AH API — Albert Heijn product API client
=========================================
Direct implementation without supermarktconnector dependency.
Uses the AH mobile app API (anonymous token, no login required).

Supports: search (with pagination), product details, bonus products,
          categories, token auto-refresh, and connection reuse.
"""

import requests
from typing import Iterator

_AH_HEADERS = {
    "Host": "api.ah.nl",
    "x-application": "AHWEBSHOP",
    "user-agent": "Appie/8.8.2 Model/phone Android/7.0-API24",
    "content-type": "application/json; charset=UTF-8",
}

_AUTH_URL = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
_SEARCH_URL = "https://api.ah.nl/mobile-services/product/search/v2"
_PRODUCT_URL = "https://api.ah.nl/mobile-services/product/detail/v4/fir/{}"
_CATEGORIES_URL = "https://api.ah.nl/mobile-services/v1/product-shelves/categories"
_SUBCATEGORIES_URL = "https://api.ah.nl/mobile-services/v1/product-shelves/categories/{}/sub-categories"

_TIMEOUT = 10


# ── Normalization helpers ─────────────────────────────────

def _normalize_product(p: dict) -> dict:
    """Normalize a raw product from search results into a clean flat dict."""
    price_before_bonus = p.get("priceBeforeBonus")
    price_current = p.get("price")
    try:
        price = float(price_before_bonus if price_before_bonus is not None else price_current or 0)
    except (ValueError, TypeError):
        price = 0.0

    bonus_price = None
    if p.get("isBonus") and price_before_bonus is not None and price_current is not None:
        try:
            bonus_price = float(price_current)
        except (ValueError, TypeError):
            pass

    images = p.get("images") or []

    return {
        # Identity
        "webshopId": str(p.get("webshopId", "")),
        "hqId": p.get("hqId"),
        "title": p.get("title", ""),
        "brand": p.get("brand", ""),

        # Price
        "price": price,
        "bonusPrice": bonus_price,
        "unitSize": p.get("salesUnitSize", ""),
        "unitPriceDescription": p.get("unitPriceDescription", ""),

        # Bonus
        "isBonus": bool(p.get("isBonus", False)),
        "isStapelBonus": bool(p.get("isStapelBonus", False)),
        "isInfiniteBonus": bool(p.get("isInfiniteBonus", False)),
        "discountLabels": p.get("discountLabels", []),

        # Availability
        "availableOnline": bool(p.get("availableOnline", False)),
        "isOrderable": bool(p.get("isOrderable", False)),
        "orderAvailabilityStatus": p.get("orderAvailabilityStatus", ""),

        # Classification
        "mainCategory": p.get("mainCategory", ""),
        "subCategory": p.get("subCategory", ""),
        "shopType": p.get("shopType", ""),

        # Health & dietary
        "nutriscore": p.get("nutriscore", ""),
        "nix18": bool(p.get("nix18", False)),
        "propertyIcons": p.get("propertyIcons", []),

        # Extra
        "descriptionFull": p.get("descriptionFull", ""),
        "descriptionHighlights": p.get("descriptionHighlights", ""),
        "isSponsored": bool(p.get("isSponsored", False)),
        "isPreviouslyBought": bool(p.get("isPreviouslyBought", False)),
        "minBestBeforeDays": p.get("minBestBeforeDays"),

        # Images (largest first)
        "images": [img.get("url", "") for img in images],
        "image": images[0].get("url", "") if images else "",
    }


def _normalize_product_detail(data: dict) -> dict:
    """Normalize a raw product detail response into a clean dict."""
    card = data.get("productCard", {})
    trade = data.get("tradeItem", {})

    base = _normalize_product(card)

    # Allergen info
    allergen_groups = trade.get("allergenInformation", [])
    allergens = []
    for group in allergen_groups:
        for item in group.get("items", []):
            allergens.append({
                "name": item.get("typeCode", {}).get("label", ""),
                "level": item.get("levelOfContainmentCode", {}).get("value", ""),
            })

    # Nutritional info
    nutrition = {}
    for header in trade.get("nutritionalInformation", {}).get("nutrientHeaders", []):
        for detail in header.get("nutrientDetail", []):
            nutrient_type = detail.get("nutrientTypeCode", {}).get("label", "")
            value = detail.get("quantityContained", [{}])
            if value:
                nutrition[nutrient_type] = {
                    "value": value[0].get("value"),
                    "unit": value[0].get("measurementUnitCode", {}).get("value", ""),
                }

    # Ingredients
    ingredients = trade.get("foodAndBeverageIngredientStatement", "")

    # Storage instructions
    consumer = trade.get("consumerInstructions", {})
    storage = consumer.get("storageInstructions", [])
    usage = consumer.get("usageInstructions", [])

    # Certifications / labels
    packaging = trade.get("packagingMarking", {})
    labels = [
        lbl.get("label", "")
        for lbl in packaging.get("localPackagingMarkedLabelAccreditationCodeReference", [])
    ]
    certifications = [
        lbl.get("label", "")
        for lbl in packaging.get("labelAccreditationCode", [])
    ]

    # Measurements
    measurements = trade.get("measurements", {})
    net_content = measurements.get("netContent", [])

    # Marketing
    marketing = trade.get("marketingInformationModule", {})

    # Contact / origin
    contact = trade.get("contactInformation", [])

    base.update({
        # Trade identifiers
        "gtin": trade.get("gtin", ""),

        # Ingredients & allergens
        "ingredients": ingredients,
        "allergens": allergens,

        # Nutrition
        "nutrition": nutrition,

        # Storage & usage
        "storageInstructions": storage,
        "usageInstructions": usage,

        # Labels & certifications
        "labels": labels,
        "certifications": certifications,

        # Measurements
        "netContent": [
            {"value": nc.get("value"), "unit": nc.get("measurementUnitCode", {}).get("value", "")}
            for nc in net_content
        ],

        # Marketing
        "marketingFeatures": marketing.get("tradeItemFeatureBenefit", []),
        "marketingMessage": marketing.get("tradeItemMarketingMessage", ""),

        # Manufacturer
        "manufacturer": contact[0].get("contactName", "") if contact else "",

        # Properties (raw — dietary, intolerance, etc.)
        "properties": data.get("properties") or card.get("properties", {}),
    })

    return base


class AHApi:
    """Albert Heijn product API client with token refresh and connection reuse."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(_AH_HEADERS)
        self._authenticate()

    def _authenticate(self):
        """Get anonymous access token from AH auth API."""
        resp = self._session.post(
            _AUTH_URL, json={"clientId": "appie"}, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        self._session.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a request with automatic token refresh on 401."""
        kwargs.setdefault("timeout", _TIMEOUT)
        resp = self._session.request(method, url, **kwargs)
        if resp.status_code == 401:
            self._authenticate()
            resp = self._session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    # ── Search ────────────────────────────────────────────

    def search(self, query: str, size: int = 10, page: int = 0,
               sort: str = "RELEVANCE", **filters) -> list[dict]:
        """
        Search for products by name.
        Returns list of normalized product dicts.

        Optional filters: bonus ("BONUS"), brand, taxonomy, diet,
        intolerance, nutriscore, diepvries — passed as query params.
        """
        params = {"sortOn": sort, "page": page, "size": size, "query": query}
        for key in ("bonus", "brand", "taxonomy", "diet", "intolerance",
                     "nutriscore", "diepvries"):
            if key in filters and filters[key] is not None:
                params[key] = filters[key]
        resp = self._request("GET", _SEARCH_URL, params=params)
        return [_normalize_product(p) for p in resp.json().get("products", [])]

    def search_all(self, query: str, size: int = 50, **filters) -> Iterator[dict]:
        """Yield all pages of search results (normalized)."""
        page = 0
        while True:
            params = {"sortOn": "RELEVANCE", "page": page, "size": size, "query": query}
            for key in ("bonus", "brand", "taxonomy", "diet", "intolerance",
                         "nutriscore", "diepvries"):
                if key in filters and filters[key] is not None:
                    params[key] = filters[key]
            try:
                resp = self._request("GET", _SEARCH_URL, params=params)
            except Exception:
                break
            data = resp.json()
            products = data.get("products", [])
            if not products:
                break
            yield from (_normalize_product(p) for p in products)
            total_pages = data.get("page", {}).get("totalPages", 1)
            page += 1
            if page >= total_pages:
                break

    # ── Product details ───────────────────────────────────

    def get_product(self, webshop_id: int | str) -> dict:
        """Get full product details by webshopId (normalized)."""
        resp = self._request("GET", _PRODUCT_URL.format(webshop_id))
        return _normalize_product_detail(resp.json())

    # ── Bonus / promotions ────────────────────────────────

    def get_bonus(self, size: int = 50, page: int = 0) -> list[dict]:
        """Get current bonus products via search filter."""
        resp = self._request(
            "GET",
            _SEARCH_URL,
            params={"sortOn": "RELEVANCE", "page": page, "size": size, "query": "", "bonus": "BONUS"},
        )
        return [_normalize_product(p) for p in resp.json().get("products", [])]

    def get_all_bonus(self, size: int = 50) -> list[dict]:
        """Fetch all bonus products across all pages."""
        return list(self.search_all("", size=size, bonus="BONUS"))

    # ── Categories ────────────────────────────────────────

    def get_categories(self) -> list[dict]:
        """Get all top-level product categories."""
        resp = self._request("GET", _CATEGORIES_URL)
        return resp.json()

    def get_subcategories(self, category_id: int) -> dict:
        """Get subcategories for a given category id."""
        resp = self._request("GET", _SUBCATEGORIES_URL.format(category_id))
        return resp.json()
