from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self, db: AsyncSession):
        super().__init__(Session, db)

    async def revoke_session(self, session_id) -> None:
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        await self.db.commit()

    async def revoke_session_by_jti(self, jti: str) -> None:
        await self.db.execute(
            update(Session)
            .where(Session.jti == jti)
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        await self.db.commit()

    async def create_session(
        self,
        *,
        user_id,
        jti: str,
        session_expires_at: datetime,
        device_id=None,
    ) -> Session:
        if session_expires_at.tzinfo is not None:
            session_expires_at = session_expires_at.astimezone(timezone.utc).replace(tzinfo=None)

        session = Session(
            user_id=user_id,
            device_id=device_id,
            jti=jti,
            session_expires_at=session_expires_at,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_active_sessions(self, user_id):
        result = await self.db.execute(
            select(Session).where(Session.user_id == user_id, Session.is_revoked.is_(False))
        )
        return result.scalars().all()

    async def get_by_jti(self, jti: str) -> Optional[Session]:
        result = await self.db.execute(select(Session).where(Session.jti == jti))
        return result.scalar_one_or_none()

    async def delete_all_user_sessions(self, user_id) -> List[str]:
        result = await self.db.execute(
            delete(Session).where(Session.user_id == user_id).returning(Session.jti)
        )
        await self.db.commit()
        return [jti for jti in result.scalars().all() if jti]

    async def revoke_other_sessions(self, *, user_id, exclude_jti: str) -> List[str]:
        result = await self.db.execute(
            update(Session)
            .where(
                Session.user_id == user_id,
                Session.jti != exclude_jti,
                Session.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=datetime.utcnow())
            .returning(Session.jti)
        )
        await self.db.commit()
        return [jti for jti in result.scalars().all() if jti]
