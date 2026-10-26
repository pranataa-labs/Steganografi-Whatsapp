# Design Document: Steganografi Citra Digital Berbasis Enkripsi & Analisis Ketahanan Transmisi WhatsApp

**Tanggal:** 2026-10-26  
**Status:** In Review / Builder Check  
**Author:** Antigravity (Pair Programming Assistant)  
**Target File:** `steganografi_whatsapp_analisis.ipynb`  
**Cover Image:** `cover_image.png` (berasal dari gambar yang diunggah pengguna, resolusi 736x919 RGB)

---

## 1. Intent and The Why
Pengguna ingin mengeksplorasi dan mempraktikkan konsep **Steganografi Modern** dengan menyisipkan pesan rahasia yang telah dienkripsi ke dalam sebuah citra digital (cover image), kemudian mensimulasikan pengiriman ke penerima via WhatsApp. 
Di samping alur praktis (*encode-send-decode*), pengguna juga secara eksplisit menginginkan **analisis mendalam mengenai dampak kompresi WhatsApp terhadap stego-image**, pembuktian matematis/empiris kegagalan LSB pada kompresi lossy, serta perbandingannya dengan pendekatan domain frekuensi (DCT/Transform Domain).

---

## 2. Goals, Non-Goals, & Anti-Goals

### Goals
1. **End-to-End Secure Workflow:**
   - Enkripsi pesan menggunakan standar kriptografi modern (AES-256-GCM / PBKDF2 dengan salt & nonce acak) sehingga memenuhi prinsip *Defense-in-Depth* (Kriptografi + Steganografi).
   - Penyisipan payload biner terenkripsi ke dalam bit paling tidak signifikan (LSB) pada kanal RGB gambar `cover_image.png`.
   - Penyematan metadata header (panjang payload, magic identifier) agar ekstraksi bersifat deterministik tanpa *out-of-bounds*.
   - Rekonstruksi dan verifikasi pesan oleh pihak penerima secara sempurna (*bit-exact*).
2. **Panduan Operasional Transmisi WhatsApp:**
   - Analisis teknis perbedaan pengiriman media di WhatsApp: mode "Foto/Galeri" (kompresi lossy JPEG agresif) vs mode "Dokumen" (bit-exact lossless transmission).
   - Verifikasi integritas file menggunakan *hash* SHA-256 sebelum dan sesudah transmisi.
3. **Analisis Empiris Dampak Kompresi WhatsApp:**
   - Eksperimen simulasi kompresi JPEG WhatsApp (Quality Factor 70-85, chroma subsampling 4:2:0).
   - Pengukuran metrik kualitas objektif:
     - **MSE** (*Mean Squared Error*)
     - **PSNR** (*Peak Signal-to-Noise Ratio*)
     - **SSIM** (*Structural Similarity Index*)
     - **BER** (*Bit Error Rate*) pada payload rahasia.
   - Visualisasi: Citra asli vs Citra Stego vs Citra Terkompresi, beserta *Amplified Difference Map* (peta residual $\times 30$).
   - Analisis teoritis dan perbandingan konseptual: LSB (Spatial Domain) vs DCT/DWT (Frequency/Transform Domain) serta batas toleransi kapasitas vs ketahanan (*robustness vs capacity tradeoff*).

### Non-Goals
- Tidak membangun server atau bot WhatsApp otomatis (pengiriman dilakukan via antarmuka WhatsApp resmi oleh pengguna dengan panduan SOP di notebook).
- Tidak mengimplementasikan steganografi audio atau video (khusus citra digital 2D RGB).

### Anti-Goals
- Tidak menyajikan kode LSB "mentah" tanpa enkripsi dan tanpa header panjang, yang rentan crash saat ekstraksi.
- Tidak memberikan klaim keliru bahwa LSB spasial dapat bertahan melewati kompresi JPEG galeri WhatsApp (edukasi teknis harus jujur dan berbasis pembuktian empiris).

---

## 3. Constraints & Dependencies
- **Lingkungan Eksekusi:** Jupyter Notebook (`.ipynb`) berjalan pada Python 3.12 (Windows).
- **Format Cover Image:** Gambar pengguna telah diubah namanya menjadi `cover_image.png` (736 x 919 piksel, 3 kanal warna RGB).
- **Kapasitas Teoretis LSB (1 bit/channel):**
  $$736 \times 919 \times 3 = 2{,}029{,}152 \text{ bit} \approx 253{,}644 \text{ byte} \ (\approx 247.7 \text{ KB})$$
  Sangat memadai untuk teks berukuran ratusan hingga ribuan kata beserta metadata enkripsi.
- **Library Python:**
  - `numpy`, `PIL` (Pillow), `matplotlib`, `cv2` (OpenCV), `scipy` (sudah terinstal).
  - Enkripsi: Menggunakan `cryptography` (atau implementasi standar Python `hashlib` + AES / ChaCha20 / pycryptodome). Jika `cryptography` belum terpasang, instalasi disiapkan di cell awal notebook.

---

## 4. Approaches Considered

1. **Opsi 1: All-in-One Comprehensive Educational & Practical Notebook (DIPILIH OLEH PENGGUNA)**
   - Mengintegrasikan seluruh teori, implementasi enkripsi AES, LSB steganografi, panduan transmisi dokumen WhatsApp, simulasi kompresi JPEG, metrik PSNR/SSIM/BER, dan visualisasi grafik dalam 1 file `.ipynb` yang komprehensif.
   - *Trade-off:* File notebook cukup panjang, namun sangat memudahkan pembacaan dan eksekusi sekuensial tanpa kehilangan konteks.
2. **Opsi 2: Dual Notebook Suite (Praktis vs Riset Kompresi)**
   - Memisahkan implementasi siap pakai dan eksperimen riset ke dalam dua file terpisah.
   - *Trade-off:* Duplikasi kode helper dan alur kerja terpecah.
3. **Opsi 3: Script Modular (`stego.py`) + Notebook Demo Ringkas**
   - *Trade-off:* Logika algoritma terisolasi di file luar, mengurangi nilai transparansi edukatif notebook.

---

## 5. Architectural & Implementation Specifications

Notebook `steganografi_whatsapp_analisis.ipynb` disusun menjadi 6 modul utama:

### Modul 1: Pengantar & Landasan Teori
- Konsep dasar Steganografi vs Kriptografi (*Confidentiality vs Invisibility*).
- Formulasi matematis LSB spasial:
  $$I'(x, y, c) = (I(x, y, c) \ \& \ \sim 1) \ | \ b_i$$
- Teori kompresi lossy JPEG pada WhatsApp (DCT transform, quantisation matrix, high-frequency coefficient discarding) dan dampaknya terhadap bit LSB.

### Modul 2: Lapisan Kriptografi (Security Layer)
- Algoritma: **AES-256-GCM** (Galois/Counter Mode).
- Derivasi Kunci: **PBKDF2HMAC** dengan SHA-256, 100.000 iterasi, dan 16-byte cryptographically secure random salt.
- Otentikasi & Integritas: GCM Tag (16 byte) untuk mendeteksi manipulasi/korupsi data sebelum didekripsi.
- Struktur Payload:
  `[Magic Header (4B: "STEG")] + [Salt (16B)] + [Nonce/IV (12B)] + [Ciphertext Length (4B)] + [Ciphertext + Tag]`

### Modul 3: Engine Steganografi LSB (Spatial Domain)
- Validasi kapasitas gambar `cover_image.png` terhadap ukuran payload.
- Fungsi penyisipan (*Embedder*): Mengubah payload biner menjadi aliran bit dan menyisipkannya pada komponen warna R, G, B secara berurutan.
- Fungsi ekstraksi (*Extractor*): Membaca header panjang data, mengambil bit-bit LSB, merekonstruksi byte payload terenkripsi.
- Fungsi dekripsi: Memvalidasi tag otentikasi GCM dan mengembalikan teks rahasia asli.

### Modul 4: Evaluasi Kualitas Visual & Peta Residual
- Perhitungan kuantitatif:
  - **MSE** (*Mean Squared Error*):
    $$\text{MSE} = \frac{1}{M \cdot N \cdot 3} \sum_{i=1}^M \sum_{j=1}^N \sum_{c=1}^3 (I(i,j,c) - I'(i,j,c))^2$$
  - **PSNR** (*Peak Signal-to-Noise Ratio*):
    $$\text{PSNR} = 10 \cdot \log_{10}\left(\frac{255^2}{\text{MSE}}\right) \text{ dB}$$
    (Target untuk LSB: $\text{PSNR} > 50\text{ dB}$, secara visual imperceptible).
  - **SSIM** (*Structural Similarity Index*): Target $\approx 0.9999$.
- Visualisasi:
  - Gambar asli vs Stego (side-by-side).
  - *Residual Difference Map* diperbesar ($|I - I'| \times 30$).
  - Histogram distribusi kanal warna sebelum dan sesudah penyisipan.

### Modul 5: Analisis Transmisi WhatsApp & Eksperimen Kompresi
- **Prosedur Transmisi WhatsApp yang Aman:**
  - Standard Operating Procedure (SOP): Mengirim file sebagai Dokumen (*Attach Document*), bukan Galeri/Foto.
  - Verifikasi SHA-256 Checksum pada sisi pengirim dan penerima.
- **Eksperimen Kerentanan (Stress Test Kompresi Lossy):**
  - Simulasi kompresi JPEG WhatsApp (QF 75, QF 85, downscaling).
  - Pengujian ekstraksi pada gambar hasil kompresi:
    - Penghitungan **Bit Error Rate (BER)**:
      $$\text{BER} = \frac{\sum |b_{\text{orig}} \oplus b_{\text{extracted}}|}{N_{\text{bits}}} \times 100\%$$
    - Pembuktian kegagalan dekripsi AES-GCM (otentikasi gagal / MAC mismatch akibat bit flip acak).
- **Analisis Komparasi LSB vs DCT / DWT:**
  - Mengapa teknik domain frekuensi (seperti DCT QIM / robust watermarking) lebih tahan terhadap kompresi dibanding LSB spasial, namun memiliki kapasitas payload jauh lebih kecil.

### Modul 6: Kesimpulan & Rekomendasi Praktis
- Ringkasan temuan analisis kompresi.
- Checklist keamanan untuk pengguna.

---

## 6. What's Left to the Builder
- Penulisan sintaks sel notebook, docstring, dan visualisasi warna yang elegan menggunakan matplotlib.
- Pengaturan cell `%pip install cryptography` di baris pertama notebook untuk memastikan kompatibilitas instan di semua mesin.
- Penataan teks markdown dwibahasa (penjelasan teoritis dalam Bahasa Indonesia yang formal dan ilmiah).
