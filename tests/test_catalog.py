"""Tests for bulk catalog processing routes and helpers."""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def test_catalog_models():
    """Catalog job and product models have correct enums."""
    from shared.models import CatalogJobStatus, CatalogProductStatus
    assert CatalogJobStatus.created.value == "created"
    assert CatalogJobStatus.processing.value == "processing"
    assert CatalogJobStatus.completed.value == "completed"
    assert CatalogJobStatus.canceled.value == "canceled"
    assert CatalogProductStatus.pending.value == "pending"
    assert CatalogProductStatus.skipped.value == "skipped"


def test_product_id_extraction():
    """Provider helpers extract correct product IDs."""
    from web_api.routes_catalog import _product_id, _product_title, _image_url, _image_id

    shopify_product = {"id": 123, "title": "T-Shirt"}
    assert _product_id(shopify_product, "shopify") == "123"
    assert _product_title(shopify_product, "shopify") == "T-Shirt"

    etsy_listing = {"listing_id": 456, "title": "Handmade Ring"}
    assert _product_id(etsy_listing, "etsy") == "456"
    assert _product_title(etsy_listing, "etsy") == "Handmade Ring"

    wc_product = {"id": 789, "name": "Coffee Mug"}
    assert _product_id(wc_product, "woocommerce") == "789"
    assert _product_title(wc_product, "woocommerce") == "Coffee Mug"


def test_image_helpers():
    """Provider helpers extract correct image URLs and IDs."""
    from web_api.routes_catalog import _image_url, _image_id

    shopify_img = {"id": 1, "src": "https://cdn.shopify.com/img.jpg"}
    assert _image_url(shopify_img, "shopify") == "https://cdn.shopify.com/img.jpg"
    assert _image_id(shopify_img, "shopify") == "1"

    etsy_img = {"listing_image_id": 2, "url_fullxfull": "https://i.etsystatic.com/img.jpg"}
    assert _image_url(etsy_img, "etsy") == "https://i.etsystatic.com/img.jpg"
    assert _image_id(etsy_img, "etsy") == "2"

    wc_img = {"id": 3, "src": "https://shop.example.com/img.jpg"}
    assert _image_url(wc_img, "woocommerce") == "https://shop.example.com/img.jpg"
    assert _image_id(wc_img, "woocommerce") == "3"


def test_product_id_with_enum_provider():
    """Helpers handle IntegrationProvider enum values."""
    from shared.models import IntegrationProvider
    from web_api.routes_catalog import _product_id

    product = {"id": 100, "title": "Test"}
    assert _product_id(product, IntegrationProvider.shopify) == "100"


def test_fetch_all_products_shopify():
    """Shopify pagination fetches all pages."""
    from web_api.routes_catalog import _fetch_all_products

    mock_client = AsyncMock()
    mock_client.get_products = AsyncMock(side_effect=[
        {"products": [{"id": 1}, {"id": 2}], "next_page_info": "page2"},
        {"products": [{"id": 3}], "next_page_info": None},
    ])

    products = asyncio.run(_fetch_all_products(mock_client, "shopify"))
    assert len(products) == 3
    assert mock_client.get_products.call_count == 2


def test_fetch_all_products_etsy():
    """Etsy offset pagination fetches all pages."""
    from web_api.routes_catalog import _fetch_all_products

    mock_client = AsyncMock()
    mock_client.get_listings = AsyncMock(side_effect=[
        {"listings": [{"listing_id": i} for i in range(100)]},
        {"listings": [{"listing_id": 100}]},
    ])

    products = asyncio.run(_fetch_all_products(mock_client, "etsy"))
    assert len(products) == 101


def test_fetch_all_products_woocommerce():
    """WooCommerce page-based pagination fetches all pages."""
    from web_api.routes_catalog import _fetch_all_products

    mock_client = AsyncMock()
    mock_client.get_products = AsyncMock(side_effect=[
        {"products": [{"id": 1}], "total_pages": 2, "page": 1},
        {"products": [{"id": 2}], "total_pages": 2, "page": 2},
    ])

    products = asyncio.run(_fetch_all_products(mock_client, "woocommerce"))
    assert len(products) == 2


def test_estimate_filters_products_without_images():
    """Estimate should only count products that have images."""
    from web_api.routes_catalog import _product_id

    products = [
        {"id": 1, "title": "Has images", "images": [{"id": 10, "src": "x.jpg"}]},
        {"id": 2, "title": "No images", "images": []},
        {"id": 3, "title": "Also no images"},
    ]

    with_images = [p for p in products if p.get("images")]
    assert len(with_images) == 1
    assert _product_id(with_images[0], "shopify") == "1"


def test_catalog_start_body_defaults():
    """CatalogStartIn has sensible defaults."""
    from web_api.routes_catalog import CatalogStartIn

    body = CatalogStartIn()
    assert body.brand_profile_id == "default"
    assert body.auto_push_back is False
    assert body.product_ids is None
    assert body.processing_options["remove_background"] is True
    assert body.processing_options["generate_scene"] is True
    assert body.processing_options["upscale"] is False


def test_catalog_start_body_custom():
    """CatalogStartIn accepts custom values."""
    from web_api.routes_catalog import CatalogStartIn

    body = CatalogStartIn(
        brand_profile_id="brand_abc",
        auto_push_back=True,
        product_ids=["1", "2", "3"],
        processing_options={"remove_background": True, "generate_scene": False, "upscale": False},
    )
    assert body.brand_profile_id == "brand_abc"
    assert body.auto_push_back is True
    assert len(body.product_ids) == 3
    assert body.processing_options["generate_scene"] is False
