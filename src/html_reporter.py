# html_reporter.py
# Yedekleme sonrası HTML rapor oluşturur — modern koyu tema, detaylı bilgi.

import os
import datetime
from config_manager import VERSION, APP_NAME


class HtmlReporter:
    """Yedekleme sonuçlarından şık HTML rapor üretir."""

    def __init__(self, output_dir):
        self.output_dir = output_dir

    def generate(self, report_data):
        """
        report_data dict:
            mode: "normal" | "zip"
            date: ISO string
            copied / added: int
            skipped: int
            errors: int
            total_size_mb: float
            zip_size_mb: float (ZIP modunda)
            zip_file: str (ZIP modunda)
            stopped: bool
            folders: [(name, path, file_count, size_bytes), ...]
            error_list: [(filename, error_msg), ...]
            duration_sec: float
        """
        mode = report_data.get("mode", "normal")
        date = report_data.get("date", datetime.datetime.now().isoformat())
        copied = report_data.get("copied", 0) or report_data.get("added", 0)
        skipped = report_data.get("skipped", 0)
        errors = report_data.get("errors", 0)
        total_mb = report_data.get("total_size_mb", 0)
        zip_mb = report_data.get("zip_size_mb", 0)
        zip_file = report_data.get("zip_file", "")
        stopped = report_data.get("stopped", False)
        folders = report_data.get("folders", [])
        error_list = report_data.get("error_list", [])
        duration = report_data.get("duration_sec", 0)
        target_dir = report_data.get("target_dir", "")

        status_text = "⏹ Durduruldu" if stopped else "✅ Tamamlandı"
        status_class = "stopped" if stopped else "success"
        mode_text = "📦 ZIP Arşiv" if mode == "zip" else "📁 Normal (Incremental)"

        # Süre formatla
        if duration >= 60:
            dur_text = f"{int(duration // 60)} dk {int(duration % 60)} sn"
        else:
            dur_text = f"{duration:.1f} sn"

        # Tarih formatla
        try:
            dt = datetime.datetime.fromisoformat(date)
            date_text = dt.strftime("%d.%m.%Y %H:%M:%S")
        except (ValueError, TypeError):
            date_text = date[:19] if date else "Bilinmiyor"

        # Klasör tablo satırları
        folder_rows = ""
        if folders:
            for name, path, fcount, size_b in folders:
                size_text = f"{size_b / (1024*1024):.1f} MB" if size_b >= 1024*1024 else f"{size_b / 1024:.0f} KB"
                folder_rows += f"""
                <tr>
                    <td>{name}</td>
                    <td class="mono">{path}</td>
                    <td class="center">{fcount}</td>
                    <td class="right">{size_text}</td>
                </tr>"""

        # Hata tablo satırları
        error_rows = ""
        if error_list:
            for fname, emsg in error_list[:50]:
                error_rows += f"""
                <tr>
                    <td class="mono">{fname}</td>
                    <td class="error-text">{emsg}</td>
                </tr>"""

        # ZIP bilgisi
        zip_section = ""
        if mode == "zip":
            ratio = round((1 - zip_mb / max(total_mb, 0.1)) * 100, 1) if total_mb > 0 else 0
            zip_section = f"""
            <div class="card">
                <h3>📦 ZIP Bilgisi</h3>
                <div class="stats-grid">
                    <div class="stat">
                        <span class="stat-value">{total_mb:.1f} MB</span>
                        <span class="stat-label">Orijinal</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">{zip_mb:.1f} MB</span>
                        <span class="stat-label">Sıkıştırılmış</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">%{ratio}</span>
                        <span class="stat-label">Tasarruf</span>
                    </div>
                </div>
                <p class="mono" style="margin-top:10px;font-size:12px;color:#aaa;">📄 {zip_file}</p>
            </div>"""

        # Donut chart SVG — başarı/hata oranı
        total_files = copied + skipped + errors
        if total_files > 0:
            pct_copied = copied / total_files * 100
            pct_skipped = skipped / total_files * 100
            pct_errors = errors / total_files * 100
        else:
            pct_copied = pct_skipped = pct_errors = 0

        # SVG donut
        chart_svg = self._donut_chart(pct_copied, pct_skipped, pct_errors)

        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yedekleme Raporu — {date_text}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
            background: #0d1117;
            color: #e6edf3;
            padding: 30px;
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{
            font-size: 28px;
            margin-bottom: 4px;
            background: linear-gradient(135deg, #58a6ff, #3fb950);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        h2 {{
            font-size: 18px;
            color: #8b949e;
            margin-bottom: 20px;
            font-weight: 400;
        }}
        h3 {{
            font-size: 16px;
            margin-bottom: 12px;
            color: #58a6ff;
        }}
        .header {{
            border-bottom: 1px solid #21262d;
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .status {{
            display: inline-block;
            padding: 4px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-top: 8px;
        }}
        .status.success {{ background: #0d3321; color: #3fb950; border: 1px solid #238636; }}
        .status.stopped {{ background: #3d1d00; color: #d29922; border: 1px solid #9e6a03; }}
        .card {{
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 16px;
        }}
        .stat {{
            text-align: center;
            padding: 12px;
            background: #0d1117;
            border-radius: 8px;
            border: 1px solid #21262d;
        }}
        .stat-value {{
            display: block;
            font-size: 28px;
            font-weight: 700;
            color: #58a6ff;
        }}
        .stat-value.green {{ color: #3fb950; }}
        .stat-value.yellow {{ color: #d29922; }}
        .stat-value.red {{ color: #f85149; }}
        .stat-label {{
            display: block;
            font-size: 12px;
            color: #8b949e;
            margin-top: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            text-align: left;
            padding: 8px 12px;
            background: #0d1117;
            color: #8b949e;
            font-weight: 600;
            border-bottom: 2px solid #21262d;
        }}
        td {{
            padding: 6px 12px;
            border-bottom: 1px solid #21262d;
        }}
        tr:hover {{ background: #1c2128; }}
        .mono {{ font-family: 'Consolas', 'Cascadia Code', monospace; font-size: 12px; }}
        .center {{ text-align: center; }}
        .right {{ text-align: right; }}
        .error-text {{ color: #f85149; font-size: 12px; }}
        .chart-container {{
            display: flex;
            align-items: center;
            gap: 24px;
            margin-top: 12px;
        }}
        .legend {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }}
        .legend-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 16px;
            border-top: 1px solid #21262d;
            text-align: center;
            font-size: 12px;
            color: #484f58;
        }}
        .footer a {{ color: #58a6ff; text-decoration: none; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🖥️ Yedekleme Raporu</h1>
        <h2>{APP_NAME} v{VERSION}</h2>
        <span class="status {status_class}">{status_text}</span>
    </div>

    <!-- Genel Bilgiler -->
    <div class="card">
        <h3>📊 Genel Bilgiler</h3>
        <div class="stats-grid">
            <div class="stat">
                <span class="stat-value green">{copied}</span>
                <span class="stat-label">Kopyalanan</span>
            </div>
            <div class="stat">
                <span class="stat-value yellow">{skipped}</span>
                <span class="stat-label">Atlanan</span>
            </div>
            <div class="stat">
                <span class="stat-value red">{errors}</span>
                <span class="stat-label">Hata</span>
            </div>
            <div class="stat">
                <span class="stat-value">{total_mb:.1f}</span>
                <span class="stat-label">MB Toplam</span>
            </div>
            <div class="stat">
                <span class="stat-value">{dur_text}</span>
                <span class="stat-label">Süre</span>
            </div>
        </div>
        <div class="chart-container">
            {chart_svg}
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-dot" style="background:#3fb950;"></div>
                    Kopyalanan: {copied} (%{pct_copied:.0f})
                </div>
                <div class="legend-item">
                    <div class="legend-dot" style="background:#d29922;"></div>
                    Atlanan: {skipped} (%{pct_skipped:.0f})
                </div>
                <div class="legend-item">
                    <div class="legend-dot" style="background:#f85149;"></div>
                    Hata: {errors} (%{pct_errors:.0f})
                </div>
            </div>
        </div>
    </div>

    <!-- Detaylar -->
    <div class="card">
        <h3>📋 Detaylar</h3>
        <table>
            <tr><td style="width:150px;color:#8b949e;">Tarih</td><td>{date_text}</td></tr>
            <tr><td style="color:#8b949e;">Mod</td><td>{mode_text}</td></tr>
            <tr><td style="color:#8b949e;">Hedef</td><td class="mono">{target_dir}</td></tr>
            <tr><td style="color:#8b949e;">Toplam dosya</td><td>{total_files}</td></tr>
        </table>
    </div>

    {zip_section}

    {"" if not folder_rows else f'''
    <div class="card">
        <h3>📂 Klasör Dağılımı</h3>
        <table>
            <thead>
                <tr>
                    <th>Klasör</th>
                    <th>Yol</th>
                    <th style="text-align:center;">Dosya</th>
                    <th style="text-align:right;">Boyut</th>
                </tr>
            </thead>
            <tbody>{folder_rows}</tbody>
        </table>
    </div>'''}

    {"" if not error_rows else f'''
    <div class="card">
        <h3>❌ Hatalar ({len(error_list)})</h3>
        <table>
            <thead>
                <tr><th>Dosya</th><th>Hata</th></tr>
            </thead>
            <tbody>{error_rows}</tbody>
        </table>
    </div>'''}

    <div class="footer">
        <p>{APP_NAME} v{VERSION} — Hazırlayan: <strong>Kadir Erozan</strong>
        | <a href="mailto:kadir.erozan@gmail.com">kadir.erozan@gmail.com</a></p>
        <p>© 2026 Kadir Erozan — Tüm hakları saklıdır.</p>
    </div>
</div>
</body>
</html>"""
        return html

    def save(self, html_content, timestamp=None):
        """HTML raporu dosyaya kaydeder, yolunu döndürür."""
        os.makedirs(self.output_dir, exist_ok=True)
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rapor_{timestamp}.html"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return path

    def _donut_chart(self, pct_green, pct_yellow, pct_red):
        """Basit SVG donut chart üretir."""
        r = 60
        cx, cy = 70, 70
        stroke = 14
        circumference = 2 * 3.14159 * r

        # Yüzdeler → dash offset
        g_len = circumference * pct_green / 100
        y_len = circumference * pct_yellow / 100
        r_len = circumference * pct_red / 100

        g_off = 0
        y_off = g_len
        r_off = g_len + y_len

        return f"""
        <svg width="140" height="140" viewBox="0 0 140 140">
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#21262d" stroke-width="{stroke}" />
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#3fb950" stroke-width="{stroke}"
                stroke-dasharray="{g_len} {circumference - g_len}"
                stroke-dashoffset="0" transform="rotate(-90 {cx} {cy})" />
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#d29922" stroke-width="{stroke}"
                stroke-dasharray="{y_len} {circumference - y_len}"
                stroke-dashoffset="-{g_len}" transform="rotate(-90 {cx} {cy})" />
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#f85149" stroke-width="{stroke}"
                stroke-dasharray="{r_len} {circumference - r_len}"
                stroke-dashoffset="-{g_len + y_len}" transform="rotate(-90 {cx} {cy})" />
        </svg>"""
