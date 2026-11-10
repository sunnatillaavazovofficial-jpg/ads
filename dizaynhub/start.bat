@echo off
chcp 65001 >nul
cd /d "%~dp0"
title DizaynHub

if not exist .venv (
  echo [1/3] Virtual muhit yaratilmoqda...
  python -m venv .venv
  if errorlevel 1 (
    echo.
    echo Python topilmadi. https://www.python.org/downloads/ dan o'rnating
    echo va o'rnatishda "Add python.exe to PATH" ni belgilang.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
echo [2/3] Kutubxonalar tekshirilmoqda...
python -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Kutubxonalarni o'rnatib bo'lmadi. Internetni tekshiring.
  pause
  exit /b 1
)

if not exist .env (
  copy .env.example .env >nul
  echo .env fayli yaratildi - uni Bloknotda ochib sozlang.
)

echo [3/3] Sayt ishga tushmoqda: http://127.0.0.1:8000
echo To'xtatish uchun shu oynani yoping yoki Ctrl+C bosing.
python run.py
pause
