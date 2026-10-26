import pytest
from stego_core import encrypt_message, decrypt_message

def test_encrypt_decrypt_roundtrip():
    secret = "Pesan rahasia steganografi 2026! @#$%"
    password = "KunciRahasiaSuperAman123"
    payload = encrypt_message(secret, password)
    assert isinstance(payload, bytes)
    assert payload[:4] == b"STEG"
    decrypted = decrypt_message(payload, password)
    assert decrypted == secret

def test_decrypt_wrong_password():
    secret = "Top secret"
    payload = encrypt_message(secret, "password_benar")
    with pytest.raises(Exception):
        decrypt_message(payload, "password_salah")

def test_tampered_payload():
    secret = "Top secret"
    payload = bytearray(encrypt_message(secret, "password"))
    payload[-1] ^= 0xFF  # Tamper with GCM tag
    with pytest.raises(Exception):
        decrypt_message(bytes(payload), "password")

def test_empty_password_raises():
    with pytest.raises(ValueError, match="Password tidak boleh kosong"):
        encrypt_message("secret", "")
    with pytest.raises(ValueError, match="Password tidak boleh kosong"):
        decrypt_message(b"STEG...", "")

def test_invalid_header_raises():
    with pytest.raises(ValueError, match="Magic header tidak valid"):
        decrypt_message(b"BADH" + b"\x00" * 50, "password")
