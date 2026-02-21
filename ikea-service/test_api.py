"""Tests for the IKEA Furniture API.

Unit tests use mocked IKEA API responses.
Integration tests (marked with @pytest.mark.integration) hit the real IKEA API.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.ikea_client import _extract_products, _parse_product

# --- Sample data mimicking real IKEA search API responses ---

SAMPLE_PRODUCT = {
    "id": "00263850",
    "itemNo": "00263850",
    "name": "BILLY",
    "typeName": "Bookcase",
    "itemMeasureReferenceText": "80x28x202 cm",
    "mainImageUrl": "https://www.ikea.com/gb/en/images/products/billy-bookcase-white__s5.jpg",
    "pipUrl": "https://www.ikea.com/gb/en/p/billy-bookcase-white-00263850/",
    "salesPrice": {"currencyCode": "GBP", "numeral": 55.0},
    "allProductImage": [
        {
            "url": "https://www.ikea.com/gb/en/images/products/billy-bookcase-white__s5.jpg",
            "altText": "BILLY Bookcase, white, 80x28x202 cm",
            "type": "MAIN_PRODUCT_IMAGE",
        }
    ],
    "categoryPath": [
        {"name": "Storage furniture"},
        {"name": "Bookcases"},
    ],
    "colors": [{"name": "white", "hex": "ffffff"}],
    "ratingValue": 4.7,
    "ratingCount": 249,
    "validDesignText": "white",
    "gprDescription": {
        "variants": [
            {
                "id": "40477340",
                "name": "BILLY",
                "typeName": "Bookcase",
                "validDesignText": "black oak effect",
                "itemMeasureReferenceText": "80x28x202 cm",
                "salesPrice": {"currencyCode": "GBP", "numeral": 70.0},
                "mainImageUrl": "https://www.ikea.com/gb/en/images/products/billy-black__s5.jpg",
                "pipUrl": "https://www.ikea.com/gb/en/p/billy-bookcase-black-40477340/",
            }
        ]
    },
}

SAMPLE_SEARCH_RESPONSE = {
    "searchResultPage": {
        "products": {
            "main": {
                "items": [
                    {"product": SAMPLE_PRODUCT, "type": "PRODUCT"}
                ]
            }
        }
    }
}

SAMPLE_STOCK_RESPONSE = {
    "availabilities": [
        {
            "availableForCashCarry": True,
            "buyingOption": {
                "cashCarry": {
                    "availability": {"quantity": 24}
                }
            },
        }
    ],
    "timestamp": "2026-02-20T17:00:00Z",
}


# --- Unit tests for parsing logic ---


class TestParseProduct:
    def test_basic_fields(self):
        item = _parse_product(SAMPLE_PRODUCT)
        assert item.item_code == "00263850"
        assert item.name == "BILLY"
        assert item.type_name == "Bookcase"
        assert item.dimensions == "80x28x202 cm"
        assert item.price == 55.0
        assert item.currency == "GBP"
        assert item.color == "white"
        assert item.rating == 4.7
        assert item.rating_count == 249

    def test_urls(self):
        item = _parse_product(SAMPLE_PRODUCT)
        assert item.buy_url == "https://www.ikea.com/gb/en/p/billy-bookcase-white-00263850/"
        assert item.image_url == "https://www.ikea.com/gb/en/images/products/billy-bookcase-white__s5.jpg"

    def test_images(self):
        item = _parse_product(SAMPLE_PRODUCT)
        assert len(item.images) == 1
        assert item.images[0].type == "MAIN_PRODUCT_IMAGE"
        assert item.images[0].alt == "BILLY Bookcase, white, 80x28x202 cm"

    def test_category(self):
        item = _parse_product(SAMPLE_PRODUCT)
        assert item.category == "Bookcases"

    def test_variants(self):
        item = _parse_product(SAMPLE_PRODUCT)
        assert len(item.variants) == 1
        v = item.variants[0]
        assert v.item_code == "40477340"
        assert v.color == "black oak effect"
        assert v.price == 70.0
        assert v.currency == "GBP"

    def test_empty_product(self):
        item = _parse_product({})
        assert item.item_code == ""
        assert item.name is None
        assert item.price is None
        assert item.images == []
        assert item.variants == []

    def test_missing_optional_fields(self):
        minimal = {"id": "12345678", "name": "TEST"}
        item = _parse_product(minimal)
        assert item.item_code == "12345678"
        assert item.name == "TEST"
        assert item.category is None
        assert item.color is None


class TestExtractProducts:
    def test_extracts_products(self):
        products = _extract_products(SAMPLE_SEARCH_RESPONSE)
        assert len(products) == 1
        assert products[0]["id"] == "00263850"

    def test_empty_response(self):
        assert _extract_products({}) == []

    def test_no_items(self):
        response = {"searchResultPage": {"products": {"main": {"items": []}}}}
        assert _extract_products(response) == []


# --- API endpoint tests (mocked IKEA API) ---


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("app.ikea_client.ikea_api.run_async", new_callable=AsyncMock)
async def test_search(mock_run, client):
    mock_run.return_value = SAMPLE_SEARCH_RESPONSE
    resp = await client.get("/search", params={"query": "billy", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "billy"
    assert len(data["items"]) == 1
    assert data["items"][0]["item_code"] == "00263850"
    assert data["items"][0]["price"] == 55.0


@pytest.mark.asyncio
@patch("app.ikea_client.ikea_api.run_async", new_callable=AsyncMock)
async def test_product_found(mock_run, client):
    mock_run.return_value = SAMPLE_SEARCH_RESPONSE
    resp = await client.get("/product/00263850")
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_code"] == "00263850"
    assert data["name"] == "BILLY"
    assert data["dimensions"] == "80x28x202 cm"


@pytest.mark.asyncio
@patch("app.ikea_client.ikea_api.run_async", new_callable=AsyncMock)
async def test_product_not_found(mock_run, client):
    mock_run.return_value = {"searchResultPage": {"products": {"main": {"items": []}}}}
    resp = await client.get("/product/99999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("app.ikea_client.ikea_api.run_async", new_callable=AsyncMock)
async def test_stock(mock_run, client):
    mock_run.return_value = SAMPLE_STOCK_RESPONSE
    resp = await client.get("/stock/00263850")
    assert resp.status_code == 200
    data = resp.json()
    assert data["item_code"] == "00263850"
    assert "availabilities" in data["available"]


@pytest.mark.asyncio
@patch("app.ikea_client.ikea_api.run_async", new_callable=AsyncMock)
async def test_search_ikea_error(mock_run, client):
    mock_run.side_effect = Exception("Connection refused")
    resp = await client.get("/search", params={"query": "test"})
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_search_limit_validation(client):
    resp = await client.get("/search", params={"query": "test", "limit": 0})
    assert resp.status_code == 422

    resp = await client.get("/search", params={"query": "test", "limit": 101})
    assert resp.status_code == 422


# --- Integration tests (hit real IKEA API) ---
# Run with: pytest test_api.py -m integration


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_search(client):
    resp = await client.get("/search", params={"query": "billy bookcase", "limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) > 0
    item = data["items"][0]
    assert item["name"] is not None
    assert item["price"] is not None
    assert item["buy_url"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_product(client):
    resp = await client.get("/product/00263850")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "BILLY"
    assert data["price"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_stock(client):
    resp = await client.get("/stock/00263850")
    assert resp.status_code == 200
    assert "availabilities" in resp.json()["available"]
