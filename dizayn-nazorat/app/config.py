"""Sozlamalar (.env fayldan yoki muhit o'zgaruvchilaridan o'qiladi)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on", "ha"}


DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
TG_MEDIA_DIR = DATA_DIR / "tg_media"
TMP_DIR = DATA_DIR / "tmp"
for _d in (DATA_DIR, UPLOAD_DIR, TG_MEDIA_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DATA_DIR / 'app.db'}")

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    # Kalit berilmagan bo'lsa, data papkasida bir marta yaratib saqlab qo'yamiz.
    _key_file = DATA_DIR / ".secret_key"
    if _key_file.exists():
        SECRET_KEY = _key_file.read_text().strip()
    else:
        import secrets

        SECRET_KEY = secrets.token_urlsafe(48)
        _key_file.write_text(SECRET_KEY)

# Birinchi ishga tushirishda yaratiladigan admin
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Saytning tashqi manzili (bot xabarlaridagi havolalar uchun), masalan https://crm.example.uz
SITE_URL = os.getenv("SITE_URL", "").rstrip("/")

# Telegram bot (@BotFather dan olinadi)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Telegram akkauntlarni ulash uchun (https://my.telegram.org -> API development tools)
TG_API_ID = int(os.getenv("TG_API_ID", "0") or 0)
TG_API_HASH = os.getenv("TG_API_HASH", "").strip()
# Saytda chat ochilganda Telegramda ham "o'qildi" deb belgilansinmi
TG_MARK_READ = _bool("TG_MARK_READ", True)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "300"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
CURRENCY = os.getenv("CURRENCY", "so'm")
# HTTPS orqali ishlaganda cookie faqat https da yuborilsin
SECURE_COOKIES = _bool("SECURE_COOKIES", False)
