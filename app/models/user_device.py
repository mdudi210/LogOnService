from sqlalchemy import ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, generate_uuid

class UserDevice(Base):
    __tablename__ = "user_devices"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )

    device_name: Mapped[str] = mapped_column(String(255))
    device_fingerprint: Mapped[str] = mapped_column(String(255), index=True)
    user_agent_hash: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(50))

    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="devices")