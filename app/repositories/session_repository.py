from sqlalchemy import select, update
from sqlalchemy.orm import Session as DBSession

from app.models.session import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self, db: DBSession):
        super().__init__(Session, db)

    def revoke_session(self, session_id) -> None:
        self.db.execute(update(Session).where(Session.id == session_id).values(is_revoked=True))
        self.db.commit()

    def get_active_sessions(self, user_id):
        return self.db.execute(
            select(Session).where(Session.user_id == user_id, Session.is_revoked.is_(False))
        ).scalars().all()
