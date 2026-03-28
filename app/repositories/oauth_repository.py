from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_account import OAuthAccount
from app.repositories.base import BaseRepository


class OAuthRepository(BaseRepository[OAuthAccount]):
    def __init__(self, db: AsyncSession):
        super().__init__(OAuthAccount, db)

    async def get_by_provider_subject(
        self, *, provider: str, provider_user_id: str
    ) -> Optional[OAuthAccount]:
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_provider(self, *, user_id: UUID, provider: str) -> Optional[OAuthAccount]:
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_link(
        self,
        *,
        user_id: UUID,
        provider: str,
        provider_user_id: str,
        access_token_encrypted: Optional[str],
        refresh_token_encrypted: Optional[str],
    ) -> OAuthAccount:
        existing = await self.get_by_user_provider(user_id=user_id, provider=provider)
        if existing is None:
            existing = OAuthAccount(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
            )
            self.db.add(existing)
        else:
            existing.provider_user_id = provider_user_id
            existing.access_token_encrypted = access_token_encrypted
            existing.refresh_token_encrypted = refresh_token_encrypted

        await self.db.commit()
        await self.db.refresh(existing)
        return existing
