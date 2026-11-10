#!/usr/bin/env bash
# DizaynHub — Linux / macOS uchun ishga tushirish
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "[1/3] Virtual muhit yaratilmoqda..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "[2/3] Kutubxonalar tekshirilmoqda..."
python -m pip install -q --disable-pip-version-check -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env fayli yaratildi — uni tahrirlab sozlang."
fi

echo "[3/3] Sayt ishga tushmoqda..."
exec python run.py
