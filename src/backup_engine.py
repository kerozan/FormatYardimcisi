# backup_engine.py
# Incremental yedekleme motoru — güvenli durdurma + manifest takibi.

import os
import json
import shutil
import datetime
import threading


class BackupEngine:
    """Incremental yedekleme: sadece yeni/değişen dosyaları kopyalar, eski yedeği silmez."""

    def __init__(self, target_dir):
        self.target_dir = target_dir
        self.manifest_file = os.path.join(target_dir, "manifest.json")
        self._stop_flag = threading.Event()
        self._is_running = False

    @property
    def is_running(self):
        return self._is_running

    def stop(self):
        """Yedeklemeyi güvenli durdur (mevcut dosya tamamlanır)."""
        self._stop_flag.set()

    # ── Manifest ───────────────────────────────────────────────────
    def load_manifest(self):
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"backups": [], "files": {}}

    def save_manifest(self, manifest):
        os.makedirs(self.target_dir, exist_ok=True)
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    # ── Yol Hesaplama ──────────────────────────────────────────────
    def _relative_path(self, source_path):
        """C:\\Users\\X\\... → C_Drive\\Users\\X\\..."""
        drive = source_path[0].upper()
        rest = source_path[3:]  # "C:\" kısmını atla
        return os.path.join(f"{drive}_Drive", rest)

    def _target_path(self, source_path):
        return os.path.join(self.target_dir, self._relative_path(source_path))

    # ── Kopyalama Kararı ───────────────────────────────────────────
    def _should_copy(self, source_file):
        """Dosyanın kopyalanması gerekip gerekmediğini belirler (boyut+tarih)."""
        target_file = self._target_path(source_file)
        if not os.path.exists(target_file):
            return True
        try:
            src_stat = os.stat(source_file)
            tgt_stat = os.stat(target_file)
            if src_stat.st_size != tgt_stat.st_size:
                return True
            if src_stat.st_mtime > tgt_stat.st_mtime:
                return True
        except OSError:
            return True
        return False

    # ── Güvenli Kopyalama ──────────────────────────────────────────
    def _safe_copy(self, source, target):
        """Dosyayı güvenli kopyalar — yarım dosya kalmaz."""
        os.makedirs(os.path.dirname(target), exist_ok=True)
        temp_target = target + ".tmp"
        try:
            shutil.copy2(source, temp_target)
            # Hedefte zaten varsa üzerine yaz (rename atomik)
            if os.path.exists(target):
                os.replace(temp_target, target)
            else:
                os.rename(temp_target, target)
        except Exception:
            # Yarım kalan temp dosyasını temizle
            if os.path.exists(temp_target):
                try:
                    os.remove(temp_target)
                except OSError:
                    pass
            raise

    # ── Dosya Toplama ──────────────────────────────────────────────
    def collect_files(self, folder_list):
        """Yedeklenecek tüm dosyaları toplar. folder_list: [(ad, yol), ...]"""
        all_files = []
        for name, source_path in folder_list:
            if not os.path.exists(source_path):
                continue
            for root, _, files in os.walk(source_path):
                for f in files:
                    full = os.path.join(root, f)
                    all_files.append(full)
        return all_files

    def count_to_copy(self, all_files):
        """Kaç dosyanın kopyalanacağını hesaplar (ön tarama)."""
        count = 0
        size = 0
        for f in all_files:
            if self._should_copy(f):
                count += 1
                try:
                    size += os.path.getsize(f)
                except OSError:
                    pass
        return count, size

    # ── Ana Yedekleme ──────────────────────────────────────────────
    def backup(self, folder_list, progress_cb=None, done_cb=None):
        """
        Yedeklemeyi başlatır.
        folder_list: [(ad, kaynak_yol), ...]
        progress_cb(current, total, message)
        done_cb(summary_text)
        """
        self._stop_flag.clear()
        self._is_running = True
        manifest = self.load_manifest()

        all_files = self.collect_files(folder_list)
        total = len(all_files)
        copied = 0
        skipped = 0
        errors = 0
        locked = 0
        total_size = 0

        if progress_cb:
            progress_cb(0, max(total, 1), f"Toplam {total} dosya bulundu.")

        for idx, source_file in enumerate(all_files):
            if self._stop_flag.is_set():
                if progress_cb:
                    progress_cb(idx, total, "⏹ Yedekleme durduruldu.")
                break

            if self._should_copy(source_file):
                target_file = self._target_path(source_file)
                try:
                    self._safe_copy(source_file, target_file)
                    file_size = os.path.getsize(source_file)
                    total_size += file_size

                    rel = self._relative_path(source_file)
                    manifest["files"][rel] = {
                        "source": source_file,
                        "size": file_size,
                        "mtime": os.path.getmtime(source_file),
                        "backed_up_at": datetime.datetime.now().isoformat(),
                    }
                    copied += 1
                    if progress_cb:
                        short = os.path.basename(source_file)
                        progress_cb(idx + 1, total, f"✅ {short}")

                except OSError as e:
                    if getattr(e, 'winerror', 0) == 32:
                        locked += 1
                        if progress_cb:
                            progress_cb(idx + 1, total, f"⚠️ Kilitli (atlandı): {os.path.basename(source_file)}")
                    else:
                        errors += 1
                        if progress_cb:
                            progress_cb(idx + 1, total, f"❌ {os.path.basename(source_file)}: {e}")
                except (PermissionError, shutil.Error) as e:
                    errors += 1
                    if progress_cb:
                        progress_cb(idx + 1, total, f"❌ {os.path.basename(source_file)}: {e}")
            else:
                skipped += 1

        # Manifest güncelle
        record = {
            "date": datetime.datetime.now().isoformat(),
            "copied": copied,
            "skipped": skipped,
            "errors": errors,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "stopped": self._stop_flag.is_set(),
        }
        manifest["backups"].append(record)
        self.save_manifest(manifest)
        self._is_running = False

        status = "durduruldu" if self._stop_flag.is_set() else "tamamlandı"
        summary = (
            f"\n{'='*50}\n"
            f"Yedekleme {status}!\n"
            f"  Kopyalanan : {copied}\n"
            f"  Atlanan    : {skipped} (değişmemiş)\n"
            f"  Kilitli    : {locked} (tarayıcı/uygulama kullanıyor)\n"
            f"  Hata       : {errors}\n"
            f"  Boyut      : {round(total_size / (1024*1024), 2)} MB\n"
            f"{'='*50}"
        )
        if done_cb:
            done_cb(summary)

    # ── Yedeklenmiş Klasörleri Listele ─────────────────────────────
    def get_backed_up_folders(self):
        """Manifest'ten yedeklenmiş üst klasörleri döndürür."""
        manifest = self.load_manifest()
        folders = {}
        for rel_path, info in manifest.get("files", {}).items():
            parts = rel_path.split(os.sep)
            if len(parts) >= 2:
                top = os.sep.join(parts[:2])
                if top not in folders:
                    folders[top] = {"count": 0, "size": 0, "last_date": ""}
                folders[top]["count"] += 1
                folders[top]["size"] += info.get("size", 0)
                dt = info.get("backed_up_at", "")
                if dt > folders[top]["last_date"]:
                    folders[top]["last_date"] = dt
        return folders

    def get_backup_history(self):
        """Yedekleme geçmişini döndürür."""
        manifest = self.load_manifest()
        return manifest.get("backups", [])

    # ── ZIP Yedekleme ──────────────────────────────────────────────
    def backup_as_zip(self, folder_list, progress_cb=None, done_cb=None):
        """Klasörleri ZIP arşiv olarak yedekler."""
        import zipfile

        self._stop_flag.clear()
        self._is_running = True
        os.makedirs(self.target_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(self.target_dir, f"yedek_{timestamp}.zip")

        all_files = self.collect_files(folder_list)
        total = len(all_files)
        added = 0
        errors = 0
        total_size = 0

        if progress_cb:
            progress_cb(0, max(total, 1), f"📦 ZIP oluşturuluyor: {total} dosya")

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for idx, source_file in enumerate(all_files):
                    if self._stop_flag.is_set():
                        if progress_cb:
                            progress_cb(idx, total, "⏹ ZIP yedekleme durduruldu.")
                        break

                    rel = self._relative_path(source_file)
                    try:
                        zf.write(source_file, rel)
                        total_size += os.path.getsize(source_file)
                        added += 1
                        if progress_cb and (idx % 50 == 0 or idx == total - 1):
                            progress_cb(idx + 1, total, f"📦 {os.path.basename(source_file)}")
                    except OSError as e:
                        if getattr(e, 'winerror', 0) == 32:
                            if progress_cb:
                                progress_cb(idx + 1, total, f"⚠️ Kilitli (atlandı): {os.path.basename(source_file)}")
                        else:
                            errors += 1
                            if progress_cb:
                                progress_cb(idx + 1, total, f"❌ {os.path.basename(source_file)}: {e}")
                    except PermissionError as e:
                        errors += 1
                        if progress_cb:
                            progress_cb(idx + 1, total, f"❌ {os.path.basename(source_file)}: {e}")
        except Exception as e:
            if progress_cb:
                progress_cb(total, total, f"❌ ZIP oluşturma hatası: {e}")

        self._is_running = False

        # ZIP boyutu
        zip_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
        zip_mb = round(zip_size / (1024 * 1024), 1)
        orig_mb = round(total_size / (1024 * 1024), 1)

        # Manifest'e ZIP yedeğini kaydet
        manifest = self.load_manifest()
        record = {
            "date": datetime.datetime.now().isoformat(),
            "type": "zip",
            "zip_file": zip_path,
            "added": added,
            "errors": errors,
            "original_size_mb": orig_mb,
            "zip_size_mb": zip_mb,
            "stopped": self._stop_flag.is_set(),
        }
        manifest["backups"].append(record)
        self.save_manifest(manifest)

        status = "durduruldu" if self._stop_flag.is_set() else "tamamlandı"
        summary = (
            f"\n{'='*50}\n"
            f"ZIP yedekleme {status}!\n"
            f"  Eklenen dosya : {added}\n"
            f"  Hata          : {errors}\n"
            f"  Orijinal boyut: {orig_mb} MB\n"
            f"  ZIP boyutu    : {zip_mb} MB\n"
            f"  Dosya         : {zip_path}\n"
            f"{'='*50}"
        )
        if done_cb:
            done_cb(summary)

