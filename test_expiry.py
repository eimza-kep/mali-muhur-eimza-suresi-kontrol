import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from check_expiry import (
    check_certificate_dates,
    is_turkish_eshs,
    format_webhook_payload,
    send_webhook_alert,
    send_email_alert,
    generate_markdown_report,
    parse_asn1_der_dates,
    scan_directory_certs
)

class TestCertificateExpiry(unittest.TestCase):
    def test_check_certificate_dates_expired(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=730)
        not_after = now - timedelta(days=10)

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "EXPIRED")
        self.assertEqual(res["days_remaining"], -10)

    def test_check_certificate_dates_critical_3_days(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=365)
        not_after = now + timedelta(days=2)

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "CRITICAL")
        self.assertIn("YALNIZCA 2 GÜN", res["status_text"])
        self.assertEqual(res["days_remaining"], 2)

    def test_check_certificate_dates_critical(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=365)
        not_after = now + timedelta(days=7)

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "CRITICAL")
        self.assertEqual(res["days_remaining"], 7)

    def test_check_certificate_dates_warning(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=365)
        not_after = now + timedelta(days=30)

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "WARNING")
        self.assertEqual(res["days_remaining"], 30)

    def test_check_certificate_dates_ok(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=30)
        not_after = now + timedelta(days=335)

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "OK")
        self.assertEqual(res["days_remaining"], 335)

    def test_custom_alert_days(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=30)
        not_after = now + timedelta(days=50)

        # Default 30 alert days -> status is OK
        res1 = check_certificate_dates(not_before, not_after, now=now, alert_days=30)
        self.assertEqual(res1["status"], "OK")

        # Custom 60 alert days -> status is WARNING
        res2 = check_certificate_dates(not_before, not_after, now=now, alert_days=60)
        self.assertEqual(res2["status"], "WARNING")

    def test_is_turkish_eshs(self):
        self.assertTrue(is_turkish_eshs("CN=Kamu SM Nitelikli Elektronik Sertifika Hizmet Saglayicisi, O=TUBITAK"))
        self.assertTrue(is_turkish_eshs("CN=TURKTRUST Nitelikli Elektronik Sertifika Hizmetleri"))
        self.assertTrue(is_turkish_eshs("CN=E-Tugra EBG Bilisim Teknolojileri"))
        self.assertFalse(is_turkish_eshs("CN=DigiCert Global Root CA, OU=www.digicert.com"))

    def test_format_webhook_payload_single(self):
        mock_payload = {
            "subject": "CN=Ahmet Yılmaz, SERIALNUMBER=12345678901",
            "issuer": "CN=Kamu SM Nitelikli Elektronik Sertifika",
            "status": "CRITICAL",
            "status_text": "KRİTİK ACİL (5 gün kaldı)",
            "days_remaining": 5
        }
        wb = format_webhook_payload(mock_payload)
        self.assertIn("text", wb)
        self.assertIn("content", wb)
        self.assertIn("Ahmet Yılmaz", wb["text"])
        self.assertIn("Kamu SM", wb["text"])
        self.assertIn("5 gün kaldı", wb["text"])
        self.assertEqual(wb["critical_count"], 1)

    def test_format_webhook_payload_multiple(self):
        mock_list = [
            {
                "subject": "CN=Şirket A Mali Mühür",
                "issuer": "CN=Kamu SM",
                "status": "CRITICAL",
                "status_text": "KRİTİK ACİL (3 gün kaldı)",
                "days_remaining": 3
            },
            {
                "subject": "CN=Mehmet Kaya E-İmza",
                "issuer": "CN=TÜRKTRUST",
                "status": "WARNING",
                "status_text": "Yaklaşıyor (25 gün kaldı)",
                "days_remaining": 25
            }
        ]
        wb = format_webhook_payload(mock_list)
        self.assertEqual(wb["critical_count"], 1)
        self.assertEqual(wb["warning_count"], 1)
        self.assertIn("Şirket A Mali Mühür", wb["text"])
        self.assertIn("Mehmet Kaya E-İmza", wb["text"])

    def test_send_email_alert_ok_skips(self):
        ok_item = {
            "subject": "CN=Test",
            "issuer": "CN=Kamu SM",
            "status": "OK",
            "days_remaining": 300
        }
        smtp_conf = {"host": "smtp.example.com", "to": "muhasebe@sirket.com"}
        ok, msg = send_email_alert(smtp_conf, [ok_item])
        self.assertTrue(ok)
        self.assertIn("gönderilmedi", msg)

    @patch("smtplib.SMTP")
    def test_send_email_alert_critical(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        critical_item = {
            "subject": "CN=Mali Mühür 2026",
            "issuer": "CN=Kamu SM",
            "status": "CRITICAL",
            "days_remaining": 2,
            "not_after": "2026-10-25 10:00:00"
        }
        smtp_conf = {
            "host": "smtp.example.com",
            "port": 587,
            "user": "alert@sirket.com",
            "password": "secretpassword",
            "to": "muhasebe@sirket.com"
        }
        ok, msg = send_email_alert(smtp_conf, [critical_item])
        self.assertTrue(ok)
        self.assertIn("başarıyla iletildi", msg)
        mock_server.sendmail.assert_called_once()

    def test_parse_asn1_der_dates(self):
        dummy_der = b"\x30\x82\x01" + b"260920120000Z" + b"\x00\x00" + b"290920120000Z" + b"\x00"
        nb, na = parse_asn1_der_dates(dummy_der)
        self.assertIsNotNone(nb)
        self.assertIsNotNone(na)
        self.assertEqual(nb.year, 2026)
        self.assertEqual(na.year, 2029)

    def test_generate_markdown_report(self):
        items = [{
            "subject": "CN=Test Şirket Mali Mühür",
            "issuer": "Kamu SM",
            "status": "WARNING",
            "days_remaining": 20,
            "not_after": "2026-11-12 12:00:00"
        }]
        md = generate_markdown_report(items)
        self.assertIn("Mali Mühür ve E-İmza Süre Denetim Raporu", md)
        self.assertIn("Test Şirket Mali Mühür", md)
        self.assertIn("20 gün", md)

if __name__ == "__main__":
    unittest.main()
