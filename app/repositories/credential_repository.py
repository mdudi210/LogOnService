from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_credentials import UserCredential
from app.repositories.base import BaseRepository


class CredentialRepository(BaseRepository[UserCredential]):
    def __init__(self, db: AsyncSession):
        super().__init__(UserCredential, db)

    async def get_by_user_id(self, user_id) -> Optional[UserCredential]:
        result = await self.db.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )
        return result.scalar_one_or_none()
