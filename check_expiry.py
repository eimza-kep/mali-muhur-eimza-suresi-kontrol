#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mali Mühür ve Nitelikli Elektronik Sertifika (E-İmza) Süre Kontrol Aracı v1.3
=============================================================================
Sertifika dosyalarını (.cer, .crt, .pem, .p12, .pfx), klasörleri (--dir) ve Windows
Kişisel Sertifika Deposundaki (MY Store) takılı token sertifikalarını tarayarak
kalan gün sayısını, ESHS sağlayıcısını, acil yenileme uyarılarını raporlar;
otomatik Webhook (Slack, Teams, Discord) ve SMTP E-Posta bildirimleri gönderir.

Özellikler:
- Sıfır Harici Bağımlılık (Pure Python Standart Kütüphane)
- Windows Sertifika Deposu (MY Store) takılı USB token tarama (--scan-store)
- Toplu Klasör Tarama (--dir)
- Otomatik Webhook Bildirimi (--webhook / --webhook-url)
- Otomatik SMTP E-Posta Bildirimi (--email-to, --smtp-host vb.)
- CI/CD ve Görev Zamanlayıcı Modu (--strict)
- Özelleştirilebilir Uyarı Eşiği (--alert-days)

Yazar: E-İmza & Dijital Dönüşüm Portalı (https://malimuhur.site/)
Lisans: MIT
"""

import sys
import os
import re
import json
import smtplib
import urllib.request
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Windows konsolunda UTF-8 çıktı desteği
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KNOWN_ESHS = [
    "Kamu SM", "Kamu Sertifikasyon Merkezi", "TUBITAK", "TÜBİTAK",
    "TURKTRUST", "TÜRKTRUST", "E-Tugra", "E-Tuğra", "E-Guven", "E-Güven",
    "Elektronik Bilgi Guvenligi", "TN KEP", "Bilgi Teknolojileri",
    "EDM Bilisim", "EDM Bilişim", "Klon Bilisim", "Mali Muhur", "Mali Mühür",
    "E-İmzaTR", "E-İmza TR", "PTT Bilgi Teknolojileri", "Türksat"
]

def check_certificate_dates(not_before, not_after, now=None, alert_days=30):
    """Sertifikanın kalan gün sayısını ve durumunu hesaplar."""
    if now is None:
        now = datetime.now(timezone.utc)
    
    if not_after.tzinfo is None:
        not_after = not_after.replace(tzinfo=timezone.utc)
    if not_before.tzinfo is None:
        not_before = not_before.replace(tzinfo=timezone.utc)

    days_remaining = (not_after - now).days

    if now < not_before:
        status = "NOT_YET_VALID"
        status_text = "Henüz Geçerli Değil"
    elif now > not_after:
        status = "EXPIRED"
        status_text = f"SÜRESİ DOLMUŞ ({abs(days_remaining)} gün önce)"
    elif days_remaining <= 3:
        status = "CRITICAL"
        status_text = f"ACİL KRİTİK: YALNIZCA {days_remaining} GÜN KALDI!"
    elif days_remaining <= 15:
        status = "CRITICAL"
        status_text = f"KRİTİK ACİL ({days_remaining} gün kaldı)"
    elif days_remaining <= alert_days:
        status = "WARNING"
        status_text = f"Yaklaşıyor ({days_remaining} gün kaldı)"
    else:
        status = "OK"
        status_text = f"Geçerli ({days_remaining} gün kaldı)"

    return {
        "status": status,
        "status_text": status_text,
        "days_remaining": days_remaining,
        "not_before": not_before.strftime("%Y-%m-%d %H:%M:%S"),
        "not_after": not_after.strftime("%Y-%m-%d %H:%M:%S")
    }

def is_turkish_eshs(issuer_str):
    """Veren makamın Türkiye'de yetkili bir ESHS olup olmadığını kontrol eder."""
    if not issuer_str:
        return False
    for eshs in KNOWN_ESHS:
        if eshs.lower() in issuer_str.lower():
            return True
    return False

def parse_asn1_der_dates(data_bytes):
    """ASN.1 DER bayt dizisi içindeki geçerlilik tarihlerini (UTCTime/GeneralizedTime) bulur."""
    pattern = re.compile(b'([0-9]{12}Z|[0-9]{14}Z)')
    matches = pattern.findall(data_bytes)
    if len(matches) >= 2:
        def to_dt(t_bytes):
            s = t_bytes.decode('ascii')
            if len(s) == 13:
                year = int(s[0:2])
                full_year = 1900 + year if year >= 50 else 2000 + year
                s = f"{full_year:04d}" + s[2:]
            return datetime.strptime(s, "%Y%m%d%H%M%SZ").replace(tzinfo=timezone.utc)
        try:
            return to_dt(matches[0]), to_dt(matches[1])
        except Exception:
            pass
    return None, None

def parse_der_or_pem(file_path, alert_days=30):
    """X.509 sertifika dosyasını analiz eder (Cryptography veya Standard Library Fallback)."""
    file_path = Path(file_path)
    if not file_path.exists():
        return {"error": f"Dosya bulunamadı: {file_path}"}

    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        with open(file_path, "rb") as f:
            data = f.read()

        cert = None
        try:
            cert = x509.load_pem_x509_certificate(data, default_backend())
        except Exception:
            cert = x509.load_der_x509_certificate(data, default_backend())

        subject = cert.subject.rfc4514_string()
        issuer = cert.issuer.rfc4514_string()
        
        not_after = getattr(cert, "not_valid_after_utc", cert.not_valid_after)
        not_before = getattr(cert, "not_valid_before_utc", cert.not_valid_before)

        analysis = check_certificate_dates(not_before, not_after, alert_days=alert_days)
        analysis["file"] = file_path.name
        analysis["subject"] = subject
        analysis["issuer"] = issuer
        analysis["is_turkish_eshs"] = is_turkish_eshs(issuer)
        return analysis

    except ImportError:
        # 1. Standard Library ssl denemesi (PEM için)
        import ssl
        try:
            cert_dict = ssl._ssl._test_decode_cert(str(file_path))
            not_after_str = cert_dict.get("notAfter")
            not_before_str = cert_dict.get("notBefore")
            fmt = "%b %d %H:%M:%S %Y %Z"
            not_after = datetime.strptime(not_after_str, fmt).replace(tzinfo=timezone.utc)
            not_before = datetime.strptime(not_before_str, fmt).replace(tzinfo=timezone.utc)
            analysis = check_certificate_dates(not_before, not_after, alert_days=alert_days)
            analysis["file"] = file_path.name
            analysis["subject"] = str(cert_dict.get("subject", ""))
            analysis["issuer"] = str(cert_dict.get("issuer", ""))
            analysis["is_turkish_eshs"] = is_turkish_eshs(analysis["issuer"])
            return analysis
        except Exception:
            pass

        # 2. Saf Python ASN.1 DER regex taraması
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            nb, na = parse_asn1_der_dates(content)
            if nb and na:
                analysis = check_certificate_dates(nb, na, alert_days=alert_days)
                analysis["file"] = file_path.name
                
                # Basit konu / veren metin çıkarımı
                text_content = content.decode('latin-1', errors='ignore')
                issuer_match = re.search(r'(?:Kamu SM|TUBITAK|TURKTRUST|E-Tugra|E-Güven|TN KEP|EDM Bilisim)[^,\x00\r\n]{0,60}', text_content, re.IGNORECASE)
                issuer_str = issuer_match.group(0) if issuer_match else "Tespit Edilemedi (Standart ASN.1)"
                analysis["subject"] = file_path.stem
                analysis["issuer"] = issuer_str
                analysis["is_turkish_eshs"] = is_turkish_eshs(issuer_str)
                return analysis
        except Exception:
            pass

        # 3. Windows certutil fallback
        if sys.platform == "win32":
            try:
                proc = subprocess.run(["certutil", "-dump", str(file_path)], capture_output=True, text=True, timeout=5)
                out = proc.stdout
                na_match = re.search(r"NotAfter:\s*([^\r\n]+)", out)
                nb_match = re.search(r"NotBefore:\s*([^\r\n]+)", out)
                sub_match = re.search(r"Subject:\s*(.*)", out)
                iss_match = re.search(r"Issuer:\s*(.*)", out)
                if na_match:
                    after_str = na_match.group(1).strip()
                    for fmt in ["%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M", "%d.%m.%Y"]:
                        try:
                            parsed_na = datetime.strptime(after_str, fmt).replace(tzinfo=timezone.utc)
                            parsed_nb = datetime.now(timezone.utc)
                            analysis = check_certificate_dates(parsed_nb, parsed_na, alert_days=alert_days)
                            analysis["file"] = file_path.name
                            analysis["subject"] = sub_match.group(1).strip() if sub_match else file_path.stem
                            analysis["issuer"] = iss_match.group(1).strip() if iss_match else "Bilinmiyor"
                            analysis["is_turkish_eshs"] = is_turkish_eshs(analysis["issuer"])
                            return analysis
                        except ValueError:
                            continue
            except Exception:
                pass

        return {"error": f"Sertifika okunamadı veya desteklenmeyen biçim: {file_path.name}"}

def scan_windows_cert_store(alert_days=30):
    """Windows Sertifika Deposu (MY Store) içindeki takılı kart ve sertifikaları listeler."""
    if sys.platform != "win32":
        return []

    try:
        proc = subprocess.run(["certutil", "-user", "-store", "My"], capture_output=True, text=True, timeout=10)
        output = proc.stdout
    except Exception:
        return []

    certs = []
    blocks = output.split("================ Certificate ")
    for block in blocks[1:]:
        subject_m = re.search(r"Subject:\s*(.*)", block)
        issuer_m = re.search(r"Issuer:\s*(.*)", block)
        not_before_m = re.search(r"NotBefore:\s*([^\r\n]+)", block)
        not_after_m = re.search(r"NotAfter:\s*([^\r\n]+)", block)

        if subject_m and not_after_m:
            sub = subject_m.group(1).strip()
            iss = issuer_m.group(1).strip() if issuer_m else "Bilinmiyor"
            after_str = not_after_m.group(1).strip()
            
            parsed_date = None
            for fmt in ["%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M", "%d.%m.%Y", "%m/%d/%Y"]:
                try:
                    parsed_date = datetime.strptime(after_str, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    pass

            if parsed_date:
                now = datetime.now(timezone.utc)
                analysis = check_certificate_dates(now, parsed_date, now=now, alert_days=alert_days)
                analysis["file"] = "Windows MY Store"
                analysis["subject"] = sub
                analysis["issuer"] = iss
                analysis["is_turkish_eshs"] = is_turkish_eshs(iss)
                certs.append(analysis)

    return certs

def scan_directory_certs(dir_path, alert_days=30, recursive=True):
    """Belirtilen dizindeki tüm sertifika dosyalarını (.cer, .crt, .pem, .pfx) tarar."""
    p = Path(dir_path)
    if not p.is_dir():
        return []
    
    extensions = [".cer", ".crt", ".pem", ".pfx", ".p12"]
    pattern = "**/*" if recursive else "*"
    files = [f for f in p.glob(pattern) if f.suffix.lower() in extensions and f.is_file()]
    
    results = []
    for f in files:
        res = parse_der_or_pem(f, alert_days=alert_days)
        if "error" not in res:
            results.append(res)
    return results

def format_webhook_payload(payload_or_list):
    """Webhook için bildirim yükü (Slack, Discord, Teams uyumlu) oluşturur."""
    items = payload_or_list if isinstance(payload_or_list, list) else [payload_or_list]
    
    critical_count = sum(1 for x in items if x.get("status") in ["CRITICAL", "EXPIRED"])
    warning_count = sum(1 for x in items if x.get("status") == "WARNING")

    title = f"⚠️ [Mali Mühür / E-İmza Süre Uyarısı] {len(items)} Sertifika İncelendi"
    lines = [title, ""]
    
    for c in items:
        status_icon = "🚨" if c.get("status") in ["CRITICAL", "EXPIRED"] else "⚠️"
        lines.append(f"{status_icon} **{c.get('subject', 'Bilinmeyen Sertifika')[:50]}**")
        lines.append(f"   ESHS: {c.get('issuer', 'Bilinmiyor')[:45]}")
        lines.append(f"   Durum: {c.get('status_text', '')}")
        lines.append(f"   Bitiş Tarihi: {c.get('not_after', '')}")
        lines.append("")

    lines.append("💡 Acil eylem: Süresi yaklaşan Mali Mühür veya e-İmzalar için Kamu SM / ESHS üzerinden derhal yenileme başvurusu yapınız.")
    full_text = "\n".join(lines)

    return {
        "text": full_text,
        "content": full_text,
        "summary": title,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "certificates": items
    }

def send_webhook_alert(webhook_url, payload_or_list, timeout=5.0):
    """
    Kritik veya süresi dolan sertifikalar için Webhook POST isteği gönderir.
    Sıfır ek bağımlılık (Pure Python urllib.request).
    """
    body_data = format_webhook_payload(payload_or_list)
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "MaliMuhur-ExpiryBot/1.3"
    }
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(body_data, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"Webhook başarıyla iletildi (HTTP {resp.status})"
    except Exception as e:
        return False, f"Webhook iletim hatası: {e}"

def send_email_alert(smtp_config, cert_results):
    """
    Kritik veya süresi dolan sertifikalar için SMTP e-posta uyarısı gönderir.
    Sıfır ek bağımlılık (Pure Python smtplib & email.mime).
    """
    smtp_host = smtp_config.get("host") or os.environ.get("SMTP_HOST")
    smtp_port = int(smtp_config.get("port") or os.environ.get("SMTP_PORT") or 587)
    smtp_user = smtp_config.get("user") or os.environ.get("SMTP_USER")
    smtp_pass = smtp_config.get("password") or os.environ.get("SMTP_PASS")
    to_email = smtp_config.get("to")
    from_email = smtp_config.get("from") or smtp_user or "mali-muhur-uyari@kurumsal.local"

    if not smtp_host or not to_email:
        return False, "E-posta gönderimi için SMTP host ve alıcı adresi (--email-to) gereklidir."

    items = cert_results if isinstance(cert_results, list) else [cert_results]
    critical_items = [c for c in items if c.get("status") in ["CRITICAL", "EXPIRED", "WARNING"]]

    if not critical_items:
        return True, "Uyarı gerektiren kritik sertifika bulunamadı, e-posta gönderilmedi."

    subject = f"🚨 [ACİL UYARI] Mali Mühür / E-İmza Süre Sonu Uyarısı ({len(critical_items)} Sertifika)"

    # HTML Tablosu
    rows_html = ""
    for c in critical_items:
        bg_color = "#ffebee" if c.get("status") in ["CRITICAL", "EXPIRED"] else "#fffde7"
        badge = "🚨 ACİL KRİTİK" if c.get("status") in ["CRITICAL", "EXPIRED"] else "⚠️ YAKLAŞIYOR"
        rows_html += f"""
        <tr style="background-color: {bg_color}; border-bottom: 1px solid #ddd;">
            <td style="padding: 10px;"><strong>{c.get('subject', 'Bilinmiyor')}</strong><br><small>{c.get('file', '')}</small></td>
            <td style="padding: 10px;">{c.get('issuer', 'Bilinmiyor')}</td>
            <td style="padding: 10px; font-weight: bold;">{c.get('days_remaining')} gün</td>
            <td style="padding: 10px;">{c.get('not_after', '')}</td>
            <td style="padding: 10px;"><span style="padding: 4px 8px; border-radius: 4px; font-weight: bold;">{badge}</span></td>
        </tr>
        """

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
        <h2 style="color: #c62828;">⚠️ Mali Mühür ve E-İmza Süre Sonu Bildirimi</h2>
        <p>Aşağıda listelenen e-İmza ve Mali Mühür sertifikalarının kullanım süresi dolmak üzeredir veya dolmuştur. 
        GİB e-Defter berat yükleme ve e-Fatura kesme süreçlerinde aksama yaşamamak için ivedilikle yenileme yapınız.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <thead>
                <tr style="background-color: #f5f5f5; text-align: left; border-bottom: 2px solid #ccc;">
                    <th style="padding: 10px;">Sertifika Sahibi</th>
                    <th style="padding: 10px;">ESHS Sağlayıcı</th>
                    <th style="padding: 10px;">Kalan Süre</th>
                    <th style="padding: 10px;">Bitiş Tarihi</th>
                    <th style="padding: 10px;">Durum</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div style="margin-top: 25px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #1976d2;">
            <strong>Mali Mühür Yenileme Adımları:</strong><br>
            TÜBİTAK Kamu SM portalı üzerinden (https://kamusm.bilgem.tubitak.gov.tr/) yetkili şirket temsilcisi tarafından online yenileme başvurusu tamamlanmalıdır.
        </div>
        <p style="font-size: 12px; color: #777; margin-top: 20px;">Bu bildirim açık kaynaklı Mali Mühür Süre Kontrol Aracı tarafından otomatik oluşturulmuştur.</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    plain_text = format_webhook_payload(critical_items)["text"]
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10.0) as server:
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except Exception:
                pass
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True, f"Uyarı e-postası başarıyla iletildi: {to_email}"
    except Exception as e:
        return False, f"E-posta gönderim hatası: {e}"

def generate_markdown_report(certs):
    """Sertifika listesi için Markdown rapor tablosu üretir."""
    lines = [
        "# Mali Mühür ve E-İmza Süre Denetim Raporu ⏱️",
        "",
        f"*Raporlama Zamanı:* `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        f"*İncelenen Toplam Sertifika:* **{len(certs)}**",
        "",
        "| Durum | Sahip (Subject) | ESHS Sağlayıcı | Kalan Gün | Bitiş Tarihi |",
        "|:---|:---|:---|:---|:---|"
    ]
    for c in certs:
        icon = "✅" if c.get("status") == "OK" else "⚠️" if c.get("status") == "WARNING" else "🚨"
        lines.append(f"| {icon} {c.get('status')} | `{c.get('subject', '')[:40]}` | {c.get('issuer', '')[:30]} | **{c.get('days_remaining')} gün** | `{c.get('not_after')}` |")
    
    lines.append("")
    return "\n".join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mali Mühür ve E-İmza Süre Kontrol, Webhook & E-Posta Aracı v1.3")
    parser.add_argument("cert_file", nargs="?", help="İncelenecek .cer, .crt veya .pem sertifika dosyası")
    parser.add_argument("--scan-store", action="store_true", help="Windows Sertifika Deposundaki takılı e-imzaları tara")
    parser.add_argument("--dir", help="Belirtilen klasördeki tüm sertifikaları (.cer, .crt, .pem, .pfx) tara")
    parser.add_argument("--alert-days", type=int, default=30, help="Uyarı eşik gün sayısı (varsayılan: 30)")
    parser.add_argument("--json", action="store_true", help="JSON formatında çıktı ver")
    parser.add_argument("--markdown", action="store_true", help="Markdown formatında rapor üret")
    parser.add_argument("--strict", action="store_true", help="Kritik veya süresi dolmuş sertifika varsa exit code 1 üret")
    
    # Webhook & E-Posta Seçenekleri
    parser.add_argument("--webhook", "--webhook-url", dest="webhook", help="Slack/Teams/Discord Webhook URL'si")
    parser.add_argument("--email-to", help="Uyarı e-postasının gönderileceği alıcı adresi")
    parser.add_argument("--email-from", help="Gönderici e-posta adresi (opsiyonel)")
    parser.add_argument("--smtp-host", help="SMTP sunucusu (Örn: smtp.gmail.com)")
    parser.add_argument("--smtp-port", type=int, default=587, help="SMTP portu (varsayılan: 587)")
    parser.add_argument("--smtp-user", help="SMTP kullanıcı adı")
    parser.add_argument("--smtp-pass", help="SMTP şifresi (veya SMTP_PASS ortam değişkeni)")

    args = parser.parse_args()

    certs = []

    # 1. Windows Store Taraması
    if args.scan_store:
        certs = scan_windows_cert_store(alert_days=args.alert_days)
    # 2. Klasör Taraması
    elif args.dir:
        certs = scan_directory_certs(args.dir, alert_days=args.alert_days)
    # 3. Tekil Dosya İncelemesi
    elif args.cert_file:
        res = parse_der_or_pem(args.cert_file, alert_days=args.alert_days)
        if "error" in res:
            print(f"[-] Hata: {res['error']}", file=sys.stderr)
            sys.exit(1)
        certs = [res]
    else:
        print("[!] Lütfen bir sertifika dosyası belirtin, klasör girin (--dir) veya takılı kartı tarayın (--scan-store):")
        print("    python check_expiry.py mali_muhur.cer")
        print("    python check_expiry.py --scan-store")
        print("    python check_expiry.py --dir ./sertifikalar/")
        return

    # Çıktı Biçimlendirme
    if args.json:
        print(json.dumps(certs if len(certs) > 1 else certs[0], indent=2, ensure_ascii=False))
    elif args.markdown:
        print(generate_markdown_report(certs))
    else:
        print("\n" + "=" * 75)
        print("      SERTİFİKA VE MALİ MÜHÜR GEÇERLİLİK ANALİZİ v1.3")
        print("=" * 75)
        if not certs:
            print("[!] İncelenecek geçerli bir sertifika bulunamadı.")
        for c in certs:
            icon = "✅" if c.get("status") == "OK" else "⚠️" if c.get("status") == "WARNING" else "🚨"
            print(f"{icon} Durum       : {c.get('status_text')}")
            print(f"   Kaynak      : {c.get('file', 'Bilinmiyor')}")
            print(f"   Sahip       : {c.get('subject', 'Bilinmiyor')[:55]}")
            print(f"   ESHS        : {c.get('issuer', 'Bilinmiyor')[:55]}")
            print(f"   Milli ESHS  : {'Evet' if c.get('is_turkish_eshs') else 'Hayır'}")
            print(f"   Bitiş Tarihi: {c.get('not_after')}\n")
        print("=" * 75)

    # Uyarı tetikleme (CRITICAL, EXPIRED veya WARNING)
    alert_needed = any(c.get("status") in ["CRITICAL", "EXPIRED", "WARNING"] for c in certs)

    # Webhook Gönderimi
    if args.webhook and alert_needed:
        ok, msg = send_webhook_alert(args.webhook, certs)
        print(f"\n[Webhook] {msg}")

    # E-Posta Gönderimi
    if args.email_to and alert_needed:
        smtp_conf = {
            "host": args.smtp_host,
            "port": args.smtp_port,
            "user": args.smtp_user,
            "password": args.smtp_pass,
            "to": args.email_to,
            "from": args.email_from
        }
        ok, msg = send_email_alert(smtp_conf, certs)
        print(f"\n[E-Posta] {msg}")

    # Strict mod: Kritik veya süresi dolmuş varsa exit code 1 üret
    has_critical_or_expired = any(c.get("status") in ["CRITICAL", "EXPIRED"] for c in certs)
    if args.strict and has_critical_or_expired:
        sys.exit(1)

if __name__ == "__main__":
    main()
