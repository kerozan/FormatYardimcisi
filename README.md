# Format Yardımcısı v2.1.0

Windows 10 format öncesi/sonrası süreçleri yöneten, şık arayüzlü Python masaüstü uygulaması.

**Hazırlayan:** Kadir Erozan  
**İletişim:** <kadir.erozan@gmail.com>  
**Lisans:** © 2026 Kadir Erozan — Tüm hakları saklıdır.

## Özellikler

### 📋 Program Tarama

- Tüm disklerdeki `Program Files`, `ProgramData`, `AppData` klasörlerini tarar
- Windows Registry'den kurulu program bilgilerini toplar
- Windows başlangıç programlarını ve 3. parti hizmetleri tarar
- Her çalıştırmada önceki tarama ile karşılaştırır → yeni/kaldırılan programları gösterir
- CSV, Markdown ve şık HTML rapor çıktılarını otomatik üretir

### 🔧 Sürücü Yedekleme

- `pnputil` ile 3. parti (Microsoft dışı) sürücüleri tarar
- Sürücüleri tek tıkla hedef klasöre dışa aktarır (`_drivers/` alt klasörü)
- Format sonrası hangi sürücülerin yeniden kurulacağını rehberde listeler

### 💾 Data Yedekleme

- **Incremental:** Sadece yeni/değişen dosyaları kopyalar
- **İncele:** Boyutları arka planda hesaplar, sonuçları cache'ler
- **ZIP desteği:** Sıkıştırılmış veya normal yedekleme seçeneği
- **Kilitli Dosya Koruması:** Tarayıcı açıksa yedekleme kalitesini artırmak için kapatma uyarısı verir
- Önerilen klasörler + AI yapılandırma klasörleri (Gemini, Claude, ChatGPT)
- Disk alanı kontrolü ve yetersizlik uyarısı
- Güvenli durdurma (atomik kopyalama, dosya yarım kalmaz)

### 📊 Yedek Karşılaştırma

- İki yedek manifest'i arasındaki farkları renk kodlu gösterir
- 🟢 Yeni / 🔴 Silinen / 🟡 Değişen dosyalar ayrı ayrı listelenir
- Karşılaştırma sonuçlarını HTML rapor olarak dışa aktarır

### 🔄 Geri Yükleme

- Yedeklenen dosyaları orijinal konumlarına geri yükler
- Manifest tabanlı, seçerek geri yükleme

### ⚙️ Ayarlar

- Taranacak disk ve AppData seçimi
- Yedekleme hedef klasörü
- **Lisans anahtarı not defteri** (ekleme/silme/saklama)
- Önceki ayarları otomatik hatırlar

### 📄 Akıllı Rehber

- 50+ program için otomatik indirme linkleri
- Lisans anahtarları rehbere dahil
- Başlangıç programları listesi
- 3. parti sürücü tablosu
- Kategorize: Güvende / Yeniden Kurulacak / Yedekle / Temizlenebilir

## Kurulum

```bash
pip install customtkinter
```

## Kullanım

### Çift Tıkla

`run.bat` dosyasına çift tıklayın.

### Komut Satırı

```bash
cd kurulu_programlar_listele
python src/main.py
```

> **Not:** Yönetici (Admin) olarak çalıştırmak daha kapsamlı sonuç verir.

## Dosya Yapısı

```text
kurulu_programlar_listele/
├── run.bat               → Çift tıkla çalıştır
├── requirements.txt      → Bağımlılıklar
├── README.md             → Bu dosya
├── TODO.md               → Geliştirme yol haritası
├── CHANGELOG.md          → Değişiklik günlüğü
├── .gitignore            → Git hariç tutma
├── src/
│   ├── main.py           → Giriş noktası
│   ├── app.py            → Ana GUI penceresi
│   ├── scanner.py        → Program + başlangıç + sürücü tarama
│   ├── driver_scanner.py → Sürücü tarama ve dışa aktarma
│   ├── backup_engine.py  → Yedekleme motoru (normal + ZIP)
│   ├── backup_diff.py    → Yedek karşılaştırma motoru
│   ├── restore_engine.py → Geri yükleme motoru
│   ├── guide_generator.py→ Rehber (MD + HTML)
│   ├── html_reporter.py  → Şık HTML Yedekleme raporları
│   ├── config_manager.py → Ayar yönetimi
│   ├── license_manager.py→ Lisans defteri
│   ├── program_listele.py→ Eski konsol scripti (referans)
│   └── ui/
│       ├── widgets.py    → Ortak bileşenler
│       ├── scan_tab.py   → Tarama sekmesi
│       ├── backup_tab.py → Yedekleme sekmesi
│       ├── restore_tab.py→ Geri yükleme sekmesi
│       ├── diff_tab.py   → Karşılaştırma sekmesi
│       └── settings_tab.py→ Ayarlar + Lisans
├── cikti/                → HTML raporlar, CSV + MD rehberi
└── data/                 → Ayarlar + tarama + lisans + boyut cache
```

## Gereksinimler

- Python 3.10+
- Windows 10/11
- customtkinter >= 5.2.0

## Sürüm Geçmişi

Detaylı değişiklikler için [CHANGELOG.md](CHANGELOG.md) dosyasına bakın.
