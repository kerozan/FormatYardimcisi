<!-- markdownlint-disable MD024 -->

# Değişiklik Günlüğü (Changelog)

## v2.1.0 (2026-04-09)

### Yeni Özellikler

- 🔧 Sürücü yedekleme: pnputil ile 3. parti sürücüleri tarama ve dışa aktarma
- 📊 Yedek karşılaştırma (diff viewer): iki yedek arasındaki farkları renk kodlu gösterme
- 📄 Karşılaştırma sonuçlarını HTML olarak dışa aktarma
- 🔧 Rehbere "Yüklü Sürücüler" bölümü eklendi
- 💾 Yedekleme sekmesine "Sürücüleri Dışa Aktar" butonu eklendi
- 📊 Yeni "Karşılaştırma" sekmesi eklendi

### İyileştirmeler

- Tarama artık sürücüleri de tarıyor ve özet bilgiye dahil ediyor
- Rehber (MD + HTML) sürücü tablosu içeriyor

## v2.0.0 (2026-04-08)

### Yeni Özellikler

- 📂 CSV butonu → "Çıktı Klasörünü Aç" olarak değişti
- 🔎 Yedekleme sekmesine "İncele" butonu eklendi (boyutları arka planda hesaplar, JSON'a kaydeder)
- 🔗 Rehbere program indirme linkleri eklendi
- 🔑 Lisans anahtarı not defteri (Ayarlar sekmesinde)
- 🖥️ Windows başlangıç programları taraması eklendi
- 📋 Başlangıç programları rehbere dahil ediliyor
- 🌐 Yedekleme raporları HTML formatında eklendi ve yedekleme sonrası otomatik açılır

### İyileştirmeler

- Boyut hesaplama artık arka planda çalışıyor, sonuçlar `backup_sizes.json`'a kaydediliyor
- Uygulama açıldığında önceki boyutlar anında görüntüleniyor
- Rehberde indirme linkleri ile hızlı kurulum desteği
- Tarayıcı açıkken yapılan kilitli dosya bildirimleri ve uygulamayı nazikçe kapatma seçeneği eklendi

## v1.1.0 (2026-04-08)

### Yeni Özellikler

- ⏹ Tarama ve yedekleme durdurma butonu
- 📄 Tarama sonrası otomatik rehber + CSV oluşturma
- 📦 ZIP sıkıştırma desteği
- 🤖 AI yapılandırma klasörleri (Gemini, Claude, ChatGPT)
- 💿 Disk alanı kontrolü
- Recursive klasör boyutu hesaplama

### Düzeltmeler

- Tab çubuğu stili iyileştirildi
- İlerleme çubuğu indeterminate mod eklendi
- Klasör boyutları doğru hesaplanıyor

## v1.0.0 (2026-04-08)

### İlk Sürüm

- Program tarama (klasör + registry)
- Incremental data yedekleme
- Geri yükleme
- Format rehberi oluşturma
- CustomTkinter koyu tema GUI
- Güvenli durdurma (atomik kopyalama)
- Ayar hatırlama (settings.json)
