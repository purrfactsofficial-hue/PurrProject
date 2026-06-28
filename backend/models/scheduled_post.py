from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Text

from models.base import Base

POST_STATUSES = ("scheduled", "publishing", "published", "failed", "cancelled")


def _in_clause(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    __table_args__ = (
        CheckConstraint(f"status IN ({_in_clause(POST_STATUSES)})", name="ck_posts_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(
        Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language = Column(Text, nullable=False)
    platform = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="scheduled")
    scheduled_for = Column(DateTime, nullable=False)
    platform_post_id = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
