from typing import Optional

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    username: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default="user"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    totp_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    deleted_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )

    # Relationships
    credentials = relationship("UserCredential", back_populates="user", uselist=False)
    devices = relationship("UserDevice", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    mfa_methods = relationship("UserMFA", back_populates="user")
    oauth_accounts = relationship("OAuthAccount", back_populates="user")
