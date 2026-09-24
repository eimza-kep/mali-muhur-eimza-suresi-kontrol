#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mali Mühür ve Nitelikli Elektronik Sertifika (E-İmza) Süre Kontrol Aracı
Sertifika dosyalarını (.cer, .crt, .pem, .p12, .pfx) ve Windows Sertifika Deposunu analiz eder.
"""

import sys
import os
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

def check_certificate_dates(not_before, not_after, now=None):
    """Sertifikanın kalan gün sayısını ve durumunu hesaplar."""
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Ensure timezone-aware
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
    elif days_remaining <= 45:
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

def parse_der_or_pem(file_path):
    """Temel X.509 ASN.1 veya ssl/cryptography kütüphanesiyle sertifika tarihini çeker."""
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
        
        # cryptography >= 42 uses not_valid_after_utc
        not_after = getattr(cert, "not_valid_after_utc", cert.not_valid_after)
        not_before = getattr(cert, "not_valid_before_utc", cert.not_valid_before)

        analysis = check_certificate_dates(not_before, not_after)
        analysis["subject"] = subject
        analysis["issuer"] = issuer
        analysis["is_turkish_eshs"] = is_turkish_eshs(issuer)
        return analysis

    except ImportError:
        # Fallback without cryptography library
        import ssl
        try:
            cert_dict = ssl._ssl._test_decode_cert(str(file_path))
            not_after_str = cert_dict.get("notAfter")
            not_before_str = cert_dict.get("notBefore")
            # format: 'May 15 12:00:00 2027 GMT'
            fmt = "%b %d %H:%M:%S %Y %Z"
            not_after = datetime.strptime(not_after_str, fmt).replace(tzinfo=timezone.utc)
            not_before = datetime.strptime(not_before_str, fmt).replace(tzinfo=timezone.utc)
            analysis = check_certificate_dates(not_before, not_after)
            analysis["subject"] = str(cert_dict.get("subject", ""))
            analysis["issuer"] = str(cert_dict.get("issuer", ""))
            analysis["is_turkish_eshs"] = is_turkish_eshs(analysis["issuer"])
            return analysis
        except Exception as e:
            return {"error": f"Sertifika okunamadı (cryptography kütüphanesi kurulu değil): {e}"}

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mali Mühür ve E-İmza Süre Kontrol Aracı")
    parser.add_argument("cert_file", nargs="?", help="İncelenecek .cer, .crt veya .pem sertifika dosyası")
    parser.add_argument("--alert-days", type=int, default=30, help="Uyarı eşik gün sayısı (varsayılan: 30)")
    args = parser.parse_args()

    if not args.cert_file:
        print("[!] Lütfen bir sertifika dosyası belirtin. Örnek:")
        print("    python check_expiry.py sertifika.cer")
        print("\nWindows Sertifika Deposu kontrolü için PowerShell betiğini kullanın:")
        print("    powershell .\\Check-CertificateExpiry.ps1")
        return

    path = Path(args.cert_file)
    if not path.exists():
        print(f"[-] Hata: '{path}' dosyası bulunamadı.")
        sys.exit(1)

    res = parse_der_or_pem(path)
    if "error" in res:
        print(f"[-] Hata: {res['error']}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  SERTİFİKA VE E-İMZA GEÇERLİLİK ANALİZİ")
    print("=" * 60)
    print(f"Dosya           : {path.name}")
    print(f"Sahip (Subject) : {res.get('subject', 'Bilinmiyor')}")
    print(f"Veren (Issuer)  : {res.get('issuer', 'Bilinmiyor')}")
    print(f"Milli ESHS      : {'Evet (Kamu SM / TÜRKTRUST / vb.)' if res.get('is_turkish_eshs') else 'Hayır'}")
    print(f"Başlangıç       : {res.get('not_before')}")
    print(f"Bitiş           : {res.get('not_after')}")
    print(f"Durum           : {res.get('status_text')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
