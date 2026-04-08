# diff_tab.py
# Yedekleme karşılaştırma sekmesi — iki manifest arasındaki farkları gösterir.

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.widgets import LogPanel


class DiffTab(ctk.CTkFrame):
    """İki yedek manifest'ini karşılaştıran diff viewer sekmesi."""

    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_ref
        self.diff_result = None
        self._build_ui()

    def _build_ui(self):
        # ── Başlık ──
        ctk.CTkLabel(self, text="İki yedek arasındaki farkları karşılaştırın.",
                     font=ctk.CTkFont(size=12), text_color="gray60",
                     anchor="w").pack(fill="x", padx=10, pady=(8, 4))

        # ── Kaynak A (Eski Yedek) ──
        frame_a = ctk.CTkFrame(self)
        frame_a.pack(fill="x", padx=10, pady=3)

        row_a = ctk.CTkFrame(frame_a, fg_color="transparent")
        row_a.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(row_a, text="📁 Eski Yedek (A):",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     width=140, anchor="w").pack(side="left")
        self.path_a_var = ctk.StringVar(value=self.app.config.get("backup_target"))
        ctk.CTkEntry(row_a, textvariable=self.path_a_var, width=380).pack(side="left", padx=(0, 4))
        ctk.CTkButton(row_a, text="📁", width=40,
                      command=lambda: self._browse("a")).pack(side="left", padx=(0, 8))
        self.lbl_info_a = ctk.CTkLabel(row_a, text="",
                                        font=ctk.CTkFont(size=11), text_color="gray60")
        self.lbl_info_a.pack(side="left")

        # ── Kaynak B (Yeni Yedek) ──
        frame_b = ctk.CTkFrame(self)
        frame_b.pack(fill="x", padx=10, pady=3)

        row_b = ctk.CTkFrame(frame_b, fg_color="transparent")
        row_b.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(row_b, text="📁 Yeni Yedek (B):",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     width=140, anchor="w").pack(side="left")
        self.path_b_var = ctk.StringVar()
        ctk.CTkEntry(row_b, textvariable=self.path_b_var, width=380).pack(side="left", padx=(0, 4))
        ctk.CTkButton(row_b, text="📁", width=40,
                      command=lambda: self._browse("b")).pack(side="left", padx=(0, 8))
        self.lbl_info_b = ctk.CTkLabel(row_b, text="",
                                        font=ctk.CTkFont(size=11), text_color="gray60")
        self.lbl_info_b.pack(side="left")

        # ── Butonlar ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=6)

        self.btn_compare = ctk.CTkButton(
            btn_frame, text="🔍 Karşılaştır", command=self._compare,
            height=40, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2874a6", hover_color="#1f5f8b")
        self.btn_compare.pack(side="left", padx=(0, 8))

        self.btn_export = ctk.CTkButton(
            btn_frame, text="📄 HTML Dışa Aktar", command=self._export_html,
            height=40, state="disabled", font=ctk.CTkFont(size=14),
            fg_color="#6e40c9", hover_color="#553098")
        self.btn_export.pack(side="left")

        # ── Özet Kutuları ──
        self.summary_frame = ctk.CTkFrame(self)
        self.summary_frame.pack(fill="x", padx=10, pady=4)

        self._stat_boxes = {}
        stats_row = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=8, pady=6)

        for key, label, color in [
            ("new", "🟢 Yeni", "#3fb950"),
            ("removed", "🔴 Silinen", "#f85149"),
            ("modified", "🟡 Değişen", "#d29922"),
            ("unchanged", "⚪ Aynı", "#8b949e"),
        ]:
            box = ctk.CTkFrame(stats_row, width=140)
            box.pack(side="left", padx=4, expand=True, fill="x")
            box.pack_propagate(False)
            box.configure(height=60)

            val_label = ctk.CTkLabel(box, text="—",
                                      font=ctk.CTkFont(size=22, weight="bold"),
                                      text_color=color)
            val_label.pack(pady=(6, 0))
            ctk.CTkLabel(box, text=label,
                         font=ctk.CTkFont(size=11), text_color="gray60").pack()

            self._stat_boxes[key] = val_label

        # ── Sonuç Listesi (Scrollable) ──
        self.result_scroll = ctk.CTkScrollableFrame(self, height=200)
        self.result_scroll.pack(fill="both", expand=True, padx=10, pady=(4, 2))

        self.lbl_placeholder = ctk.CTkLabel(
            self.result_scroll,
            text="Karşılaştırma sonuçları burada görünecek.\n"
                 "İki yedek klasörü seçip 'Karşılaştır' butonuna tıklayın.",
            font=ctk.CTkFont(size=12), text_color="gray50")
        self.lbl_placeholder.pack(pady=30)

        # ── Alt bilgi ──
        self.log = LogPanel(self, height=80)
        self.log.pack(fill="x", padx=10, pady=(2, 10))

    # ── Yardımcılar ────────────────────────────────────────────────
    def _browse(self, which):
        folder = filedialog.askdirectory(title="Yedek klasörünü seçin")
        if not folder:
            return
        if which == "a":
            self.path_a_var.set(folder)
            self._show_manifest_info(folder, self.lbl_info_a)
        else:
            self.path_b_var.set(folder)
            self._show_manifest_info(folder, self.lbl_info_b)

    def _show_manifest_info(self, path, label):
        """Manifest hakkında kısa bilgi göster."""
        from backup_diff import BackupDiffEngine
        manifest = BackupDiffEngine.load_manifest(path)
        if not manifest:
            label.configure(text="⚠️ manifest.json bulunamadı")
            return
        info = BackupDiffEngine.get_manifest_info(manifest)
        label.configure(
            text=f"📊 {info['file_count']} dosya | "
                 f"{BackupDiffEngine.format_size(info['total_size'])} | "
                 f"Son: {info['date']}")

    # ── Karşılaştırma ─────────────────────────────────────────────
    def _compare(self):
        path_a = self.path_a_var.get().strip()
        path_b = self.path_b_var.get().strip()

        if not path_a or not path_b:
            messagebox.showwarning("Uyarı", "Her iki yedek klasörünü de seçmelisiniz!")
            return

        from backup_diff import BackupDiffEngine

        manifest_a = BackupDiffEngine.load_manifest(path_a)
        manifest_b = BackupDiffEngine.load_manifest(path_b)

        if manifest_a is None:
            messagebox.showerror("Hata", f"A manifest'i yüklenemedi:\n{path_a}")
            return
        if manifest_b is None:
            messagebox.showerror("Hata", f"B manifest'i yüklenemedi:\n{path_b}")
            return

        result = BackupDiffEngine.compare(manifest_a, manifest_b)
        self.diff_result = result
        self._display_results(result)
        self.btn_export.configure(state="normal")
        self.app.status_bar.set_text(
            f"Karşılaştırma: {result['summary']['new_count']} yeni, "
            f"{result['summary']['removed_count']} silinen, "
            f"{result['summary']['modified_count']} değişen")

    def _display_results(self, result):
        """Karşılaştırma sonuçlarını UI'da göster."""
        summary = result["summary"]
        fmt = BackupDiffEngine.format_size if hasattr(self, '_fmt') else None

        # Lazy import
        from backup_diff import BackupDiffEngine
        fmt = BackupDiffEngine.format_size

        # Özet kutularını güncelle
        self._stat_boxes["new"].configure(text=str(summary["new_count"]))
        self._stat_boxes["removed"].configure(text=str(summary["removed_count"]))
        self._stat_boxes["modified"].configure(text=str(summary["modified_count"]))
        self._stat_boxes["unchanged"].configure(text=str(summary["unchanged_count"]))

        # Sonuç listesini temizle
        for w in self.result_scroll.winfo_children():
            w.destroy()

        total_changes = summary["new_count"] + summary["removed_count"] + summary["modified_count"]

        if total_changes == 0:
            ctk.CTkLabel(self.result_scroll,
                         text="✅ İki yedek tamamen aynı — hiç fark yok!",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color="#3fb950").pack(pady=30)
            self.log.log("✅ Karşılaştırma tamamlandı — fark bulunamadı.")
            return

        # ── Yeni dosyalar ──
        if result["new"]:
            self._add_section_header("🟢 Yeni Dosyalar", "#3fb950",
                                     f"{summary['new_count']} dosya (+{fmt(summary['new_size'])})")
            for item in result["new"][:100]:
                self._add_file_row(item["path"], fmt(item["size"]),
                                   "yeni", item.get("source", ""))

        # ── Silinen dosyalar ──
        if result["removed"]:
            self._add_section_header("🔴 Silinen Dosyalar", "#f85149",
                                     f"{summary['removed_count']} dosya (-{fmt(summary['removed_size'])})")
            for item in result["removed"][:100]:
                self._add_file_row(item["path"], fmt(item["size"]),
                                   "silinen", item.get("source", ""))

        # ── Değişen dosyalar ──
        if result["modified"]:
            self._add_section_header("🟡 Değişen Dosyalar", "#d29922",
                                     f"{summary['modified_count']} dosya")
            for item in result["modified"][:100]:
                diff_text = fmt(item["size_diff"])
                if item["size_diff"] > 0:
                    diff_text = f"+{diff_text}"
                self._add_file_row(item["path"],
                                   f"{fmt(item['size_old'])} → {fmt(item['size_new'])} ({diff_text})",
                                   "değişen", item.get("source", ""))

        self.log.log(
            f"📊 Karşılaştırma: {summary['new_count']} yeni, "
            f"{summary['removed_count']} silinen, "
            f"{summary['modified_count']} değişen, "
            f"{summary['unchanged_count']} aynı")

    def _add_section_header(self, title, color, subtitle):
        """Bölüm başlığı ekle."""
        frame = ctk.CTkFrame(self.result_scroll, fg_color="transparent")
        frame.pack(fill="x", padx=2, pady=(8, 2))
        ctk.CTkLabel(frame, text=title,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=color).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(frame, text=subtitle,
                     font=ctk.CTkFont(size=11),
                     text_color="gray60").pack(side="left")

    def _add_file_row(self, path, size_text, change_type, source=""):
        """Dosya satırı ekle."""
        colors = {"yeni": "#0d3321", "silinen": "#3d1d1d", "değişen": "#3d2e00"}
        bg = colors.get(change_type, "transparent")

        row = ctk.CTkFrame(self.result_scroll, fg_color=bg, corner_radius=4)
        row.pack(fill="x", padx=2, pady=1)

        # Dosya adı (kısa)
        filename = os.path.basename(path)
        parent = os.path.dirname(path)

        ctk.CTkLabel(row, text=filename,
                     font=ctk.CTkFont(family="Consolas", size=11),
                     anchor="w", width=250).pack(side="left", padx=(6, 4))
        ctk.CTkLabel(row, text=parent,
                     font=ctk.CTkFont(size=10), text_color="gray50",
                     anchor="w", width=300).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(row, text=size_text,
                     font=ctk.CTkFont(size=11), text_color="gray60",
                     anchor="e", width=180).pack(side="right", padx=6)

    # ── HTML Dışa Aktarma ──────────────────────────────────────────
    def _export_html(self):
        """Karşılaştırma sonuçlarını HTML olarak dışa aktar."""
        if not self.diff_result:
            return

        from backup_diff import BackupDiffEngine
        fmt = BackupDiffEngine.format_size
        result = self.diff_result
        summary = result["summary"]

        import datetime
        from config_manager import VERSION, APP_NAME

        now = datetime.datetime.now()
        date_text = now.strftime("%d.%m.%Y %H:%M:%S")
        path_a = self.path_a_var.get()
        path_b = self.path_b_var.get()

        # Tablo satırları
        def _rows(items, row_type):
            rows = ""
            for item in items:
                cls = {"yeni": "new", "silinen": "removed", "değişen": "modified"}.get(row_type, "")
                if row_type == "değişen":
                    size_text = (f"{fmt(item['size_old'])} → {fmt(item['size_new'])}"
                                 f" ({'+' if item['size_diff'] > 0 else ''}{fmt(item['size_diff'])})")
                else:
                    size_text = fmt(item.get("size", 0))
                rows += (f'<tr class="{cls}">'
                         f'<td class="mono">{os.path.basename(item["path"])}</td>'
                         f'<td class="mono" style="color:#8b949e">{os.path.dirname(item["path"])}</td>'
                         f'<td class="right">{size_text}</td></tr>\n')
            return rows

        new_rows = _rows(result["new"], "yeni")
        removed_rows = _rows(result["removed"], "silinen")
        modified_rows = _rows(result["modified"], "değişen")

        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yedek Karşılaştırma — {date_text}</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family: 'Segoe UI','Inter',-apple-system,sans-serif;
            background: #0d1117; color: #e6edf3;
            padding: 30px; line-height: 1.6;
        }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        h1 {{
            font-size: 26px; margin-bottom: 4px;
            background: linear-gradient(135deg,#58a6ff,#d29922);
            background-clip: text;
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .subtitle {{ font-size: 14px; color: #8b949e; margin-bottom: 20px; }}
        .card {{
            background: #161b22; border: 1px solid #21262d;
            border-radius: 8px; padding: 20px; margin-bottom: 16px;
        }}
        .card-title {{ font-size: 16px; font-weight: 700; margin-bottom: 12px; }}
        .stats {{
            display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 12px; margin-bottom: 20px;
        }}
        .stat-box {{
            text-align: center; padding: 14px;
            background: #0d1117; border-radius: 8px; border: 1px solid #21262d;
        }}
        .stat-val {{ font-size: 24px; font-weight: 700; }}
        .stat-lbl {{ font-size: 11px; color: #8b949e; }}
        .green {{ color: #3fb950; }}
        .red {{ color: #f85149; }}
        .yellow {{ color: #d29922; }}
        .gray {{ color: #8b949e; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{
            text-align: left; padding: 8px 10px;
            background: #0d1117; color: #8b949e; font-weight: 600;
            border-bottom: 2px solid #21262d;
        }}
        td {{ padding: 5px 10px; border-bottom: 1px solid #21262d; }}
        tr.new {{ background: #0d3321; }}
        tr.removed {{ background: #3d1d1d; }}
        tr.modified {{ background: #3d2e00; }}
        .mono {{ font-family: 'Consolas','Cascadia Code',monospace; font-size: 12px; }}
        .right {{ text-align: right; }}
        .paths {{ font-size: 12px; color: #8b949e; margin-top: 8px; }}
        .footer {{
            margin-top: 30px; padding-top: 16px;
            border-top: 1px solid #21262d;
            text-align: center; font-size: 12px; color: #484f58;
        }}
        .footer a {{ color: #58a6ff; text-decoration: none; }}
    </style>
</head>
<body>
<div class="container">
    <h1>📊 Yedek Karşılaştırma Raporu</h1>
    <p class="subtitle">{APP_NAME} v{VERSION} — {date_text}</p>

    <div class="stats">
        <div class="stat-box">
            <div class="stat-val green">{summary['new_count']}</div>
            <div class="stat-lbl">Yeni Dosya</div>
        </div>
        <div class="stat-box">
            <div class="stat-val red">{summary['removed_count']}</div>
            <div class="stat-lbl">Silinen Dosya</div>
        </div>
        <div class="stat-box">
            <div class="stat-val yellow">{summary['modified_count']}</div>
            <div class="stat-lbl">Değişen Dosya</div>
        </div>
        <div class="stat-box">
            <div class="stat-val gray">{summary['unchanged_count']}</div>
            <div class="stat-lbl">Aynı Dosya</div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">📋 Karşılaştırma Bilgileri</div>
        <div class="paths">
            <strong>A (Eski):</strong> {path_a}<br>
            <strong>B (Yeni):</strong> {path_b}
        </div>
    </div>

    {"" if not new_rows else f'''
    <div class="card">
        <div class="card-title green">🟢 Yeni Dosyalar ({summary['new_count']})</div>
        <table>
            <thead><tr><th>Dosya</th><th>Klasör</th><th style="text-align:right">Boyut</th></tr></thead>
            <tbody>{new_rows}</tbody>
        </table>
    </div>'''}

    {"" if not removed_rows else f'''
    <div class="card">
        <div class="card-title red">🔴 Silinen Dosyalar ({summary['removed_count']})</div>
        <table>
            <thead><tr><th>Dosya</th><th>Klasör</th><th style="text-align:right">Boyut</th></tr></thead>
            <tbody>{removed_rows}</tbody>
        </table>
    </div>'''}

    {"" if not modified_rows else f'''
    <div class="card">
        <div class="card-title yellow">🟡 Değişen Dosyalar ({summary['modified_count']})</div>
        <table>
            <thead><tr><th>Dosya</th><th>Klasör</th><th style="text-align:right">Boyut Farkı</th></tr></thead>
            <tbody>{modified_rows}</tbody>
        </table>
    </div>'''}

    <div class="footer">
        <p>{APP_NAME} v{VERSION} — Hazırlayan: <strong>Kadir Erozan</strong>
        | <a href="mailto:kadir.erozan@gmail.com">kadir.erozan@gmail.com</a></p>
    </div>
</div>
</body>
</html>"""

        # Kaydet
        os.makedirs(self.app.output_dir, exist_ok=True)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.app.output_dir, f"karsilastirma_{timestamp}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        self.log.log(f"📄 HTML rapor kaydedildi: {filepath}")

        try:
            os.startfile(filepath)
        except OSError:
            pass
