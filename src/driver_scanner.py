# driver_scanner.py
# Windows DriverStore'dan 3. parti sürücüleri tarar ve dışa aktarır.

import os
import re
import subprocess
import threading


class DriverScanner:
    """Windows 3. parti sürücülerini tarar ve yedekler."""

    def __init__(self):
        self._stop_flag = threading.Event()

    def stop(self):
        self._stop_flag.set()

    def scan_drivers(self, callback=None):
        """
        pnputil /enum-drivers ile 3. parti sürücüleri listeler.
        Döndürür: [{name, provider, version, date, inf_name, class_name}, ...]
        """
        self._stop_flag.clear()
        drivers = []

        try:
            result = subprocess.run(
                ["pnputil", "/enum-drivers"],
                capture_output=True, timeout=30,
                encoding="utf-8", errors="replace"
            )
            if result.returncode != 0:
                if callback:
                    callback(f"⚠️ pnputil hatası: {result.stderr.strip()}")
                return drivers

            output = result.stdout
        except FileNotFoundError:
            if callback:
                callback("⚠️ pnputil bulunamadı (Windows dışı sistem?).")
            return drivers
        except subprocess.TimeoutExpired:
            if callback:
                callback("⚠️ pnputil zaman aşımına uğradı.")
            return drivers

        # pnputil çıktısını parse et — her sürücü blok halinde
        current = {}
        for line in output.splitlines():
            if self._stop_flag.is_set():
                break

            line = line.strip()
            if not line:
                # Blok sonu — sürücüyü kaydet
                if current.get("inf_name"):
                    drivers.append(current)
                current = {}
                continue

            # Anahtar:Değer formatı (TR ve EN lokalizasyon)
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()

                if "yayımlanan ad" in key or "published name" in key:
                    current["inf_name"] = value
                elif "özgün ad" in key or "original name" in key:
                    current["original_name"] = value
                elif "sağlayıcı ad" in key or "provider name" in key:
                    current["provider"] = value
                elif "sınıf ad" in key or "class name" in key:
                    current["class_name"] = value
                elif "sürücü sürüm" in key or "driver version" in key:
                    # Tarih ve versiyon bir arada: "04/21/2023 31.0.101.4502"
                    parts = value.split(None, 1)
                    if len(parts) == 2:
                        current["date"] = parts[0]
                        current["version"] = parts[1]
                    else:
                        current["version"] = value
                elif "imzalayan ad" in key or "signer name" in key:
                    current["signer"] = value

        # Son blok
        if current.get("inf_name"):
            drivers.append(current)

        # Microsoft sürücülerini filtrele (3. parti olanları tut)
        third_party = []
        for drv in drivers:
            provider = drv.get("provider", "").lower()
            signer = drv.get("signer", "").lower()
            # Microsoft sürücülerini atla
            if "microsoft" in provider:
                continue
            third_party.append({
                "inf_name": drv.get("inf_name", ""),
                "name": drv.get("original_name", drv.get("inf_name", "")),
                "provider": drv.get("provider", "Bilinmiyor"),
                "class_name": drv.get("class_name", ""),
                "version": drv.get("version", ""),
                "date": drv.get("date", ""),
            })

        if callback:
            callback(f"\n🔧 Sürücüler: {len(third_party)} üçüncü parti sürücü bulundu.")

        return third_party

    def export_drivers(self, driver_list, target_dir, progress_cb=None):
        """
        Sürücüleri hedef klasöre dışa aktarır (pnputil /export-driver).
        driver_list: scan_drivers() çıktısı
        target_dir: hedef ana klasör (_drivers alt klasörü oluşturulur)
        """
        self._stop_flag.clear()
        export_dir = os.path.join(target_dir, "_drivers")
        os.makedirs(export_dir, exist_ok=True)

        total = len(driver_list)
        exported = 0
        errors = 0

        for idx, drv in enumerate(driver_list):
            if self._stop_flag.is_set():
                if progress_cb:
                    progress_cb(idx, total, "⏹ Sürücü dışa aktarma durduruldu.")
                break

            inf_name = drv.get("inf_name", "")
            if not inf_name:
                continue

            # Her sürücü için alt klasör
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', drv.get("provider", "unknown"))
            drv_subdir = os.path.join(export_dir, f"{safe_name}_{inf_name.replace('.inf', '')}")
            os.makedirs(drv_subdir, exist_ok=True)

            try:
                result = subprocess.run(
                    ["pnputil", "/export-driver", inf_name, drv_subdir],
                    capture_output=True, timeout=15,
                    encoding="utf-8", errors="replace"
                )
                if result.returncode == 0:
                    exported += 1
                    if progress_cb:
                        progress_cb(idx + 1, total,
                                    f"✅ {drv.get('provider', '')} — {drv.get('class_name', '')}")
                else:
                    errors += 1
                    if progress_cb:
                        progress_cb(idx + 1, total,
                                    f"⚠️ {inf_name}: {result.stderr.strip()[:80]}")

            except (subprocess.TimeoutExpired, OSError) as e:
                errors += 1
                if progress_cb:
                    progress_cb(idx + 1, total, f"❌ {inf_name}: {e}")

        summary = (
            f"\n{'='*50}\n"
            f"Sürücü dışa aktarma {'durduruldu' if self._stop_flag.is_set() else 'tamamlandı'}!\n"
            f"  Aktarılan : {exported}\n"
            f"  Hata      : {errors}\n"
            f"  Hedef     : {export_dir}\n"
            f"{'='*50}"
        )
        return summary, export_dir
