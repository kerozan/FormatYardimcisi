# scanner.py
# Sistem tarayıcı — disklerdeki programları ve Windows Registry'yi tarar.
# Mevcut program_listele.py'den refactor edilmiştir.

import os
import csv
import json
import datetime
import threading


class ProgramScanner:
    """Disklerdeki program klasörlerini ve Registry'yi tarar."""

    def __init__(self, data_dir, output_dir):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.history_file = os.path.join(data_dir, "scan_history.json")
        self._stop_flag = threading.Event()

    def stop(self):
        self._stop_flag.set()

    def disk_exists(self, drive_letter):
        return os.path.exists(f"{drive_letter}:\\")

    # ── Klasör Tarama ──────────────────────────────────────────────
    def scan_folder(self, folder_path, callback=None):
        """Verilen klasördeki 1. seviye alt klasörleri tarar."""
        programs = []
        if not os.path.exists(folder_path):
            return programs

        try:
            items = os.listdir(folder_path)
        except (PermissionError, OSError):
            return programs

        for item in items:
            if self._stop_flag.is_set():
                break
            full_path = os.path.join(folder_path, item)
            if not os.path.isdir(full_path):
                continue

            total_size = 0
            try:
                for root, _, files in os.walk(full_path):
                    for f in files:
                        try:
                            total_size += os.path.getsize(os.path.join(root, f))
                        except (OSError, PermissionError):
                            pass
            except PermissionError:
                pass

            size_mb = round(total_size / (1024 * 1024), 2)

            try:
                mtime = os.path.getmtime(full_path)
                mod_date = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            except OSError:
                mod_date = "Bilinmiyor"

            programs.append({
                "program_adi": item,
                "kurulum_yolu": full_path,
                "boyut_mb": size_mb,
                "son_degisiklik": mod_date,
                "kaynak_klasor": os.path.basename(folder_path),
                "disk": full_path[0].upper(),
            })

        return programs

    # ── Registry Tarama ────────────────────────────────────────────
    def scan_registry(self, callback=None):
        """Windows Registry'den kurulu programları alır."""
        programs = []
        try:
            import winreg
        except ImportError:
            return programs

        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for root_key, sub_path in registry_paths:
            if self._stop_flag.is_set():
                break
            try:
                key = winreg.OpenKey(root_key, sub_path)
            except (FileNotFoundError, PermissionError):
                continue

            count = winreg.QueryInfoKey(key)[0]
            for i in range(count):
                if self._stop_flag.is_set():
                    break
                try:
                    sub_name = winreg.EnumKey(key, i)
                    sub_key = winreg.OpenKey(key, sub_name)

                    def _val(sk, name):
                        try:
                            return winreg.QueryValueEx(sk, name)[0]
                        except (FileNotFoundError, TypeError):
                            return ""

                    ad = _val(sub_key, "DisplayName")
                    if not ad:
                        winreg.CloseKey(sub_key)
                        continue

                    kurulum_yeri = _val(sub_key, "InstallLocation") or "Belirtilmemiş"
                    versiyon = _val(sub_key, "DisplayVersion")
                    yayinci = _val(sub_key, "Publisher")
                    kurulum_tarihi = _val(sub_key, "InstallDate")

                    if kurulum_tarihi and len(kurulum_tarihi) == 8:
                        kurulum_tarihi = f"{kurulum_tarihi[:4]}-{kurulum_tarihi[4:6]}-{kurulum_tarihi[6:]}"

                    try:
                        boyut_kb = winreg.QueryValueEx(sub_key, "EstimatedSize")[0]
                        boyut_mb = round(boyut_kb / 1024, 2)
                    except (FileNotFoundError, TypeError):
                        boyut_mb = 0

                    winreg.CloseKey(sub_key)

                    programs.append({
                        "program_adi": ad,
                        "kurulum_yolu": kurulum_yeri,
                        "boyut_mb": boyut_mb,
                        "versiyon": versiyon,
                        "yayinci": yayinci,
                        "kurulum_tarihi": kurulum_tarihi,
                    })

                    if callback:
                        callback(f"  {ad}")

                except (OSError, PermissionError):
                    continue
            winreg.CloseKey(key)

        # Tekrarları kaldır
        seen = set()
        unique = []
        for p in programs:
            if p["program_adi"] not in seen:
                seen.add(p["program_adi"])
                unique.append(p)
        return unique

    # ── Tüm Tarama ────────────────────────────────────────────────
    def scan_all(self, disks, appdata_subdirs, callback=None):
        """Tam tarama yapar. callback(msg) ile ilerleme bildirir."""
        self._stop_flag.clear()
        results = {
            "scan_date": datetime.datetime.now().isoformat(),
            "folder_programs": [],
            "registry_programs": [],
        }
        username = os.environ.get("USERNAME", "")
        folder_targets = ["Program Files", "Program Files (x86)", "ProgramData"]

        for disk in disks:
            if self._stop_flag.is_set():
                break
            if not self.disk_exists(disk):
                if callback:
                    callback(f"[{disk}:] Disk bulunamadı, atlanıyor.")
                continue

            if callback:
                callback(f"\n[{disk}:] Disk taranıyor...")

            # Program Files + ProgramData
            for folder in folder_targets:
                if self._stop_flag.is_set():
                    break
                full = os.path.join(f"{disk}:\\", folder)
                found = self.scan_folder(full, callback)
                results["folder_programs"].extend(found)
                if found and callback:
                    callback(f"  ├── {folder}: {len(found)} program")

            # AppData alt klasörleri
            for sub in appdata_subdirs:
                if self._stop_flag.is_set():
                    break
                full = os.path.join(f"{disk}:\\", "Users", username, sub)
                found = self.scan_folder(full, callback)
                results["folder_programs"].extend(found)
                if found and callback:
                    callback(f"  ├── {os.path.basename(sub)} (AppData): {len(found)} öğe")

            # Local\Programs
            progs = os.path.join(f"{disk}:\\", "Users", username, "AppData", "Local", "Programs")
            if os.path.exists(progs):
                found = self.scan_folder(progs, callback)
                results["folder_programs"].extend(found)
                if found and callback:
                    callback(f"  ├── Local\\Programs: {len(found)} öğe")

        if callback:
            callback(f"\nKlasör taraması: {len(results['folder_programs'])} öğe bulundu.")

        # Registry tarama
        if not self._stop_flag.is_set():
            if callback:
                callback("\nRegistry taranıyor...")
            results["registry_programs"] = self.scan_registry(callback)
            if callback:
                callback(f"Registry taraması: {len(results['registry_programs'])} program bulundu.")

        # Sürücü tarama
        if not self._stop_flag.is_set():
            if callback:
                callback("\nSürücüler taranıyor...")
            try:
                from driver_scanner import DriverScanner
                drv_scanner = DriverScanner()
                results["drivers"] = drv_scanner.scan_drivers(callback)
            except Exception as e:
                if callback:
                    callback(f"⚠️ Sürücü taraması atlandı: {e}")
                results["drivers"] = []

        return results

    # ── Karşılaştırma ──────────────────────────────────────────────
    def compare_scans(self, current, previous):
        """İki taramayı karşılaştırır → yeni/kaldırılan programlar."""
        if not previous:
            return {"new": [], "removed": [], "unchanged": len(current.get("registry_programs", []))}

        curr_names = {p["program_adi"] for p in current.get("registry_programs", [])}
        prev_names = {p["program_adi"] for p in previous.get("registry_programs", [])}

        new_progs = [p for p in current["registry_programs"] if p["program_adi"] in (curr_names - prev_names)]
        rem_progs = [p for p in previous["registry_programs"] if p["program_adi"] in (prev_names - curr_names)]

        return {
            "new": new_progs,
            "removed": rem_progs,
            "unchanged": len(curr_names & prev_names),
        }

    # ── Kaydetme / Yükleme ─────────────────────────────────────────
    def save_scan(self, results):
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    def load_previous_scan(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def export_csv(self, results):
        """Sonuçları CSV dosyalarına kaydeder, dosya yollarını döndürür."""
        os.makedirs(self.output_dir, exist_ok=True)
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        folder_csv = os.path.join(self.output_dir, f"klasor_programlar_{now}.csv")
        folder_data = sorted(results.get("folder_programs", []), key=lambda x: x["boyut_mb"], reverse=True)
        fields1 = ["program_adi", "disk", "kaynak_klasor", "kurulum_yolu", "boyut_mb", "son_degisiklik"]
        with open(folder_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields1)
            w.writeheader()
            for p in folder_data:
                w.writerow({k: p.get(k, "") for k in fields1})

        reg_csv = os.path.join(self.output_dir, f"registry_programlar_{now}.csv")
        reg_data = sorted(results.get("registry_programs", []), key=lambda x: x["program_adi"].lower())
        fields2 = ["program_adi", "versiyon", "yayinci", "kurulum_yolu", "boyut_mb", "kurulum_tarihi"]
        with open(reg_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields2)
            w.writeheader()
            for p in reg_data:
                w.writerow({k: p.get(k, "") for k in fields2})

        return folder_csv, reg_csv

    # ── Başlangıç Programları Tarama ───────────────────────────────
    def scan_startup_programs(self, callback=None):
        """Registry'den Windows başlangıç programlarını tarar."""
        startups = []
        try:
            import winreg
        except ImportError:
            return startups

        run_keys = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM(x86)"),
        ]

        for root_key, path, source in run_keys:
            try:
                key = winreg.OpenKey(root_key, path)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        startups.append({
                            "name": name,
                            "command": str(value),
                            "source": source,
                        })
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except (FileNotFoundError, PermissionError):
                pass

        if callback:
            callback(f"\nBaşlangıç programları: {len(startups)} öğe bulundu.")

        return startups

    def scan_services(self, callback=None):
        """Üçüncü parti Windows hizmetlerini tarar (Microsoft dışı)."""
        import subprocess
        services = []
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Service | Where-Object {"
                 "$_.PathName -and $_.PathName -notmatch 'system32|SysWOW64|Windows'"
                 "} | Select-Object Name,DisplayName,State,StartMode | ConvertTo-Json -Compress"],
                capture_output=True, timeout=30,
                encoding="utf-8", errors="replace"
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                if isinstance(data, dict):
                    data = [data]
                for svc in data:
                    services.append({
                        "name": svc.get("Name", ""),
                        "display_name": svc.get("DisplayName", ""),
                        "state": svc.get("State", ""),
                        "start_mode": svc.get("StartMode", ""),
                    })
        except Exception as e:
            if callback:
                callback(f"  Hizmet taraması atlandı: {e}")

        if callback:
            callback(f"Üçüncü parti hizmetler: {len(services)} öğe bulundu.")

        return services

