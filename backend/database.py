from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config import settings
from models import Base, Caption, Episode, Fact, ScheduledPost, Video

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})


def create_tables() -> None:
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


__all__ = [
    "Base",
    "Caption",
    "Episode",
    "Fact",
    "ScheduledPost",
    "Video",
    "create_tables",
    "engine",
    "get_db",
]
