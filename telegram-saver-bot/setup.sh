#!/usr/bin/env bash
# Telegram Saver Bot — bitta buyruq bilan o'rnatish yoki yangilash (Ubuntu/Debian).
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/sunnatillaavazovofficial-jpg/ads/refs/heads/claude/inspiring-shannon-renzbu/telegram-saver-bot/setup.sh)
#
# Skript token va Telegram ID'ni so'raydi, kodni yuklab oladi va botni
# systemd xizmati sifatida ishga tushiradi. Qayta ishga tushirilsa — botni
# yangilaydi va avvalgi sozlamalarni saqlab qoladi.
#
# Qo'shimcha foydalanuvchilarga ruxsat berish (ro'yxat to'liq almashtiriladi):
#   ALLOWED_IDS=111111111,222222222 bash <(curl -fsSL .../setup.sh)
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
ALLOWED_IDS="${ALLOWED_IDS:-}"
ALLOWED_SET=0
[ -n "$ALLOWED_IDS" ] && ALLOWED_SET=1
REUSE_ENV=0

valid_ids() { [[ -z "$1" || "$1" =~ ^[0-9]+([,[:space:]]+[0-9]+)*$ ]]; }
if ! valid_ids "$ALLOWED_IDS"; then
  echo "❌ ALLOWED_IDS noto'g'ri: faqat raqamlar va vergul bo'lishi kerak (masalan 111,222)."
  exit 1
fi

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
  if [ "$ALLOWED_SET" -eq 0 ]; then
    while true; do
      read -r -p "👥 Yana kimlarga ruxsat berasiz? ID'larni vergul bilan yozing (yo'q bo'lsa Enter): " ALLOWED_IDS < /dev/tty
      ALLOWED_IDS="$(printf '%s' "$ALLOWED_IDS" | tr -d '[:space:]')"
      valid_ids "$ALLOWED_IDS" && break
      echo "   Faqat raqamlar va vergul (masalan 111,222)."
    done
  fi
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
  if [ "$ALLOWED_SET" -eq 1 ]; then
    sed -i '/^ALLOWED_IDS=/d' .env
    echo "ALLOWED_IDS=$(printf '%s' "$ALLOWED_IDS" | tr -s ' ' ',')" >> .env
    echo "👥 Ruxsat etilgan qo'shimcha foydalanuvchilar: $ALLOWED_IDS"
  fi
else
  cat > .env <<EOF
BOT_TOKEN=$BOT_TOKEN
OWNER_ID=$OWNER_ID
ALLOWED_IDS=$ALLOWED_IDS
KEEP_DAYS=30
TZ_OFFSET=5
DELETE_TRIGGER_REPLY=1
EOF
fi
chmod 600 .env

bash install.sh
