# config_manager.py
# Uygulama ayarlarını JSON formatında saklar ve yönetir.

import json
import os

VERSION = "3.0.0"
APP_NAME = "Format Yardımcısı"


class ConfigManager:
    """Kullanıcı ayarlarını settings.json'da saklar."""

    DEFAULT_SETTINGS = {
        "backup_target": "G:\\Yedekler",
        "scan_disks": ["C", "D", "E", "G"],
        "appdata_subdirs": [
            "AppData\\Local",
            "AppData\\Roaming",
            "AppData\\LocalLow",
        ],
        "backup_folders": [],
        "window_geometry": "1280x800",
        "last_scan_date": None,
        "last_backup_date": None,
        "last_restore_date": None,
        "gemini_api_key": "",
        "use_ai_analyzer": False,
    }

    def __init__(self, data_dir):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.settings_file = os.path.join(data_dir, "settings.json")
        self.settings = self._load()

    def _load(self):
        """Ayar dosyasını yükle, yoksa varsayılanları kullan."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Yeni eklenen anahtarlar için varsayılanlarla birleştir
                return {**self.DEFAULT_SETTINGS, **saved}
            except (json.JSONDecodeError, IOError):
                pass
        return dict(self.DEFAULT_SETTINGS)

    def save(self):
        """Ayarları dosyaya kaydet."""
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def set_many(self, updates: dict):
        self.settings.update(updates)
        self.save()
