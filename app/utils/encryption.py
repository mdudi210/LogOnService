from __future__ import annotations


def encrypt_text(_: str) -> str:
    raise NotImplementedError("Implement encryption provider before storing secrets")


def decrypt_text(_: str) -> str:
    raise NotImplementedError("Implement encryption provider before reading secrets")
