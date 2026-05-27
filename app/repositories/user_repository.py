from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.credentials),
                selectinload(User.sessions),
                selectinload(User.mfa_methods),
                selectinload(User.oauth_accounts),
            )
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.credentials),
                selectinload(User.sessions),
                selectinload(User.mfa_methods),
                selectinload(User.oauth_accounts),
            )
            .where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_relationships(self, user_id) -> Optional[User]:
        """Example async CRUD read with eager loading to avoid MissingGreenlet."""
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.credentials),
                selectinload(User.sessions),
                selectinload(User.mfa_methods),
                selectinload(User.oauth_accounts),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_admin_auth_view(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.mfa_methods),
                selectinload(User.oauth_accounts),
            )
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
