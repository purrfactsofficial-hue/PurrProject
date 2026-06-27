from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Caption, Video


def _engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def test_caption_row_persists():
    eng = _engine()
    with Session(eng) as s:
        v = Video(
            episode_num=9,
            name="Pizza",
            slug="episode-9-pizza",
            folder_path="/fake",
            languages='["en"]',
            status="draft",
            scanned_at=datetime.now(UTC),
        )
        s.add(v)
        s.flush()
        c = Caption(
            video_id=v.id,
            language="en",
            platform="youtube",
            title="Why Pizza Looks Like a Flag",
            caption="Did you know the first Margherita matched the Italian flag?",
            hashtags="#KidsLearning #Shorts #PurrFacts",
            source="skill",
            updated_at=datetime.now(UTC),
        )
        s.add(c)
        s.commit()
        row = s.query(Caption).first()
        assert row.language == "en"
        assert row.platform == "youtube"
        assert row.source == "skill"


def test_caption_unique_constraint_enforced():
    import pytest
    from sqlalchemy.exc import IntegrityError

    eng = _engine()
    with Session(eng) as s:
        v = Video(
            episode_num=9,
            name="Pizza",
            slug="episode-9-pizza",
            folder_path="/fake",
            languages='["en"]',
            status="draft",
            scanned_at=datetime.now(UTC),
        )
        s.add(v)
        s.flush()
        for _ in range(2):
            s.add(
                Caption(
                    video_id=v.id,
                    language="en",
                    platform="youtube",
                    title="T",
                    caption="C",
                    hashtags="#PurrFacts",
                    source="skill",
                    updated_at=datetime.now(UTC),
                )
            )
        with pytest.raises(IntegrityError):
            s.commit()
