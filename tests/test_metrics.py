import numpy as np
import pytest
from stego_core import (
    compute_mse,
    compute_psnr,
    compute_ssim,
    compute_ber,
    simulate_jpeg_compression,
    embed_payload_lsb,
    encrypt_message,
)

def test_identical_images_metrics():
    img = np.ones((50, 50, 3), dtype=np.uint8) * 128
    assert compute_mse(img, img) == 0.0
    assert compute_psnr(img, img) == float("inf")
    assert pytest.approx(compute_ssim(img, img), 0.0001) == 1.0

def test_stego_image_high_psnr():
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    payload = encrypt_message("Tes PSNR tinggi", "kunci")
    stego = embed_payload_lsb(img, payload)

    psnr = compute_psnr(img, stego)
    ssim = compute_ssim(img, stego)
    assert psnr > 50.0  # LSB modifications yield very high PSNR (> 50 dB)
    assert ssim > 0.999

def test_ber_calculation():
    # 2 bytes = 16 bits
    # b1: 00000000 11111111
    # b2: 00000001 11111111 (1 bit difference out of 16 -> 6.25%)
    b1 = b"\x00\xFF"
    b2 = b"\x01\xFF"
    ber = compute_ber(b1, b2)
    assert pytest.approx(ber, 0.001) == (1 / 16) * 100

def test_simulate_jpeg_degrades_quality():
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    compressed = simulate_jpeg_compression(img, quality=75)
    assert compressed.shape == img.shape
    assert compute_psnr(img, compressed) < float("inf")
    assert compute_mse(img, compressed) > 0.0
