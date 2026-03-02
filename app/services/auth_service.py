from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_password_salt, hash_password, verify_password
from app.models.user import User
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


class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_repository = UserRepository(db)

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
