import os
import subprocess
import sys
from pathlib import Path

def test_notebook_file_exists():
    notebook_path = Path("steganografi_whatsapp_analisis.ipynb")
    assert notebook_path.exists(), "File steganografi_whatsapp_analisis.ipynb tidak ditemukan"
    assert notebook_path.stat().st_size > 1000, "Ukuran file notebook terlalu kecil"

def test_cover_image_exists():
    cover_path = Path("cover_image.png")
    assert cover_path.exists(), "Cover image cover_image.png tidak ditemukan"

def test_output_artifacts_generated():
    stego_path = Path("stego_image.png")
    assert stego_path.exists(), "File stego_image.png harus terbentuk dari eksekusi steganografi"
