"""
Test finalize_job_status logic — especially the fix for premature 'partial' webhook.

Uses an in-memory SQLite database to avoid needing PostgreSQL.
"""
import pytest
from unittest.mock import patch
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.db import Base
from shared.models import Job, JobItem, JobStatus, ItemStatus


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine with jobs/job_items tables."""
    engine = create_engine("sqlite:///:memory:")
    tables = [Job.__table__, JobItem.__table__]
    Base.metadata.create_all(engine, tables=tables)
    return engine


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


def _create_job(session, job_id="job_1", callback_url=None):
    job = Job(
        id=job_id, tenant_id="t1", brand_profile_id="default",
        correlation_id="c1", status=JobStatus.created,
        callback_url=callback_url,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    session.add(job)
    session.commit()
    return job


def _create_item(session, job_id, item_id, status=ItemStatus.created):
    item = JobItem(
        id=item_id, job_id=job_id, tenant_id="t1",
        filename="test.png", status=status,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    session.add(item)
    session.commit()
    return item


def _run_finalize(db_engine, job_id="job_1"):
    """Call finalize_job_status with shared.db.SessionLocal patched to our test engine."""
    TestSession = sessionmaker(bind=db_engine)

    @contextmanager
    def fake_session_local():
        s = TestSession()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    with patch("shared.db.SessionLocal", fake_session_local), \
         patch("shared.pipeline._fire_webhook") as mock_wh:
        from shared.pipeline import finalize_job_status
        finalize_job_status(job_id)
        return mock_wh


class TestFinalizeJobStatus:

    def test_all_completed_sets_completed(self, db_engine, db_session):
        _create_job(db_session, callback_url="https://example.com/hook")
        _create_item(db_session, "job_1", "i1", ItemStatus.completed)
        _create_item(db_session, "job_1", "i2", ItemStatus.completed)

        mock_wh = _run_finalize(db_engine)

        db_session.expire_all()
        job = db_session.get(Job, "job_1")
        assert job.status == JobStatus.completed
        mock_wh.assert_called_once_with("https://example.com/hook", "job_1", "completed")

    def test_all_failed_sets_failed(self, db_engine, db_session):
        _create_job(db_session)
        _create_item(db_session, "job_1", "i1", ItemStatus.failed)
        _create_item(db_session, "job_1", "i2", ItemStatus.failed)

        _run_finalize(db_engine)

        db_session.expire_all()
        job = db_session.get(Job, "job_1")
        assert job.status == JobStatus.failed

    def test_mixed_terminal_sets_partial(self, db_engine, db_session):
        _create_job(db_session)
        _create_item(db_session, "job_1", "i1", ItemStatus.completed)
        _create_item(db_session, "job_1", "i2", ItemStatus.failed)

        _run_finalize(db_engine)

        db_session.expire_all()
        job = db_session.get(Job, "job_1")
        assert job.status == JobStatus.partial

    def test_processing_items_stay_processing(self, db_engine, db_session):
        """If any item is still processing, job stays processing — no webhook."""
        _create_job(db_session, callback_url="https://example.com/hook")
        _create_item(db_session, "job_1", "i1", ItemStatus.completed)
        _create_item(db_session, "job_1", "i2", ItemStatus.processing)

        mock_wh = _run_finalize(db_engine)

        db_session.expire_all()
        job = db_session.get(Job, "job_1")
        assert job.status == JobStatus.processing
        mock_wh.assert_not_called()

    def test_pending_items_stay_processing(self, db_engine, db_session):
        """REGRESSION: items still in created/uploaded should NOT trigger 'partial'."""
        _create_job(db_session, callback_url="https://example.com/hook")
        _create_item(db_session, "job_1", "i1", ItemStatus.failed)
        _create_item(db_session, "job_1", "i2", ItemStatus.created)
        _create_item(db_session, "job_1", "i3", ItemStatus.uploaded)

        mock_wh = _run_finalize(db_engine)

        db_session.expire_all()
        job = db_session.get(Job, "job_1")
        # Should be processing, NOT partial — items haven't been attempted yet
        assert job.status == JobStatus.processing
        mock_wh.assert_not_called()

    def test_no_webhook_when_no_callback_url(self, db_engine, db_session):
        _create_job(db_session, callback_url=None)
        _create_item(db_session, "job_1", "i1", ItemStatus.completed)

        mock_wh = _run_finalize(db_engine)

        db_session.expire_all()
        job = db_session.get(Job, "job_1")
        assert job.status == JobStatus.completed
        mock_wh.assert_not_called()
