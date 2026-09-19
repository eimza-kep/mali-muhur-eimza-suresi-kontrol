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
    [switch]$AsJson = $false,
    [string]$ExportPath = "",
    [switch]$OnlyExpiring = $false,
    [switch]$FailOnCritical = $false
)

try {
    $OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

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
        $subjectName = if ($cert.Subject) { $cert.Subject } else { "Bilinmeyen Sertifika" }
        if ($cert.Subject -match "CN=([^,]+)") {
            $subjectName = $matches[1]
        }
        $issuerName = if ($cert.Issuer) { ($cert.Issuer -replace "CN=([^,]+).*", '$1') } else { "Bilinmeyen ESHS" }

        $results += [PSCustomObject]@{
            Sahip            = $subjectName
            VerenKurum       = $issuerName
            BaslangicTarihi  = $cert.NotBefore.ToString("yyyy-MM-dd")
            BitisTarihi      = $cert.NotAfter.ToString("yyyy-MM-dd")
            KalanGun         = $daysLeft
            Durum            = $status
            Thumbprint       = $cert.Thumbprint
        }
    }
}

if ($OnlyExpiring) {
    $results = @($results | Where-Object { $_.Durum -ne "NORMAL" })
}

if ($ExportPath) {
    try {
        if ($ExportPath -like "*.csv") {
            $results | Export-Csv -Path $ExportPath -NoTypeInformation -Encoding UTF8
        } else {
            $results | ConvertTo-Json -Depth 3 | Set-Content -Path $ExportPath -Encoding UTF8
        }
        Write-Host "[OK] Sertifika raporu dosyaya aktarıldı: $ExportPath" -ForegroundColor Green
    } catch {
        Write-Host "[HATA] Dışa aktarma başarısız: $_" -ForegroundColor Red
    }
}

if ($AsJson) {
    $results | ConvertTo-Json -Depth 3
    if ($FailOnCritical -and ($results | Where-Object { $_.Durum -in "KRITIK_TEHLIKE", "SURESI_DOLMUS" })) {
        exit 1
    }
    exit 0
}

Write-Host "==========================================================================================" -ForegroundColor Cyan
Write-Host "         MALİ MÜHÜR & E-İMZA BİTİŞ SÜRESİ DENETLEME ARACI v1.1                            " -ForegroundColor Yellow
Write-Host "==========================================================================================" -ForegroundColor Cyan
Write-Host "Tarih: $($now.ToString('dd.MM.yyyy HH:mm')) | Uyarı Eşiği: $AlertDays Gün`n" -ForegroundColor Gray

if ($results.Count -eq 0) {
    Write-Host "[!] Eşleşen E-İmza / Mali Mühür sertifikası bulunamadı." -ForegroundColor Yellow
    Write-Host "    İpucu: USB Token takılıysa AKİS veya kart okuyucu sürücüsünün açık olduğunu kontrol edin." -ForegroundColor DarkGray
    Write-Host "`nRehber: https://mali-muhur-merkezi.pages.dev/yazilar/mali-muhur-ve-e-imza-arasindaki-farklar.html" -ForegroundColor Cyan
    exit 0
}

Write-Host ("{0,-35} | {1,-20} | {2,-10} | {3,9} | {4}" -f "SERTİFİKA SAHİBİ / ŞİRKET", "VEREN KURUM", "BİTİŞ", "KALAN GÜN", "DURUM") -ForegroundColor White
Write-Host ("-" * 90) -ForegroundColor Gray

$hasCritical = $false
foreach ($r in $results) {
    $color = "Green"
    $durumMetin = "🟢 Güvenli"

    if ($r.Durum -eq "SURESI_DOLMUS") {
        $color = "Red"
        $durumMetin = "❌ SÜRESİ DOLMUŞ!"
        $hasCritical = $true
    } elseif ($r.Durum -eq "KRITIK_TEHLIKE") {
        $color = "Red"
        $durumMetin = "🚨 ACİL YENİLEME GEREKİYOR!"
        $hasCritical = $true
    } elseif ($r.Durum -eq "YAKLASIYOR") {
        $color = "Yellow"
        $durumMetin = "⚠️  Yaklaşıyor (Hazırlık yapın)"
    }

    $rawName = if ($r.Sahip) { $r.Sahip } else { "N/A" }
    $rawIssuer = if ($r.VerenKurum) { $r.VerenKurum } else { "N/A" }

    $dispName = if ($rawName.Length -gt 33) { $rawName.Substring(0, 30) + "..." } else { $rawName }
    $dispIssuer = if ($rawIssuer.Length -gt 18) { $rawIssuer.Substring(0, 15) + "..." } else { $rawIssuer }

    Write-Host ("{0,-35} | {1,-20} | {2,-10} | {3,9} | " -f $dispName, $dispIssuer, $r.BitisTarihi, $r.KalanGun) -NoNewline -ForegroundColor White
    Write-Host $durumMetin -ForegroundColor $color
}

Write-Host "`n------------------------------------------------------------------------------------------" -ForegroundColor Gray
Write-Host "💡 ÖNEMLİ TAVSİYE: Mali mühür yenileme başvuruları TÜBİTAK Kamu SM tarafından ortalama" -ForegroundColor Yellow
Write-Host "   3-7 iş gününde kargolanır. Son 30 güne girmeden önce başvurunuzu tamamlayın." -ForegroundColor Yellow
Write-Host "   Detaylı Kriz Rehberi: https://mali-muhur-merkezi.pages.dev/yazilar/mali-muhur-arizalandi-kayboldu-ne-yapilmali.html" -ForegroundColor Cyan
Write-Host "==========================================================================================`n" -ForegroundColor Cyan

if ($FailOnCritical -and $hasCritical) {
    exit 1
}

