@echo off
title GameSense AI Launcher
color 0A

echo.
echo  ============================================
echo   GameSense AI - Starting...
echo  ============================================
echo.
echo  PERHATIAN:
echo  Pastikan Docker Desktop sudah dibuka dan
echo  sudah dalam kondisi RUNNING (ikon Docker
echo  di taskbar tidak loading) sebelum lanjut!
echo.
echo  Jika Docker belum jalan, tekan CTRL+C
echo  untuk batalkan, buka Docker Desktop dulu,
echo  tunggu sampai ready, lalu jalankan lagi.
echo.
pause

:: Pindah ke folder project
cd /d C:\Users\Rafli\Desktop\GameSense-ai

:: Cek Docker sudah jalan
echo [1/4] Mengecek Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Docker belum jalan!
    echo  Buka Docker Desktop dulu, tunggu sampai ready,
    echo  lalu jalankan start.bat lagi.
    echo.
    pause
    exit
)
echo       Docker OK!

:: Jalankan docker-compose
echo [2/4] Menjalankan PostgreSQL + Redis + Ollama...
docker-compose up -d
echo       Menunggu PostgreSQL siap (10 detik)...
timeout /t 10 /nobreak >nul
echo       Services OK!

:: Jalankan FastAPI di terminal baru
echo [3/4] Menjalankan FastAPI backend...
start "GameSense API" cmd /k "cd /d C:\Users\Rafli\Desktop\GameSense-ai && venv\Scripts\activate && uvicorn app.main:app --reload"

:: Tunggu FastAPI siap
echo       Menunggu FastAPI siap (5 detik)...
timeout /t 5 /nobreak >nul

:: Jalankan Streamlit di terminal baru
echo [4/4] Menjalankan Streamlit portal...
start "GameSense Portal" cmd /k "cd /d C:\Users\Rafli\Desktop\GameSense-ai && venv\Scripts\activate && streamlit run portal/app.py"

:: Tunggu Streamlit siap
echo       Menunggu Streamlit siap (5 detik)...
timeout /t 5 /nobreak >nul

:: Buka browser
echo.
echo  ============================================
echo   Semua service sudah jalan!
echo   API     : http://localhost:8000
echo   Docs    : http://localhost:8000/docs
echo   Portal  : http://localhost:8501
echo  ============================================
echo.
start http://localhost:8501

echo  Tekan tombol apapun untuk menutup launcher...
pause >nul