import json
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import Column, DateTime, Float, Integer, Text, create_engine
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
    languages = Column(Text, default="[]")   # stored as JSON string
    status = Column(Text, default="new")
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
)


def create_tables() -> None:
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
