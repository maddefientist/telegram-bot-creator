"""User model."""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.bot import Bot
    from models.ai_usage import AIUsage
    from models.audit_log import AuditLog


class UserRole(str, Enum):
    """User roles."""
    USER = "user"
    ADMIN = "admin"


class AuthMethod(str, Enum):
    """Authentication methods."""
    EMAIL = "email"
    WALLET = "wallet"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    wallet_address: Mapped[str | None] = mapped_column(
        String(44),
        unique=True,
        nullable=True,
        index=True,
    )
    auth_method: Mapped[AuthMethod] = mapped_column(
        String(20),
        nullable=False,
        default=AuthMethod.EMAIL,
    )
    role: Mapped[UserRole] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.USER,
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
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
    bots: Mapped[list["Bot"]] = relationship(
        "Bot",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    ai_usage: Mapped[list["AIUsage"]] = relationship(
        "AIUsage",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        identifier = self.email if self.auth_method == AuthMethod.EMAIL else self.wallet_address
        return f"<User {identifier} ({self.auth_method.value})>"
