import numpy as np
import pytest
from stego_core import (
    calculate_capacity,
    embed_payload_lsb,
    extract_payload_lsb,
    encrypt_message,
    decrypt_message,
    save_stego_image,
    load_image,
)

def test_capacity_calculation():
    # 100 x 100 x 3 image -> 30,000 bits = 3,750 bytes
    cap = calculate_capacity((100, 100, 3))
    assert cap == 3750

def test_embed_and_extract_roundtrip():
    img = np.random.randint(0, 256, (120, 120, 3), dtype=np.uint8)
    password = "kunci_rahasia_stego"
    msg = "Halo dunia! Ini adalah pesan rahasia yang terenkripsi dan disisipkan pada LSB citra PNG."
    payload = encrypt_message(msg, password)

    stego_img = embed_payload_lsb(img, payload)
    assert stego_img.shape == img.shape
    assert stego_img.dtype == np.uint8

    extracted_payload = extract_payload_lsb(stego_img)
    assert extracted_payload == payload
    assert decrypt_message(extracted_payload, password) == msg

def test_capacity_exceeded_raises():
    img = np.zeros((10, 10, 3), dtype=np.uint8)  # 300 bits = 37 bytes
    payload = b"A" * 100  # 100 bytes > 37 bytes
    with pytest.raises(ValueError, match="Kapasitas gambar tidak mencukupi"):
        embed_payload_lsb(img, payload)

def test_extract_invalid_magic_raises():
    img = np.zeros((100, 100, 3), dtype=np.uint8)  # No valid magic header
    with pytest.raises(ValueError, match="Header magic steganografi tidak valid"):
        extract_payload_lsb(img)

def test_rgba_converted_to_rgb():
    img_rgba = np.random.randint(0, 256, (100, 100, 4), dtype=np.uint8)
    payload = encrypt_message("secret", "pass123")
    stego = embed_payload_lsb(img_rgba, payload)
    assert stego.shape == (100, 100, 3)

def test_save_and_load_lossless_roundtrip(tmp_path):
    img = np.random.randint(0, 256, (80, 80, 3), dtype=np.uint8)
    payload = encrypt_message("Lossless file check", "kunci")
    stego = embed_payload_lsb(img, payload)

    filepath = str(tmp_path / "test_stego.png")
    save_stego_image(stego, filepath)

    loaded_img = load_image(filepath)
    np.testing.assert_array_equal(stego, loaded_img)

    extracted = extract_payload_lsb(loaded_img)
    assert decrypt_message(extracted, "kunci") == "Lossless file check"
