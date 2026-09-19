@echo off
chcp 65001 >nul
title Mali Muhur ve E-Imza Bitis Suresi Kontrol Araci
echo ====================================================================
echo  Mali Muhur ve E-Imza Bitis Suresi Taranıyor...
echo ====================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Check-CertificateExpiry.ps1"

echo.
pause
