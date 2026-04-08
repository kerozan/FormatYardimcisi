# restore_engine.py
# Yedeklenmiş dosyaları orijinal konumlarına geri yükler.

import os
import json
import shutil
import datetime
import threading


class RestoreEngine:
    """Manifest tabanlı geri yükleme motoru."""

    def __init__(self, backup_dir):
        self.backup_dir = backup_dir
        self.manifest_file = os.path.join(backup_dir, "manifest.json")
        self._stop_flag = threading.Event()
        self._is_running = False

    @property
    def is_running(self):
        return self._is_running

    def stop(self):
        self._stop_flag.set()

    def load_manifest(self):
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"backups": [], "files": {}}

    def get_restorable_items(self):
        """Geri yüklenebilir klasörleri ve dosya sayılarını döndürür."""
        manifest = self.load_manifest()
        groups = {}

        for rel_path, info in manifest.get("files", {}).items():
            source = info.get("source", "")
            # Kaynak klasörü bul (ilk 3 seviye: C:\Users\Kadir\AppData\Roaming\Xyz)
            parts = source.replace("/", "\\").split("\\")
            if len(parts) >= 5:
                group_key = "\\".join(parts[:5])
            else:
                group_key = source

            if group_key not in groups:
                groups[group_key] = {
                    "folder": group_key,
                    "file_count": 0,
                    "total_size": 0,
                    "rel_paths": [],
                }
            groups[group_key]["file_count"] += 1
            groups[group_key]["total_size"] += info.get("size", 0)
            groups[group_key]["rel_paths"].append(rel_path)

        return list(groups.values())

    def restore(self, rel_paths, progress_cb=None, done_cb=None):
        """
        Belirli dosyaları geri yükler.
        rel_paths: geri yüklenecek relative path listesi
        """
        self._stop_flag.clear()
        self._is_running = True
        manifest = self.load_manifest()

        total = len(rel_paths)
        restored = 0
        skipped = 0
        errors = 0

        if progress_cb:
            progress_cb(0, max(total, 1), f"Toplam {total} dosya geri yüklenecek.")

        for idx, rel_path in enumerate(rel_paths):
            if self._stop_flag.is_set():
                if progress_cb:
                    progress_cb(idx, total, "⏹ Geri yükleme durduruldu.")
                break

            info = manifest.get("files", {}).get(rel_path)
            if not info:
                skipped += 1
                continue

            backup_file = os.path.join(self.backup_dir, rel_path)
            original_path = info["source"]

            if not os.path.exists(backup_file):
                skipped += 1
                if progress_cb:
                    progress_cb(idx + 1, total, f"⚠️ Yedek dosya bulunamadı: {os.path.basename(backup_file)}")
                continue

            try:
                os.makedirs(os.path.dirname(original_path), exist_ok=True)
                # Güvenli kopyalama: temp dosya ile
                temp = original_path + ".tmp"
                shutil.copy2(backup_file, temp)
                if os.path.exists(original_path):
                    os.replace(temp, original_path)
                else:
                    os.rename(temp, original_path)

                restored += 1
                if progress_cb:
                    progress_cb(idx + 1, total, f"✅ {os.path.basename(original_path)}")

            except (OSError, PermissionError, shutil.Error) as e:
                errors += 1
                # Temp dosyayı temizle
                temp = original_path + ".tmp"
                if os.path.exists(temp):
                    try:
                        os.remove(temp)
                    except OSError:
                        pass
                if progress_cb:
                    progress_cb(idx + 1, total, f"❌ {os.path.basename(original_path)}: {e}")

        self._is_running = False

        status = "durduruldu" if self._stop_flag.is_set() else "tamamlandı"
        summary = (
            f"\n{'='*50}\n"
            f"Geri yükleme {status}!\n"
            f"  Geri yüklenen: {restored}\n"
            f"  Atlanan      : {skipped}\n"
            f"  Hata         : {errors}\n"
            f"{'='*50}"
        )
        if done_cb:
            done_cb(summary)
