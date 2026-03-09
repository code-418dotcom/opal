"""
Tests for user API key management routes (routes_api_keys.py)
and the auth.py user-key lookup flow.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_USER = {
    "user_id": "usr-abc-123",
    "tenant_id": "tenant_abc",
    "email": "test@example.com",
    "token_balance": 100,
    "is_admin": False,
}

MOCK_ADMIN_KEY_USER = {
    "user_id": "apikey",
    "tenant_id": "dev",
    "email": "",
    "token_balance": 999999,
}


def _make_session_mock(execute_returns=None):
    """Build a mock SessionLocal context manager."""
    session = MagicMock()
    if execute_returns is not None:
        session.execute.return_value = execute_returns
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, session


def _mappings_first(row_dict):
    """Simulate .mappings().first() returning a dict-like row."""
    mock = MagicMock()
    mock.mappings.return_value.first.return_value = row_dict
    return mock


def _mappings_all(rows):
    """Simulate .mappings().all() returning a list of dict-like rows."""
    mock = MagicMock()
    mock.mappings.return_value.all.return_value = rows
    return mock


# ---------------------------------------------------------------------------
# Test key generation
# ---------------------------------------------------------------------------


class TestCreateApiKey:
    def test_key_format(self):
        """Generated keys start with 'opal_' and are ~49 chars."""
        from web_api.routes_api_keys import KEY_PREFIX
        raw_key = KEY_PREFIX + secrets.token_urlsafe(32)
        assert raw_key.startswith("opal_")
        assert len(raw_key) >= 40

    def test_key_hash_is_sha256(self):
        """Key hash is a valid SHA-256 hex digest."""
        from web_api.routes_api_keys import _hash_key
        h = _hash_key("opal_test123")
        assert len(h) == 64  # SHA-256 = 64 hex chars
        assert h == hashlib.sha256(b"opal_test123").hexdigest()

    @patch("web_api.routes_api_keys.new_id", return_value="ak_test123")
    @patch("web_api.routes_api_keys.SessionLocal")
    def test_create_key_returns_plain_key(self, mock_sl, _mock_new_id):
        """POST creates a key and returns the plain key once."""
        from web_api.routes_api_keys import create_api_key, CreateKeyIn

        ctx, session = _make_session_mock()
        mock_sl.return_value = ctx
        # First execute: count query returns 0
        # Second execute: insert (no return needed)
        session.execute.side_effect = [
            _mappings_first({"cnt": 0}),
            MagicMock(),  # insert
        ]

        result = create_api_key(CreateKeyIn(name="My Store"), user=MOCK_USER)

        assert result.key.startswith("opal_")
        assert result.prefix == result.key[:8]
        assert result.name == "My Store"
        assert result.id == "ak_test123"
        session.commit.assert_called_once()

    @patch("web_api.routes_api_keys.SessionLocal")
    def test_create_key_limit_enforced(self, mock_sl):
        """Cannot create more than MAX_KEYS_PER_USER keys."""
        from web_api.routes_api_keys import create_api_key, CreateKeyIn, MAX_KEYS_PER_USER

        ctx, session = _make_session_mock()
        mock_sl.return_value = ctx
        session.execute.return_value = _mappings_first({"cnt": MAX_KEYS_PER_USER})

        with pytest.raises(HTTPException) as exc_info:
            create_api_key(CreateKeyIn(name=""), user=MOCK_USER)
        assert exc_info.value.status_code == 400
        assert "Maximum" in exc_info.value.detail


class TestListApiKeys:
    @patch("web_api.routes_api_keys.SessionLocal")
    def test_list_returns_keys_without_hash(self, mock_sl):
        """List endpoint returns key info but never the hash or full key."""
        from web_api.routes_api_keys import list_api_keys

        now = datetime.now(timezone.utc)
        ctx, session = _make_session_mock()
        mock_sl.return_value = ctx
        session.execute.return_value = _mappings_all([
            {
                "id": "key-1",
                "name": "Store A",
                "key_prefix": "opal_abc",
                "created_at": now,
                "last_used_at": now,
                "is_active": True,
            },
        ])

        result = list_api_keys(user=MOCK_USER)

        assert len(result) == 1
        assert result[0].prefix == "opal_abc"
        assert result[0].name == "Store A"
        assert result[0].is_active is True
        # Verify no key or hash in the response model
        assert not hasattr(result[0], "key")
        assert not hasattr(result[0], "key_hash")

    @patch("web_api.routes_api_keys.SessionLocal")
    def test_list_empty(self, mock_sl):
        """List returns empty array when user has no keys."""
        from web_api.routes_api_keys import list_api_keys

        ctx, session = _make_session_mock()
        mock_sl.return_value = ctx
        session.execute.return_value = _mappings_all([])

        result = list_api_keys(user=MOCK_USER)
        assert result == []


class TestRevokeApiKey:
    @patch("web_api.routes_api_keys.SessionLocal")
    def test_revoke_sets_inactive(self, mock_sl):
        """DELETE sets is_active = FALSE."""
        from web_api.routes_api_keys import revoke_api_key

        ctx, session = _make_session_mock()
        mock_sl.return_value = ctx
        update_result = MagicMock()
        update_result.rowcount = 1
        session.execute.return_value = update_result

        result = revoke_api_key("key-1", user=MOCK_USER)
        assert result is None
        session.commit.assert_called_once()

    @patch("web_api.routes_api_keys.SessionLocal")
    def test_revoke_nonexistent_returns_404(self, mock_sl):
        """DELETE for non-existent key returns 404."""
        from web_api.routes_api_keys import revoke_api_key

        ctx, session = _make_session_mock()
        mock_sl.return_value = ctx
        update_result = MagicMock()
        update_result.rowcount = 0
        session.execute.return_value = update_result

        with pytest.raises(HTTPException) as exc_info:
            revoke_api_key("nonexistent", user=MOCK_USER)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test auth.py user-key lookup
# ---------------------------------------------------------------------------


class TestAuthUserKeyLookup:
    def test_static_key_returns_unlimited(self):
        """Static env var keys still return 999999 tokens."""
        from web_api.auth import _resolve_api_key_user

        with patch("web_api.auth.get_valid_api_keys", return_value={"dev_testkey123"}):
            result = _resolve_api_key_user("dev_testkey123")
        assert result["token_balance"] == 999999
        assert result["user_id"] == "apikey"

    @patch("web_api.auth.SessionLocal")
    def test_user_key_returns_real_balance(self, mock_sl):
        """User-generated key returns the actual user's token balance."""
        from web_api.auth import _resolve_api_key_user
        import uuid

        test_key = "opal_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(test_key.encode()).hexdigest()
        user_id = str(uuid.uuid4())

        ctx, session = _make_session_mock()
        mock_sl.return_value = ctx

        # First call: SELECT returns user row
        # Second call: UPDATE last_used_at
        session.execute.side_effect = [
            _mappings_first({
                "key_id": str(uuid.uuid4()),
                "user_id": user_id,
                "tenant_id": "tenant_xyz",
                "email": "user@shop.com",
                "token_balance": 42,
                "is_admin": False,
            }),
            MagicMock(),  # update
        ]

        with patch("web_api.auth.get_valid_api_keys", return_value=set()):
            result = _resolve_api_key_user(test_key)

        assert result["user_id"] == user_id
        assert result["token_balance"] == 42  # real balance, not 999999
        assert result["email"] == "user@shop.com"
        session.commit.assert_called_once()

    @patch("web_api.auth.SessionLocal")
    def test_invalid_key_raises_403(self, mock_sl):
        """Unknown key raises 403."""
        from web_api.auth import _resolve_api_key_user

        ctx, session = _make_session_mock()
        mock_sl.return_value = ctx
        session.execute.return_value = _mappings_first(None)  # no match

        with patch("web_api.auth.get_valid_api_keys", return_value=set()):
            with pytest.raises(HTTPException) as exc_info:
                _resolve_api_key_user("opal_bogus_key")
            assert exc_info.value.status_code == 403

    def test_key_hash_is_consistent(self):
        """Same key always produces the same hash (for auth lookup)."""
        from web_api.routes_api_keys import _hash_key
        key = "opal_" + secrets.token_urlsafe(32)
        assert _hash_key(key) == _hash_key(key)

    def test_different_keys_produce_different_hashes(self):
        """Different keys produce different hashes (collision resistance)."""
        from web_api.routes_api_keys import _hash_key
        key1 = "opal_" + secrets.token_urlsafe(32)
        key2 = "opal_" + secrets.token_urlsafe(32)
        assert _hash_key(key1) != _hash_key(key2)
