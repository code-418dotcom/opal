"""Tests for brand profile CRUD routes."""
from unittest.mock import patch
import pytest


class TestCreateBrandProfile:
    @patch("web_api.routes_brand_profiles.create_brand_profile")
    def test_create_profile(self, mock_create, client):
        mock_create.return_value = {"id": "bp_1", "name": "My Brand", "tenant_id": "tenant_test"}
        resp = client.post("/v1/brand-profiles", json={"name": "My Brand"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "My Brand"

    @patch("web_api.routes_brand_profiles.create_brand_profile")
    def test_create_with_all_fields(self, mock_create, client):
        mock_create.return_value = {"id": "bp_1", "name": "Full Brand"}
        resp = client.post("/v1/brand-profiles", json={
            "name": "Full Brand",
            "default_scene_prompt": "on marble table",
            "style_keywords": ["minimal", "luxury"],
            "color_palette": ["#fff", "#000"],
            "mood": "elegant",
            "product_category": "jewelry",
            "default_scene_count": 3,
            "default_scene_types": ["flat_lay", "lifestyle", "studio"],
        })
        assert resp.status_code == 201

    def test_create_missing_name_422(self, client):
        resp = client.post("/v1/brand-profiles", json={})
        assert resp.status_code == 422


class TestListBrandProfiles:
    @patch("web_api.routes_brand_profiles.list_brand_profiles")
    def test_list_profiles(self, mock_list, client):
        mock_list.return_value = [
            {"id": "bp_1", "name": "Brand A"},
            {"id": "bp_2", "name": "Brand B"},
        ]
        resp = client.get("/v1/brand-profiles")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetBrandProfile:
    @patch("web_api.routes_brand_profiles.get_brand_profile")
    def test_get_existing(self, mock_get, client):
        mock_get.return_value = {"id": "bp_1", "name": "My Brand"}
        resp = client.get("/v1/brand-profiles/bp_1")
        assert resp.status_code == 200

    @patch("web_api.routes_brand_profiles.get_brand_profile")
    def test_get_nonexistent_404(self, mock_get, client):
        mock_get.return_value = None
        resp = client.get("/v1/brand-profiles/bp_missing")
        assert resp.status_code == 404


class TestUpdateBrandProfile:
    @patch("web_api.routes_brand_profiles.update_brand_profile")
    def test_update_profile(self, mock_update, client):
        mock_update.return_value = {"id": "bp_1", "name": "Updated Brand"}
        resp = client.put("/v1/brand-profiles/bp_1", json={"name": "Updated Brand"})
        assert resp.status_code == 200

    @patch("web_api.routes_brand_profiles.update_brand_profile")
    def test_update_nonexistent_404(self, mock_update, client):
        mock_update.return_value = None
        resp = client.put("/v1/brand-profiles/bp_missing", json={"name": "X"})
        assert resp.status_code == 404

    def test_update_no_fields_400(self, client):
        resp = client.put("/v1/brand-profiles/bp_1", json={})
        assert resp.status_code == 400


class TestDeleteBrandProfile:
    @patch("web_api.routes_brand_profiles.delete_brand_profile")
    def test_delete_profile(self, mock_delete, client):
        mock_delete.return_value = True
        resp = client.delete("/v1/brand-profiles/bp_1")
        assert resp.status_code == 204

    @patch("web_api.routes_brand_profiles.delete_brand_profile")
    def test_delete_nonexistent_404(self, mock_delete, client):
        mock_delete.return_value = False
        resp = client.delete("/v1/brand-profiles/bp_missing")
        assert resp.status_code == 404
