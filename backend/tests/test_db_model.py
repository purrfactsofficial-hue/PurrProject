from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Caption, Episode, Fact, ScheduledPost


def _engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def _episode(s: Session, number: int = 9, topic: str = "Pizza") -> Episode:
    ep = Episode(
        number=number,
        topic=topic,
        slug=f"{topic.lower().replace(' ', '-')}",
        category="food",
        status="draft",
    )
    s.add(ep)
    s.flush()
    return ep


def test_caption_row_persists():
    eng = _engine()
    with Session(eng) as s:
        ep = _episode(s)
        c = Caption(
            episode_id=ep.id,
            language="en",
            platform="youtube",
            title="Why Pizza Looks Like a Flag",
            body="Did you know the first Margherita matched the Italian flag?",
            hashtags=["#KidsLearning", "#Shorts", "#PurrFacts"],
            source="skill",
            updated_at=datetime.now(UTC),
        )
        s.add(c)
        s.commit()
        row = s.query(Caption).first()
        assert row.language == "en"
        assert row.platform == "youtube"
        assert row.source == "skill"
        assert row.hashtags == ["#KidsLearning", "#Shorts", "#PurrFacts"]


def test_caption_unique_constraint_enforced():
    eng = _engine()
    with Session(eng) as s:
        ep = _episode(s)
        for _ in range(2):
            s.add(
                Caption(
                    episode_id=ep.id,
                    language="en",
                    platform="youtube",
                    title="T",
                    body="C",
                    hashtags=["#PurrFacts"],
                    source="skill",
                    updated_at=datetime.now(UTC),
                )
            )
        with pytest.raises(IntegrityError):
            s.commit()


def test_episode_number_unique_constraint_enforced():
    eng = _engine()
    with Session(eng) as s:
        s.add(Episode(number=5, topic="Venus", slug="venus", category="space"))
        s.add(Episode(number=5, topic="Mars", slug="mars", category="space"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_facts_persist_ordered_by_position():
    eng = _engine()
    with Session(eng) as s:
        ep = _episode(s)
        s.add(Fact(episode_id=ep.id, position=2, body="Second fact"))
        s.add(Fact(episode_id=ep.id, position=1, body="First fact"))
        s.commit()
        rows = s.query(Fact).order_by(Fact.position).all()
        assert [r.position for r in rows] == [1, 2]
        assert rows[0].body == "First fact"


def test_facts_unique_position_per_episode_enforced():
    eng = _engine()
    with Session(eng) as s:
        ep = _episode(s)
        s.add(Fact(episode_id=ep.id, position=1, body="A"))
        s.add(Fact(episode_id=ep.id, position=1, body="B"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_scheduled_post_persists():
    eng = _engine()
    with Session(eng) as s:
        ep = _episode(s)
        sp = ScheduledPost(
            episode_id=ep.id,
            language="en",
            platform="youtube",
            status="scheduled",
            scheduled_for=datetime(2025, 7, 5, 0, 0, 0),
        )
        s.add(sp)
        s.commit()
        row = s.query(ScheduledPost).first()
        assert row.language == "en"
        assert row.status == "scheduled"
        assert row.platform_post_id is None


def test_scheduled_post_invalid_status_rejected():
    eng = _engine()
    with Session(eng) as s:
        ep = _episode(s)
        s.add(
            ScheduledPost(
                episode_id=ep.id,
                language="en",
                platform="youtube",
                status="bogus",
                scheduled_for=datetime(2025, 7, 5, 0, 0, 0),
            )
        )
        with pytest.raises(IntegrityError):
            s.commit()
