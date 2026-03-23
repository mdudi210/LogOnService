from app.utils import encryption


def test_encrypt_decrypt_roundtrip() -> None:
    encryption._fernet.cache_clear()
    plaintext = "BASE32SECRET1234567890"
    encrypted = encryption.encrypt_text(plaintext)

    assert encrypted.startswith(encryption.ENCRYPTION_PREFIX)
    assert encryption.decrypt_text(encrypted) == plaintext


def test_decrypt_plaintext_legacy_value() -> None:
    legacy_plaintext = "LEGACYBASE32SECRET"
    assert encryption.decrypt_text(legacy_plaintext) == legacy_plaintext
