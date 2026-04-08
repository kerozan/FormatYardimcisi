# scan_tab.py
# Tarama sekmesi — tarama, durdurma, otomatik rehber+CSV, dosya açma.

import os
import threading
import datetime
import customtkinter as ctk
from ui.widgets import LogPanel, ProgressFrame


class ScanTab(ctk.CTkFrame):
    """Program tarama ve rehber oluşturma sekmesi."""

    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_ref
        self.scan_results = None
        self.guide_path = None
        self.csv_paths = None
        self._build_ui()

    def _build_ui(self):
        # ── Üst Butonlar ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.btn_scan = ctk.CTkButton(
            btn_frame, text="🔍 Taramayı Başlat", command=self._start_scan,
            height=38, font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_scan.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            btn_frame, text="⏹ Durdur", command=self._stop_scan,
            height=38, state="disabled",
            fg_color="#c0392b", hover_color="#922b21",
            font=ctk.CTkFont(size=14))
        self.btn_stop.pack(side="left", padx=(0, 16))

        self.btn_guide = ctk.CTkButton(
            btn_frame, text="📄 Rehberi Aç", command=self._open_guide,
            height=38, state="disabled", font=ctk.CTkFont(size=14))
        self.btn_guide.pack(side="left", padx=(0, 8))

        self.btn_folder = ctk.CTkButton(
            btn_frame, text="📂 Çıktı Klasörü", command=self._open_output_folder,
            height=38, state="disabled", font=ctk.CTkFont(size=14))
        self.btn_folder.pack(side="left")

        # ── İlerleme (indeterminate mod) ──
        self.progress = ProgressFrame(self)
        self.progress.pack(fill="x", padx=10, pady=4)

        # ── Özet Panel ──
        self.summary_frame = ctk.CTkFrame(self)
        self.summary_frame.pack(fill="x", padx=10, pady=4)

        self.lbl_summary = ctk.CTkLabel(
            self.summary_frame, text="Henüz tarama yapılmadı.",
            font=ctk.CTkFont(size=13), anchor="w", wraplength=900)
        self.lbl_summary.pack(fill="x", padx=10, pady=6)

        # ── Log Paneli ──
        self.log = LogPanel(self, height=350)
        self.log.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # Başlangıç durumu: Eski dosyaları kontrol et
        self.after(100, self._check_previous_state)

    def _check_previous_state(self):
        """Uygulama açıldığında önceki rehber ve çıktıları kontrol edip butonları aktif eder."""
        out = self.app.output_dir
        
        # Çıktı klasörü doluysa klasör butonunu aç
        if os.path.exists(out) and len(os.listdir(out)) > 0:
            self.btn_folder.configure(state="normal")
            
        # Rehber dosyası varsa butonunu aç
        if os.path.exists(os.path.join(out, "yedekleme_rehberi.html")) or os.path.exists(os.path.join(out, "yedekleme_rehberi.md")):
            self.btn_guide.configure(state="normal")

        # Önceki tarama özetini göster
        try:
            prev = self.app.scanner.load_previous_scan()
            if prev and prev.get("registry_programs"):
                folder_count = len(prev.get("folder_programs", []))
                reg_count = len(prev.get("registry_programs", []))
                drv_count = len(prev.get("drivers", []))
                total_gb = sum(p.get("boyut_mb", 0) for p in prev.get("folder_programs", [])) / 1024
                
                summary = f"Geçmiş Tarama ( {prev.get('scan_date', '')[:10]} ): 📊 {reg_count} registry programı + {folder_count} klasör öğesi | {total_gb:.1f} GB"
                if drv_count:
                    summary += f" | 🔧 {drv_count} sürücü"
                    
                self.lbl_summary.configure(text=summary)
                self.log.log("ℹ️ Önceki tarama sonuçları tespit edildi. Rehberi veya çıktı klasörünü açabilirsiniz.\n")
        except Exception:
            pass

    # ── Tarama Kontrol ─────────────────────────────────────────────
    def _start_scan(self):
        self.btn_scan.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_guide.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        self.log.clear()

        # İndeterminate ilerleme çubuğu (animasyonlu)
        self.progress.progress_bar.configure(mode="indeterminate")
        self.progress.progress_bar.start()
        self.progress.label.configure(text="Tarama devam ediyor...")
        self.app.status_bar.set_text("Tarama devam ediyor...")

        disks = self.app.config.get("scan_disks")
        appdata = self.app.config.get("appdata_subdirs")
        thread = threading.Thread(target=self._scan_worker, args=(disks, appdata), daemon=True)
        thread.start()

    def _stop_scan(self):
        self.app.scanner.stop()
        self.btn_stop.configure(state="disabled")
        self.log.log("⏳ Durdurma sinyali gönderildi, mevcut işlem tamamlanıyor...")

    def _scan_worker(self, disks, appdata):
        scanner = self.app.scanner
        prev = scanner.load_previous_scan()

        def cb(msg):
            self.after(0, self.log.log, msg)

        try:
            results = scanner.scan_all(disks, appdata, callback=cb)
            diff = scanner.compare_scans(results, prev)
            scanner.save_scan(results)
            self.scan_results = results

            # Başlangıç programları ve hizmetleri tara
            startup_progs = scanner.scan_startup_programs(callback=cb)
            services = scanner.scan_services(callback=cb)
            results["startup_programs"] = startup_progs
            results["services"] = services

            # Eski CSV dosyalarını temizle
            self._cleanup_old_files()

            # Lisans bilgilerini al
            licenses = self.app.license_mgr.get_all() if hasattr(self.app, "license_mgr") else None

            # Otomatik rehber ve CSV oluştur
            self.after(0, lambda: self.log.log("\n📄 Rehber ve CSV otomatik oluşturuluyor..."))

            gen_args = dict(licenses=licenses, startup_programs=startup_progs)
            # Markdown rehber
            content = self.app.guide_gen.generate(results, diff, **gen_args)
            guide_path = self.app.guide_gen.save(content)
            # HTML rehber
            html_content = self.app.guide_gen.generate_html(results, diff, **gen_args)
            html_guide_path = self.app.guide_gen.save_html(html_content)

            csv_paths = scanner.export_csv(results)

            self.guide_path = guide_path
            self.html_guide_path = html_guide_path
            self.csv_paths = csv_paths
            self.after(0, self._scan_done, results, diff)

        except Exception as e:
            # Hata olursa da UI kilidini aç
            self.after(0, self.log.log, f"❌ Tarama hatası: {e}")
            self.after(0, self._scan_error)

    def _cleanup_old_files(self):
        """Eski CSV dosyalarını siler (rehber her zaman üzerine yazılır)."""
        out = self.app.output_dir
        if not os.path.exists(out):
            return
        for f in os.listdir(out):
            if (f.startswith("klasor_programlar_") or f.startswith("registry_programlar_")) and f.endswith(".csv"):
                try:
                    os.remove(os.path.join(out, f))
                except OSError:
                    pass

    def _scan_done(self, results, diff):
        # İlerlemeyi durdur
        self.progress.progress_bar.stop()
        self.progress.progress_bar.configure(mode="determinate")
        self.progress.progress_bar.set(1.0)
        self.progress.label.configure(text="✅ Tarama tamamlandı!")

        folder_count = len(results.get("folder_programs", []))
        reg_count = len(results.get("registry_programs", []))
        drv_count = len(results.get("drivers", []))
        total_gb = sum(p["boyut_mb"] for p in results.get("folder_programs", [])) / 1024

        summary = f"📊 {reg_count} registry programı + {folder_count} klasör öğesi | {total_gb:.1f} GB"
        if drv_count:
            summary += f" | 🔧 {drv_count} sürücü"

        new_list = diff.get("new", [])
        rem_list = diff.get("removed", [])
        if new_list or rem_list:
            summary += f"\n🟢 Yeni: {len(new_list)} | 🔴 Kaldırılan: {len(rem_list)}"
            if new_list:
                self.log.log("\n── 🟢 YENİ KURULAN ──")
                for p in new_list:
                    self.log.log(f"  + {p['program_adi']} ({p.get('versiyon', '')})")
            if rem_list:
                self.log.log("\n── 🔴 KALDIRILAN ──")
                for p in rem_list:
                    self.log.log(f"  - {p['program_adi']} ({p.get('versiyon', '')})")

        if self.guide_path:
            self.log.log(f"\n✅ Rehber (MD): {self.guide_path}")
        if hasattr(self, 'html_guide_path') and self.html_guide_path:
            self.log.log(f"✅ Rehber (HTML): {self.html_guide_path}")
        if self.csv_paths:
            self.log.log(f"✅ Klasör CSV: {self.csv_paths[0]}")
            self.log.log(f"✅ Registry CSV: {self.csv_paths[1]}")

        self.lbl_summary.configure(text=summary)
        self.btn_scan.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_guide.configure(state="normal")
        self.btn_folder.configure(state="normal")

        self.app.config.set("last_scan_date", datetime.datetime.now().isoformat())
        self.app.status_bar.set_text(f"Tarama tamamlandı — {reg_count} program | Rehber ve CSV hazır")

    def _scan_error(self):
        """Tarama sırasında hata olursa UI kilidini aç."""
        self.progress.progress_bar.stop()
        self.progress.progress_bar.configure(mode="determinate")
        self.progress.progress_bar.set(0)
        self.progress.label.configure(text="❌ Tarama hatası!")
        self.btn_scan.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.app.status_bar.set_text("Tarama hatası oluştu")

    # ── Dosya Açma ────────────────────────────────────────────────
    def _open_guide(self):
        """HTML rehberi tarayıcıda aç (daha görsel)."""
        html_path = getattr(self, 'html_guide_path', None) or os.path.join(self.app.output_dir, "yedekleme_rehberi.html")
        if os.path.exists(html_path):
            os.startfile(html_path)
        else:
            # Fallback: MD dosyası
            md_path = self.guide_path or os.path.join(self.app.output_dir, "yedekleme_rehberi.md")
            if os.path.exists(md_path):
                os.startfile(md_path)

    def _open_output_folder(self):
        """Çıktı klasörünü dosya yöneticisinde aç."""
        out = self.app.output_dir
        if os.path.exists(out):
            os.startfile(out)
