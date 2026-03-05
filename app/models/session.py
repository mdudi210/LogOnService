from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )

    device_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_devices.id", ondelete="SET NULL"),
        nullable=True
    )

    jti: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    session_started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    session_expires_at: Mapped[datetime] = mapped_column(
        DateTime
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    revoked_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )

    user = relationship("User", back_populates="sessions")
