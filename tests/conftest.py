"""
Shared test fixtures for FastAPI route testing.
Provides a pre-configured TestClient with auth dependency overrides.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ── Auth user dicts (importable via tests._users) ─────────────────

MOCK_USER = {
    "user_id": "user_test123",
    "tenant_id": "tenant_test",
    "email": "test@example.com",
    "token_balance": 100,
    "is_admin": False,
}

MOCK_ADMIN = {
    "user_id": "user_admin456",
    "tenant_id": "tenant_admin",
    "email": "admin@example.com",
    "token_balance": 999999,
    "is_admin": True,
}

MOCK_APIKEY_USER = {
    "user_id": "apikey",
    "tenant_id": "dev",
    "email": "",
    "token_balance": 999999,
    "is_admin": True,
}


def _make_app(user_override=None):
    """Create a fresh app instance with auth overrides."""
    from web_api.main import app
    from web_api.auth import get_current_user, get_tenant_from_api_key

    user = user_override or MOCK_USER

    async def _mock_user():
        return user

    async def _mock_tenant():
        return user["tenant_id"]

    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_tenant_from_api_key] = _mock_tenant
    return app


@pytest.fixture
def client():
    """TestClient authenticated as a normal user."""
    app = _make_app(MOCK_USER)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client():
    """TestClient authenticated as an admin user."""
    app = _make_app(MOCK_ADMIN)
    # Mock get_user_by_id so require_admin's DB check works without a real DB
    with patch("web_api.routes_admin.get_user_by_id", return_value={"is_admin": True}):
        yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def apikey_client():
    """TestClient authenticated as an API key user (unlimited tokens)."""
    app = _make_app(MOCK_APIKEY_USER)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    return MOCK_USER.copy()


@pytest.fixture
def mock_admin():
    return MOCK_ADMIN.copy()
