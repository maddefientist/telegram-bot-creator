"""Subscription model."""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.bot import Bot


class SubscriptionState(str, Enum):
    """Subscription states."""
    PENDING = "pending"  # Awaiting first payment
    ACTIVE = "active"  # Paid and valid
    GRACE = "grace"  # Expired but in grace period
    EXPIRED = "expired"  # Fully expired
    CANCELLED = "cancelled"  # User cancelled


class Subscription(Base):
    """Bot subscription model."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    price_per_month_sol: Mapped[float] = mapped_column(
        Numeric(precision=18, scale=9),
        nullable=False,
    )
    state: Mapped[SubscriptionState] = mapped_column(
        String(20),
        nullable=False,
        default=SubscriptionState.PENDING,
        index=True,
    )
    active_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    grace_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    bot: Mapped["Bot"] = relationship(
        "Bot",
        back_populates="subscription",
    )

    def __repr__(self) -> str:
        return f"<Subscription bot={self.bot_id} state={self.state}>"
