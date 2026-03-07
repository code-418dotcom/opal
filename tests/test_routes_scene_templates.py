"""Tests for scene template CRUD and preview routes."""
from unittest.mock import patch
import pytest


class TestListSceneTemplates:
    @patch("web_api.routes_scene_templates.generate_download_url")
    @patch("web_api.routes_scene_templates.list_scene_templates")
    def test_list_templates(self, mock_list, mock_sas, client):
        mock_list.return_value = [
            {"id": "st_1", "name": "Marble", "prompt": "on marble", "preview_blob_path": "p/preview.png"},
        ]
        mock_sas.return_value = "https://example.com/preview?sig=abc"
        resp = client.get("/v1/scene-templates")
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) == 1
        assert "preview_url" in templates[0]

    @patch("web_api.routes_scene_templates.list_scene_templates")
    def test_list_templates_no_preview(self, mock_list, client):
        mock_list.return_value = [
            {"id": "st_1", "name": "Marble", "prompt": "on marble", "preview_blob_path": None},
        ]
        resp = client.get("/v1/scene-templates")
        assert resp.status_code == 200

    @patch("web_api.routes_scene_templates.list_scene_templates")
    def test_list_by_brand_profile(self, mock_list, client):
        mock_list.return_value = []
        resp = client.get("/v1/scene-templates?brand_profile_id=bp_1")
        assert resp.status_code == 200
        mock_list.assert_called_once_with("tenant_test", brand_profile_id="bp_1")


class TestCreateSceneTemplate:
    @patch("web_api.routes_scene_templates.create_scene_template")
    def test_create_template(self, mock_create, client):
        mock_create.return_value = {"id": "st_new", "name": "Wood", "prompt": "on oak table"}
        resp = client.post("/v1/scene-templates", json={
            "name": "Wood", "prompt": "on oak table",
        })
        assert resp.status_code == 201

    def test_create_missing_fields_422(self, client):
        resp = client.post("/v1/scene-templates", json={"name": "No prompt"})
        assert resp.status_code == 422


class TestDeleteSceneTemplate:
    @patch("web_api.routes_scene_templates.delete_scene_template")
    def test_delete_template(self, mock_delete, client):
        mock_delete.return_value = True
        resp = client.delete("/v1/scene-templates/st_1")
        assert resp.status_code == 204

    @patch("web_api.routes_scene_templates.delete_scene_template")
    def test_delete_nonexistent_404(self, mock_delete, client):
        mock_delete.return_value = False
        resp = client.delete("/v1/scene-templates/st_missing")
        assert resp.status_code == 404
