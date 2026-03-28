from __future__ import annotations

from typing import Any


class TOTPServiceError(Exception):
    pass


def _pyotp() -> Any:
    try:
        import pyotp
    except ImportError as exc:
        raise TOTPServiceError("pyotp is required for TOTP MFA support") from exc
    return pyotp


def generate_totp_secret() -> str:
    return _pyotp().random_base32()


def build_provisioning_uri(*, secret: str, email: str, issuer_name: str = "LogOnService") -> str:
    return _pyotp().TOTP(secret).provisioning_uri(name=email, issuer_name=issuer_name)


def verify_totp_code(*, secret: str, code: str) -> bool:
    return bool(_pyotp().TOTP(secret).verify(code.strip(), valid_window=1))
