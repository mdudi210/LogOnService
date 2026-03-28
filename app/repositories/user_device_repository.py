from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_device import UserDevice
from app.repositories.base import BaseRepository


class UserDeviceRepository(BaseRepository[UserDevice]):
    def __init__(self, db: AsyncSession):
        super().__init__(UserDevice, db)

    async def get_by_user_and_fingerprint(
        self, *, user_id: UUID, fingerprint: str
    ) -> Optional[UserDevice]:
        result = await self.db.execute(
            select(UserDevice).where(
                UserDevice.user_id == user_id,
                UserDevice.device_fingerprint == fingerprint,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_from_login(
        self,
        *,
        user_id: UUID,
        fingerprint: str,
        user_agent: str,
        ip_address: str,
        trusted: bool = True,
    ) -> UserDevice:
        existing = await self.get_by_user_and_fingerprint(user_id=user_id, fingerprint=fingerprint)
        user_agent_hash = hashlib.sha256((user_agent or "").encode("utf-8")).hexdigest()
        now = datetime.utcnow()

        if existing is None:
            existing = UserDevice(
                user_id=user_id,
                device_name=(user_agent or "unknown")[:255],
                device_fingerprint=fingerprint,
                user_agent_hash=user_agent_hash,
                ip_address=(ip_address or "unknown")[:50],
                is_trusted=trusted,
                last_used_at=now,
            )
            self.db.add(existing)
        else:
            existing.user_agent_hash = user_agent_hash
            existing.ip_address = (ip_address or "unknown")[:50]
            existing.is_trusted = trusted or existing.is_trusted
            existing.last_used_at = now

        await self.db.commit()
        await self.db.refresh(existing)
        return existing
