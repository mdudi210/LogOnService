from typing import Any, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


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
        return await self.create(audit_event)

    async def list_security_events(
        self,
        *,
        limit: int = 50,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> list[AuditLog]:
        query = select(AuditLog).where(AuditLog.event_type == "SECURITY_ALERT")
        if severity:
            query = query.where(AuditLog.event_metadata["severity"].astext == severity)
        if alert_type:
            query = query.where(AuditLog.event_metadata["alert_type"].astext == alert_type)

        query = query.order_by(desc(AuditLog.created_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
