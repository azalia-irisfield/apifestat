@echo off
cd /d D:\BPS\Latsar\Aktualisasi\apifestat
call .venv\Scripts\activate.bat
python manage.py tugas_harian >> log\harian.log 2>&1