#!/usr/bin/env bash
# Ubuntu/Debian serverga o'rnatish (systemd). Ishlatish:  sudo bash install.sh
set -euo pipefail

APP_DIR=/opt/telegram-saver-bot
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "❌ .env fayli topilmadi. Avval:  cp .env.example .env  va uni to'ldiring."
  exit 1
fi

apt-get update -y
apt-get install -y python3 python3-venv

mkdir -p "$APP_DIR/data"
cp bot.py requirements.txt .env "$APP_DIR/"
chmod 600 "$APP_DIR/.env"

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

cp saver-bot.service /etc/systemd/system/saver-bot.service
systemctl daemon-reload
systemctl enable saver-bot
systemctl restart saver-bot

echo "✅ Bot o'rnatildi va ishga tushdi."
echo "   Holat:  systemctl status saver-bot"
echo "   Loglar: journalctl -u saver-bot -f"
