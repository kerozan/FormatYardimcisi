# backup_diff.py
# İki yedek manifest'ini karşılaştıran diff motoru.

import os
import json
import datetime


class BackupDiffEngine:
    """İki BackupEngine manifest dosyasını karşılaştırır."""

    @staticmethod
    def load_manifest(path):
        """Manifest dosyasını veya manifest içeren klasörü yükler."""
        if os.path.isdir(path):
            path = os.path.join(path, "manifest.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    @staticmethod
    def compare(manifest_a, manifest_b):
        """
        İki manifest'i karşılaştırır.
        manifest_a: eski yedek (referans)
        manifest_b: yeni yedek (mevcut)

        Döndürür: {
            new: [...],       # B'de var, A'da yok
            removed: [...],   # A'da var, B'de yok
            modified: [...],  # Her ikisinde var ama boyut/tarih farklı
            unchanged: [...], # Her ikisinde aynı
            summary: {new_count, removed_count, modified_count, unchanged_count,
                      new_size, removed_size, modified_size}
        }
        """
        files_a = manifest_a.get("files", {}) if manifest_a else {}
        files_b = manifest_b.get("files", {}) if manifest_b else {}

        keys_a = set(files_a.keys())
        keys_b = set(files_b.keys())

        # Küme işlemleri
        only_in_a = keys_a - keys_b  # silinen
        only_in_b = keys_b - keys_a  # yeni
        common = keys_a & keys_b     # her ikisinde var

        new_items = []
        for key in sorted(only_in_b):
            info = files_b[key]
            new_items.append({
                "path": key,
                "source": info.get("source", ""),
                "size": info.get("size", 0),
                "date": info.get("backed_up_at", ""),
            })

        removed_items = []
        for key in sorted(only_in_a):
            info = files_a[key]
            removed_items.append({
                "path": key,
                "source": info.get("source", ""),
                "size": info.get("size", 0),
                "date": info.get("backed_up_at", ""),
            })

        modified_items = []
        unchanged_items = []
        for key in sorted(common):
            info_a = files_a[key]
            info_b = files_b[key]

            # Boyut veya mtime farkı → değişmiş
            size_a = info_a.get("size", 0)
            size_b = info_b.get("size", 0)
            mtime_a = info_a.get("mtime", 0)
            mtime_b = info_b.get("mtime", 0)

            if size_a != size_b or abs(mtime_a - mtime_b) > 1:
                modified_items.append({
                    "path": key,
                    "source": info_b.get("source", ""),
                    "size_old": size_a,
                    "size_new": size_b,
                    "size_diff": size_b - size_a,
                    "date_old": info_a.get("backed_up_at", ""),
                    "date_new": info_b.get("backed_up_at", ""),
                })
            else:
                unchanged_items.append(key)

        # Özet istatistikler
        summary = {
            "new_count": len(new_items),
            "removed_count": len(removed_items),
            "modified_count": len(modified_items),
            "unchanged_count": len(unchanged_items),
            "new_size": sum(i["size"] for i in new_items),
            "removed_size": sum(i["size"] for i in removed_items),
            "modified_size": sum(abs(i["size_diff"]) for i in modified_items),
        }

        return {
            "new": new_items,
            "removed": removed_items,
            "modified": modified_items,
            "unchanged": unchanged_items,
            "summary": summary,
        }

    @staticmethod
    def get_manifest_info(manifest):
        """Manifest hakkında özet bilgi döndürür."""
        if not manifest:
            return {"date": "—", "file_count": 0, "total_size": 0, "backup_count": 0}

        files = manifest.get("files", {})
        backups = manifest.get("backups", [])
        total_size = sum(info.get("size", 0) for info in files.values())

        # Son yedekleme tarihi
        last_date = "—"
        if backups:
            last_date = backups[-1].get("date", "—")
            try:
                dt = datetime.datetime.fromisoformat(last_date)
                last_date = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError):
                last_date = last_date[:16]

        return {
            "date": last_date,
            "file_count": len(files),
            "total_size": total_size,
            "backup_count": len(backups),
        }

    @staticmethod
    def format_size(size_bytes):
        """Bayt değerini okunaklı formata çevirir."""
        abs_size = abs(size_bytes)
        if abs_size >= 1024 ** 3:
            return f"{size_bytes / (1024**3):.1f} GB"
        elif abs_size >= 1024 ** 2:
            return f"{size_bytes / (1024**2):.1f} MB"
        elif abs_size >= 1024:
            return f"{size_bytes / 1024:.0f} KB"
        return f"{size_bytes} B"
