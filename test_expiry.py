import unittest
from datetime import datetime, timedelta, timezone
from check_expiry import check_certificate_dates, is_turkish_eshs

class TestCertificateExpiry(unittest.TestCase):
    def test_check_certificate_dates_expired(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=730)
        not_after = now - timedelta(days=10) # expired 10 days ago

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "EXPIRED")
        self.assertEqual(res["days_remaining"], -10)

    def test_check_certificate_dates_critical(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=365)
        not_after = now + timedelta(days=7) # 7 days left

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "CRITICAL")
        self.assertEqual(res["days_remaining"], 7)

    def test_check_certificate_dates_warning(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=365)
        not_after = now + timedelta(days=30) # 30 days left

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "WARNING")
        self.assertEqual(res["days_remaining"], 30)

    def test_check_certificate_dates_ok(self):
        now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
        not_before = now - timedelta(days=30)
        not_after = now + timedelta(days=335) # 335 days left

        res = check_certificate_dates(not_before, not_after, now=now)
        self.assertEqual(res["status"], "OK")
        self.assertEqual(res["days_remaining"], 335)

    def test_is_turkish_eshs(self):
        self.assertTrue(is_turkish_eshs("CN=Kamu SM Nitelikli Elektronik Sertifika Hizmet Saglayicisi, O=TUBITAK"))
        self.assertTrue(is_turkish_eshs("CN=TURKTRUST Nitelikli Elektronik Sertifika Hizmetleri"))
        self.assertTrue(is_turkish_eshs("CN=E-Tugra EBG Bilisim Teknolojileri"))
        self.assertFalse(is_turkish_eshs("CN=DigiCert Global Root CA, OU=www.digicert.com"))

if __name__ == "__main__":
    unittest.main()
