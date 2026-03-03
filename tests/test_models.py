"""Regression tests for SQLAlchemy models — ensure new fields are defined."""
from shared.models import BrandProfile, Job, JobItem


class TestBrandProfileModel:
    def test_has_expected_columns(self):
        cols = {c.name for c in BrandProfile.__table__.columns}
        expected = {
            "id", "tenant_id", "name", "default_scene_prompt",
            "style_keywords", "color_palette", "mood",
            "created_at", "updated_at",
        }
        assert expected.issubset(cols), f"Missing columns: {expected - cols}"

    def test_tablename(self):
        assert BrandProfile.__tablename__ == "brand_profiles"


class TestJobModel:
    def test_has_callback_url(self):
        cols = {c.name for c in Job.__table__.columns}
        assert "callback_url" in cols

    def test_has_processing_options(self):
        cols = {c.name for c in Job.__table__.columns}
        assert "processing_options" in cols

    def test_callback_url_nullable(self):
        col = Job.__table__.c.callback_url
        assert col.nullable is True
