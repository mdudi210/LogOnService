import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


_password_hasher = PasswordHasher()


def generate_password_salt() -> str:
    return secrets.token_urlsafe(24)


def hash_password(plain_password: str, salt: str) -> str:
    return _password_hasher.hash(f"{salt}{plain_password}")


def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, f"{salt}{plain_password}")
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
