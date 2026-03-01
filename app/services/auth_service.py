from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User
from app.repositories.credential_repository import CredentialRepository
from app.repositories.user_repository import UserRepository


def validate_user_password(plain_password: str, stored_hash: str) -> bool:
    return verify_password(plain_password, stored_hash)


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class AuthService:
    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)
        self.credential_repository = CredentialRepository(db)

    def login(self, email_or_username: str, password: str) -> User:
        identifier = email_or_username.strip()
        if not identifier:
            raise InvalidCredentialsError("Invalid credentials")

        user = self.user_repository.get_by_email(identifier.lower())
        if user is None:
            user = self.user_repository.get_by_username(identifier)

        if user is None:
            raise InvalidCredentialsError("Invalid credentials")
        if user.deleted_at is not None or not user.is_active:
            raise InactiveUserError("User account is inactive")

        credential = self.credential_repository.get_by_user_id(user.id)
        if credential is None:
            raise InvalidCredentialsError("Invalid credentials")
        if not validate_user_password(password, credential.password_hash):
            raise InvalidCredentialsError("Invalid credentials")

        return user
