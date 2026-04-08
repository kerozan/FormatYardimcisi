# guide_generator.py
# Tarama sonuçlarından otomatik format rehberi (Markdown + HTML) oluşturur.
# İndirme linkleri, lisanslar ve başlangıç programları desteği.

import os
import datetime
from config_manager import VERSION, APP_NAME


# Bilinen programlar için indirme linkleri sözlüğü
DOWNLOAD_LINKS = {
    "google chrome": "https://www.google.com/chrome/",
    "mozilla firefox": "https://www.mozilla.org/firefox/",
    "brave": "https://brave.com/download/",
    "opera": "https://www.opera.com/download",
    "visual studio code": "https://code.visualstudio.com/",
    "microsoft visual studio": "https://visualstudio.microsoft.com/downloads/",
    "git": "https://git-scm.com/download/win",
    "python": "https://www.python.org/downloads/",
    "node.js": "https://nodejs.org/",
    "docker desktop": "https://www.docker.com/products/docker-desktop/",
    "notepad++": "https://notepad-plus-plus.org/downloads/",
    "7-zip": "https://www.7-zip.org/download.html",
    "winrar": "https://www.rarlab.com/download.htm",
    "vlc media player": "https://www.videolan.org/vlc/",
    "obs studio": "https://obsproject.com/download",
    "spotify": "https://www.spotify.com/download/windows/",
    "discord": "https://discord.com/download",
    "telegram desktop": "https://desktop.telegram.org/",
    "steam": "https://store.steampowered.com/about/",
    "epic games launcher": "https://store.epicgames.com/download",
    "adobe creative cloud": "https://creativecloud.adobe.com/apps/download/creative-cloud",
    "nvidia geforce experience": "https://www.nvidia.com/geforce-experience/download/",
    "realtek high definition audio": "https://www.realtek.com/Download/Index",
    "foxit pdf reader": "https://www.foxit.com/pdf-reader/",
    "filezilla client": "https://filezilla-project.org/download.php",
    "calibre": "https://calibre-ebook.com/download_windows",
    "handbrake": "https://handbrake.fr/downloads.php",
    "putty": "https://www.putty.org/",
    "winscp": "https://winscp.net/eng/downloads.php",
    "gimp": "https://www.gimp.org/downloads/",
    "inkscape": "https://inkscape.org/release/",
    "libreoffice": "https://www.libreoffice.org/download/",
    "powertoys": "https://github.com/microsoft/PowerToys/releases",
    "everything": "https://www.voidtools.com/",
    "wireshark": "https://www.wireshark.org/download.html",
    "postman": "https://www.postman.com/downloads/",
    "avg": "https://www.avg.com/tr-tr/free-antivirus-download",
    "malwarebytes": "https://www.malwarebytes.com/mwb-download",
    "ccleaner": "https://www.ccleaner.com/ccleaner/download",
    "cpu-z": "https://www.cpuid.com/softwares/cpu-z.html",
    "hwmonitor": "https://www.cpuid.com/softwares/hwmonitor.html",
    "mp3tag": "https://www.mp3tag.de/en/download.html",
    "irfanview": "https://www.irfanview.com/64bit.htm",
    "qbittorrent": "https://www.qbittorrent.org/download",
    "utorrent": "https://www.utorrent.com/downloads/",
    "blender": "https://www.blender.org/download/",
    "audacity": "https://www.audacityteam.org/download/",
    "zoom": "https://zoom.us/download",
    "teamviewer": "https://www.teamviewer.com/tr/download/",
}


def _md_table(headers, rows):
    """Lint uyumlu markdown tablo oluşturur (pipe etrafında boşluk)."""
    # Başlıklar
    header_line = "| " + " | ".join(headers) + " |"
    # Ayırıcı — boşluklu format
    sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    # Satırlar
    data_lines = []
    for row in rows:
        cells = [str(c).replace("|", "\\|") for c in row]
        data_lines.append("| " + " | ".join(cells) + " |")
    return [header_line, sep_line] + data_lines


class GuideGenerator:
    """Tarama sonuçlarından kategorize edilmiş format rehberi üretir (MD + HTML)."""

    REINSTALL_KEYWORDS = [
        "nvidia", "realtek", "intel", "driver", "sürücü", "codec",
        "avg", "malwarebytes", "chrome", "firefox", "edge",
        "docker", "visual studio", "powershell",
    ]

    BACKUP_APPDATA = [
        "Code", "Adobe", "obs-studio", "FileZilla", "Notepad++",
        "HandBrake", "Mp3tag", "uTorrent", "calibre", "Docker Desktop",
        "Foxit Software", "npm", "Antigravity", "Claude", "gcloud",
        "Telegram Desktop", "Microsoft Flight Simulator",
    ]

    CLEANUP_NAMES = [
        "Temp", "CrashDumps", "npm-cache", "NuGet", "go-build",
        "electron", "ms-playwright", "pnpm-cache", "pip",
    ]

    def __init__(self, output_dir):
        self.output_dir = output_dir

    def _find_download_link(self, program_name):
        """Program adına göre indirme linki bul."""
        name_lower = program_name.lower().strip()
        if name_lower in DOWNLOAD_LINKS:
            return DOWNLOAD_LINKS[name_lower]
        for key, url in DOWNLOAD_LINKS.items():
            if key in name_lower or name_lower in key:
                return url
        return ""

    # ── Veri Toplama ───────────────────────────────────────────────
    def _collect_data(self, scan_results, diff=None, licenses=None, startup_programs=None):
        """Tüm bölümler için veriyi toplar — hem MD hem HTML kullanır."""
        folder_progs = scan_results.get("folder_programs", [])
        reg_progs = scan_results.get("registry_programs", [])
        drivers = scan_results.get("drivers", [])
        scan_date = scan_results.get("scan_date", datetime.datetime.now().isoformat())[:10]

        c_disk = [p for p in reg_progs if self._is_on_c(p)]
        other_disk = [p for p in reg_progs if not self._is_on_c(p) and p["kurulum_yolu"] != "Belirtilmemiş"]
        appdata = [p for p in folder_progs if "AppData" in p.get("kurulum_yolu", "")]
        important = [p for p in appdata if any(k.lower() in p["program_adi"].lower() for k in self.BACKUP_APPDATA)]
        cleanup = [p for p in folder_progs if any(c.lower() in p["program_adi"].lower() for c in self.CLEANUP_NAMES)]
        total_gb = sum(p["boyut_mb"] for p in folder_progs) / 1024

        return {
            "folder_progs": folder_progs, "reg_progs": reg_progs,
            "drivers": drivers,
            "scan_date": scan_date, "c_disk": c_disk, "other_disk": other_disk,
            "important": important, "cleanup": cleanup, "total_gb": total_gb,
            "diff": diff, "licenses": licenses, "startup_programs": startup_programs,
        }

    # ── MARKDOWN ───────────────────────────────────────────────────
    def generate(self, scan_results, diff=None, licenses=None, startup_programs=None):
        """Tam format rehberini markdown olarak oluşturur."""
        d = self._collect_data(scan_results, diff, licenses, startup_programs)
        lines = []

        lines.append("# 🖥️ C Diski Format Öncesi Yedekleme ve Kurulum Rehberi")
        lines.append("")
        lines.append(f"> Tarih: {d['scan_date']} | {len(d['reg_progs'])} registry programı"
                     f" + {len(d['folder_progs'])} klasör öğesi")
        lines.append("")

        # Değişiklik Özeti
        if d["diff"]:
            new_list = d["diff"].get("new", [])
            removed_list = d["diff"].get("removed", [])
            if new_list or removed_list:
                lines.append("---")
                lines.append("")
                lines.append("## 🔄 Son Taramadan Bu Yana Değişiklikler")
                lines.append("")
                if new_list:
                    lines.append(f"### 🟢 Yeni Kurulan ({len(new_list)} program)")
                    lines.append("")
                    rows = [(p["program_adi"], p.get("versiyon", ""), p.get("yayinci", "")) for p in new_list[:30]]
                    lines.extend(_md_table(["Program", "Versiyon", "Yayıncı"], rows))
                    lines.append("")
                if removed_list:
                    lines.append(f"### 🔴 Kaldırılan ({len(removed_list)} program)")
                    lines.append("")
                    rows = [(p["program_adi"], p.get("versiyon", "")) for p in removed_list[:30]]
                    lines.extend(_md_table(["Program", "Versiyon"], rows))
                    lines.append("")

        # Güvende
        lines.append("---")
        lines.append("")
        lines.append("## 🟢 BAŞKA DİSKTE — Güvende")
        lines.append("")
        lines.append("Bu programlar C diskinde değil, format sonrası launcher ile gösterilmesi yeterli:")
        lines.append("")
        if d["other_disk"]:
            rows = []
            for p in sorted(d["other_disk"], key=lambda x: x["boyut_mb"], reverse=True)[:40]:
                disk = p["kurulum_yolu"][0].upper() if p["kurulum_yolu"] else "?"
                rows.append((p["program_adi"], f"{disk}:", str(p["boyut_mb"]), f"`{p['kurulum_yolu'][:60]}`"))
            lines.extend(_md_table(["Program", "Disk", "Boyut (MB)", "Yol"], rows))
            lines.append("")

        # Yeniden kurulacaklar
        lines.append("---")
        lines.append("")
        lines.append("## 🔵 YENİDEN KURULACAKLAR (C Diskinde)")
        lines.append("")
        if d["c_disk"]:
            rows = []
            for p in sorted(d["c_disk"], key=lambda x: x["boyut_mb"], reverse=True)[:50]:
                link = self._find_download_link(p["program_adi"])
                link_text = f"[İndir]({link})" if link else "—"
                rows.append((p["program_adi"], p.get("versiyon", ""), str(p["boyut_mb"]), link_text))
            lines.extend(_md_table(["Program", "Versiyon", "Boyut (MB)", "İndirme Linki"], rows))
            lines.append("")

        # AppData yedekle
        lines.append("---")
        lines.append("")
        lines.append("## 🔴 YEDEKLE — AppData Verileri")
        lines.append("")
        lines.append("Bu klasörler format sonrası kaybolacak, yedeklenmeli:")
        lines.append("")
        if d["important"]:
            rows = []
            for p in sorted(d["important"], key=lambda x: x["boyut_mb"], reverse=True):
                rows.append((f"**{p['program_adi']}**", str(p["boyut_mb"]), f"`{p['kurulum_yolu'][:70]}`"))
            lines.extend(_md_table(["Klasör", "Boyut (MB)", "Konum"], rows))
            lines.append("")

        # Temizlenebilir
        lines.append("---")
        lines.append("")
        lines.append("## 🗑️ TEMİZLENEBİLİR")
        lines.append("")
        if d["cleanup"]:
            total_cleanup = sum(p["boyut_mb"] for p in d["cleanup"])
            lines.append(f"> Toplam temizlenebilir alan: ~{round(total_cleanup / 1024, 1)} GB")
            lines.append("")
            rows = [(p["program_adi"], str(p["boyut_mb"])) for p in sorted(d["cleanup"], key=lambda x: x["boyut_mb"], reverse=True)]
            lines.extend(_md_table(["Öğe", "Boyut (MB)"], rows))
            lines.append("")

        # Başlangıç programları
        if d["startup_programs"]:
            lines.append("---")
            lines.append("")
            lines.append("## 🚀 BAŞLANGIÇ PROGRAMLARI")
            lines.append("")
            lines.append("Windows açılışında otomatik başlayan programlar:")
            lines.append("")
            rows = [(sp["name"], f"`{sp.get('command', '')[:80]}`", sp.get("source", "")) for sp in d["startup_programs"]]
            lines.extend(_md_table(["Program", "Komut", "Kaynak"], rows))
            lines.append("")

        # Lisanslar
        if d["licenses"]:
            lines.append("---")
            lines.append("")
            lines.append("## 🔑 LİSANS ANAHTARLARI")
            lines.append("")
            rows = [(f"**{lic['program']}**", f"`{lic['key']}`", lic.get("notes", "")) for lic in d["licenses"]]
            lines.extend(_md_table(["Program", "Lisans Anahtarı", "Not"], rows))
            lines.append("")

        # Kurulum sırası
        lines.append("---")
        lines.append("")
        lines.append("## 📋 FORMAT SONRASI KURULUM SIRASI")
        lines.append("")
        lines.append("1. **Windows sürücüleri** (NVIDIA, Realtek, Intel, Chipset)")
        lines.append("2. **Güvenlik** — Antivirüs yazılımı")
        lines.append("3. **Tarayıcı** — Chrome/Firefox (sync ile ayarlar geri gelir)")
        lines.append("4. **Geliştirme** — VS Code → Git → Node.js → Python")
        lines.append("5. **Platform launcher'ları** — Steam, Adobe CC, vb.")
        lines.append("6. **Kütüphaneleri göster** — Diğer disklerdeki oyun/program klasörlerini ekle")
        lines.append("7. **Diğer programlar** — İhtiyaç oldukça kur")
        lines.append("")

        # Sürücüler
        if d["drivers"]:
            lines.append("---")
            lines.append("")
            lines.append(f"## 🔧 YÜKLÜ SÜRÜCÜLER (3. Parti)")
            lines.append("")
            lines.append("Format sonrası bu sürücülerin yeniden kurulması gerekebilir:")
            lines.append("")
            rows = [
                (drv["provider"], drv.get("class_name", ""), drv.get("version", ""),
                 drv.get("date", ""), drv.get("inf_name", ""))
                for drv in d["drivers"]
            ]
            lines.extend(_md_table(["Sağlayıcı", "Sınıf", "Versiyon", "Tarih", "INF"], rows))
            lines.append("")

        # Özet
        lines.append("---")
        lines.append("")
        lines.append("## 📊 ÖZET")
        lines.append("")
        lines.append(f"- **Toplam taranan program:** {len(d['reg_progs'])} (registry)"
                     f" + {len(d['folder_progs'])} (klasör)")
        lines.append(f"- **Toplam disk kullanımı:** {d['total_gb']:.1f} GB (klasör taraması)")
        lines.append(f"- **C diskinde:** {len(d['c_disk'])} program")
        lines.append(f"- **Diğer disklerde:** {len(d['other_disk'])} program")
        lines.append("")
        lines.append(f"> Bu rehber {APP_NAME} v{VERSION} tarafından otomatik oluşturulmuştur.")
        lines.append(f"> Hazırlayan: Kadir Erozan | kadir.erozan@gmail.com")
        lines.append("")

        return "\n".join(lines)

        # ── HTML ───────────────────────────────────────────────────────
    def generate_html(self, scan_results, diff=None, licenses=None, startup_programs=None):
        """Rehberin HTML versiyonunu oluşturur."""
        d = self._collect_data(scan_results, diff, licenses, startup_programs)
        sections = []
        nav_links = []

        def _add_section(id_name, nav_text, html_card):
            nav_links.append(f'<a href="#{id_name}">{nav_text}</a>')
            sections.append(f'<div id="{id_name}">{html_card}</div>')

        # Değişiklikler
        if d["diff"]:
            new_list = d["diff"].get("new", [])
            removed_list = d["diff"].get("removed", [])
            if new_list:
                rows = "".join(f"<tr><td>{p['program_adi']}</td><td>{p.get('versiyon','')}</td>"
                               f"<td>{p.get('yayinci','')}</td></tr>" for p in new_list[:30])
                card = self._html_card("🟢 Yeni Kurulan", f"{len(new_list)} program",
                    f"<p style='margin-bottom:10px;color:#8b949e'>Son taramadan bu yana yeni tespit edilen programlar.</p>"
                    f"<table><thead><tr><th>Program</th><th>Versiyon</th><th>Yayıncı</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>")
                _add_section("diff_new", "✨ Yeni Programlar", card)

            if removed_list:
                rows = "".join(f"<tr><td>{p['program_adi']}</td><td>{p.get('versiyon','')}</td></tr>"
                               for p in removed_list[:30])
                card = self._html_card("🔴 Kaldırılan", f"{len(removed_list)} program",
                    f"<p style='margin-bottom:10px;color:#8b949e'>Son taramada olan ancak artık bulunamayan programlar.</p>"
                    f"<table><thead><tr><th>Program</th><th>Versiyon</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>")
                _add_section("diff_removed", "🗑 Şilinen Programlar", card)

        # Güvende
        if d["other_disk"]:
            rows = ""
            for p in sorted(d["other_disk"], key=lambda x: x["boyut_mb"], reverse=True)[:40]:
                disk = p["kurulum_yolu"][0].upper() if p["kurulum_yolu"] else "?"
                rows += (f"<tr><td>{p['program_adi']}</td><td>{disk}:</td>"
                         f"<td class='right'>{p['boyut_mb']}</td>"
                         f"<td class='mono'>{p['kurulum_yolu'][:60]}</td></tr>")
            card = self._html_card("🟢 Başka Diskte — YENİDEN KURMANA GEREK YOK",
                f"{len(d['other_disk'])} program",
                f"<p style='margin-bottom:10px;color:#8b949e'>🎯 <strong>Analiz Önerisi:</strong> Bu programlar/oyunlar (Gigabaytlarca yer tutan Steam kütüphanen dahil) format atacağın C: diskinde değil! Format sonrası bunları silmene veya yeniden indirmene gerek yok; sadece ana uygulamadan kütüphane yolunu göstermen yeterli.</p>"
                f"<table><thead><tr><th>Program</th><th>Disk</th><th>MB</th><th>Yol</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
            _add_section("other_disk", "🟢 Güvendekiler", card)

        # C diskinde (Yeniden Kurulacak)
        if d["c_disk"]:
            rows = ""
            for p in sorted(d["c_disk"], key=lambda x: x["boyut_mb"], reverse=True)[:50]:
                link = self._find_download_link(p["program_adi"])
                link_html = f'<a href="{link}" target="_blank">İndir</a>' if link else "—"
                rows += (f"<tr><td>{p['program_adi']}</td><td>{p.get('versiyon','')}</td>"
                         f"<td class='right'>{p['boyut_mb']}</td><td>{link_html}</td></tr>")
            card = self._html_card("🔵 C Diskinde — YENİDEN KURULACAKLAR",
                f"{len(d['c_disk'])} program",
                f"<p style='margin-bottom:10px;color:#8b949e'>⚠️ <strong>Analiz Önerisi:</strong> Sistem diskinde kurulu olduklarından formattan sonra bu programları tekrar yüklemen (veya Setup edinmen) gerekecek.</p>"
                f"<table><thead><tr><th>Program</th><th>Versiyon</th><th>MB</th><th>İndir</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
            _add_section("c_disk", "🔵 Kurulacaklar", card)

        # AppData
        if d["important"]:
            rows = ""
            for p in sorted(d["important"], key=lambda x: x["boyut_mb"], reverse=True):
                rows += (f"<tr><td><strong>{p['program_adi']}</strong></td>"
                         f"<td class='right'>{p['boyut_mb']}</td>"
                         f"<td class='mono'>{p['kurulum_yolu'][:70]}</td></tr>")
            card = self._html_card("🔴 Yedekle — AppData Özel Verileri", f"{len(d['important'])} klasör",
                f"<p style='margin-bottom:10px;color:#8b949e'>🚨 <strong>Önemli:</strong> Bu klasörler, kurulu programlarının ayarlarını (save'ler, config vs.) tutar. Formattan önce mutlaka yedeğini alıp formattan sonra geri atman önerilir.</p>"
                f"<table><thead><tr><th>Klasör</th><th>MB</th><th>Konum</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
            _add_section("appdata", "🔴 Yedeklenecekler", card)
            
        # Temizlenebilir (Gereksizler)
        if d["cleanup"]:
            total_cleanup = sum(p["boyut_mb"] for p in d["cleanup"])
            rows = "".join(f"<tr><td>{p['program_adi']}</td><td class='right'>{p['boyut_mb']}</td></tr>" for p in sorted(d["cleanup"], key=lambda x: x["boyut_mb"], reverse=True))
            card = self._html_card("🗑️ TEMİZLENEBİLİR (Geçici ve Çöp Dosyalar)", f"~{round(total_cleanup / 1024, 1)} GB tasarruf",
                f"<p style='margin-bottom:10px;color:#8b949e'>🧹 <strong>Analiz Önerisi:</strong> Sistemindeki geçici paketler, önbellekler veya crash raporlarıdır. Yedeklemene veya geri yüklemene gerek yoktur.</p>"
                f"<table><thead><tr><th>Öğe</th><th>Boyut (MB)</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
            _add_section("cleanup", "🗑 Gereksizler", card)

        # Başlangıç
        if d["startup_programs"]:
            rows = ""
            for sp in d["startup_programs"]:
                rows += (f"<tr><td>{sp['name']}</td>"
                         f"<td class='mono'>{sp.get('command','')[:80]}</td>"
                         f"<td>{sp.get('source','')}</td></tr>")
            card = self._html_card("🚀 Başlangıç Programları",
                f"{len(d['startup_programs'])} öğe",
                f"<p style='margin-bottom:10px;color:#8b949e'>Sistem ile otomatik başlayan programlardır.</p>"
                f"<table><thead><tr><th>Program</th><th>Komut</th><th>Kaynak</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
            _add_section("startup", "🚀 Başlangıç", card)

        # Lisanslar
        if d["licenses"]:
            rows = ""
            for lic in d["licenses"]:
                rows += (f"<tr><td><strong>{lic['program']}</strong></td>"
                         f"<td class='mono'>{lic['key']}</td>"
                         f"<td>{lic.get('notes','')}</td></tr>")
            card = self._html_card("🔑 Lisans Anahtarları", f"{len(d['licenses'])} adet",
                f"<p style='margin-bottom:10px;color:#8b949e'>Kaybetmemen gereken aktivasyon anahtarları.</p>"
                f"<table><thead><tr><th>Program</th><th>Anahtar</th><th>Not</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
            _add_section("licenses", "🔑 Lisanslar", card)

        # Kurulum sırası
        card = self._html_card("📋 Format Sonrası Kurulum Sırası", "",
            "<ol>"
            "<li><strong>Windows sürücüleri</strong> — NVIDIA, Realtek, Intel, Chipset</li>"
            "<li><strong>Güvenlik</strong> — Antivirüs yazılımı</li>"
            "<li><strong>Tarayıcı</strong> — Chrome/Firefox (sync ile ayarlar geri gelir)</li>"
            "<li><strong>Geliştirme</strong> — VS Code → Git → Node.js → Python</li>"
            "<li><strong>Platform launcher'ları</strong> — Steam, Adobe CC, vb.</li>"
            "<li><strong>Kütüphaneleri göster</strong> — Diğer disklerdeki oyun/program klasörlerini ekle</li>"
            "<li><strong>Diğer programlar</strong> — İhtiyaç oldukça kur</li>"
            "</ol>")
        _add_section("install_order", "📋 Kurulum Sırası", card)

        # Sürücüler
        if d["drivers"]:
            rows = ""
            for drv in d["drivers"]:
                rows += (f"<tr><td>{drv['provider']}</td>"
                         f"<td>{drv.get('class_name','')}</td>"
                         f"<td>{drv.get('version','')}</td>"
                         f"<td>{drv.get('date','')}</td>"
                         f"<td class='mono'>{drv.get('inf_name','')}</td></tr>")
            card = self._html_card("🔧 Yüklü Sürücüler (3. Parti)",
                f"{len(d['drivers'])} sürücü",
                f"<p style='margin-bottom:10px;color:#8b949e'>Format sonrası eksik olan sürücüler için bu listeye başvurulabilir.</p>"
                f"<table><thead><tr><th>Sağlayıcı</th><th>Sınıf</th><th>Versiyon</th><th>Tarih</th><th>INF</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
            _add_section("drivers", "🔧 Sürücüler", card)

        nav_html = ' | '.join(nav_links)
        content = "\n".join(sections)

        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yedekleme ve Kurulum Rehberi — {d['scan_date']}</title>
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
            background: linear-gradient(135deg,#58a6ff,#3fb950);
            background-clip: text;
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .subtitle {{ font-size: 14px; color: #8b949e; margin-bottom: 20px; }}
        .card {{
            background: #161b22; border: 1px solid #21262d;
            border-radius: 8px; padding: 20px; margin-bottom: 16px;
        }}
        .card-title {{
            font-size: 16px; font-weight: 700; color: #58a6ff;
            margin-bottom: 4px;
        }}
        .card-sub {{ font-size: 12px; color: #8b949e; margin-bottom: 12px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{
            text-align: left; padding: 8px 10px;
            background: #0d1117; color: #8b949e; font-weight: 600;
            border-bottom: 2px solid #21262d;
        }}
        td {{ padding: 5px 10px; border-bottom: 1px solid #21262d; }}
        tr:hover {{ background: #1c2128; }}
        .mono {{ font-family: 'Consolas','Cascadia Code',monospace; font-size: 12px; }}
        .right {{ text-align: right; }}
        a {{ color: #58a6ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        ol {{ padding-left: 24px; }}
        ol li {{ margin-bottom: 6px; }}
        .footer {{
            margin-top: 30px; padding-top: 16px;
            border-top: 1px solid #21262d;
            text-align: center; font-size: 12px; color: #484f58;
        }}
        .stats {{
            display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 12px; margin-bottom: 20px;
        }}
        .stat-box {{
            text-align: center; padding: 14px;
            background: #0d1117; border-radius: 8px; border: 1px solid #21262d;
        }}
        .stat-val {{ font-size: 24px; font-weight: 700; color: #58a6ff; }}
        .stat-lbl {{ font-size: 11px; color: #8b949e; }}
        @media print {{
            body {{ background: #fff; color: #000; padding: 10px; }}
            .card {{ border: 1px solid #ccc; background: #f9f9f9; }}
            th {{ background: #eee; color: #333; }}
            a {{ color: #0366d6; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>🖥️ Yedekleme ve Kurulum Rehberi</h1>
    <p class="subtitle">{APP_NAME} v{VERSION} — {d['scan_date']}</p>

    <div class="stats">
        <div class="stat-box">
            <div class="stat-val">{len(d['reg_progs'])}</div>
            <div class="stat-lbl">Registry Programı</div>
        </div>
        <div class="stat-box">
            <div class="stat-val">{len(d['c_disk'])}</div>
            <div class="stat-lbl">C Diskinde</div>
        </div>
        <div class="stat-box">
            <div class="stat-val">{len(d['other_disk'])}</div>
            <div class="stat-lbl">Diğer Disklerde</div>
        </div>
        <div class="stat-box">
            <div class="stat-val">{d['total_gb']:.1f} GB</div>
            <div class="stat-lbl">Toplam Boyut</div>
        </div>
    </div>
    
    <div style="background:#1c2128; padding:15px; border-radius:8px; margin-bottom:20px; text-align:center; font-weight:600;">
        {nav_html}
    </div>

    {content}

    <div class="footer">
        <p>{APP_NAME} v{VERSION} — Hazırlayan: <strong>Kadir Erozan</strong>
        | <a href="mailto:kadir.erozan@gmail.com">kadir.erozan@gmail.com</a></p>
        <p>© 2026 Kadir Erozan — Tüm hakları saklıdır.</p>
    </div>
</div>
</body>
</html>"""

    def _html_card(self, title, subtitle, body):
        """Tek bir HTML kart bölümü."""
        sub_html = f'<div class="card-sub">{subtitle}</div>' if subtitle else ""
        return f'<div class="card"><div class="card-title">{title}</div>{sub_html}{body}</div>'

    # ── KAYDETME ───────────────────────────────────────────────────
    def save(self, content, filename="yedekleme_rehberi.md"):
        """Rehberi dosyaya kaydeder."""
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def save_html(self, html_content, filename="yedekleme_rehberi.html"):
        """HTML rehberi dosyaya kaydeder."""
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return path

    def _is_on_c(self, program):
        yol = program.get("kurulum_yolu", "")
        if yol == "Belirtilmemiş" or not yol:
            return False
        return yol.upper().startswith("C:")
