# backup_tab.py
# Yedekleme sekmesi — İncele butonu, boyut cache, AI klasörleri, disk alanı, ZIP.

import os
import json
import time
import shutil
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.widgets import LogPanel, ProgressFrame


def _get_folder_size(path):
    """Klasörün gerçek boyutunu recursive hesaplar."""
    if not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _get_folder_size(entry.path)
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass
    return total


def _format_size(size_bytes):
    """Bayt → okunaklı format."""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024**3):.1f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"


def get_recommended_folders():
    """Sistemde mevcut olan önerilen yedekleme klasörlerini döndürür."""
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")

    candidates = [
        ("🔴 Masaüstü", os.path.join(home, "Desktop")),
        ("🔴 Belgelerim", os.path.join(home, "Documents")),
        ("🔴 Favoriler", os.path.join(home, "Favorites")),
        ("🔴 SSH Anahtarları", os.path.join(home, ".ssh")),
        ("🟠 VS Code Ayarları", os.path.join(appdata, "Code")),
        ("🟠 Adobe Ayarları", os.path.join(appdata, "Adobe")),
        ("🟠 OBS Studio", os.path.join(appdata, "obs-studio")),
        ("🟠 FileZilla", os.path.join(appdata, "FileZilla")),
        ("🟠 Notepad++", os.path.join(appdata, "Notepad++")),
        ("🟠 HandBrake", os.path.join(appdata, "HandBrake")),
        ("🟠 Mp3tag", os.path.join(appdata, "Mp3tag")),
        ("🟠 uTorrent", os.path.join(appdata, "uTorrent")),
        ("🟠 Calibre", os.path.join(appdata, "calibre")),
        ("🟠 Docker Desktop", os.path.join(appdata, "Docker Desktop")),
        ("🟠 Foxit Software", os.path.join(appdata, "Foxit Software")),
        ("🟠 PowerToys", os.path.join(localappdata, "PowerToys")),
        ("🟡 npm Global", os.path.join(appdata, "npm")),
        ("🟡 Git Config", os.path.join(home, ".gitconfig")),
        ("🤖 Gemini Config", os.path.join(home, ".gemini")),
        ("🤖 Antigravity Data", os.path.join(appdata, "Antigravity")),
        ("🤖 Claude Config", os.path.join(appdata, "Claude")),
        ("🤖 ChatGPT Config", os.path.join(appdata, "ChatGPT")),
        ("🤖 Copilot Config", os.path.join(appdata, "GitHub Copilot")),
        ("🤖 Antigravity Local", os.path.join(localappdata, "Antigravity")),
    ]
    return [(name, path) for name, path in candidates if os.path.exists(path)]


class BackupTab(ctk.CTkFrame):
    """Data yedekleme sekmesi."""

    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_ref
        self.check_vars = {}   # {path: BooleanVar}
        self.folder_sizes = {} # {path: size_bytes}
        self.custom_folders = []
        self._sizes_file = os.path.join(app_ref.data_dir, "backup_sizes.json")
        self._load_cached_sizes()
        self._build_ui()
        self._load_saved_selections()

    def _load_cached_sizes(self):
        """Önceki inceleme sonuçlarını dosyadan yükle."""
        if os.path.exists(self._sizes_file):
            try:
                with open(self._sizes_file, "r", encoding="utf-8") as f:
                    self.folder_sizes = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.folder_sizes = {}

    def _save_cached_sizes(self):
        """İnceleme sonuçlarını dosyaya kaydet."""
        with open(self._sizes_file, "w", encoding="utf-8") as f:
            json.dump(self.folder_sizes, f, indent=2, ensure_ascii=False)

    def _build_ui(self):
        # ── Hedef Klasör + ZIP ──
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=(8, 4))

        row1 = ctk.CTkFrame(top_frame, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkLabel(row1, text="Yedekleme Hedefi:",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(0, 8))
        self.target_var = ctk.StringVar(value=self.app.config.get("backup_target"))
        ctk.CTkEntry(row1, textvariable=self.target_var, width=350).pack(side="left", padx=(0, 4))
        ctk.CTkButton(row1, text="📁", width=40, command=self._browse_target).pack(side="left", padx=(0, 12))

        self.zip_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row1, text="📦 ZIP olarak sıkıştır", variable=self.zip_var,
                        font=ctk.CTkFont(size=12)).pack(side="left")

        # Bilgi satırı
        self.lbl_info = ctk.CTkLabel(top_frame, text="",
                                     font=ctk.CTkFont(size=12), anchor="w", text_color="gray60")
        self.lbl_info.pack(fill="x", padx=8, pady=(0, 6))

        # ── Klasör Listesi ──
        ctk.CTkLabel(self, text="Yedeklenecek Klasörler:",
                     font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=10, pady=(4, 2))

        self.folder_scroll = ctk.CTkScrollableFrame(self, height=190)
        self.folder_scroll.pack(fill="x", padx=10, pady=2)
        self._populate_folders()

        # ── Buton Satırı: Özel Klasör + İncele ──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(btn_row, text="➕ Özel Klasör Ekle", command=self._add_custom_folder,
                      height=30, font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))

        self.btn_inspect = ctk.CTkButton(
            btn_row, text="🔎 İncele (Boyut Hesapla)", command=self._start_inspect,
            height=30, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2874a6", hover_color="#1f5f8b")
        self.btn_inspect.pack(side="left", padx=(0, 8))

        self.lbl_inspect_status = ctk.CTkLabel(
            btn_row, text="", font=ctk.CTkFont(size=11), text_color="gray60")
        self.lbl_inspect_status.pack(side="left")

        # Sürücü dışa aktar butonu
        self.btn_drivers = ctk.CTkButton(
            btn_row, text="🔧 Sürücüleri Dışa Aktar", command=self._start_driver_export,
            height=30, font=ctk.CTkFont(size=12),
            fg_color="#7d3c98", hover_color="#6c3483")
        self.btn_drivers.pack(side="right")

        # ── Kontrol Butonları ──
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=4)

        self.btn_start = ctk.CTkButton(
            ctrl_frame, text="▶ Yedeklemeyi Başlat", command=self._start_backup,
            height=40, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2d8a4e", hover_color="#236b3c")
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            ctrl_frame, text="⏹ Durdur", command=self._stop_backup,
            height=40, state="disabled", font=ctk.CTkFont(size=14),
            fg_color="#c0392b", hover_color="#922b21")
        self.btn_stop.pack(side="left", padx=(0, 8))

        self.btn_report = ctk.CTkButton(
            ctrl_frame, text="📄 Son Raporu Aç", command=self._open_last_report,
            height=40, state="disabled", font=ctk.CTkFont(size=14),
            fg_color="#6e40c9", hover_color="#553098")
        self.btn_report.pack(side="left")

        # ── İlerleme ──
        self.progress = ProgressFrame(self)
        self.progress.pack(fill="x", padx=10, pady=4)

        # ── Log ──
        self.log = LogPanel(self, height=140)
        self.log.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    # ── Klasör Populasyonu ────────────────────────────────────────
    def _populate_folders(self):
        """Klasörleri listele, cache'deki boyutlarla göster."""
        for w in self.folder_scroll.winfo_children():
            w.destroy()
        self.check_vars.clear()

        self._folder_items = get_recommended_folders()
        for path in self.custom_folders:
            if os.path.exists(path) and path not in [p for _, p in self._folder_items]:
                self._folder_items.append((f"📂 {os.path.basename(path)}", path))

        self._cb_widgets = {}
        for name, path in self._folder_items:
            var = ctk.BooleanVar(value=True)
            self.check_vars[path] = var

            # Cache'den boyut göster
            cached_size = self.folder_sizes.get(path)
            if cached_size is not None:
                size_text = f"({_format_size(cached_size)})"
            else:
                size_text = "(boyut bilinmiyor)"

            cb = ctk.CTkCheckBox(
                self.folder_scroll, text=f"{name}  {size_text}",
                variable=var, font=ctk.CTkFont(size=12),
                command=self._update_info)
            cb.pack(anchor="w", padx=4, pady=1)
            self._cb_widgets[path] = (cb, name)

        self._update_info()

    # ── İncele (Boyut Hesapla) ────────────────────────────────────
    def _start_inspect(self):
        """Seçili klasörlerin boyutlarını arka planda hesaplar."""
        self.btn_inspect.configure(state="disabled")
        self.lbl_inspect_status.configure(text="⏳ Hesaplanıyor...")
        thread = threading.Thread(target=self._inspect_worker, daemon=True)
        thread.start()

    def _inspect_worker(self):
        """Her klasörü sırayla hesapla, UI'ı güncelle."""
        total_items = len(self._folder_items)
        for idx, (name, path) in enumerate(self._folder_items):
            self.after(0, self.lbl_inspect_status.configure,
                       {"text": f"⏳ [{idx+1}/{total_items}] {name}..."})
            size = _get_folder_size(path)
            self.folder_sizes[path] = size

            # Checkbox metnini güncelle
            if path in self._cb_widgets:
                cb, orig_name = self._cb_widgets[path]
                self.after(0, cb.configure,
                           {"text": f"{orig_name}  ({_format_size(size)})"})

        # Sonuçları kaydet
        self._save_cached_sizes()
        self.after(0, self._inspect_done)

    def _inspect_done(self):
        self.btn_inspect.configure(state="normal")
        self.lbl_inspect_status.configure(text="✅ Boyutlar hesaplandı ve kaydedildi.")
        self._update_info()

    # ── Bilgi Satırı ──────────────────────────────────────────────
    def _update_info(self):
        """Seçili toplam boyut + hedef disk alanını göster."""
        total = 0
        for path, var in self.check_vars.items():
            if var.get():
                total += self.folder_sizes.get(path, 0)

        info = f"📦 Seçili toplam: {_format_size(total)}"

        target = self.target_var.get().strip()
        if target and len(target) >= 2:
            drive = os.path.splitdrive(target)[0]
            if drive and os.path.exists(drive + "\\"):
                try:
                    free = shutil.disk_usage(drive + "\\").free
                    info += f"  |  💿 Hedef disk boş alan: {_format_size(free)}"
                    if total > free > 0:
                        info += "  ⚠️ YETERSİZ ALAN!"
                except OSError:
                    pass

        self.lbl_info.configure(text=info)

    def _browse_target(self):
        folder = filedialog.askdirectory(title="Yedekleme hedef klasörünü seçin")
        if folder:
            self.target_var.set(folder)
            self.app.config.set("backup_target", folder)
            self._update_info()

    def _add_custom_folder(self):
        folder = filedialog.askdirectory(title="Yedeklenecek klasörü seçin")
        if folder and folder not in self.check_vars:
            self.custom_folders.append(folder)
            self._populate_folders()

    def _get_selected_folders(self):
        return [(os.path.basename(p), p) for p, v in self.check_vars.items() if v.get()]

    def _save_selections(self):
        self.app.config.set("backup_folders", [p for p, v in self.check_vars.items() if v.get()])
        self.app.config.set("backup_target", self.target_var.get())

    def _load_saved_selections(self):
        saved = self.app.config.get("backup_folders", [])
        if saved:
            for path, var in self.check_vars.items():
                var.set(path in saved)
            self._update_info()

    # ── Yedekleme ──────────────────────────────────────────────────
    def _start_backup(self):
        selected = self._get_selected_folders()
        if not selected:
            messagebox.showwarning("Uyarı", "Yedeklenecek klasör seçilmedi!")
            return
        target = self.target_var.get()
        if not target:
            messagebox.showwarning("Uyarı", "Yedekleme hedef klasörü belirtilmedi!")
            return

        total = sum(self.folder_sizes.get(p, 0) for _, p in selected)
        drive = os.path.splitdrive(target)[0]
        if drive:
            try:
                free = shutil.disk_usage(drive + "\\").free
                if total > free > 0:
                    messagebox.showerror("Yetersiz Alan",
                                         f"Yedek: {_format_size(total)}\nBoş: {_format_size(free)}")
                    return
            except OSError:
                pass

        mode = "ZIP" if self.zip_var.get() else "Normal"
        names = "\n".join([f"  • {n}" for n, _ in selected])
        if not messagebox.askyesno("Yedekleme Onayı",
                                   f"Mod: {mode}\nToplam: {_format_size(total)}\n\n{names}\n\nHedef: {target}"):
            return

        # Tarayıcı kontrolü — kilitli dosya sorununu önle
        running_browsers = self._detect_browsers()
        if running_browsers:
            browser_names = ", ".join(running_browsers)
            choice = messagebox.askyesnocancel(
                "Tarayıcı Açık",
                f"Şu tarayıcılar çalışıyor: {browser_names}\n\n"
                f"Tam yedekleme için tarayıcıların kapatılması gerekir.\n"
                f"Cookies, oturum ve sekme verileri ancak böyle yedeklenebilir.\n\n"
                f"• Evet → Tarayıcıları kapat ve yedekle\n"
                f"• Hayır → Kilitli dosyaları atlayarak devam et\n"
                f"• İptal → Yedeklemeyi iptal et")
            if choice is None:  # İptal
                return
            if choice:  # Evet — kapat
                self._close_browsers(running_browsers)

        self._save_selections()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log.clear()
        self.progress.reset("Yedekleme başlıyor...")
        self.app.status_bar.set_text("Yedekleme devam ediyor...")

        from backup_engine import BackupEngine
        self.engine = BackupEngine(target)

        use_zip = self.zip_var.get()
        thread = threading.Thread(target=self._backup_worker, args=(selected, use_zip), daemon=True)
        thread.start()

    def _backup_worker(self, folder_list, use_zip):
        self._error_list = []
        self._start_time = time.time()

        def progress_cb(cur, total, msg):
            self.after(0, self.progress.update_progress, cur, total, msg)
            self.after(0, self.log.log, msg)
            # Hata topla
            if msg.startswith("❌"):
                self._error_list.append((msg.split(":", 1)[0][2:].strip(), msg.split(":", 1)[-1].strip() if ":" in msg else ""))

        def done_cb(summary):
            elapsed = time.time() - self._start_time
            self.after(0, self._backup_done, summary, folder_list, use_zip, elapsed)

        if use_zip:
            self.engine.backup_as_zip(folder_list, progress_cb=progress_cb, done_cb=done_cb)
        else:
            self.engine.backup(folder_list, progress_cb=progress_cb, done_cb=done_cb)

    def _backup_done(self, summary, folder_list=None, use_zip=False, elapsed=0):
        self.log.log(summary)
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        import datetime
        self.app.config.set("last_backup_date", datetime.datetime.now().isoformat())
        self.app.status_bar.set_text("Yedekleme tamamlandı")

        # HTML rapor oluştur
        try:
            self._generate_report(summary, folder_list or [], use_zip, elapsed)
        except Exception as e:
            self.log.log(f"⚠️ Rapor oluşturulamadı: {e}")

    def _generate_report(self, summary, folder_list, use_zip, elapsed):
        """HTML rapor oluştur ve ta rayıcıda aç."""
        from html_reporter import HtmlReporter
        import datetime

        # Summary'den sayıları çıkar
        lines = summary.strip().split("\n")
        copied = skipped = errors = total_mb = zip_mb = 0
        zip_file = ""
        stopped = False

        for line in lines:
            line = line.strip()
            if "Kopyalanan" in line or "Eklenen dosya" in line:
                try: copied = int(line.split(":")[1].strip())
                except: pass
            elif "Atlanan" in line:
                try: skipped = int(line.split(":")[1].strip().split()[0])
                except: pass
            elif "Hata" in line and ":" in line:
                try: errors = int(line.split(":")[1].strip())
                except: pass
            elif "Boyut" in line or "Orijinal boyut" in line:
                try: total_mb = float(line.split(":")[1].strip().split()[0])
                except: pass
            elif "ZIP boyutu" in line:
                try: zip_mb = float(line.split(":")[1].strip().split()[0])
                except: pass
            elif "Dosya" in line and "zip" in line.lower():
                zip_file = line.split(":", 1)[1].strip() if ":" in line else ""
            elif "durduruldu" in line.lower():
                stopped = True

        # Klasör bilgileri
        folders_info = []
        for name, path in folder_list:
            size = self.folder_sizes.get(path, 0)
            fcount = 0
            try:
                for _, _, files in os.walk(path):
                    fcount += len(files)
            except (PermissionError, OSError):
                pass
            folders_info.append((name, path, fcount, size))

        report_data = {
            "mode": "zip" if use_zip else "normal",
            "date": datetime.datetime.now().isoformat(),
            "copied": copied,
            "skipped": skipped,
            "errors": errors,
            "total_size_mb": total_mb,
            "zip_size_mb": zip_mb,
            "zip_file": zip_file,
            "stopped": stopped,
            "folders": folders_info,
            "error_list": getattr(self, "_error_list", []),
            "duration_sec": elapsed,
            "target_dir": self.target_var.get(),
        }

        reporter = HtmlReporter(self.app.output_dir)
        html = reporter.generate(report_data)
        path = reporter.save(html)

        self._last_report_path = path
        self.btn_report.configure(state="normal")
        self.log.log(f"\n📄 HTML Rapor: {path}")

        # Tarayıcıda otomatik aç
        try:
            os.startfile(path)
        except OSError:
            pass

    def _open_last_report(self):
        """Son oluşturulan raporu tarayıcıda aç."""
        path = getattr(self, "_last_report_path", None)
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            # cikti/ klasöründe en son raporu bul
            out = self.app.output_dir
            reports = [f for f in os.listdir(out) if f.startswith("rapor_") and f.endswith(".html")]
            if reports:
                latest = os.path.join(out, sorted(reports)[-1])
                os.startfile(latest)
            else:
                messagebox.showinfo("Bilgi", "Henüz rapor oluşturulmamış.")

    def _stop_backup(self):
        if hasattr(self, "engine") and self.engine.is_running:
            self.engine.stop()
            self.btn_stop.configure(state="disabled")
            self.log.log("⏳ Durdurma sinyali gönderildi, mevcut dosya tamamlanıyor...")

    # ── Tarayıcı Kontrol ──────────────────────────────────────────
    BROWSER_PROCESSES = {
        "chrome.exe": "Google Chrome",
        "msedge.exe": "Microsoft Edge",
        "firefox.exe": "Mozilla Firefox",
        "brave.exe": "Brave",
        "opera.exe": "Opera",
        "vivaldi.exe": "Vivaldi",
    }

    def _detect_browsers(self):
        """Çalışan tarayıcıları tespit eder."""
        import subprocess
        running = []
        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            processes = result.stdout.lower()
            for proc, name in self.BROWSER_PROCESSES.items():
                if proc in processes:
                    running.append(name)
        except Exception:
            pass
        return running

    def _close_browsers(self, browser_names):
        """Tarayıcıları nazikçe kapatır, 5 sn bekler, zorla kapatır."""
        import subprocess
        import time

        # İsim → process eşle
        name_to_proc = {v: k for k, v in self.BROWSER_PROCESSES.items()}

        for bname in browser_names:
            proc = name_to_proc.get(bname)
            if not proc:
                continue
            try:
                # Önce nazik kapatma (WM_CLOSE sinyali)
                subprocess.run(
                    ["taskkill", "/IM", proc],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass

        # Tarayıcıların kapanması için bekle
        time.sleep(3)

        # Hâlâ açıksa zorla kapat
        still_running = self._detect_browsers()
        for bname in still_running:
            proc = name_to_proc.get(bname)
            if not proc:
                continue
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", proc],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass

        time.sleep(1)

    # ── Sürücü Dışa Aktarma ────────────────────────────────────────
    def _start_driver_export(self):
        """Sürücüleri tarayıp hedef klasöre dışa aktarır."""
        target = self.target_var.get().strip()
        if not target:
            messagebox.showwarning("Uyarı", "Yedekleme hedef klasörü belirtilmedi!")
            return

        self.btn_drivers.configure(state="disabled")
        self.log.log("\n🔧 Sürücüler taranıyor...")
        self.progress.reset("🔧 Sürücü taraması...")
        self.app.status_bar.set_text("Sürücü dışa aktarma devam ediyor...")

        thread = threading.Thread(target=self._driver_export_worker, args=(target,), daemon=True)
        thread.start()

    def _driver_export_worker(self, target_dir):
        """Arka planda sürücü tara + export."""
        from driver_scanner import DriverScanner

        scanner = DriverScanner()

        # Önce tara
        def scan_cb(msg):
            self.after(0, self.log.log, msg)

        drivers = scanner.scan_drivers(callback=scan_cb)

        if not drivers:
            self.after(0, self.log.log, "⚠️ Üçüncü parti sürücü bulunamadı.")
            self.after(0, self.btn_drivers.configure, {"state": "normal"})
            self.after(0, self.app.status_bar.set_text, "Sürücü tara— bulunamadı")
            return

        self.after(0, self.log.log, f"\n📦 {len(drivers)} sürücü dışa aktarılıyor...")

        def progress_cb(cur, total, msg):
            self.after(0, self.progress.update_progress, cur, total, msg)
            self.after(0, self.log.log, msg)

        summary, export_dir = scanner.export_drivers(drivers, target_dir, progress_cb=progress_cb)

        self.after(0, self.log.log, summary)
        self.after(0, self.btn_drivers.configure, {"state": "normal"})
        self.after(0, self.app.status_bar.set_text,
                   f"Sürücü dışa aktarma tamamlandı — {export_dir}")
