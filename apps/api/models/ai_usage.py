"""AI usage tracking model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User
    from models.bot import Bot


class AIUsage(Base):
    """AI usage tracking for rate limiting and quotas."""

    __tablename__ = "ai_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    requests_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="ai_usage",
    )
    bot: Mapped["Bot | None"] = relationship(
        "Bot",
        back_populates="ai_usage",
    )

    def __repr__(self) -> str:
        return f"<AIUsage user={self.user_id} requests={self.requests_count}>"
