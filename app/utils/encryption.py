from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from app.core.config import settings


class EncryptionError(Exception):
    pass


_TOTP_ENCRYPTION_PREFIX = "enc:v1:"


def _cryptography_fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise EncryptionError("cryptography package is required for secret encryption") from exc
    return Fernet


def _derive_fernet_key(material: str) -> bytes:
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _resolve_key_material() -> str:
    configured = (settings.TOTP_ENCRYPTION_KEY or "").strip()
    if configured:
        return configured
    # Backward-compatible fallback for local development.
    return settings.JWT_SECRET_KEY


@lru_cache(maxsize=1)
def _get_fernet():
    fernet_cls = _cryptography_fernet()
    key = _derive_fernet_key(_resolve_key_material())
    return fernet_cls(key)


def is_encrypted_text(value: str) -> bool:
    return value.startswith(_TOTP_ENCRYPTION_PREFIX)


def encrypt_text(value: str) -> str:
    plaintext = value.strip()
    if not plaintext:
        raise EncryptionError("Cannot encrypt empty value")

    token = _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{_TOTP_ENCRYPTION_PREFIX}{token}"


def decrypt_text(value: str) -> str:
    if not value:
        raise EncryptionError("Cannot decrypt empty value")

    if not is_encrypted_text(value):
        # Legacy plaintext compatibility path for existing rows.
        return value

    token = value[len(_TOTP_ENCRYPTION_PREFIX) :]
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise EncryptionError("Encrypted value could not be decrypted") from exc
