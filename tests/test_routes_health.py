"""Tests for health check routes."""
from unittest.mock import patch
import pytest


class TestHealthz:
    @patch("web_api.routes_health._check_storage", return_value=True)
    @patch("web_api.routes_health._check_db", return_value=True)
    def test_healthy(self, mock_db, mock_storage, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @patch("web_api.routes_health._check_storage", return_value=True)
    @patch("web_api.routes_health._check_db", return_value=False)
    def test_db_down_degraded(self, mock_db, mock_storage, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["db"] == "fail"

    @patch("web_api.routes_health._check_storage", return_value=False)
    @patch("web_api.routes_health._check_db", return_value=True)
    def test_storage_down_degraded(self, mock_db, mock_storage, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"


class TestReadyz:
    @patch("web_api.routes_health._check_storage", return_value=True)
    @patch("web_api.routes_health._check_db", return_value=True)
    def test_ready(self, mock_db, mock_storage, client):
        resp = client.get("/readyz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @patch("web_api.routes_health._check_storage", return_value=False)
    @patch("web_api.routes_health._check_db", return_value=False)
    def test_not_ready(self, mock_db, mock_storage, client):
        resp = client.get("/readyz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "not-ready"
