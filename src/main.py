# main.py
# Format Yardımcısı — Giriş noktası.
# Çift tıkla veya `python src/main.py` ile çalıştırılır.

import sys
import os

# src/ klasörünü sys.path'e ekle (modül importları için)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import FormatYardimcisiApp


def main():
    app = FormatYardimcisiApp()
    app.mainloop()


if __name__ == "__main__":
    main()
