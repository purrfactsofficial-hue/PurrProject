from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import scheduler
from database import Base, Caption, Episode, ScheduledPost

TEST_DB = "sqlite:///:memory:"


def _make_engine_with_past_post():
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=2)
    with Session(eng) as s:
        s.add(Episode(id=10, number=10, topic="Test", slug="test-ep", category="space"))
        s.add(
            ScheduledPost(
                episode_id=10,
                language="en",
                platform="youtube",
                status="scheduled",
                scheduled_for=past,
            )
        )
        s.commit()
    return eng


def test_check_and_post_publishes_due_post_in_dev_mode():
    eng = _make_engine_with_past_post()
    scheduler.check_and_post(engine=eng, dev_mode=True)
    with Session(eng) as s:
        post = s.query(ScheduledPost).first()
        assert post.status == "published"
        assert post.platform_post_id is not None
        assert post.platform_post_id.startswith("dev-")


def test_check_and_post_does_not_publish_future_post():
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    future = datetime(2099, 1, 1, 0, 0, 0)
    with Session(eng) as s:
        s.add(Episode(id=11, number=11, topic="Future", slug="future", category="space"))
        s.add(
            ScheduledPost(
                episode_id=11,
                language="en",
                platform="youtube",
                status="scheduled",
                scheduled_for=future,
            )
        )
        s.commit()
    scheduler.check_and_post(engine=eng, dev_mode=True)
    with Session(eng) as s:
        post = s.query(ScheduledPost).first()
        assert post.status == "scheduled"


# --- real dispatch tests ---


def _make_engine_with_retryable_post(retry_count=0, minutes_past=2):
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=minutes_past)
    with Session(eng) as s:
        s.add(Episode(id=20, number=20, topic="T", slug="t20", category="space"))
        s.add(
            ScheduledPost(
                episode_id=20,
                language="en",
                platform="youtube",
                status="scheduled",
                scheduled_for=past,
                retry_count=retry_count,
            )
        )
        s.add(
            Caption(
                episode_id=20,
                language="en",
                platform="youtube",
                body="test",
                hashtags=[],
                topic_tag="t",
                source="skill",
            )
        )
        s.commit()
    return eng


@patch("scheduler._dispatch")
@patch("scheduler._resolve_video_path")
def test_real_mode_publishes_post(mock_resolve, mock_dispatch):
    mock_dispatch.return_value = "real-video-id"
    mock_resolve.return_value = MagicMock()

    eng = _make_engine_with_retryable_post()
    scheduler.check_and_post(engine=eng, dev_mode=False)

    with Session(eng) as s:
        post = s.query(ScheduledPost).first()
        assert post.status == "published"
        assert post.platform_post_id == "real-video-id"
        assert post.published_at is not None
        assert post.retry_count == 0


@patch("scheduler._dispatch")
@patch("scheduler._resolve_video_path")
def test_real_mode_retries_on_first_failure(mock_resolve, mock_dispatch):
    mock_dispatch.side_effect = Exception("Network error")
    mock_resolve.return_value = MagicMock()

    eng = _make_engine_with_retryable_post(retry_count=0)
    scheduler.check_and_post(engine=eng, dev_mode=False)

    with Session(eng) as s:
        post = s.query(ScheduledPost).first()
        assert post.status == "scheduled"
        assert post.retry_count == 1
        assert post.error_message == "Network error"
        assert post.scheduled_for > datetime.now(UTC).replace(tzinfo=None)


@patch("scheduler._dispatch")
@patch("scheduler._resolve_video_path")
def test_real_mode_marks_failed_after_max_retries(mock_resolve, mock_dispatch):
    mock_dispatch.side_effect = Exception("Persistent error")
    mock_resolve.return_value = MagicMock()

    eng = _make_engine_with_retryable_post(retry_count=2)  # 2 prior retries → this attempt makes 3
    scheduler.check_and_post(engine=eng, dev_mode=False)

    with Session(eng) as s:
        post = s.query(ScheduledPost).first()
        assert post.status == "failed"
        assert post.retry_count == 3
