from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self, db: AsyncSession):
        super().__init__(Session, db)

    async def revoke_session(self, session_id) -> None:
        await self.db.execute(update(Session).where(Session.id == session_id).values(is_revoked=True))
        await self.db.commit()

    async def get_active_sessions(self, user_id):
        result = await self.db.execute(
            select(Session).where(Session.user_id == user_id, Session.is_revoked.is_(False))
        )
        return result.scalars().all()
