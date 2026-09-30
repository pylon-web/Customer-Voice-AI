"""Base declarative class and common model mixins."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Declarative Base with utility helper methods."""

    def to_dict(self) -> dict:
        """Convert model instance columns to a dictionary."""
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
        }


class TimestampMixin:
    """Reusable mixin providing created_at and updated_at UTC timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def generate_uuid() -> str:
    """Generate a clean string UUID4."""
    return str(uuid.uuid4())
