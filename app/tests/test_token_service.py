import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.core.redis import close_redis_client, get_redis_client
from app.models.audit_log import AuditLog
from app.models.session import Session
from app.models.user import User
from app.models.user_credentials import UserCredential
from app.repositories.session_repository import SessionRepository
from app.services.token_service import (
    RefreshTokenReuseDetectedError,
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    get_refresh_session_metadata,
    persist_refresh_jti,
    rotate_refresh_token_or_revoke_all,
    verify_access_token,
    verify_refresh_token,
)


def test_access_token_roundtrip() -> None:
    token = create_access_token(user_id="11111111-1111-1111-1111-111111111111", role="admin")
    payload = verify_access_token(token)
    assert payload["sub"] == "11111111-1111-1111-1111-111111111111"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token(user_id="22222222-2222-2222-2222-222222222222", role="user")
    payload = verify_refresh_token(token)
    assert payload["sub"] == "22222222-2222-2222-2222-222222222222"
    assert payload["role"] == "user"
    assert payload["type"] == "refresh"


def test_access_verify_rejects_refresh_token() -> None:
    refresh = create_refresh_token(user_id="22222222-2222-2222-2222-222222222222", role="user")
    with pytest.raises(TokenValidationError):
        verify_access_token(refresh)


def test_refresh_verify_rejects_access_token() -> None:
    access = create_access_token(user_id="11111111-1111-1111-1111-111111111111", role="admin")
    with pytest.raises(TokenValidationError):
        verify_refresh_token(access)


async def _create_user(db) -> User:
    suffix = uuid4().hex[:10]
    user = User(
        email=f"token-{suffix}@test.local",
        username=f"token_{suffix}",
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()

    credential = UserCredential(
        user_id=user.id,
        password_hash="hash",
        password_salt="salt",
        hash_algorithm="argon2id",
    )
    db.add(credential)
    await db.commit()
    await db.refresh(user)
    return user


async def _cleanup_user(db, user_id) -> None:
    await db.execute(delete(AuditLog).where(AuditLog.user_id == user_id))
    await db.execute(delete(Session).where(Session.user_id == user_id))
    await db.execute(delete(UserCredential).where(UserCredential.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    await close_redis_client()


async def _flush_redis() -> None:
    await close_redis_client()
    redis_conn = get_redis_client()
    await redis_conn.flushdb()


def test_refresh_metadata_persist_and_retrieve_real_redis() -> None:
    async def scenario():
        await _flush_redis()
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(minutes=30)
        device_info = {"client": "Mozilla/5.0", "platform": "Mac"}
        jti = f"jti-{uuid4()}"

        await persist_refresh_jti(
            user_id="11111111-1111-1111-1111-111111111111",
            jti=jti,
            device_info=device_info,
            issued_at=issued_at,
            expires_at=expires_at,
            fingerprint="fp-123",
        )

        metadata = await get_refresh_session_metadata(jti=jti)
        assert metadata is not None
        assert metadata["user_id"] == "11111111-1111-1111-1111-111111111111"
        assert metadata["device_info"] == device_info
        assert metadata["fingerprint"] == "fp-123"
        assert metadata["issued_at"] == issued_at.replace(microsecond=0)
        assert metadata["expires_at"] == expires_at.replace(microsecond=0)

    asyncio.run(scenario())


def test_rotation_inherits_metadata_and_updates_timestamps_real_services() -> None:
    async def scenario():
        await _flush_redis()
        db = SessionLocal()
        try:
            user = await _create_user(db)
            user_id = user.id
            issued_at = datetime.now(timezone.utc) - timedelta(minutes=10)
            expires_at = issued_at + timedelta(minutes=30)
            device_info = {"client": "Mozilla/5.0", "platform": "Linux"}

            old_jti = f"jti-old-{uuid4()}"
            new_jti = f"jti-new-{uuid4()}"

            await persist_refresh_jti(
                user_id=str(user.id),
                jti=old_jti,
                device_info=device_info,
                issued_at=issued_at,
                expires_at=expires_at,
                fingerprint="fp-old",
            )
            await SessionRepository(db).create_session(
                user_id=user.id,
                jti=old_jti,
                session_expires_at=datetime.utcnow() + timedelta(minutes=30),
            )

            await rotate_refresh_token_or_revoke_all(
                db=db,
                user_id=str(user.id),
                current_jti=old_jti,
                new_jti=new_jti,
                role=user.role,
            )

            old_metadata = await get_refresh_session_metadata(jti=old_jti)
            new_metadata = await get_refresh_session_metadata(jti=new_jti)
            assert old_metadata is None
            assert new_metadata is not None
            assert new_metadata["device_info"] == device_info
            assert new_metadata["fingerprint"] == "fp-old"
            assert new_metadata["issued_at"] > issued_at
            assert new_metadata["expires_at"] > new_metadata["issued_at"]

            old_session = await SessionRepository(db).get_by_jti(old_jti)
            assert old_session is not None
            assert old_session.is_revoked is True
        finally:
            await db.rollback()
            if "user_id" in locals():
                await _cleanup_user(db, user_id)
            await db.close()

    asyncio.run(scenario())


def test_reuse_detection_revokes_sessions_and_persists_audit_row() -> None:
    async def scenario():
        await _flush_redis()
        db = SessionLocal()
        try:
            user = await _create_user(db)
            user_id = user.id
            jti_1 = f"jti-active-1-{uuid4()}"
            jti_2 = f"jti-active-2-{uuid4()}"

            await persist_refresh_jti(
                user_id=str(user.id),
                jti=jti_1,
                device_info={"client": "Mozilla", "platform": "Linux"},
                fingerprint="fp-1",
            )
            await persist_refresh_jti(
                user_id=str(user.id),
                jti=jti_2,
                device_info={"client": "Chrome", "platform": "Mac"},
                fingerprint="fp-2",
            )
            await SessionRepository(db).create_session(
                user_id=user.id,
                jti=jti_1,
                session_expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
            await SessionRepository(db).create_session(
                user_id=user.id,
                jti=jti_2,
                session_expires_at=datetime.utcnow() + timedelta(minutes=30),
            )

            with pytest.raises(RefreshTokenReuseDetectedError):
                await rotate_refresh_token_or_revoke_all(
                    db=db,
                    user_id=str(user.id),
                    current_jti=f"jti-replayed-{uuid4()}",
                    new_jti=f"jti-new-{uuid4()}",
                    role="admin",
                    ip_address="127.0.0.1",
                    user_agent="pytest-agent/1.0",
                )

            sessions = await SessionRepository(db).get_active_sessions(user.id)
            assert sessions == []

            redis_conn = get_redis_client()
            assert await redis_conn.smembers(f"auth:user:jtis:{user.id}") == set()

            result = await db.execute(
                select(AuditLog)
                .where(
                    AuditLog.user_id == user.id,
                    AuditLog.event_type == "TOKEN_REUSE_DETECTED",
                    AuditLog.ip_address == "127.0.0.1",
                )
                .order_by(AuditLog.created_at.desc())
            )
            audit_row = result.scalars().first()
            assert audit_row is not None
            assert audit_row.user_agent == "pytest-agent/1.0"
            assert len(audit_row.event_metadata["active_refresh_sessions"]) == 2
        finally:
            await db.rollback()
            if "user_id" in locals():
                await _cleanup_user(db, user_id)
            await db.close()

    asyncio.run(scenario())
