#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mali Mühür ve Nitelikli Elektronik Sertifika (E-İmza) Süre Kontrol Aracı v1.2
=============================================================================
Sertifika dosyalarını (.cer, .crt, .pem, .p12, .pfx) ve Windows Kişisel Sertifika
Deposundaki (MY Store) takılı token sertifikalarını tarayarak kalan gün sayısını,
ESHS sağlayıcısını ve acil yenileme uyarılarını raporlar.

Yazar: E-İmza & Dijital Dönüşüm Portalı (https://mali-muhur-merkezi.pages.dev/)
Lisans: MIT
"""

import sys
import os
import re
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KNOWN_ESHS = [
    "Kamu SM", "Kamu Sertifikasyon Merkezi", "TUBITAK", "TÜBİTAK",
    "TURKTRUST", "TÜRKTRUST", "E-Tugra", "E-Tuğra", "E-Guven", "E-Güven",
    "Elektronik Bilgi Guvenligi", "TN KEP", "Bilgi Teknolojileri",
    "EDM Bilisim", "EDM Bilişim", "Klon Bilisim", "Mali Muhur", "Mali Mühür"
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
    for eshs in KNOWN_ESHS:
        if eshs.lower() in issuer_str.lower():
            return True
    return False

def parse_der_or_pem(file_path, alert_days=30):
    """X.509 ASN.1 veya cryptography kütüphanesiyle sertifika tarihini çeker."""
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
        analysis["subject"] = subject
        analysis["issuer"] = issuer
        analysis["is_turkish_eshs"] = is_turkish_eshs(issuer)
        return analysis

    except ImportError:
        import ssl
        try:
            cert_dict = ssl._ssl._test_decode_cert(str(file_path))
            not_after_str = cert_dict.get("notAfter")
            not_before_str = cert_dict.get("notBefore")
            fmt = "%b %d %H:%M:%S %Y %Z"
            not_after = datetime.strptime(not_after_str, fmt).replace(tzinfo=timezone.utc)
            not_before = datetime.strptime(not_before_str, fmt).replace(tzinfo=timezone.utc)
            analysis = check_certificate_dates(not_before, not_after, alert_days=alert_days)
            analysis["subject"] = str(cert_dict.get("subject", ""))
            analysis["issuer"] = str(cert_dict.get("issuer", ""))
            analysis["is_turkish_eshs"] = is_turkish_eshs(analysis["issuer"])
            return analysis
        except Exception as e:
            return {"error": f"Sertifika okunamadı: {e}"}

def scan_windows_cert_store(alert_days=30):
    """Windows Sertifika Deposu (MY Store) içindeki takılı kart ve sertifikaları certutil ile listeler."""
    if sys.platform != "win32":
        return []

    try:
        proc = subprocess.run(["certutil", "-user", "-store", "My"], capture_output=True, text=True, timeout=10)
        output = proc.stdout
    except Exception as e:
        return []

    certs = []
    # Split by certificate blocks
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
            
            # certutil format: 24.09.2027 15:30 or 9/24/2027
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
                analysis["subject"] = sub
                analysis["issuer"] = iss
                analysis["is_turkish_eshs"] = is_turkish_eshs(iss)
                certs.append(analysis)

    return certs

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mali Mühür ve E-İmza Süre Kontrol Aracı v1.2")
    parser.add_argument("cert_file", nargs="?", help="İncelenecek .cer, .crt veya .pem sertifika dosyası")
    parser.add_argument("--scan-store", action="store_true", help="Windows Sertifika Deposundaki takılı e-imzaları tara")
    parser.add_argument("--alert-days", type=int, default=30, help="Uyarı eşik gün sayısı (varsayılan: 30)")
    parser.add_argument("--json", action="store_true", help="JSON formatında çıktı ver")
    parser.add_argument("--markdown", action="store_true", help="Markdown formatında rapor üret")
    args = parser.parse_args()

    if args.scan_store:
        certs = scan_windows_cert_store(alert_days=args.alert_days)
        if args.json:
            print(json.dumps(certs, indent=2, ensure_ascii=False))
            return
        if not certs:
            print("[!] Windows Sertifika Deposunda takılı akıllı kart sertifikası tespit edilemedi.")
            return
        
        print("=" * 70)
        print(f"Windows Sertifika Deposunda {len(certs)} Adet Sertifika Bulundu:")
        print("=" * 70)
        for c in certs:
            icon = "✅" if c["status"] == "OK" else "⚠️" if c["status"] == "WARNING" else "🚨"
            print(f"{icon} {c['status_text']}")
            print(f"   Sahip: {c['subject'][:55]}")
            print(f"   ESHS:  {c['issuer'][:55]}")
            print(f"   Bitiş: {c['not_after']}\n")
        return

    if not args.cert_file:
        print("[!] Lütfen bir sertifika dosyası belirtin veya --scan-store ile takılı kartı tarayın:")
        print("    python check_expiry.py sertifika.cer")
        print("    python check_expiry.py --scan-store")
        return

    path = Path(args.cert_file)
    if not path.exists():
        print(f"[-] Hata: '{path}' dosyası bulunamadı.")
        sys.exit(1)

    res = parse_der_or_pem(path, alert_days=args.alert_days)
    if "error" in res:
        print(f"[-] Hata: {res['error']}")
        sys.exit(1)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.markdown:
        md = f"# Sertifika Süre Raporu: {path.name}\n\n"
        md += f"- **Sahip:** `{res.get('subject')}`\n"
        md += f"- **ESHS Sağlayıcı:** `{res.get('issuer')}`\n"
        md += f"- **Kalan Gün:** **{res.get('days_remaining')} gün** ({res.get('status_text')})\n"
        md += f"- **Son Kullanma Tarihi:** `{res.get('not_after')}`\n"
        print(md)
        return

    print("\n" + "=" * 65)
    print("      SERTİFİKA VE E-İMZA GEÇERLİLİK ANALİZİ v1.2")
    print("=" * 65)
    print(f"Dosya           : {path.name}")
    print(f"Sahip (Subject) : {res.get('subject', 'Bilinmiyor')}")
    print(f"Veren (Issuer)  : {res.get('issuer', 'Bilinmiyor')}")
    print(f"Milli ESHS      : {'Evet (Kamu SM / TÜRKTRUST / vb.)' if res.get('is_turkish_eshs') else 'Hayır'}")
    print(f"Başlangıç       : {res.get('not_before')}")
    print(f"Bitiş           : {res.get('not_after')}")
    print(f"Durum           : {res.get('status_text')}")
    print("=" * 65)

if __name__ == "__main__":
    main()
