"""stego_core.py - Core Engine untuk Kriptografi AES-256-GCM, Steganografi LSB,

dan Analisis Ketahanan Transmisi WhatsApp.
"""

from __future__ import annotations

import os
import struct
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import numpy as np
from PIL import Image

# Magic identifier 4-byte untuk menandai payload steganografi
MAGIC_HEADER = b"STEG"
SALT_SIZE = 16
NONCE_SIZE = 12
HEADER_META_SIZE = len(MAGIC_HEADER) + SALT_SIZE + NONCE_SIZE + 4  # 4B untuk panjang ciphertext
MIN_PAYLOAD_SIZE = HEADER_META_SIZE + 16  # Minimal 16B untuk AES-GCM authentication tag


def derive_key(password: str, salt: bytes) -> bytes:
    """Melakukan derivasi kunci 256-bit dari password menggunakan PBKDF2HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_message(plaintext: str, password: str) -> bytes:
    """Mengenkripsi pesan teks rahasia menggunakan AES-256-GCM dengan otentikasi.

    Format Payload Biner yang Dihasilkan:
    [MAGIC: 4B] + [SALT: 16B] + [NONCE: 12B] + [LEN: 4B big-endian] + [CIPHERTEXT + 16B TAG]
    """
    if not password:
        raise ValueError("Password tidak boleh kosong.")
    if not isinstance(plaintext, str):
        raise TypeError("Plaintext harus berupa string.")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = derive_key(password, salt)

    aesgcm = AESGCM(key)
    # Magic header dijadikan associated_data agar tidak dapat dipalsukan
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=MAGIC_HEADER)
    ciphertext_len = len(ciphertext_and_tag)

    payload = (
        MAGIC_HEADER
        + salt
        + nonce
        + struct.pack(">I", ciphertext_len)
        + ciphertext_and_tag
    )
    return payload


def decrypt_message(payload: bytes, password: str) -> str:
    """Mendekripsi payload biner steganografi dan memverifikasi integritas tag GCM."""
    if not password:
        raise ValueError("Password tidak boleh kosong.")
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("Payload harus berupa bytes.")
    if len(payload) < MIN_PAYLOAD_SIZE:
        raise ValueError(f"Ukuran payload terlalu kecil ({len(payload)} bytes, min {MIN_PAYLOAD_SIZE} bytes).")

    magic = payload[: len(MAGIC_HEADER)]
    if magic != MAGIC_HEADER:
        raise ValueError(f"Magic header tidak valid: {magic!r}. Bukan payload steganografi yang valid.")

    offset = len(MAGIC_HEADER)
    salt = payload[offset : offset + SALT_SIZE]
    offset += SALT_SIZE
    nonce = payload[offset : offset + NONCE_SIZE]
    offset += NONCE_SIZE
    (ciphertext_len,) = struct.unpack(">I", payload[offset : offset + 4])
    offset += 4

    ciphertext_and_tag = payload[offset : offset + ciphertext_len]
    if len(ciphertext_and_tag) != ciphertext_len:
        raise ValueError("Panjang ciphertext tidak sesuai dengan metadata header.")

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    # Akan memunculkan InvalidTag exception jika password salah atau data termodifikasi/terkompresi
    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=MAGIC_HEADER)
    return plaintext_bytes.decode("utf-8")
