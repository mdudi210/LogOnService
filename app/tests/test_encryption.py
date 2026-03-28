from app.utils.encryption import decrypt_text, encrypt_text, is_encrypted_text


def test_encrypt_decrypt_roundtrip() -> None:
    plaintext = "JBSWY3DPEHPK3PXP"
    encrypted = encrypt_text(plaintext)

    assert encrypted != plaintext
    assert is_encrypted_text(encrypted)
    assert decrypt_text(encrypted) == plaintext


def test_decrypt_legacy_plaintext_passthrough() -> None:
    plaintext = "JBSWY3DPEHPK3PXP"
    assert decrypt_text(plaintext) == plaintext
