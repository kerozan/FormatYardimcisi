# settings_tab.py
# Ayarlar sekmesi — disk seçimi, yedek hedefi, lisans defteri, hakkında.

import customtkinter as ctk
from tkinter import filedialog, messagebox
from config_manager import VERSION, APP_NAME


class LicenseDialog(ctk.CTkToplevel):
    """Lisans ekleme/düzenleme dialogu."""

    def __init__(self, master, on_save, program="", key="", notes=""):
        super().__init__(master)
        self.title("Lisans Ekle/Düzenle")
        self.geometry("450x280")
        self.resizable(False, False)
        self.on_save = on_save

        ctk.CTkLabel(self, text="Program Adı:", font=ctk.CTkFont(size=13)).pack(padx=15, pady=(15, 2), anchor="w")
        self.program_var = ctk.StringVar(value=program)
        ctk.CTkEntry(self, textvariable=self.program_var, width=400).pack(padx=15, pady=(0, 8))

        ctk.CTkLabel(self, text="Lisans Anahtarı:", font=ctk.CTkFont(size=13)).pack(padx=15, pady=(0, 2), anchor="w")
        self.key_var = ctk.StringVar(value=key)
        ctk.CTkEntry(self, textvariable=self.key_var, width=400).pack(padx=15, pady=(0, 8))

        ctk.CTkLabel(self, text="Notlar:", font=ctk.CTkFont(size=13)).pack(padx=15, pady=(0, 2), anchor="w")
        self.notes_var = ctk.StringVar(value=notes)
        ctk.CTkEntry(self, textvariable=self.notes_var, width=400).pack(padx=15, pady=(0, 12))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=8)
        ctk.CTkButton(btn_frame, text="💾 Kaydet", command=self._save,
                      fg_color="#2d8a4e", hover_color="#236b3c").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="İptal", command=self.destroy,
                      fg_color="gray40").pack(side="left")

        self.grab_set()
        self.focus_force()
        self.lift()

    def _save(self):
        p = self.program_var.get().strip()
        k = self.key_var.get().strip()
        if not p or not k:
            messagebox.showwarning("Uyarı", "Program adı ve lisans anahtarı zorunlu!")
            return
        self.on_save(p, k, self.notes_var.get().strip())
        self.destroy()


class SettingsTab(ctk.CTkFrame):
    """Uygulama ayarları sekmesi."""

    AVAILABLE_DISKS = ["C", "D", "E", "F", "G", "H"]

    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_ref
        self.disk_vars = {}
        self.appdata_vars = {}
        self._build_ui()

    def _build_ui(self):
        # ── Taranacak Diskler ──
        ctk.CTkLabel(self, text="⚙️ Tarama Ayarları",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     anchor="w").pack(fill="x", padx=15, pady=(10, 3))

        disk_frame = ctk.CTkFrame(self)
        disk_frame.pack(fill="x", padx=15, pady=3)

        ctk.CTkLabel(disk_frame, text="Taranacak Diskler:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=10, pady=(4, 2))

        disk_row = ctk.CTkFrame(disk_frame, fg_color="transparent")
        disk_row.pack(fill="x", padx=10, pady=(0, 4))

        selected = self.app.config.get("scan_disks", [])
        for d in self.AVAILABLE_DISKS:
            var = ctk.BooleanVar(value=(d in selected))
            self.disk_vars[d] = var
            ctk.CTkCheckBox(disk_row, text=f"{d}:", variable=var,
                            font=ctk.CTkFont(size=13), width=70).pack(side="left", padx=4)

        # ── AppData ──
        appdata_frame = ctk.CTkFrame(self)
        appdata_frame.pack(fill="x", padx=15, pady=3)

        ctk.CTkLabel(appdata_frame, text="AppData Alt Klasörleri:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=10, pady=(4, 2))

        appdata_row = ctk.CTkFrame(appdata_frame, fg_color="transparent")
        appdata_row.pack(fill="x", padx=10, pady=(0, 4))

        appdata_options = [("AppData\\Local", "Local"), ("AppData\\Roaming", "Roaming"),
                           ("AppData\\LocalLow", "LocalLow")]
        selected_appdata = self.app.config.get("appdata_subdirs", [])
        for val, label in appdata_options:
            var = ctk.BooleanVar(value=(val in selected_appdata))
            self.appdata_vars[val] = var
            ctk.CTkCheckBox(appdata_row, text=label, variable=var,
                            font=ctk.CTkFont(size=13), width=120).pack(side="left", padx=4)

        # ── Varsayılan Yedek Hedefi ──
        ctk.CTkLabel(self, text="💾 Yedekleme Ayarları",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     anchor="w").pack(fill="x", padx=15, pady=(10, 3))

        target_frame = ctk.CTkFrame(self)
        target_frame.pack(fill="x", padx=15, pady=3)

        entry_row = ctk.CTkFrame(target_frame, fg_color="transparent")
        entry_row.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(entry_row, text="Hedef:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 6))
        self.target_var = ctk.StringVar(value=self.app.config.get("backup_target"))
        ctk.CTkEntry(entry_row, textvariable=self.target_var, width=350).pack(side="left", padx=(0, 4))
        ctk.CTkButton(entry_row, text="📁", width=40, command=self._browse_target).pack(side="left")

        # ── Kaydet ──
        ctk.CTkButton(self, text="💾 Ayarları Kaydet", command=self._save_settings,
                      height=36, font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color="#2d8a4e", hover_color="#236b3c").pack(padx=15, pady=8, anchor="w")

        # ── Lisans Anahtarı Defteri ──
        ctk.CTkLabel(self, text="🔑 Lisans Anahtarı Defteri",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     anchor="w").pack(fill="x", padx=15, pady=(10, 3))

        lic_frame = ctk.CTkFrame(self)
        lic_frame.pack(fill="x", padx=15, pady=3)

        lic_btn_row = ctk.CTkFrame(lic_frame, fg_color="transparent")
        lic_btn_row.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(lic_btn_row, text="➕ Lisans Ekle", command=self._add_license,
                      height=30, font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(lic_btn_row, text="🗑️ Seçiliyi Sil", command=self._delete_license,
                      height=30, font=ctk.CTkFont(size=12),
                      fg_color="#c0392b", hover_color="#922b21").pack(side="left")

        self.lic_scroll = ctk.CTkScrollableFrame(lic_frame, height=100)
        self.lic_scroll.pack(fill="x", padx=10, pady=(0, 6))

        self.lic_radio_var = ctk.IntVar(value=-1)
        self._refresh_license_list()

        # ── Son Tarihler ──
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=15, pady=3)
        last_scan = self.app.config.get("last_scan_date", "Hiç") or "Hiç"
        last_backup = self.app.config.get("last_backup_date", "Hiç") or "Hiç"
        ctk.CTkLabel(info_frame, text=f"📋 Son tarama: {last_scan[:19] if last_scan != 'Hiç' else 'Hiç'}",
                     font=ctk.CTkFont(size=11), anchor="w").pack(fill="x", padx=10, pady=1)
        ctk.CTkLabel(info_frame, text=f"💾 Son yedekleme: {last_backup[:19] if last_backup != 'Hiç' else 'Hiç'}",
                     font=ctk.CTkFont(size=11), anchor="w").pack(fill="x", padx=10, pady=1)

        # ── Hakkında ──
        sep = ctk.CTkFrame(self, height=2, fg_color="gray40")
        sep.pack(fill="x", padx=15, pady=(8, 4))

        about = ctk.CTkFrame(self)
        about.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(about, text=f"🖥️ {APP_NAME} v{VERSION}",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(padx=10, pady=(6, 1))
        ctk.CTkLabel(about, text="Windows format öncesi/sonrası yedekleme ve rehber aracı",
                     font=ctk.CTkFont(size=11), text_color="gray60").pack(padx=10, pady=1)
        ctk.CTkLabel(about, text="Hazırlayan: Kadir Erozan  |  📧 kadir.erozan@gmail.com",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(padx=10, pady=(4, 1))
        ctk.CTkLabel(about, text="© 2026 Kadir Erozan — Tüm hakları saklıdır.",
                     font=ctk.CTkFont(size=10), text_color="gray50").pack(padx=10, pady=(0, 6))

    # ── Lisans Yönetimi ─────────────────────────────────────────
    def _refresh_license_list(self):
        """Lisans listesini yenile."""
        for w in self.lic_scroll.winfo_children():
            w.destroy()
        self.lic_radio_var.set(-1)

        if not hasattr(self.app, "license_mgr"):
            return

        licenses = self.app.license_mgr.get_all()
        if not licenses:
            ctk.CTkLabel(self.lic_scroll, text="Kayıtlı lisans yok.",
                         font=ctk.CTkFont(size=11), text_color="gray60").pack(padx=4, pady=4)
            return

        for idx, lic in enumerate(licenses):
            row = ctk.CTkFrame(self.lic_scroll, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=1)
            ctk.CTkRadioButton(row, text="", variable=self.lic_radio_var,
                               value=idx, width=20).pack(side="left")
            text = f"{lic['program']}  →  {lic['key']}"
            if lic.get("notes"):
                text += f"  ({lic['notes']})"
            ctk.CTkLabel(row, text=text, font=ctk.CTkFont(size=11),
                         anchor="w").pack(side="left", padx=4)

    def _add_license(self):
        def on_save(program, key, notes):
            self.app.license_mgr.add(program, key, notes)
            self._refresh_license_list()

        LicenseDialog(self, on_save)

    def _delete_license(self):
        idx = self.lic_radio_var.get()
        if idx < 0:
            messagebox.showwarning("Uyarı", "Silmek için bir lisans seçin!")
            return
        if messagebox.askyesno("Onay", "Seçili lisans silinsin mi?"):
            self.app.license_mgr.remove(idx)
            self._refresh_license_list()

    def _browse_target(self):
        folder = filedialog.askdirectory(title="Varsayılan yedekleme hedefini seçin")
        if folder:
            self.target_var.set(folder)

    def _save_settings(self):
        disks = [d for d, v in self.disk_vars.items() if v.get()]
        appdata = [k for k, v in self.appdata_vars.items() if v.get()]
        self.app.config.set_many({
            "scan_disks": disks, "appdata_subdirs": appdata,
            "backup_target": self.target_var.get(),
        })
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi!")
        self.app.status_bar.set_text("Ayarlar kaydedildi")
