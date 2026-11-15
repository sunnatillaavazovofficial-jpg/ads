#!/usr/bin/env bash
# Telegram Saver Bot — bitta buyruq bilan o'rnatish yoki yangilash (Ubuntu/Debian).
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/sunnatillaavazovofficial-jpg/ads/refs/heads/claude/inspiring-shannon-renzbu/telegram-saver-bot/setup.sh)
#
# Skript token va Telegram ID'ni so'raydi, kodni yuklab oladi va botni
# systemd xizmati sifatida ishga tushiradi. Qayta ishga tushirilsa — botni
# yangilaydi va avvalgi sozlamalarni saqlab qoladi.
set -euo pipefail

REPO_URL="https://github.com/sunnatillaavazovofficial-jpg/ads.git"
BRANCH="claude/inspiring-shannon-renzbu"
SRC_DIR="/opt/telegram-saver-bot-src"
APP_ENV="/opt/telegram-saver-bot/.env"

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ Skriptni root sifatida ishga tushiring (oldiga sudo qo'shing)."
  exit 1
fi

ask() {
  local value=""
  while [ -z "$value" ]; do
    read -r -p "$1" value < /dev/tty
    value="$(printf '%s' "$value" | tr -d '[:space:]')"
  done
  printf '%s' "$value"
}

BOT_TOKEN="${BOT_TOKEN:-}"
OWNER_ID="${OWNER_ID:-}"
REUSE_ENV=0

if [ -z "$BOT_TOKEN" ] && [ -f "$APP_ENV" ]; then
  echo "ℹ️  Avvalgi sozlamalar topildi — bot yangilanadi, token va ID o'zgarmaydi."
  REUSE_ENV=1
else
  [ -n "$BOT_TOKEN" ] || BOT_TOKEN="$(ask '🔑 Bot tokenini kiriting (BotFather bergan): ')"
  until [[ "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{30,}$ ]]; do
    echo "   Token noto'g'ri ko'rinadi (masalan: 123456789:AAH...)."
    BOT_TOKEN="$(ask '🔑 Bot tokenini qayta kiriting: ')"
  done
  [ -n "$OWNER_ID" ] || OWNER_ID="$(ask '🆔 Telegram ID raqamingizni kiriting: ')"
  until [[ "$OWNER_ID" =~ ^[0-9]+$ ]]; do
    echo "   ID faqat raqamlardan iborat bo'lishi kerak."
    OWNER_ID="$(ask '🆔 Telegram ID raqamingizni qayta kiriting: ')"
  done
fi

echo "📦 Kerakli dasturlar o'rnatilmoqda..."
apt-get update -y
apt-get install -y git

echo "⬇️  Bot kodi yuklab olinmoqda..."
if [ -d "$SRC_DIR/.git" ]; then
  git -C "$SRC_DIR" fetch --depth 1 origin "$BRANCH"
  git -C "$SRC_DIR" reset --hard FETCH_HEAD
else
  rm -rf "$SRC_DIR"
  git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$SRC_DIR"
fi

cd "$SRC_DIR/telegram-saver-bot"
if [ "$REUSE_ENV" -eq 1 ]; then
  cp "$APP_ENV" .env
else
  cat > .env <<EOF
BOT_TOKEN=$BOT_TOKEN
OWNER_ID=$OWNER_ID
KEEP_DAYS=30
TZ_OFFSET=5
DELETE_TRIGGER_REPLY=1
EOF
fi
chmod 600 .env

bash install.sh
