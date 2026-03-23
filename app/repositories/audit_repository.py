from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository
from app.services.security_event_service import emit_security_event
from sqlalchemy import desc, select


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)

    async def create_event(
        self,
        *,
        event_type: str,
        metadata: dict[str, Any],
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        audit_event = AuditLog(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata=metadata,
        )
        created = await self.create(audit_event)
        await emit_security_event(
            event_type=event_type,
            metadata=metadata,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return created

    async def list_recent_events(
        self,
        *,
        limit: int = 50,
        event_types: Optional[list[str]] = None,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        if event_types:
            stmt = stmt.where(AuditLog.event_type.in_(event_types))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
