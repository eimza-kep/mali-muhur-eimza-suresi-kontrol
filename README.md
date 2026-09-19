# Mali Mühür & E-İmza Bitiş Süresi Kontrol Aracı ⏳🔑

[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20%7C%20Server-blue.svg)](https://microsoft.com)
[![PowerShell](https://img.shields.io/badge/PowerShell-5.1%2B%20%7C%207%2B-blueviolet.svg)](https://github.com/PowerShell/PowerShell)
[![Blog](https://img.shields.io/badge/Rehber-E--%C4%B0mza%20Blog-22c55e.svg)](https://eimza-kep.github.io/eimza-blog/)

Şirketlerin ve muhasebe departmanlarının en büyük kabuslarından biri, **ayın son günü e-Defter beratı yüklerken** veya **acil e-fatura keserken** mali mührün süresinin bittiğini fark etmektir. Yeni mali mührün TÜBİTAK Kamu SM tarafından üretilip kargoyla gelmesi en az 3 ila 7 iş günü sürdüğünden, binlerce liralık usulsüzlük cezalarıyla karşılaşılır.

Bu açık kaynaklı hafif araç; bilgisayarınıza takılı USB Token'ları ve Windows Sertifika Deposu'nu tarayarak mali mühür ve e-imzanızın **kalan gün sayısını hesaplar**, renkli uyarılar üretir ve süresi yaklaşan sertifikalar için erkenden harekete geçmenizi sağlar.

---

## 🖥️ Terminal Çıktı Örneği

```text
==========================================================================================
         MALİ MÜHÜR & E-İMZA BİTİŞ SÜRESİ DENETLEME ARACI v1.0                            
==========================================================================================
Tarih: 19.09.2026 23:30 | Uyarı Eşiği: 30 Gün

SERTİFİKA SAHİBİ / ŞİRKET           | VEREN KURUM          | BİTİŞ      | KALAN GÜN | DURUM
------------------------------------------------------------------------------------------
ABC YAZILIM TEKNOLOJİLERİ A.Ş.      | TÜBİTAK Kamu SM      | 2026-10-12 |        23 | 🚨 ACİL YENİLEME GEREKİYOR!
AHMET YILMAZ (TC: 12345678901)      | TÜRKTRUST NES        | 2027-04-15 |       208 | 🟢 Güvenli
XYZ İNŞAAT TİCARET LTD. ŞTİ.        | E-Tuğra ESHS         | 2026-08-01 |       -49 | ❌ SÜRESİ DOLMUŞ!
```

---

## 🚀 Hızlı Başlangıç

### 1. Dosyayı İndirip Çalıştırma
* Repodaki **`check.bat`** dosyasına çift tıklamanız yeterlidir.
* Sonuçlar anında terminalde listelenir.

### 2. PowerShell ile Doğrudan Çalıştırma
```powershell
irm https://raw.githubusercontent.com/eimza-kep/mali-muhur-eimza-suresi-kontrol/main/Check-CertificateExpiry.ps1 | iex
```

### 3. Özel Gün Eşiği Belirleme (Örn: 45 gün kala uyar)
```powershell
.\Check-CertificateExpiry.ps1 -AlertDays 45
```

### 4. Otomasyon & JSON Çıktısı (Zabbix, Nagios veya Özel Yazılımlar İçin)
```powershell
.\Check-CertificateExpiry.ps1 -AsJson
```

---

## ⏰ Otomatik Haftalık Kontrol Kurulumu (Önerilen)

Şirketinizde bu kontrolü unutmamak için Windows Görev Zamanlayıcısı'na (Task Scheduler) tek bir komutla haftalık görev ekleyebilirsiniz:

```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\Tools\Check-CertificateExpiry.ps1"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "MaliMuhurSureKontrol" -Description "Haftalık Mali Mühür ve E-İmza Bitiş Tarihi Denetimi"
```

---

## 🏢 Desteklenen Sertifika Sağlayıcıları (ESHS)

* ✅ **TÜBİTAK BİLGEM Kamu Sertifikasyon Merkezi (Kamu SM)** (Mali Mühür & Kurumsal E-İmza)
* ✅ **TÜRKTRUST**
* ✅ **E-Tuğra**
* ✅ **E-Güven (Elektronik Bilgi Güvenliği A.Ş.)**
* ✅ **TN KEP / TN Bilişim**
* ✅ **Bilgi Teknolojileri (BilgiTek)**
* ✅ **EDM Bilişim**

---

## 📚 İlgili Rehberler ve Çözüm Yazıları

Mali mühür süresi bittiğinde yapılması gereken resmi kriz prosedürleri ve detaylı rehberler için blogumuzu inceleyebilirsiniz:

* 📄 [Mali Mühür Süresi Bitti! E-Fatura Kesemiyorum, Acil Ne Yapmalıyım? Şirketler İçin Kriz Yönetimi](https://eimza-kep.github.io/eimza-blog/posts/mali-muhur-suresi-doldu-ne-yapilmali.html)
* 📄 [e-Defter Beratı Gönderiminde Son Gün Krizleri: Mali Mühür Sorunları Nasıl Aşılır?](https://eimza-kep.github.io/eimza-blog/posts/e-defter-berati-gonderimi-mali-muhur.html)
* 📄 [E-İmza USB'mi Kaybettim/Çaldırdım, Ne Yapmalıyım? İptal ve Yenileme Rehberi](https://eimza-kep.github.io/eimza-blog/posts/e-imza-kayboldu-calindi-iptal-rehberi.html)
* 📄 [E-İmza Cihazları (USB Token) Nasıl Çalışır? Çipin İçindeki Teknik Dünya](https://eimza-kep.github.io/eimza-blog/posts/e-imza-cihazlari-nasil-calisir-teknik-rehber.html)

---

## ⚖️ Lisans

Bu yazılım [MIT Lisansı](LICENSE) ile lisanslanmıştır. Tamamen ücretsizdir.
