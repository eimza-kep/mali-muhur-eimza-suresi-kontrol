# Mali Mühür ve E-İmza Süre Kontrol Aracı ⏱️🔏

[![Python CI](https://github.com/eimza-kep/mali-muhur-eimza-suresi-kontrol/actions/workflows/ci.yml/badge.svg)](https://github.com/eimza-kep/mali-muhur-eimza-suresi-kontrol/actions)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Windows | Linux | Mac](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](https://github.com)
[![Blog](https://img.shields.io/badge/Rehber-Mali%20M%C3%BCh%C3%BCr%20Merkezi-purple.svg)](https://mali-muhur-merkezi.pages.dev/)

Türkiye'deki Mali Mühür (Kamu SM) ve E-İmza (TÜRKTRUST, E-Tuğra, E-Güven vb.) USB token cihazlarının sertifika geçerlilik sürelerini, son kullanma tarihlerini ve kalan gün sayılarını denetleyen; e-Defter ve e-Fatura krizlerini önceden haber veren açık kaynaklı denetim aracı.

---

## ✨ Öne Çıkan Özellikler

* 🔍 **Windows Sertifika Deposu Taraması:** `--scan-store` parametresi ile bilgisayara takılı tüm akıllı kart ve token sertifikalarını otomatik tespit eder.
* 📁 **Dosya Tabanlı İnceleme:** `.cer`, `.crt`, `.pem` ve `.pfx` dosyalarını doğrudan analiz eder.
* 🚨 **Özelleştirilebilir Uyarı Eşiği:** `--alert-days` ile kritik gün eşiklerini (örneğin 45 gün, 60 gün) tanımlayabilme.
* 🇹🇷 **Milli ESHS Tanıma:** Kamu SM, TÜRKTRUST, E-Tuğra, E-Güven ve EDM Bilişim sertifikalarını otomatik ayırt eder.
* 📊 **Çoklu Çıktı:** Terminal renkli çıktı, JSON ve Markdown rapor desteği.

---

## 🚀 Hızlı Başlangıç

### 1. Takılı Akıllı Kartı / Tokenı Otomatik Tarama
```bash
python check_expiry.py --scan-store
```

### 2. Sertifika Dosyasını İnceleme
```bash
python check_expiry.py mali_muhur.cer --alert-days 45
```

### 3. JSON ve Markdown Raporu Alma
```bash
# Markdown formatında rapor oluşturma
python check_expiry.py mali_muhur.cer --markdown

# Otomasyon sistemleri için JSON çıktısı
python check_expiry.py --scan-store --json
```

### 4. Windows PowerShell İle Doğrudan Çalıştırma
```powershell
powershell -ExecutionPolicy Bypass -File .\Check-CertificateExpiry.ps1
```

---

## 🔗 E-Dönüşüm Açık Kaynak Ekosistemi

Bu araç [eimza-kep](https://github.com/eimza-kep) organizasyonunun açık kaynak e-dönüşüm araçları ekosisteminin bir parçasıdır:

* 🇹🇷 **[awesome-turkiye-e-donusum](https://github.com/eimza-kep/awesome-turkiye-e-donusum):** Türkiye E-Dönüşüm kütüphane, mevzuat ve araçlar listesi.
* 📊 **[gib-edefter-berat-xml-dogrulayici](https://github.com/eimza-kep/gib-edefter-berat-xml-dogrulayici):** GİB e-Defter ve berat doğrulama aracı.
* 🩺 **[akilli-kart-surucu-teshis](https://github.com/eimza-kep/akilli-kart-surucu-teshis):** Akıllı kart okuyucu ve sürücü teşhis aracı.
* 🔓 **[eimza-pin-bloke-asistani](https://github.com/eimza-kep/eimza-pin-bloke-asistani):** USB token PIN kilitlendiğinde PUK kodu ile sıfırlama terminali.

---

## 📚 İlgili Teknik Rehberler
* 📄 [Mali Mühür Sertifika Süresi Dolduğunda Cezalı Duruma Düşmemek İçin Ne Yapılmalı?](https://mali-muhur-merkezi.pages.dev/yazilar/mali-muhur-suresi-doldu-ne-yapilmali.html)
* 📄 [e-Defter Berat Yükleme Günü Mali Mühür Çalışmazsa Acil Eylem Planı](https://mali-muhur-merkezi.pages.dev/yazilar/e-defter-berat-gunu-mali-muhur-calismazsa-cozum.html)
* 📄 [Mali Mühür Başvurusu Nasıl Yapılır ve Kaç Günde Gelir?](https://mali-muhur-merkezi.pages.dev/yazilar/mali-muhur-basvuru-sureci-ve-teslimat-suresi.html)

---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.