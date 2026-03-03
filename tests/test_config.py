"""Regression tests for config — CORS origins."""
from shared.config import Settings


class TestCorsConfig:
    def test_default_cors_origins(self):
        s = Settings()
        origins = [o.strip() for o in s.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
        assert "http://localhost:5173" in origins
        assert "https://ambitious-smoke-04d5b1703.1.azurestaticapps.net" in origins
        assert len(origins) == 3

    def test_cors_origins_parseable(self):
        s = Settings(CORS_ALLOWED_ORIGINS="https://a.com, https://b.com")
        origins = [o.strip() for o in s.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
        assert origins == ["https://a.com", "https://b.com"]

    def test_empty_cors_origins(self):
        s = Settings(CORS_ALLOWED_ORIGINS="")
        origins = [o.strip() for o in s.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
        assert origins == []
