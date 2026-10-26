"""stego_core.py - Core Engine untuk Kriptografi AES-256-GCM, Steganografi LSB,

dan Analisis Ketahanan Transmisi WhatsApp.
"""

from __future__ import annotations

import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import numpy as np
from PIL import Image
import io
from skimage.metrics import structural_similarity as ssim_func

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

    if len(payload) != offset + ciphertext_len:
        raise ValueError("Panjang payload tidak sesuai dengan metadata header.")

    ciphertext_and_tag = payload[offset : offset + ciphertext_len]

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=MAGIC_HEADER)
    return plaintext_bytes.decode("utf-8")


# ----------------------------------------------------------------------
# Mesin Steganografi Spasial LSB (Least Significant Bit)
# ----------------------------------------------------------------------

def calculate_capacity(image_shape: tuple[int, ...]) -> int:
    """Menghitung kapasitas maksimum data (dalam byte) yang dapat ditampung

    oleh citra dengan menyisipkan 1 bit pada setiap kanal warna piksel.
    """
    total_samples = int(np.prod(image_shape[:2]))
    channels = image_shape[2] if len(image_shape) > 2 else 1
    total_bits = total_samples * channels
    return total_bits // 8


def _standardize_rgb_image(image: np.ndarray) -> np.ndarray:
    """Memastikan citra berformat 3 kanal warna RGB (uint8)."""
    if not isinstance(image, np.ndarray):
        raise TypeError("Citra harus berupa numpy ndarray.")

    img = image.copy()
    if img.ndim == 2:
        # Grayscale -> RGB
        img = np.stack([img, img, img], axis=-1)
    elif img.ndim == 3 and img.shape[2] == 4:
        # RGBA -> RGB (abaikan kanal alpha)
        img = np.ascontiguousarray(img[:, :, :3])
    elif img.ndim != 3 or img.shape[2] != 3:
        raise ValueError(f"Dimensi citra tidak didukung: {img.shape}")

    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)

    return img


def embed_payload_lsb(image: np.ndarray, payload: bytes) -> np.ndarray:
    """Menyisipkan payload biner ke dalam bit LSB kanal RGB citra secara sekuensial.

    Struktur bit yang disisipkan:
    [4 Bytes Panjang Payload (32-bit big endian)] + [N Bytes Payload]
    """
    img = _standardize_rgb_image(image)
    max_bytes = calculate_capacity(img.shape)

    # 4 byte dialokasikan untuk menyimpan panjang total payload
    required_bytes = 4 + len(payload)
    if required_bytes > max_bytes:
        raise ValueError(
            f"Kapasitas gambar tidak mencukupi! "
            f"Dibutuhkan {required_bytes} bytes, kapasitas maksimum citra {max_bytes} bytes."
        )

    # Susun paket: 4B panjang payload + payload
    packet = struct.pack(">I", len(payload)) + payload
    packet_array = np.frombuffer(packet, dtype=np.uint8)
    bits = np.unpackbits(packet_array)
    num_bits = len(bits)

    # Flatten citra untuk mempermudah manipulasi LSB tervektorisasi
    flat_img = img.reshape(-1)
    flat_img[:num_bits] = (flat_img[:num_bits] & np.uint8(0xFE)) | bits.astype(np.uint8)

    return flat_img.reshape(img.shape)


def extract_payload_lsb(stego_image: np.ndarray) -> bytes:
    """Mengekstrak payload biner dari bit LSB kanal RGB citra stego."""
    img = _standardize_rgb_image(stego_image)
    flat_img = img.reshape(-1)

    if len(flat_img) < 32:
        raise ValueError("Ukuran citra terlalu kecil untuk steganografi.")

    # 1. Ekstrak 32 bit pertama untuk mengetahui panjang payload
    len_bits = flat_img[:32] & 1
    len_bytes = np.packbits(len_bits).tobytes()
    (payload_len,) = struct.unpack(">I", len_bytes)

    # Validasi batas kewajaran panjang payload
    max_possible_payload = (len(flat_img) - 32) // 8
    if payload_len < MIN_PAYLOAD_SIZE or payload_len > max_possible_payload:
        raise ValueError(
            f"Header magic steganografi tidak valid atau panjang payload rusak ({payload_len} bytes)."
        )

    # 2. Ekstrak bit payload sebanyak (payload_len * 8)
    num_payload_bits = payload_len * 8
    payload_bits = flat_img[32 : 32 + num_payload_bits] & 1
    payload = np.packbits(payload_bits).tobytes()

    # 3. Validasi magic header
    if payload[: len(MAGIC_HEADER)] != MAGIC_HEADER:
        raise ValueError("Header magic steganografi tidak valid. Citra tidak memuat pesan stego yang sah.")

    return payload


def save_stego_image(stego_image: np.ndarray, filepath: str) -> None:
    """Menyimpan citra stego ke dalam format file PNG murni (lossless)."""
    img = _standardize_rgb_image(stego_image)
    pil_img = Image.fromarray(img)
    pil_img.save(filepath, format="PNG")


def load_image(filepath: str) -> np.ndarray:
    """Memuat file citra dari disk dan mengembalikannya sebagai array RGB uint8."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File citra tidak ditemukan: {filepath}")
    with Image.open(filepath) as pil_img:
        rgb_img = pil_img.convert("RGB")
        return np.array(rgb_img, dtype=np.uint8)


# ----------------------------------------------------------------------
# Modul Evaluasi Kualitas Citra & Simulasi Kompresi WhatsApp
# ----------------------------------------------------------------------

def compute_mse(img1: np.ndarray, img2: np.ndarray) -> float:
    """Menghitung Mean Squared Error (MSE) antara dua citra RGB."""
    i1 = _standardize_rgb_image(img1).astype(np.float64)
    i2 = _standardize_rgb_image(img2).astype(np.float64)
    mse = np.mean((i1 - i2) ** 2)
    return float(mse)


def compute_psnr(img1: np.ndarray, img2: np.ndarray) -> float:
    """Menghitung Peak Signal-to-Noise Ratio (PSNR) dalam satuan desibel (dB).

    Jika kedua citra identik (MSE = 0), mengembalikan float('inf').
    """
    mse = compute_mse(img1, img2)
    if mse == 0.0:
        return float("inf")
    return float(10.0 * np.log10((255.0 ** 2) / mse))


def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """Menghitung Structural Similarity Index (SSIM) antara dua citra RGB."""
    i1 = _standardize_rgb_image(img1)
    i2 = _standardize_rgb_image(img2)
    score = ssim_func(i1, i2, channel_axis=2, data_range=255)
    return float(score)


def compute_ber(original_data: bytes, received_data: bytes) -> float:
    """Menghitung Bit Error Rate (BER) dalam persentase antara dua stream data biner."""
    if not original_data and not received_data:
        return 0.0

    b1 = np.unpackbits(np.frombuffer(original_data, dtype=np.uint8))
    b2 = np.unpackbits(np.frombuffer(received_data, dtype=np.uint8))

    min_len = min(len(b1), len(b2))
    max_len = max(len(b1), len(b2))

    # Bit mismatch pada irisan panjang yang sama
    errors = int(np.count_nonzero(b1[:min_len] != b2[:min_len]))
    # Penalti untuk bit yang hilang/berlebih
    errors += (max_len - min_len)

    return float((errors / max_len) * 100.0)


def simulate_jpeg_compression(image: np.ndarray, quality: int = 75) -> np.ndarray:
    """Mensimulasikan kompresi lossy JPEG seperti yang dilakukan WhatsApp pada mode Foto/Galeri."""
    img = _standardize_rgb_image(image)
    pil_img = Image.fromarray(img)
    buffer = io.BytesIO()
    pil_img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as comp_pil:
        comp_rgb = comp_pil.convert("RGB")
        return np.array(comp_rgb, dtype=np.uint8)

