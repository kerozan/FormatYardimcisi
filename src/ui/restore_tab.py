# restore_tab.py
# Geri yükleme sekmesi — yedeklenen verileri orijinal konumlarına geri yükler.

import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.widgets import LogPanel, ProgressFrame


class RestoreTab(ctk.CTkFrame):
    """Yedek geri yükleme sekmesi."""

    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_ref
        self.check_vars = {}  # {group_key: (BooleanVar, rel_paths)}
        self._build_ui()

    def _build_ui(self):
        # ── Kaynak Klasör ──
        src_frame = ctk.CTkFrame(self, fg_color="transparent")
        src_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(src_frame, text="Yedek Kaynağı:",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 8))

        self.source_var = ctk.StringVar(value=self.app.config.get("backup_target"))
        self.source_entry = ctk.CTkEntry(src_frame, textvariable=self.source_var, width=400)
        self.source_entry.pack(side="left", padx=(0, 4))

        ctk.CTkButton(src_frame, text="📁", width=40,
                      command=self._browse_source).pack(side="left", padx=(0, 8))

        ctk.CTkButton(src_frame, text="🔄 Yedekleri Yükle",
                      command=self._load_backups, height=32).pack(side="left")

        # ── Yedek Listesi ──
        ctk.CTkLabel(self, text="Geri Yüklenebilir Klasörler:",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))

        self.folder_scroll = ctk.CTkScrollableFrame(self, height=220)
        self.folder_scroll.pack(fill="x", padx=10, pady=2)

        self.lbl_info = ctk.CTkLabel(self.folder_scroll,
                                     text="Yedek kaynağını seçin ve 'Yedekleri Yükle' butonuna tıklayın.",
                                     font=ctk.CTkFont(size=12))
        self.lbl_info.pack(anchor="w", padx=4, pady=8)

        # ── Butonlar ──
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=4)

        self.btn_restore = ctk.CTkButton(ctrl_frame, text="🔄 Geri Yükle",
                                         command=self._start_restore, height=40,
                                         state="disabled",
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         fg_color="#2874a6", hover_color="#1f5f8b")
        self.btn_restore.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(ctrl_frame, text="⏹ Durdur",
                                      command=self._stop_restore, height=40,
                                      state="disabled", font=ctk.CTkFont(size=14),
                                      fg_color="#c0392b", hover_color="#922b21")
        self.btn_stop.pack(side="left")

        # ── İlerleme ──
        self.progress = ProgressFrame(self)
        self.progress.pack(fill="x", padx=10, pady=4)

        # ── Log ──
        self.log = LogPanel(self, height=180)
        self.log.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    def _browse_source(self):
        folder = filedialog.askdirectory(title="Yedek klasörünü seçin")
        if folder:
            self.source_var.set(folder)

    def _load_backups(self):
        """Manifest'ten geri yüklenebilir öğeleri listele."""
        backup_dir = self.source_var.get()
        manifest_path = os.path.join(backup_dir, "manifest.json")

        if not os.path.exists(manifest_path):
            messagebox.showwarning("Uyarı", f"Manifest dosyası bulunamadı:\n{manifest_path}")
            return

        from restore_engine import RestoreEngine
        engine = RestoreEngine(backup_dir)
        items = engine.get_restorable_items()

        # Listeyi temizle
        for w in self.folder_scroll.winfo_children():
            w.destroy()
        self.check_vars.clear()

        if not items:
            ctk.CTkLabel(self.folder_scroll, text="Yedekte geri yüklenebilir öğe bulunamadı.",
                         font=ctk.CTkFont(size=12)).pack(anchor="w", padx=4, pady=8)
            return

        for item in sorted(items, key=lambda x: x["folder"]):
            var = ctk.BooleanVar(value=True)
            self.check_vars[item["folder"]] = (var, item["rel_paths"])

            size_mb = round(item["total_size"] / (1024 * 1024), 1)
            text = f"{item['folder']}  ({item['file_count']} dosya, {size_mb} MB)"

            cb = ctk.CTkCheckBox(self.folder_scroll, text=text, variable=var,
                                 font=ctk.CTkFont(size=12))
            cb.pack(anchor="w", padx=4, pady=1)

        self.btn_restore.configure(state="normal")
        self.log.log(f"✅ {len(items)} geri yüklenebilir grup bulundu.")

    # ── Geri Yükleme ───────────────────────────────────────────────
    def _start_restore(self):
        selected_paths = []
        for key, (var, paths) in self.check_vars.items():
            if var.get():
                selected_paths.extend(paths)

        if not selected_paths:
            messagebox.showwarning("Uyarı", "Geri yüklenecek öğe seçilmedi!")
            return

        if not messagebox.askyesno("Geri Yükleme Onayı",
                                   f"{len(selected_paths)} dosya orijinal konumlarına geri yüklenecek.\n"
                                   f"Mevcut dosyaların üzerine yazılacak.\n\nDevam edilsin mi?"):
            return

        self.btn_restore.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log.clear()
        self.progress.reset("Geri yükleme başlıyor...")
        self.app.status_bar.set_text("Geri yükleme devam ediyor...")

        from restore_engine import RestoreEngine
        self.engine = RestoreEngine(self.source_var.get())

        thread = threading.Thread(target=self._restore_worker, args=(selected_paths,), daemon=True)
        thread.start()

    def _restore_worker(self, rel_paths):
        def progress_cb(cur, total, msg):
            self.after(0, self.progress.update_progress, cur, total, msg)
            self.after(0, self.log.log, msg)

        def done_cb(summary):
            self.after(0, self._restore_done, summary)

        self.engine.restore(rel_paths, progress_cb=progress_cb, done_cb=done_cb)

    def _restore_done(self, summary):
        self.log.log(summary)
        self.btn_restore.configure(state="normal")
        self.btn_stop.configure(state="disabled")

        import datetime
        self.app.config.set("last_restore_date", datetime.datetime.now().isoformat())
        self.app.status_bar.set_text("Geri yükleme tamamlandı")

    def _stop_restore(self):
        if hasattr(self, "engine") and self.engine.is_running:
            self.engine.stop()
            self.btn_stop.configure(state="disabled")
            self.log.log("⏳ Durdurma sinyali gönderildi...")
