<#
.SYNOPSIS
    Mali Mühür ve E-İmza Bitiş Süresi & Sertifika Geçerlilik Kontrol Aracı

.DESCRIPTION
    Bu betik, Windows üzerindeki sertifika depolarını ve takılı akıllı kart sertifikalarını tarar;
    TÜBİTAK Kamu SM, TÜRKTRUST, E-Tuğra, E-Güven vb. Nitelikli Elektronik Sertifika (NES)
    ve Mali Mühürlerin bitiş tarihlerini hesaplayarak kritik süre uyarıları üretir.

.PARAMETER AlertDays
    Kaç günden az kalan sertifikalar için kritik uyarı verileceği (Varsayılan: 30)

.PARAMETER AsJson
    Sonuçları JSON formatında verir (Otomasyon ve izleme sistemleri için)

.NOTES
    Yazar: E-İmza & Dijital Dönüşüm Portalı (https://eimza-kep.github.io/eimza-blog/)
    Lisans: MIT
#>

[CmdletBinding()]
param(
    [int]$AlertDays = 30,
    [switch]$AsJson = $false
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Tanınan Türk Elektronik Sertifika Hizmet Sağlayıcıları (ESHS)
$knownIssuers = @(
    "Kamu Sertifikasyon Merkezi",
    "Kamu SM",
    "TUBITAK",
    "TURKTRUST",
    "E-Tugra",
    "E-Güven",
    "Elektronik Bilgi Guvenligi",
    "TN KEP",
    "Bilgi Teknolojileri",
    "EDM Bilisim",
    "Klon Bilisim",
    "Mali Muhur",
    "NES"
)

# Sertifikaları Tara (Kullanıcı ve Makine Deposu)
$allCerts = Get-ChildItem -Path Cert:\CurrentUser\My, Cert:\LocalMachine\My -ErrorAction SilentlyContinue

$results = @()
$now = Get-Date

foreach ($cert in $allCerts) {
    $issuerStr = $cert.Issuer
    $isTurkishESHS = $false

    foreach ($kw in $knownIssuers) {
        if ($issuerStr -like "*$kw*" -or $cert.Subject -like "*$kw*") {
            $isTurkishESHS = $true
            break
        }
    }

    # E-imza veya mali mühür adayı ise listeye ekle
    if ($isTurkishESHS -or ($cert.EnhancedKeyUsageList | Where-Object { $_.FriendlyName -like "*Secure Email*" -or $_.FriendlyName -like "*Client Authentication*" })) {
        $daysLeft = [math]::Floor(($cert.NotAfter - $now).TotalDays)
        
        $status = "NORMAL"
        $statusColor = "Green"

        if ($daysLeft -lt 0) {
            $status = "SURESI_DOLMUS"
            $statusColor = "DarkRed"
        } elseif ($daysLeft -le $AlertDays) {
            $status = "KRITIK_TEHLIKE"
            $statusColor = "Red"
        } elseif ($daysLeft -le 60) {
            $status = "YAKLASIYOR"
            $statusColor = "Yellow"
        }

        # İsim / VKN / TCKN ayıkla
        $subjectName = $cert.Subject
        if ($cert.Subject -match "CN=([^,]+)") {
            $subjectName = $matches[1]
        }

        $results += [PSCustomObject]@{
            Sahip            = $subjectName
            VerenKurum       = ($cert.Issuer -replace "CN=([^,]+).*", '$1')
            BaslangicTarihi  = $cert.NotBefore.ToString("yyyy-MM-dd")
            BitisTarihi      = $cert.NotAfter.ToString("yyyy-MM-dd")
            KalanGun         = $daysLeft
            Durum            = $status
            Thumbprint       = $cert.Thumbprint
        }
    }
}

if ($AsJson) {
    $results | ConvertTo-Json -Depth 3
    exit 0
}

Write-Host "==========================================================================================" -ForegroundColor Cyan
Write-Host "         MALİ MÜHÜR & E-İMZA BİTİŞ SÜRESİ DENETLEME ARACI v1.0                            " -ForegroundColor Yellow
Write-Host "==========================================================================================" -ForegroundColor Cyan
Write-Host "Tarih: $($now.ToString('dd.MM.yyyy HH:mm')) | Uyarı Eşiği: $AlertDays Gün`n" -ForegroundColor Gray

if ($results.Count -eq 0) {
    Write-Host "[!] Bilgisayarda takılı veya yüklü bir E-İmza / Mali Mühür sertifikası bulunamadı." -ForegroundColor Yellow
    Write-Host "    İpucu: USB Token takılıysa AKİS veya kart okuyucu sürücüsünün açık olduğunu kontrol edin." -ForegroundColor DarkGray
    Write-Host "`nRehber: https://mali-muhur-merkezi.pages.dev/yazilar/mali-muhur-ve-e-imza-arasindaki-farklar.html" -ForegroundColor Cyan
    exit 0
}

Write-Host ("{0,-35} | {1,-20} | {2,-10} | {3,9} | {4}" -f "SERTİFİKA SAHİBİ / ŞİRKET", "VEREN KURUM", "BİTİŞ", "KALAN GÜN", "DURUM") -ForegroundColor White
Write-Host ("-" * 90) -ForegroundColor Gray

foreach ($r in $results) {
    $color = "Green"
    $durumMetin = "🟢 Güvenli"

    if ($r.Durum -eq "SURESI_DOLMUS") {
        $color = "Red"
        $durumMetin = "❌ SÜRESİ DOLMUŞ!"
    } elseif ($r.Durum -eq "KRITIK_TEHLIKE") {
        $color = "Red"
        $durumMetin = "🚨 ACİL YENİLEME GEREKİYOR!"
    } elseif ($r.Durum -eq "YAKLASIYOR") {
        $color = "Yellow"
        $durumMetin = "⚠️  Yaklaşıyor (Hazırlık yapın)"
    }

    $dispName = if ($r.Sahip.Length -gt 33) { $r.Sahip.Substring(0, 30) + "..." } else { $r.Sahip }
    $dispIssuer = if ($r.VerenKurum.Length -gt 18) { $r.VerenKurum.Substring(0, 15) + "..." } else { $r.VerenKurum }

    Write-Host ("{0,-35} | {1,-20} | {2,-10} | {3,9} | " -f $dispName, $dispIssuer, $r.BitisTarihi, $r.KalanGun) -NoNewline -ForegroundColor White
    Write-Host $durumMetin -ForegroundColor $color
}

Write-Host "`n------------------------------------------------------------------------------------------" -ForegroundColor Gray
Write-Host "💡 ÖNEMLİ TAVSİYE: Mali mühür yenileme başvuruları TÜBİTAK Kamu SM tarafından ortalama" -ForegroundColor Yellow
Write-Host "   3-7 iş gününde kargolanır. Son 30 güne girmeden önce başvurunuzu tamamlayın." -ForegroundColor Yellow
Write-Host "   Detaylı Kriz Rehberi: https://mali-muhur-merkezi.pages.dev/yazilar/mali-muhur-arizalandi-kayboldu-ne-yapilmali.html" -ForegroundColor Cyan
Write-Host "==========================================================================================`n" -ForegroundColor Cyan
