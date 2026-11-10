"""Sozlamalar: .env faylidan o'qiladi."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "ha", "on")


DATA_DIR = Path(os.getenv("DATA_DIR") or (BASE_DIR / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
TG_SESSION_DIR = DATA_DIR / "tg_sessions"
TG_CACHE_DIR = DATA_DIR / "tg_cache"
TMP_DIR = DATA_DIR / "tmp"
for _d in (DATA_DIR, UPLOAD_DIR, TG_SESSION_DIR, TG_CACHE_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{(DATA_DIR / 'dizaynhub.db').as_posix()}"

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
SITE_NAME = os.getenv("SITE_NAME", "DizaynHub")
# Bot xabarlaridagi havolalar uchun (masalan, https://ish.domen.uz)
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
# Sayt HTTPS (domen) orqali ochilsa — true qiling
COOKIE_SECURE = _bool("COOKIE_SECURE", False)


def _secret_key() -> str:
    env = os.getenv("SECRET_KEY", "").strip()
    if env:
        return env
    path = DATA_DIR / "secret.key"
    if path.exists():
        return path.read_text().strip()
    key = secrets.token_urlsafe(48)
    path.write_text(key)
    return key


SECRET_KEY = _secret_key()

# Ro'yxatdan o'tish kalitlari (birinchi ishga tushirishda bazaga yoziladi,
# keyin admin panelidan o'zgartiriladi). Bo'sh bo'lsa tasodifiy yaratiladi.
INITIAL_KEYS = {
    "admin": os.getenv("ADMIN_KEY", "").strip(),
    "manager": os.getenv("MANAGER_KEY", "").strip(),
    "chief": os.getenv("CHIEF_KEY", "").strip(),
    "designer": os.getenv("DESIGNER_KEY", "").strip(),
}

# Telegram (my.telegram.org -> API development tools)
TG_API_ID = int(os.getenv("TG_API_ID", "0") or 0)
TG_API_HASH = os.getenv("TG_API_HASH", "").strip()
# BotFather'dan olingan token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

TELEGRAM_ENABLED = bool(TG_API_ID and TG_API_HASH)
BOT_ENABLED = TELEGRAM_ENABLED and bool(BOT_TOKEN)

# Telegramdan yuklab olinadigan media uchun chegara (MB)
TG_MEDIA_MAX_MB = int(os.getenv("TG_MEDIA_MAX_MB", "50"))
