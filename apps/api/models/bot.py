"""Bot model."""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.subscription import Subscription
    from models.invoice import Invoice
    from models.ai_usage import AIUsage


class BotStatus(str, Enum):
    """Bot operational status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    DELETED = "deleted"


class Bot(Base):
    """Telegram bot model."""

    __tablename__ = "bots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    telegram_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    telegram_username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    spec_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[BotStatus] = mapped_column(
        String(20),
        nullable=False,
        default=BotStatus.STOPPED,
        index=True,
    )
    container_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
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
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="bots",
    )
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription",
        back_populates="bot",
        uselist=False,
        cascade="all, delete-orphan",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="bot",
        cascade="all, delete-orphan",
    )
    ai_usage: Mapped[list["AIUsage"]] = relationship(
        "AIUsage",
        back_populates="bot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Bot {self.name} ({self.status})>"
