# app.py
# Format Yardımcısı — Ana GUI penceresi (CustomTkinter).

import os
import sys
import customtkinter as ctk

from config_manager import ConfigManager, VERSION, APP_NAME
from scanner import ProgramScanner
from guide_generator import GuideGenerator
from license_manager import LicenseManager
from driver_scanner import DriverScanner
from ui.widgets import StatusBar
from ui.scan_tab import ScanTab
from ui.backup_tab import BackupTab
from ui.restore_tab import RestoreTab
from ui.diff_tab import DiffTab
from ui.settings_tab import SettingsTab


class FormatYardimcisiApp(ctk.CTk):
    """Ana uygulama penceresi."""

    def __init__(self):
        super().__init__()

        # ── Tema ──
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ── Yollar ──
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.output_dir = os.path.join(self.base_dir, "cikti")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # ── Core nesneler ──
        self.config = ConfigManager(self.data_dir)
        self.scanner = ProgramScanner(self.data_dir, self.output_dir)
        self.guide_gen = GuideGenerator(self.output_dir)
        self.license_mgr = LicenseManager(self.data_dir)
        self.driver_scanner = DriverScanner()

        # ── Pencere Ayarları ──
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry(self.config.get("window_geometry", "1280x800"))
        self.minsize(900, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── UI Oluştur ──
        self._build_ui()

    def _build_ui(self):
        # ── Başlık ──
        header = ctk.CTkFrame(self, height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text=f"🖥️ {APP_NAME}",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=15, pady=8)

        ctk.CTkLabel(header, text=f"v{VERSION}",
                     font=ctk.CTkFont(size=12), text_color="gray60").pack(side="left", pady=8)

        # Çıkış butonu
        ctk.CTkButton(header, text="✕ Çıkış", width=80, height=30,
                      command=self._on_close,
                      fg_color="#c0392b", hover_color="#922b21",
                      font=ctk.CTkFont(size=12)).pack(side="right", padx=15, pady=8)

        # ── Tab View — belirgin çerçeve ile ──
        self.tabview = ctk.CTkTabview(
            self, corner_radius=8, border_width=2,
            border_color=("gray70", "gray30"),
            segmented_button_fg_color=("gray80", "gray25"),
            segmented_button_selected_color=("#1f6aa5", "#1f6aa5"),
            segmented_button_unselected_color=("gray70", "gray40"),
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(5, 0))

        # Tab buton fontunu büyüt
        try:
            self.tabview._segmented_button.configure(
                font=ctk.CTkFont(size=14, weight="bold"), height=38)
        except Exception:
            pass

        tab_scan = self.tabview.add("📋 Tarama")
        tab_backup = self.tabview.add("💾 Yedekleme")
        tab_restore = self.tabview.add("🔄 Geri Yükleme")
        tab_diff = self.tabview.add("📊 Karşılaştırma")
        tab_settings = self.tabview.add("⚙️ Ayarlar")

        # ── Sekme İçerikleri ──
        self.scan_tab = ScanTab(tab_scan, app_ref=self)
        self.scan_tab.pack(fill="both", expand=True)

        self.backup_tab = BackupTab(tab_backup, app_ref=self)
        self.backup_tab.pack(fill="both", expand=True)

        self.restore_tab = RestoreTab(tab_restore, app_ref=self)
        self.restore_tab.pack(fill="both", expand=True)

        self.diff_tab = DiffTab(tab_diff, app_ref=self)
        self.diff_tab.pack(fill="both", expand=True)

        self.settings_tab = SettingsTab(tab_settings, app_ref=self)
        self.settings_tab.pack(fill="both", expand=True)

        # ── Durum Çubuğu ──
        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill="x", side="bottom")

    def _on_close(self):
        """Pencere kapanırken ayarları kaydet."""
        geo = self.geometry()
        self.config.set("window_geometry", geo)
        self.destroy()
