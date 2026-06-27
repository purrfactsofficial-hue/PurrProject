from collections.abc import Generator
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session

from config import settings


class Base(DeclarativeBase):
    pass


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_num = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    folder_path = Column(Text, nullable=False)
    primary_file = Column(Text)
    duration_secs = Column(Float)
    size_bytes = Column(Integer)
    thumbnail_path = Column(Text)
    languages = Column(Text, default="[]")
    status = Column(Text, default="new")
    scanned_at = Column(DateTime, default=lambda: datetime.now(UTC))


class Caption(Base):
    __tablename__ = "captions"
    __table_args__ = (UniqueConstraint("video_id", "language", "platform"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    language = Column(Text, nullable=False)
    platform = Column(Text, nullable=False)
    title = Column(Text)
    caption = Column(Text, nullable=False)
    hashtags = Column(Text, nullable=False)
    source = Column(Text, nullable=False, default="skill")
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC))


engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})


def create_tables() -> None:
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
