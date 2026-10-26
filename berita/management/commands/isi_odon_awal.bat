@echo off
REM Pengisian awal ODON 07/09/2026 s.d. 25/10/2026 (cukup dijalankan sekali)
cd /d D:\BPS\Latsar\Aktualisasi\apifestat
call .venv\Scripts\activate.bat

echo ===== SIMULASI (belum menulis ke sheet) =====
python manage.py isi_odon --dari 07/09/2026 --sampai 25/10/2026 --dry-run

echo.
set /p LANJUT=Tulis hasil di atas ke spreadsheet ODON? (Y/N): 
if /i not "%LANJUT%"=="Y" goto selesai

python manage.py isi_odon --dari 07/09/2026 --sampai 25/10/2026

:selesai
pause
