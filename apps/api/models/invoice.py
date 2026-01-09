"""Invoice model."""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.bot import Bot


class InvoiceStatus(str, Enum):
    """Invoice payment status."""
    PENDING = "pending"  # Awaiting payment
    CONFIRMING = "confirming"  # Transaction found, awaiting confirmations
    PAID = "paid"  # Payment confirmed
    EXPIRED = "expired"  # Not paid before expiry
    CANCELLED = "cancelled"  # Manually cancelled


class Invoice(Base):
    """Payment invoice model."""

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount_sol: Mapped[float] = mapped_column(
        Numeric(precision=18, scale=9),
        nullable=False,
    )
    treasury_address: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # Solana Pay reference key (base58 encoded public key)
    reference: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        String(20),
        nullable=False,
        default=InvoiceStatus.PENDING,
        index=True,
    )
    tx_signature: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    bot: Mapped["Bot"] = relationship(
        "Bot",
        back_populates="invoices",
    )

    def __repr__(self) -> str:
        return f"<Invoice {self.id} amount={self.amount_sol} status={self.status}>"
