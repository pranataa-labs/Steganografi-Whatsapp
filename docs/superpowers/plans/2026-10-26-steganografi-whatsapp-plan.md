# Steganografi Citra Digital & Analisis Transmisi WhatsApp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun engine steganografi berbasis enkripsi AES-256-GCM + LSB pada citra digital PNG dan file Jupyter Notebook (`steganografi_whatsapp_analisis.ipynb`) komprehensif untuk pengiriman via WhatsApp serta analisis empiris ketahanan terhadap kompresi lossy.

**Architecture:** Pendekatan arsitektur berlapis:
1. Core Engine (`stego_core.py`): Implementasi fungsi kriptografi terotentikasi (AES-256-GCM + PBKDF2), embedding & ekstraksi LSB spasial pada citra RGB, metrik kualitas citra (MSE, PSNR, SSIM, BER), dan simulasi kompresi WhatsApp JPEG.
2. Unit Tests (`tests/`): Verifikasi TDD untuk setiap komponen modular (kriptografi, steganografi, metrik kualitas).
3. Jupyter Notebook Interaktif (`steganografi_whatsapp_analisis.ipynb`): Dokumentasi teoritis mendalam (Bahasa Indonesia dengan KaTeX), demonstrasi alur pengirim & penerima, visualisasi peta perbedaan residual citra, SOP pengiriman WhatsApp dokumen, simulasi kompresi, dan grafik performa degradasi kualitas.

**Tech Stack:** Python 3.12, Jupyter Notebook (`.ipynb`), `cryptography` (AES-256-GCM, PBKDF2HMAC), `numpy`, `Pillow` (PIL), `matplotlib`, `scikit-image` (structural_similarity), `pytest`.

**Spec:** `docs/superpowers/specs/2026-10-26-steganografi-whatsapp-design.md`

## Global Constraints
- Target platform: Windows / Python 3.12, Jupyter Notebook.
- Cover Image: `cover_image.png` (736 $\times$ 919 piksel RGB, 3 channels).
- Kriptografi: AES-256-GCM, PBKDF2HMAC (SHA-256, 100.000 iterasi, salt 16-byte, nonce/IV 12-byte).
- Format Header Payload: `[Magic: "STEG" (4B)] + [Salt (16B)] + [Nonce (12B)] + [Ciphertext Length (4B)] + [Ciphertext + 16B GCM Tag]`.
- LSB Embedding: 1 bit per komponen R, G, B secara berurutan.
- Transmisi WhatsApp: SOP pengiriman sebagai Dokumen (*lossless*).
- Ambang Kualitas Citra: PSNR citra stego $> 50\text{ dB}$, SSIM $> 0.999$.
- Bahasa Notebook: Bahasa Indonesia formal, ilmiah, dengan formula LaTeX KaTeX.

## Review Focus
1. Password kosong atau invalid: Menghasilkan `ValueError` secara eksplisit dan tidak menyebabkan crash tak terkontrol.
2. Ukuran payload melebihi kapasitas gambar: Menghasilkan `ValueError` informatif dengan rincian byte payload vs kapasitas maksimum gambar sebelum memodifikasi piksel.
3. Dekripsi dengan password salah atau citra terkorupsi kompresi: Mengangkat pengecualian otentikasi GCM (`InvalidTag` / `DecryptionError`) secara elegan alih-alih menghasilkan teks sampah yang membingungkan.
4. Input citra non-RGB (RGBA atau Grayscale): Divalidasi dan dikonversi secara otomatis atau aman ke format 3-channel RGB uint8.
5. Ekstraksi pada citra biasa (bukan stego): Header magic identifier `STEG` tidak cocok, memicu error validasi yang jelas alih-alih membaca memori sembarangan.

---

### Task 1: Core Cryptography Module (`stego_core.py` - Crypto)

**Files:**
- Create: `stego_core.py`
- Test: `tests/test_crypto.py`

**Interfaces:**
- Produces:
  - `encrypt_message(plaintext: str, password: str) -> bytes`
  - `decrypt_message(payload: bytes, password: str) -> str`
  - `MAGIC_HEADER = b"STEG"` (4 bytes)

- [ ] **Step 1: Tulis unit test untuk enkripsi dan dekripsi**

Create `tests/test_crypto.py`:
```python
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
    with pytest.raises(ValueError):
        encrypt_message("secret", "")
```

- [ ] **Step 2: Jalankan test untuk memverifikasi kegagalan (Red)**

Run: `python -m pytest tests/test_crypto.py -v`  
Expected: FAIL (ModuleNotFoundError: No module named 'stego_core')

- [ ] **Step 3: Implementasikan fungsi kriptografi pada `stego_core.py`**

Implement `encrypt_message` and `decrypt_message` with:
- PBKDF2HMAC with SHA256, 100,000 iterations, 16-byte random salt.
- AES-256-GCM cipher with 12-byte random nonce.
- Payload serialization: `MAGIC (4B) + SALT (16B) + NONCE (12B) + LENGTH (4B, big-endian) + (CIPHERTEXT + TAG)`.
- Input validation (non-empty password).

- [ ] **Step 4: Jalankan test untuk memverifikasi kelulusan (Green)**

Run: `python -m pytest tests/test_crypto.py -v`  
Expected: PASS

- [ ] **Step 5: Commit task 1**

```bash
git add stego_core.py tests/test_crypto.py
git commit -m "feat(crypto): implement AES-256-GCM encryption and decryption with tests"
```

---

### Task 2: Core Steganography Module (`stego_core.py` - LSB Engine)

**Files:**
- Modify: `stego_core.py`
- Test: `tests/test_stego.py`

**Interfaces:**
- Consumes: `encrypt_message`, `decrypt_message` from Task 1.
- Produces:
  - `calculate_capacity(image_shape: tuple[int, ...]) -> int` (returns max bytes)
  - `embed_payload_lsb(image: np.ndarray, payload: bytes) -> np.ndarray`
  - `extract_payload_lsb(stego_image: np.ndarray) -> bytes`
  - `save_stego_image(stego_image: np.ndarray, filepath: str) -> None`
  - `load_image(filepath: str) -> np.ndarray`

- [ ] **Step 1: Tulis unit test untuk LSB embedding dan extraction**

Create `tests/test_stego.py`:
```python
import numpy as np
import pytest
from stego_core import (
    calculate_capacity, embed_payload_lsb, extract_payload_lsb,
    encrypt_message, decrypt_message
)

def test_capacity_calculation():
    # 100 x 100 x 3 image -> 30,000 bits = 3,750 bytes
    cap = calculate_capacity((100, 100, 3))
    assert cap == 3750

def test_embed_and_extract_roundtrip():
    # Buat dummy image 100x100x3
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    password = "kunciku"
    msg = "Halo dunia steganografi!"
    payload = encrypt_message(msg, password)
    
    stego_img = embed_payload_lsb(img, payload)
    assert stego_img.shape == img.shape
    assert stego_img.dtype == np.uint8
    
    extracted_payload = extract_payload_lsb(stego_img)
    assert extracted_payload == payload
    assert decrypt_message(extracted_payload, password) == msg

def test_capacity_exceeded_raises():
    img = np.zeros((10, 10, 3), dtype=np.uint8) # 300 bits = 37 bytes
    payload = b"A" * 100 # 100 bytes > 37 bytes
    with pytest.raises(ValueError, match="Kapasitas gambar tidak mencukupi"):
        embed_payload_lsb(img, payload)

def test_extract_invalid_magic_raises():
    img = np.zeros((100, 100, 3), dtype=np.uint8) # No valid magic header
    with pytest.raises(ValueError, match="Header magic steganografi tidak valid"):
        extract_payload_lsb(img)
```

- [ ] **Step 2: Jalankan test untuk memverifikasi kegagalan (Red)**

Run: `python -m pytest tests/test_stego.py -v`  
Expected: FAIL (ImportError for missing functions)

- [ ] **Step 3: Implementasikan fungsi LSB pada `stego_core.py`**

- Vectorized bit extraction and embedding with NumPy for high efficiency.
- Header checking (4-byte MAGIC "STEG", 4-byte total payload length).
- Capacity check before modifying pixels.
- Lossless PNG image save/load helpers.

- [ ] **Step 4: Jalankan test untuk memverifikasi kelulusan (Green)**

Run: `python -m pytest tests/test_stego.py -v`  
Expected: PASS

- [ ] **Step 5: Commit task 2**

```bash
git add stego_core.py tests/test_stego.py
git commit -m "feat(stego): implement LSB embedding and extraction engine with tests"
```

---

### Task 3: Quality Metrics & Compression Simulation (`stego_core.py` - Metrics)

**Files:**
- Modify: `stego_core.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Produces:
  - `compute_mse(img1: np.ndarray, img2: np.ndarray) -> float`
  - `compute_psnr(img1: np.ndarray, img2: np.ndarray) -> float`
  - `compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float`
  - `compute_ber(original_bits: str | bytes, received_bits: str | bytes) -> float`
  - `simulate_jpeg_compression(image: np.ndarray, quality: int) -> np.ndarray`

- [ ] **Step 1: Tulis unit test untuk perhitungan metrik dan simulasi kompresi**

Create `tests/test_metrics.py`:
```python
import numpy as np
import pytest
from stego_core import (
    compute_mse, compute_psnr, compute_ssim, compute_ber,
    simulate_jpeg_compression, embed_payload_lsb, encrypt_message
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
    assert psnr > 50.0  # LSB modifications yield very high PSNR
    assert ssim > 0.999

def test_ber_calculation():
    b1 = b"\x00\xFF"  # 00000000 11111111
    b2 = b"\x01\xFF"  # 00000001 11111111 (1 bit difference out of 16)
    ber = compute_ber(b1, b2)
    assert pytest.approx(ber, 0.001) == (1 / 16) * 100

def test_simulate_jpeg_degrades_quality():
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    compressed = simulate_jpeg_compression(img, quality=75)
    assert compressed.shape == img.shape
    assert compute_psnr(img, compressed) < float("inf")
```

- [ ] **Step 2: Jalankan test untuk memverifikasi kegagalan (Red)**

Run: `python -m pytest tests/test_metrics.py -v`  
Expected: FAIL

- [ ] **Step 3: Implementasikan fungsi metrik dan simulasi kompresi di `stego_core.py`**

- `compute_mse`: NumPy mean squared difference across all channels.
- `compute_psnr`: $10 \log_{10}(255^2 / \text{MSE})$.
- `compute_ssim`: via `skimage.metrics.structural_similarity(img1, img2, channel_axis=2)`.
- `compute_ber`: Bit error rate percentage using bitwise XOR counting.
- `simulate_jpeg_compression`: In-memory encode/decode via PIL JPEG buffer at specified quality factor.

- [ ] **Step 4: Jalankan test untuk memverifikasi kelulusan (Green)**

Run: `python -m pytest tests/test_metrics.py -v`  
Expected: PASS

- [ ] **Step 5: Commit task 3**

```bash
git add stego_core.py tests/test_metrics.py
git commit -m "feat(metrics): implement MSE, PSNR, SSIM, BER and JPEG compression simulation"
```

---

### Task 4: Interactive Comprehensive Jupyter Notebook (`steganografi_whatsapp_analisis.ipynb`)

**Files:**
- Create: `steganografi_whatsapp_analisis.ipynb`

**Content Requirements:**
Sesuai Dokumen Desain, notebook harus memiliki struktur teratur dengan 6 Modul Utama:
1. **Modul 1: Landasan Teori & Arsitektur**
   - Perbedaan Kriptografi vs Steganografi (*Defense-in-Depth*).
   - Formulasi matematis LSB spasial.
   - Prinsip kompresi lossy JPEG WhatsApp.
2. **Modul 2: Implementasi Kriptografi (Security Layer)**
   - AES-256-GCM + PBKDF2 (SHA-256).
   - Pengujian enkripsi dan proteksi integritas.
3. **Modul 3: Mesin Steganografi Citra (Lossless LSB)**
   - Pemuatan citra `cover_image.png`.
   - Perhitungan kapasitas embedding gambar.
   - Penyisipan pesan rahasia terenkripsi & pembuatan `stego_image.png`.
   - Ekstraksi dan dekripsi balik pesan rahasia.
4. **Modul 4: Evaluasi Kualitas Visual & Peta Residual**
   - Nilai MSE, PSNR, dan SSIM.
   - Plot citra berdampingan (Asli vs Stego).
   - *Amplified Difference Map* ($|I_{\text{asli}} - I_{\text{stego}}| \times 30$).
   - Histogram distribusi warna sebelum vs sesudah.
5. **Modul 5: Analisis Transmisi WhatsApp & Eksperimen Kompresi**
   - Panduan SOP: Mengapa wajib dikirim sebagai **Dokumen** (*Send as Document*), bukan Galeri/Foto.
   - Verifikasi *hash* SHA-256 sebelum dan sesudah kirim.
   - Stres tes: Simulasi apa yang terjadi jika dikirim via Galeri (kompresi JPEG QF 75–85).
   - Pengukuran BER dan pembuktian kegagalan dekripsi AES-GCM akibat bit flip.
   - Analisis perbandingan teoritis: LSB spasial vs DCT/DWT domain frekuensi (tradeoff kapasitas vs ketahanan kompresi).
6. **Modul 6: Kesimpulan & Panduan Praktis**
   - Ringkasan temuan dan tabel komparasi.

- [ ] **Step 1: Bangun file notebook `steganografi_whatsapp_analisis.ipynb` secara programmatic**
- [ ] **Step 2: Jalankan dan validasi notebook untuk menghasilkan semua visualisasi dan nilai metrik**
- [ ] **Step 3: Commit task 4**

```bash
git add steganografi_whatsapp_analisis.ipynb
git commit -m "feat(notebook): generate complete steganography and WhatsApp analysis notebook"
```

---

### Task 5: End-to-End Test & Automated Execution Validation

**Files:**
- Create: `tests/test_notebook_execution.py`

**Interfaces:**
- Memvalidasi bahwa `steganografi_whatsapp_analisis.ipynb` dapat dieksekusi secara otomatis dari awal hingga akhir tanpa ada cell yang error.

- [ ] **Step 1: Tulis automated test eksekusi notebook**

Create `tests/test_notebook_execution.py`:
```python
import subprocess
import sys
from pathlib import Path

def test_notebook_runs_without_errors():
    notebook_path = Path("steganografi_whatsapp_analisis.ipynb")
    assert notebook_path.exists(), "Notebook file does not exist"
    
    # Run notebook via nbclient/jupyter execute
    cmd = [
        sys.executable, "-m", "nbclient",
        str(notebook_path),
        "--timeout", "120"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Notebook execution failed: {result.stderr}"
```

- [ ] **Step 2: Jalankan end-to-end execution test**

Run: `python -m pytest tests/test_notebook_execution.py -v`  
Expected: PASS

- [ ] **Step 3: Verifikasi keberadaan file artefak hasil eksekusi (`stego_image.png`, dll.)**
- [ ] **Step 4: Commit task 5**

```bash
git add tests/test_notebook_execution.py
git commit -m "test: add automated notebook execution verification test"
```
