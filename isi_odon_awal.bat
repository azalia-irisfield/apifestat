@echo off
REM Pengisian awal ODON 07/09/2026 s.d. 25/10/2026 (cukup dijalankan sekali)
cd /d D:\BPS\Latsar\Aktualisasi\apifestat
call .venv\Scripts\activate.bat

echo ===== LANGKAH 1: Klasifikasi ulang kategori dan dampak dengan Gemini =====
set /p ULANG=Jalankan klasifikasi ulang berita berstatus Baru? (Y/N): 
if /i "%ULANG%"=="Y" python manage.py klasifikasi_ulang --dari 07/09/2026 --sampai 25/10/2026

echo.
echo ===== LANGKAH 2: Simulasi pengisian ODON (belum menulis ke sheet) =====
python manage.py isi_odon --dari 07/09/2026 --sampai 25/10/2026 --dry-run

echo.
set /p LANJUT=Tulis hasil di atas ke spreadsheet ODON? (Y/N): 
if /i not "%LANJUT%"=="Y" goto selesai

echo ===== LANGKAH 3: Menulis ke spreadsheet ODON =====
python manage.py isi_odon --dari 07/09/2026 --sampai 25/10/2026

:selesai
pause
