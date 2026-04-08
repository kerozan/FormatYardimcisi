# license_manager.py
# Lisans anahtarlarını JSON formatında saklar ve yönetir.

import json
import os
import datetime


class LicenseManager:
    """Program lisans anahtarlarını data/licenses.json'da saklar."""

    def __init__(self, data_dir):
        self.file = os.path.join(data_dir, "licenses.json")
        self.licenses = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.licenses, f, indent=2, ensure_ascii=False)

    def add(self, program, key, notes=""):
        self.licenses.append({
            "program": program,
            "key": key,
            "notes": notes,
            "added": datetime.datetime.now().strftime("%Y-%m-%d"),
        })
        self.save()

    def remove(self, index):
        if 0 <= index < len(self.licenses):
            self.licenses.pop(index)
            self.save()

    def update(self, index, program, key, notes):
        if 0 <= index < len(self.licenses):
            self.licenses[index].update({
                "program": program, "key": key, "notes": notes,
            })
            self.save()

    def get_all(self):
        return list(self.licenses)

    def export_text(self):
        """Lisansları metin olarak dışa aktarır (rehbere eklenmek için)."""
        lines = []
        for lic in self.licenses:
            lines.append(f"| **{lic['program']}** | `{lic['key']}` | {lic.get('notes', '')} |")
        return lines
