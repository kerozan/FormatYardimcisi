import json
import re

class AIAnalyzer:
    """Google Gemini AI kullanarak format öncesi program analizi yapar."""

    def __init__(self, api_key):
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self._is_ready = True
        except ImportError:
            self.client = None
            self._is_ready = False
            print("google-genai kütüphanesi bulunamadı.")

    @property
    def is_ready(self):
        return self._is_ready and self.client is not None

    def analyze(self, scan_results):
        """Tarama sonuçlarını AI'a gönderir ve JSON rapor döndürür."""
        if not self.is_ready:
            raise RuntimeError("Gemini API hazır değil. Lütfen geçerli bir API Anahtarı girin.")

        # Sadece analiz için gerekenleri sıkıştır (Token tasarrufu)
        compact_data = {
            "registry": [p["program_adi"] for p in scan_results.get("registry_programs", [])],
            "folders": [
                {"n": p["program_adi"], "path": p.get("kurulum_yolu", ""), "mb": p.get("boyut_mb", 0)} 
                for p in scan_results.get("folder_programs", [])
                # Sadece büyük / önemli klasörleri gönderelim
                if p["boyut_mb"] > 10 or "AppData" in p.get("kurulum_yolu", "")
            ]
        }

        # Dinamik System Prompt Oluştur
        disks = scan_results.get("scanned_disks", ["C"])
        other_disks = [d for d in disks if d != "C"]
        other_disk_str = ", ".join(f"{d}:" for d in other_disks) if other_disks else "YOK (Sadece C diski taranmış, hepsi gidecek)"

        system_prompt = f"""Sen uzman bir Windows Sistem Mühendisi ve Format Öncesi Analistisin. 
Sana JSON formatında kullanıcının bilgisayarına ait kurulu programlar verilecek.
Kullanıcı C diskini formatlayıp Windows'u baştan kuracak. C diski SİLİNECEK. Kullanıcının koruduğu ve formattan sonra YERİNDE KALACAK diğer diskler şunlardır: {other_disk_str}

Gelen bu program listesini incele ve aşağıdaki JSON formatında bir format rehberi/raporu oluştur:

{{
  "reinstall_c": [
    {{"name": "Program Adı", "reason": "Neden yeniden kurulması şart? (örn: Registry, Driver bağımlı)"}}
  ],
  "safe_other_disks": [
    {{"name": "Program/Oyun Adı", "disk": "Bulunduğu Disk Harfi", "reason": "Bunu silmene gerek yok, sadece kütüphane yolunu göster."}}
  ],
  "backup_appdata": [
    {{"name": "Klasör Adı", "reason": "Verileri format öncesi yedeklemelisin, çünkü save/config dosyaları burada."}}
  ],
  "cleanup_junk": [
    {{"name": "Klasör Adı", "reason": "Gereksiz çöp dosyalar, yedeklenmesine gerek yok."}}
  ]
}}

Sistemdeki gereksiz Microsoft/Windows paketlerini (örn. çoklu Visual C++ kurulumları), küçük donanım alt-sürücülerini ve önemsiz ufak yazılımları YAZMA. 
SADECE KULLANICI İÇİN GERÇEK BİR DEĞER VEYA RİSK TAŞIYAN BÜYÜK VE KRİTİK UYGULAMALARI (Oyunlar, Geliştirici Araçları, Medya Editörleri vb.) LİSTELE. 
Miktar limitin yoktur; gerçekten önemliyse 100 tane bile yazabilirsin. Cevabın YALNIZCA geçerli bir JSON objesi olmalıdır. Ekstra metin ekleme.
"""

        user_content = json.dumps(compact_data, ensure_ascii=False)

        prompt = f"{system_prompt}\n\nKULLANICI VERİSİ:\n{user_content}"
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            # Markdown veya json codeblock'ları temizle
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
                
            if text.endswith("```"):
                text = text[:-3]
                
            json_data = json.loads(text.strip())
            
            # Token istatistikleri
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                json_data["_token_stats"] = {
                    "prompt": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "candidates": getattr(response.usage_metadata, "candidates_token_count", 0),
                    "total": getattr(response.usage_metadata, "total_token_count", 0)
                }
                
            return json_data

        except Exception as e:
            raise Exception(f"AI Analiz Hatası: {str(e)}")
