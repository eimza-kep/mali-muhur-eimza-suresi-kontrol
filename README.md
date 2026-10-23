# Mali Mühür ve E-İmza Süre Kontrol Aracı ⏱️🔏

[![Python CI](https://github.com/eimza-kep/mali-muhur-eimza-suresi-kontrol/actions/workflows/ci.yml/badge.svg)](https://github.com/eimza-kep/mali-muhur-eimza-suresi-kontrol/actions)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Platform: Windows | Linux | macOS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue.svg)](https://github.com)
[![Blog](https://img.shields.io/badge/Rehber-Mali%20M%C3%BCh%C3%BCr%20Merkezi-purple.svg)](https://malimuhur.site/)

Türkiye'deki Mali Mühür (TÜBİTAK Kamu SM) ve Nitelikli Elektronik Sertifika / E-İmza (TÜRKTRUST, E-Tuğra, E-Güven, EDM Bilişim vb.) USB token cihazlarının sertifika geçerlilik sürelerini, son kullanma tarihlerini ve kalan gün sayılarını denetleyen; **otomatik Webhook (Slack/Teams/Discord) ve SMTP e-posta uyarıları** üreterek e-Defter ve e-Fatura krizlerini önceden engelleyen açık kaynaklı denetim aracı.

---

## ✨ Öne Çıkan Özellikler (v1.3)

* 🔍 **Windows Sertifika Deposu (MY Store) Taraması:** `--scan-store` parametresi ile bilgisayara takılı tüm akıllı kart ve token sertifikalarını otomatik tespit eder.
* 📁 **Toplu Klasör Taraması:** `--dir` parametresi ile muhasebe veya arşiv klasörlerindeki tüm `.cer`, `.crt`, `.pem`, `.pfx` sertifikalarını tek seferde tarar.
* 🚨 **Otomatik Webhook Bildirimi:** Süresi yaklaşan (30, 15 ve 3 gün kala) veya süresi dolan sertifikalar için Slack, Microsoft Teams ve Discord uyumlu webhook mesajları gönderir (`--webhook`).
* 📧 **Otomatik SMTP E-Posta Bildirimi:** Muhasebe departmanına ve mali müşavirlere acil eylem planı içeren HTML formatında renkli durum raporu postalar (`--email-to`, `--smtp-host`).
* ⚡ **Sıfır Dış Bağımlılık (Zero-Dependency):** Saf Python standart kütüphanesi mimarisi (`urllib`, `smtplib`, `ssl`, ASN.1 DER parser).
* 🚦 **CI/CD & Görev Zamanlayıcı Uyumu:** `--strict` parametresi ile süresi dolmuş veya kritik sertifika tespit edildiğinde `exit code 1` üreterek otomasyonları uyarır.
* 🇹🇷 **Milli ESHS Tanıma:** Kamu SM, TÜRKTRUST, E-Tuğra, E-Güven, TN KEP, EDM Bilişim ve Klon Bilişim sağlayıcılarını otomatik eşleştirir.

---

## 🛠️ Kurulum ve Yerel Geliştirme (Local Setup)

### Sistem Gereksinimleri
- Python 3.8 veya üzeri
- `git`
- (Windows için) Akıllı kart taraması için sistemde `certutil` (varsayılan mevcuttur)

### 1. Depoyu Klonlama ve Çalışma Ortamı
```bash
# Depoyu klonlayın
git clone https://github.com/eimza-kep/mali-muhur-eimza-suresi-kontrol.git
cd mali-muhur-eimza-suresi-kontrol

# Sanal ortam (virtualenv) oluşturma ve aktifleştirme (Opsiyonel)
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

### 2. Birim Testleri Çalıştırma
```bash
python test_expiry.py
```
veya `unittest` keşif mekanizmasıyla:
```bash
python -m unittest discover -v
```

---

## 🚀 Hızlı Başlangıç ve Kullanım Örnekleri

### 1. Bilgisayara Takılı USB Token / Akıllı Kartı Tarama
```bash
python check_expiry.py --scan-store
```

### 2. Sertifika Dosyasını İnceleme
```bash
python check_expiry.py mali_muhur.cer --alert-days 45
```

### 3. Klasördeki Tüm Sertifikaları Toplu Tarama
```bash
python check_expiry.py --dir ./sertifikalar/
```

### 4. Markdown ve JSON Çıktısı Alma
```bash
# Markdown tablo raporu
python check_expiry.py --scan-store --markdown

# Otomasyon sistemleri için JSON çıktısı
python check_expiry.py --scan-store --json
```

---

## 🔔 Otomatik Webhook ve E-Posta Bildirim Servisi

Mali mühürün süresinin bitmesine 30, 15 veya 3 gün kaldığında ya da süre dolduğunda otomatik bildirim tetiklenir:

### 1. Slack / Microsoft Teams / Discord Webhook Bildirimi
```bash
python check_expiry.py --scan-store --webhook "https://hooks.slack.com/services/T00/B00/XXXXX"
```

### 2. SMTP E-Posta Bildirimi
```bash
python check_expiry.py --scan-store \
  --email-to "muhasebe@sirketiniz.com" \
  --smtp-host "smtp.gmail.com" \
  --smtp-port 587 \
  --smtp-user "bildirim@sirketiniz.com" \
  --smtp-pass "uygulama_sifresi"
```
*(Not: `SMTP_PASS`, `SMTP_USER`, `SMTP_HOST` değerleri ortam değişkeni olarak da tanımlanabilir).*

---

## ⏰ Windows Görev Zamanlayıcı (Task Scheduler) ile Günlük Otomasyon

Mali mühürlerin her sabah saat 09:00'da otomatik kontrol edilmesi ve kritik durumda e-posta gönderilmesi için Windows Görev Zamanlayıcısına ekleyebilirsiniz:

```powershell
# PowerShell ile günlük zamanlanmış görev oluşturma
$Action = New-ScheduledTaskAction -Execute "python.exe" `
  -Argument "C:\Scripts\check_expiry.py --scan-store --webhook https://webhook.url --strict"

$Trigger = New-ScheduledTaskTrigger -Daily -At 09:00AM

Register-ScheduledTask -TaskName "MaliMuhur-Sure-Denetimi" -Action $Action -Trigger $Trigger -Description "Günlük Mali Mühür Süre Kontrolü"
```

Alternatif olarak PowerShell betiğini doğrudan çalıştırabilirsiniz:
```powershell
powershell -ExecutionPolicy Bypass -File .\Check-CertificateExpiry.ps1 -AlertDays 30
```

---

## 📊 Durum ve Uyarı Eşikleri

| Durum Kodu | Kalan Süre | Açıklama | Eylem |
|:---|:---|:---|:---|
| `OK` | > 30 Gün | Sertifika geçerli ve güvenli | İşlem gerekmez |
| `WARNING` | 16 - 30 Gün | Bitiş tarihi yaklaşıyor | Kamu SM / ESHS yenileme hazırlığı yapın |
| `CRITICAL` | 4 - 15 Gün | Kritik acil seviye | Derhal online başvuru ve ödeme tamamlanmalı |
| `CRITICAL` | ≤ 3 Gün | Acil eylem: Son 72 saat! | e-Defter berat krizini önlemek için acil kurye talep edilmeli |
| `EXPIRED` | < 0 Gün | Sertifika süresi dolmuş | Geçersiz sertifika ile imzalanan beratlar GİB tarafından reddedilir |

---

## 🔗 E-Dönüşüm Açık Kaynak Ekosistemi

Bu araç [eimza-kep](https://github.com/eimza-kep) organizasyonunun açık kaynak e-dönüşüm araçları ekosisteminin bir parçasıdır:

* 🇹🇷 **[awesome-turkiye-e-donusum](https://github.com/eimza-kep/awesome-turkiye-e-donusum):** Türkiye E-Dönüşüm kütüphane, mevzuat ve araçlar listesi.
* 📊 **[gib-edefter-berat-xml-dogrulayici](https://github.com/eimza-kep/gib-edefter-berat-xml-dogrulayici):** GİB e-Defter ve berat doğrulama aracı.
* 🩺 **[akilli-kart-surucu-teshis](https://github.com/eimza-kep/akilli-kart-surucu-teshis):** Akıllı kart okuyucu ve sürücü teşhis aracı.
* 🔓 **[eimza-pin-bloke-asistani](https://github.com/eimza-kep/eimza-pin-bloke-asistani):** USB token PIN kilitlendiğinde PUK kodu ile sıfırlama terminali.
* 📬 **[kep-adresi-dogrulayici](https://github.com/eimza-kep/kep-adresi-dogrulayici):** BTK KEP ve UETS adres doğrulama aracı.

---

## 📚 İlgili Teknik Rehberler
* 📄 [Mali Mühür Sertifika Süresi Dolduğunda Cezalı Duruma Düşmemek İçin Ne Yapılmalı?](https://malimuhur.site/yazilar/mali-muhur-suresi-doldu-ne-yapilmali.html)
* 📄 [e-Defter Berat Yükleme Günü Mali Mühür Çalışmazsa Acil Eylem Planı](https://malimuhur.site/yazilar/e-defter-berat-gunu-mali-muhur-calismazsa-cozum.html)
* 📄 [Mali Mühür Başvurusu Nasıl Yapılır ve Kaç Günde Gelir?](https://malimuhur.site/yazilar/mali-muhur-basvuru-sureci-ve-teslimat-suresi.html)

---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.
