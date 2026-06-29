from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import scheduler
from database import Base, Episode, ScheduledPost

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
