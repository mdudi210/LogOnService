from datetime import datetime
from uuid import UUID

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_password_salt, hash_password, verify_password
from app.models.user import User
from app.models.user_credentials import UserCredential
from app.repositories.audit_repository import AuditRepository
from app.repositories.credential_repository import CredentialRepository
from app.repositories.user_repository import UserRepository


def validate_user_password(plain_password: str, stored_hash: str, salt: str) -> bool:
    return verify_password(plain_password, stored_hash, salt)


def create_password_material(plain_password: str) -> tuple[str, str]:
    salt = generate_password_salt()
    password_hash = hash_password(plain_password, salt)
    return password_hash, salt


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class InvalidOldPasswordError(Exception):
    pass


class AuthService:
    def __init__(self, db: AsyncSession, audit_repository: Optional[AuditRepository] = None):
        self.db = db
        self.user_repository = UserRepository(db)
        self.credential_repository = CredentialRepository(db)
        self.audit_repository = audit_repository or AuditRepository(db)

    async def login(self, email_or_username: str, password: str) -> User:
        identifier = email_or_username.strip()
        if not identifier:
            raise InvalidCredentialsError("Invalid credentials")

        user = await self.user_repository.get_by_email(identifier.lower())
        if user is None:
            user = await self.user_repository.get_by_username(identifier)

        if user is None:
            raise InvalidCredentialsError("Invalid credentials")
        if user.deleted_at is not None or not user.is_active:
            raise InactiveUserError("User account is inactive")

        credential = user.credentials
        if credential is None:
            raise InvalidCredentialsError("Invalid credentials")
        if not credential.password_salt:
            raise InvalidCredentialsError("Invalid credentials")
        if not validate_user_password(password, credential.password_hash, credential.password_salt):
            raise InvalidCredentialsError("Invalid credentials")

        return user

    async def register_user(
        self,
        *,
        email: str,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        normalized_email = email.strip().lower()
        normalized_username = username.strip()
        if not normalized_email or not normalized_username:
            raise ValueError("Email and username are required")

        if await self.user_repository.get_by_email(normalized_email):
            raise UserAlreadyExistsError("Email already exists")
        if await self.user_repository.get_by_username(normalized_username):
            raise UserAlreadyExistsError("Username already exists")

        password_hash, password_salt = create_password_material(password)
        user = User(
            email=normalized_email,
            username=normalized_username,
            role="user",
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.flush()

        credentials = UserCredential(
            user_id=user.id,
            password_hash=password_hash,
            password_salt=password_salt,
            hash_algorithm="argon2id",
            password_changed_at=datetime.utcnow(),
        )
        self.db.add(credentials)
        await self.db.commit()
        await self.db.refresh(user)

        await self.audit_repository.create_event(
            user_id=user.id,
            event_type="USER_REGISTERED",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "email": user.email,
                "username": user.username,
            },
        )

        return user

    async def change_password(
        self,
        *,
        user_id: UUID,
        old_password: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        credential = await self.credential_repository.get_by_user_id(user_id)
        if credential is None or not credential.password_salt:
            raise InvalidOldPasswordError("Invalid old password")

        if not validate_user_password(old_password, credential.password_hash, credential.password_salt):
            raise InvalidOldPasswordError("Invalid old password")

        new_hash, new_salt = create_password_material(new_password)
        credential.password_hash = new_hash
        credential.password_salt = new_salt
        credential.hash_algorithm = "argon2id"
        credential.password_changed_at = datetime.utcnow()
        await self.db.commit()

        await self.audit_repository.create_event(
            user_id=user_id,
            event_type="PASSWORD_CHANGED",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={},
        )
