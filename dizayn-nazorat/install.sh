#!/usr/bin/env bash
# =====================================================================
#  Dizayn Nazorat — avtomatik o'rnatish / yangilash skripti
#  Ubuntu / Debian serverda root sifatida ishga tushiring:
#
#    curl -fsSL https://raw.githubusercontent.com/sunnatillaavazovofficial-jpg/ads/refs/heads/claude/bold-albattani-13sehu/dizayn-nazorat/install.sh | sudo bash
#
#  Qayta ishga tushirilsa — kodni yangilaydi, ma'lumotlar va sozlamalar saqlanadi.
# =====================================================================
set -euo pipefail

REPO="sunnatillaavazovofficial-jpg/ads"
BRANCH="${DN_BRANCH:-claude/bold-albattani-13sehu}"
DIR="${DN_DIR:-/opt/dizayn-nazorat}"

say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✔ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✖ %s\033[0m\n' "$*" >&2; exit 1; }

# Savol berish (skript "curl | bash" orqali ishlaganda ham klaviaturadan o'qiydi)
ask() {
  local __var="$1" __q="$2" __def="${3:-}" __ans=""
  if [ -n "$__def" ]; then
    read -r -p "$__q [$__def]: " __ans </dev/tty || true
  else
    read -r -p "$__q: " __ans </dev/tty || true
  fi
  __ans="$(printf '%s' "${__ans:-$__def}" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  printf -v "$__var" '%s' "$__ans"
}

# .env qiymatlarida muammo tug'diradigan belgilar bo'lmasin
safe_value() { [[ "$1" != *"'"* && "$1" != *'"'* && "$1" != *'\'* && "$1" != *' '* ]]; }

port_busy() { ss -ltnH "( sport = :$1 )" 2>/dev/null | grep -q .; }

[ "$(id -u)" -eq 0 ] || die "Root sifatida ishga tushiring (buyruq oxiriga: | sudo bash)"
command -v apt-get >/dev/null || die "Bu skript faqat Ubuntu/Debian uchun"
[ -r /dev/tty ] || die "Interaktiv terminal topilmadi. Server konsolida ishga tushiring."

printf '\033[1m\n  Dizayn Nazorat — o'"'"'rnatish\n\033[0m\n'

# ---------------------------------------------------------------------
say "1/6  Kerakli dasturlar o'rnatilmoqda"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl ca-certificates tar iproute2 >/dev/null
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh >/dev/null
fi
systemctl enable --now docker >/dev/null 2>&1 || true
docker compose version >/dev/null 2>&1 || apt-get install -y -qq docker-compose-plugin >/dev/null 2>&1 \
  || apt-get install -y -qq docker-compose-v2 >/dev/null 2>&1 || true
docker compose version >/dev/null 2>&1 || die "docker compose o'rnatilmadi"
ok "Docker tayyor: $(docker --version | cut -d, -f1)"

# ---------------------------------------------------------------------
say "2/6  Dastur kodi yuklanmoqda ($BRANCH)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" \
  | tar xz -C "$TMP" --wildcards '*/dizayn-nazorat/*' --strip-components=2
[ -f "$TMP/docker-compose.yml" ] || die "Kod yuklanmadi"
mkdir -p "$DIR"
rm -rf "$DIR/app"
cp -a "$TMP"/. "$DIR"/
cd "$DIR"
ok "Kod: $DIR"

PUBLIC_IP="$(curl -4 -fsS --max-time 8 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"

# ---------------------------------------------------------------------
if [ -f .env ]; then
  say "3/6  Sozlamalar allaqachon bor — yangilash rejimi (.env o'zgarmaydi)"
  MODE="$(cat .dn_mode 2>/dev/null || echo caddy)"
  DOMAIN="$(cat .dn_domain 2>/dev/null || true)"
  ADMIN_USER="(avvalgi)"
  ADMIN_PASS="(avvalgi)"
else
  say "3/6  Sozlamalar (Enter bosilsa — o'tkazib yuboriladi)"
  echo "Bo'sh joy, qo'shtirnoq va \\ belgilarini ishlatmang."
  while :; do
    ask ADMIN_USER "Administrator logini" "admin"
    ADMIN_USER="$(printf '%s' "$ADMIN_USER" | tr '[:upper:]' '[:lower:]')"
    [[ "$ADMIN_USER" =~ ^[a-z0-9_.-]{3,32}$ ]] && break
    warn "Login faqat lotin harflari va raqamlardan iborat bo'lsin (3-32 belgi)"
  done
  while :; do
    ask ADMIN_PASS "Administrator paroli (kamida 8 belgi)"
    if [ "${#ADMIN_PASS}" -lt 8 ]; then warn "Parol juda qisqa"; continue; fi
    safe_value "$ADMIN_PASS" || { warn "Parolda bo'sh joy yoki qo'shtirnoq bo'lmasin"; continue; }
    break
  done
  echo
  echo "Telegram bot tokeni: Telegramda @BotFather -> /newbot (keyin ham qo'shish mumkin)"
  while :; do
    ask BOT_TOKEN "BOT_TOKEN"
    [ -z "$BOT_TOKEN" ] || [[ "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]] && break
    warn "Token ko'rinishi noto'g'ri (masalan 123456:ABC-def...)"
  done
  echo
  echo "Telegram akkauntlar uchun: https://my.telegram.org -> API development tools"
  while :; do
    ask TG_API_ID "TG_API_ID (faqat raqam)"
    [ -z "$TG_API_ID" ] || [[ "$TG_API_ID" =~ ^[0-9]+$ ]] && break
    warn "Faqat raqam kiriting"
  done
  TG_API_HASH=""
  if [ -n "$TG_API_ID" ]; then
    while :; do
      ask TG_API_HASH "TG_API_HASH"
      [[ "$TG_API_HASH" =~ ^[0-9a-fA-F]{32}$ ]] && break
      warn "API hash 32 belgidan iborat bo'ladi"
    done
  fi
  echo
  echo "Domen (masalan crm.firma.uz). Domen yo'q bo'lsa Enter — sayt IP orqali ochiladi."
  echo "Domen bo'lsa, uning A-yozuvi shu serverga ($PUBLIC_IP) qaratilgan bo'lishi kerak."
  while :; do
    ask DOMAIN "Domen"
    DOMAIN="${DOMAIN#http://}"; DOMAIN="${DOMAIN#https://}"; DOMAIN="${DOMAIN%%/*}"
    [ -z "$DOMAIN" ] || [[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] && break
    warn "Domen ko'rinishi noto'g'ri"
  done

  # 80/443 portlari bo'sh bo'lsa — Caddy (HTTPS), aks holda 8000-port
  if port_busy 80 || port_busy 443; then
    MODE="port"
    warn "80/443-portlar band (serverda boshqa veb-server bor). Sayt 8000-portda ochiladi."
  else
    MODE="caddy"
  fi

  if [ -n "$DOMAIN" ] && [ "$MODE" = "caddy" ]; then
    SITE_URL="https://$DOMAIN"; SECURE="true"
  elif [ "$MODE" = "caddy" ]; then
    SITE_URL="http://$PUBLIC_IP"; SECURE="false"
  else
    SITE_URL="http://$PUBLIC_IP:8000"; SECURE="false"
  fi

  SECRET="$(head -c 48 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  umask 077
  cat > .env <<EOF
ADMIN_USERNAME='$ADMIN_USER'
ADMIN_PASSWORD='$ADMIN_PASS'
SITE_URL='$SITE_URL'
SECRET_KEY='$SECRET'
SECURE_COOKIES=$SECURE
BOT_TOKEN='$BOT_TOKEN'
TG_API_ID='$TG_API_ID'
TG_API_HASH='$TG_API_HASH'
TG_MARK_READ=true
MAX_UPLOAD_MB=300
TIMEZONE=Asia/Tashkent
EOF
  umask 022
  echo "$MODE" > .dn_mode
  echo "$DOMAIN" > .dn_domain
  ok "Sozlamalar saqlandi: $DIR/.env"
fi

# ---------------------------------------------------------------------
say "4/6  Veb-server sozlanmoqda"
if [ "$MODE" = "caddy" ]; then
  if [ ! -f Caddyfile ]; then
    if [ -n "$DOMAIN" ]; then SITE_ADDR="$DOMAIN"; else SITE_ADDR=":80"; fi
    cat > Caddyfile <<EOF
$SITE_ADDR {
    encode gzip
    reverse_proxy app:8000
}
EOF
  fi
  cat > docker-compose.override.yml <<'EOF'
services:
  caddy:
    image: caddy:2
    container_name: dizayn-nazorat-caddy
    restart: unless-stopped
    depends_on:
      - app
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./caddy_data:/data
EOF
  ok "Caddy (avtomatik HTTPS) sozlandi"
else
  rm -f docker-compose.override.yml
  sed -i 's/"127.0.0.1:8000:8000"/"8000:8000"/' docker-compose.yml
  ok "Sayt 8000-portda ochiladi"
fi

if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  if [ "$MODE" = "caddy" ]; then ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
  else ufw allow 8000/tcp >/dev/null; fi
  ok "Firewall (ufw) da port ochildi"
fi

# ---------------------------------------------------------------------
say "5/6  Dastur yig'ilmoqda va ishga tushirilmoqda (2-5 daqiqa)"
docker compose up -d --build --remove-orphans

say "6/6  Tekshirilmoqda"
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 || die "Dastur ishga tushmadi. Jurnal: cd $DIR && docker compose logs --tail=80 app"
ok "Dastur ishlayapti"

if [ "$MODE" = "caddy" ] && [ -n "$DOMAIN" ]; then
  URL="https://$DOMAIN"
  RESOLVED="$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk 'NR==1{print $1}' || true)"
  if [ "$RESOLVED" != "$PUBLIC_IP" ]; then
    warn "$DOMAIN hozircha $PUBLIC_IP ga qaratilmagan (topildi: ${RESOLVED:-hech narsa})."
    warn "Domen panelida A-yozuv qo'shing: $DOMAIN -> $PUBLIC_IP. HTTPS sertifikat keyin avtomatik olinadi."
  fi
elif [ "$MODE" = "caddy" ]; then
  URL="http://$PUBLIC_IP"
else
  URL="http://$PUBLIC_IP:8000"
fi

cat <<EOF

=====================================================================
  Dizayn Nazorat o'rnatildi!

  Sayt:    $URL
  Login:   $ADMIN_USER
  Parol:   $ADMIN_PASS

  Fayllar: $DIR   (ma'lumotlar: $DIR/data — zaxiralab turing)

  Foydali buyruqlar:
    Jurnal:      cd $DIR && docker compose logs -f app
    Qayta ishga: cd $DIR && docker compose restart
    Yangilash:   shu o'rnatish buyrug'ini qayta ishga tushiring
    Sozlamalar:  nano $DIR/.env   (keyin: cd $DIR && docker compose up -d)
=====================================================================
EOF
