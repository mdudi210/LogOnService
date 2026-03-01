from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_credentials import UserCredential
from app.repositories.base import BaseRepository


class CredentialRepository(BaseRepository[UserCredential]):
    def __init__(self, db: Session):
        super().__init__(UserCredential, db)

    def get_by_user_id(self, user_id) -> Optional[UserCredential]:
        return self.db.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        ).scalar_one_or_none()
