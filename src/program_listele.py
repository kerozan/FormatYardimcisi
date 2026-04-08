# program_listele.py
# C, D, E ve G disklerindeki Program Files ve AppData klasörlerinde
# kurulu bulunan programları tarayıp CSV dosyasına kaydeden araç.

import os
import csv
import datetime
import ctypes
import sys


def disk_mevcut_mu(disk_harfi):
    """Belirtilen disk harfinin sistemde mevcut olup olmadığını kontrol eder."""
    return os.path.exists(f"{disk_harfi}:\\")


def klasor_tara(klasor_yolu):
    """
    Verilen klasördeki birinci seviye alt klasörleri (program adlarını) tarar.
    Her klasör için ad, yol ve boyut bilgisini döndürür.
    """
    programlar = []

    if not os.path.exists(klasor_yolu):
        return programlar

    try:
        alt_klasorler = os.listdir(klasor_yolu)
    except PermissionError:
        print(f"  [!] Erişim engellendi: {klasor_yolu}")
        return programlar
    except OSError as hata:
        print(f"  [!] Hata: {klasor_yolu} -> {hata}")
        return programlar

    for alt_klasor in alt_klasorler:
        tam_yol = os.path.join(klasor_yolu, alt_klasor)

        if not os.path.isdir(tam_yol):
            continue

        # Klasör boyutunu hesapla (MB cinsinden)
        toplam_boyut = 0
        try:
            for kok, _, dosyalar in os.walk(tam_yol):
                for dosya in dosyalar:
                    try:
                        toplam_boyut += os.path.getsize(os.path.join(kok, dosya))
                    except (OSError, PermissionError):
                        pass
        except PermissionError:
            pass

        boyut_mb = round(toplam_boyut / (1024 * 1024), 2)

        # Son değiştirilme tarihini al
        try:
            degisim_zamani = os.path.getmtime(tam_yol)
            degisim_tarihi = datetime.datetime.fromtimestamp(degisim_zamani).strftime("%Y-%m-%d %H:%M")
        except OSError:
            degisim_tarihi = "Bilinmiyor"

        programlar.append({
            "program_adi": alt_klasor,
            "kurulum_yolu": tam_yol,
            "boyut_mb": boyut_mb,
            "son_degisiklik": degisim_tarihi,
            "kaynak_klasor": os.path.basename(klasor_yolu),
            "disk": tam_yol[0].upper()
        })

    return programlar


def registry_programlari_al():
    """
    Windows Registry'den kurulu programların listesini alır.
    Bu liste, Program Files'ta görünmeyen programları da yakalar.
    """
    programlar = []

    try:
        import winreg
    except ImportError:
        print("  [!] winreg modülü bulunamadı (sadece Windows'ta çalışır).")
        return programlar

    # Registry anahtarları (32-bit ve 64-bit)
    registry_yollari = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for ana_anahtar, alt_yol in registry_yollari:
        try:
            anahtar = winreg.OpenKey(ana_anahtar, alt_yol)
        except FileNotFoundError:
            continue
        except PermissionError:
            continue

        alt_anahtar_sayisi = winreg.QueryInfoKey(anahtar)[0]

        for i in range(alt_anahtar_sayisi):
            try:
                alt_anahtar_adi = winreg.EnumKey(anahtar, i)
                alt_anahtar = winreg.OpenKey(anahtar, alt_anahtar_adi)

                try:
                    ad = winreg.QueryValueEx(alt_anahtar, "DisplayName")[0]
                except FileNotFoundError:
                    ad = None

                try:
                    kurulum_yeri = winreg.QueryValueEx(alt_anahtar, "InstallLocation")[0]
                except FileNotFoundError:
                    kurulum_yeri = ""

                try:
                    versiyon = winreg.QueryValueEx(alt_anahtar, "DisplayVersion")[0]
                except FileNotFoundError:
                    versiyon = ""

                try:
                    yayinci = winreg.QueryValueEx(alt_anahtar, "Publisher")[0]
                except FileNotFoundError:
                    yayinci = ""

                try:
                    kurulum_tarihi = winreg.QueryValueEx(alt_anahtar, "InstallDate")[0]
                    if len(kurulum_tarihi) == 8:
                        kurulum_tarihi = f"{kurulum_tarihi[:4]}-{kurulum_tarihi[4:6]}-{kurulum_tarihi[6:]}"
                except (FileNotFoundError, ValueError):
                    kurulum_tarihi = ""

                try:
                    boyut_kb = winreg.QueryValueEx(alt_anahtar, "EstimatedSize")[0]
                    boyut_mb = round(boyut_kb / 1024, 2)
                except (FileNotFoundError, TypeError):
                    boyut_mb = 0

                winreg.CloseKey(alt_anahtar)

                if ad:
                    programlar.append({
                        "program_adi": ad,
                        "kurulum_yolu": kurulum_yeri if kurulum_yeri else "Belirtilmemiş",
                        "boyut_mb": boyut_mb,
                        "versiyon": versiyon,
                        "yayinci": yayinci,
                        "kurulum_tarihi": kurulum_tarihi,
                    })

            except (OSError, PermissionError):
                continue

        winreg.CloseKey(anahtar)

    # Tekrarları kaldır (program adına göre)
    gorulen = set()
    benzersiz = []
    for p in programlar:
        if p["program_adi"] not in gorulen:
            gorulen.add(p["program_adi"])
            benzersiz.append(p)

    return benzersiz


def ana():
    """Ana fonksiyon: Tüm diskleri ve klasörleri tarar, CSV'ye yazar."""

    print("=" * 60)
    print("  KURULU PROGRAM LİSTELEME ARACI")
    print("  C diski yükseltmesi öncesi yedekleme raporu")
    print(f"  Tarih: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Taranacak diskler
    diskler = ["C", "D", "E", "G"]

    # Her diskte taranacak klasörler
    taranacak_klasorler = [
        "Program Files",
        "Program Files (x86)",
    ]

    # AppData klasörleri (sadece kullanıcı profili olan disklerde)
    kullanici_adi = os.environ.get("USERNAME", "")

    appdata_klasorleri = [
        os.path.join("Users", kullanici_adi, "AppData", "Local"),
        os.path.join("Users", kullanici_adi, "AppData", "Roaming"),
        os.path.join("Users", kullanici_adi, "AppData", "LocalLow"),
    ]

    # ── 1. BÖLÜM: Klasör Tarama ──
    print("\n[1/2] Disk klasörleri taranıyor...\n")

    tum_klasor_programlari = []

    for disk in diskler:
        if not disk_mevcut_mu(disk):
            print(f"  [{disk}:] Disk bulunamadı, atlanıyor.")
            continue

        print(f"  [{disk}:] Disk taranıyor...")

        # Program Files klasörleri
        for klasor in taranacak_klasorler:
            tam_yol = os.path.join(f"{disk}:\\", klasor)
            bulunan = klasor_tara(tam_yol)
            tum_klasor_programlari.extend(bulunan)
            if bulunan:
                print(f"    ├── {klasor}: {len(bulunan)} program bulundu")

        # AppData klasörleri
        for appdata_yolu in appdata_klasorleri:
            tam_yol = os.path.join(f"{disk}:\\", appdata_yolu)
            bulunan = klasor_tara(tam_yol)
            tum_klasor_programlari.extend(bulunan)
            if bulunan:
                print(f"    ├── {os.path.basename(appdata_yolu)} (AppData): {len(bulunan)} öğe bulundu")

    print(f"\n  Klasör taraması tamamlandı: {len(tum_klasor_programlari)} öğe bulundu.")

    # ── 2. BÖLÜM: Registry Tarama ──
    print("\n[2/2] Windows Registry taranıyor...\n")
    registry_programlari = registry_programlari_al()
    print(f"  Registry taraması tamamlandı: {len(registry_programlari)} program bulundu.")

    # ── CSV ÇIKTI ──
    simdi = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    script_dizini = os.path.dirname(os.path.abspath(__file__))
    cikti_dizini = os.path.join(script_dizini, "..", "cikti")
    os.makedirs(cikti_dizini, exist_ok=True)

    # CSV 1: Klasör bazlı tarama
    klasor_csv = os.path.join(cikti_dizini, f"klasor_programlar_{simdi}.csv")
    with open(klasor_csv, "w", newline="", encoding="utf-8-sig") as dosya:
        yazici = csv.DictWriter(dosya, fieldnames=[
            "program_adi", "disk", "kaynak_klasor", "kurulum_yolu", "boyut_mb", "son_degisiklik"
        ])
        yazici.writeheader()

        # Boyuta göre büyükten küçüğe sırala
        tum_klasor_programlari.sort(key=lambda x: x["boyut_mb"], reverse=True)

        for program in tum_klasor_programlari:
            yazici.writerow(program)

    print(f"\n  ✅ Klasör tarama raporu: {klasor_csv}")

    # CSV 2: Registry bazlı tarama
    registry_csv = os.path.join(cikti_dizini, f"registry_programlar_{simdi}.csv")
    with open(registry_csv, "w", newline="", encoding="utf-8-sig") as dosya:
        yazici = csv.DictWriter(dosya, fieldnames=[
            "program_adi", "versiyon", "yayinci", "kurulum_yolu", "boyut_mb", "kurulum_tarihi"
        ])
        yazici.writeheader()

        # Ada göre sırala
        registry_programlari.sort(key=lambda x: x["program_adi"].lower())

        for program in registry_programlari:
            yazici.writerow(program)

    print(f"  ✅ Registry tarama raporu: {registry_csv}")

    # ── ÖZET ──
    toplam_boyut_gb = sum(p["boyut_mb"] for p in tum_klasor_programlari) / 1024
    print("\n" + "=" * 60)
    print("  ÖZET RAPOR")
    print("=" * 60)
    print(f"  Taranan diskler     : {', '.join(diskler)}")
    print(f"  Klasör programları  : {len(tum_klasor_programlari)} öğe")
    print(f"  Registry programları: {len(registry_programlari)} program")
    print(f"  Toplam disk kullanım: {toplam_boyut_gb:.2f} GB (klasör taraması)")
    print(f"  Çıktı klasörü       : {os.path.abspath(cikti_dizini)}")
    print("=" * 60)

    input("\nÇıkmak için Enter'a basın...")


if __name__ == "__main__":
    ana()
