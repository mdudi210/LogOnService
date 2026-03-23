from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

ENCRYPTION_PREFIX = "enc:v1:"


class EncryptionError(Exception):
    pass


def _derive_fernet_key() -> bytes:
    seed = (settings.TOTP_ENCRYPTION_KEY or settings.JWT_SECRET_KEY).encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return Fernet(_derive_fernet_key())


def encrypt_text(value: str) -> str:
    if not value:
        raise EncryptionError("Cannot encrypt empty value")

    token = _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTION_PREFIX}{token}"


def decrypt_text(value: str) -> str:
    if not value:
        raise EncryptionError("Cannot decrypt empty value")

    # Backward compatibility for legacy plaintext rows.
    if not value.startswith(ENCRYPTION_PREFIX):
        return value

    payload = value[len(ENCRYPTION_PREFIX) :]
    try:
        return _fernet().decrypt(payload.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionError("Failed to decrypt value") from exc
