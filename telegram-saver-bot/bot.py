"""
Telegram Saver Bot — maxfiy (bir martalik) media, o'chirilgan va tahrirlangan
xabarlarni saqlab qoluvchi bot.

Telegram Business (Chatbotlar) orqali ruxsat berilgan foydalanuvchilar akkauntiga
ulanadi. Har bir foydalanuvchi FAQAT o'zining xabarlarini oladi:
  * maxfiy (bir martalik) rasm/video/ovozga REPLY qilsangiz — uni sizga yuboradi
    (oddiy rasm/videoga reply qilsangiz — hech narsa qilmaydi);
  * suhbatdosh xabarni o'chirsa — o'chirilgan xabarni yuboradi;
  * suhbatdosh xabarni tahrirlasa — eski va yangi matnni yuboradi;
  * chat tozalansa — butun yozishmani (matn + media) siz ulagan guruhga yuboradi.

Foydalanuvchilarga ruxsat berish/olish — faqat bot orqali (admin = OWNER_ID).
"""

from __future__ import annotations

import asyncio
import html
import io
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramMigrateToChat,
    TelegramRetryAfter,
)
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BufferedInputFile,
    BusinessConnection,
    BusinessMessagesDeleted,
    CallbackQuery,
    Chat,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    KeyboardButton,
    KeyboardButtonRequestUsers,
    Message,
    ReplyKeyboardMarkup,
)

try:  # .env faylini o'qish (ixtiyoriy)
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:  # pragma: no cover
    pass


# --------------------------------------------------------------------------- #
# Sozlamalar
# --------------------------------------------------------------------------- #
def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "ha"}


def _env_ids(name: str) -> set[int]:
    raw = os.getenv(name, "")
    return {int(x) for x in re.split(r"[\s,;]+", raw) if x.strip().isdigit()}


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
# Admin: foydalanuvchilarga ruxsat beradi/oladi
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
# Birinchi ishga tushishda bazaga qo'shiladigan foydalanuvchilar (keyin — bot orqali)
SEED_IDS = _env_ids("ALLOWED_IDS")
DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).with_name("data") / "messages.db"))
KEEP_DAYS = int(os.getenv("KEEP_DAYS", "30"))
TZ = timezone(timedelta(hours=float(os.getenv("TZ_OFFSET", "5"))))  # Toshkent: UTC+5
# Maxfiy mediani saqlash uchun yozilgan reply xabarni chatdan o'chirish
# (Business sozlamalarida "Barcha xabarlarni o'chirish" ruxsati kerak)
DELETE_TRIGGER_REPLY = _env_bool("DELETE_TRIGGER_REPLY", True)
# Bir vaqtda shuncha va undan ko'p xabar o'chirilsa — "chat tozalandi" deb hisoblanadi
CLEAR_MIN = int(os.getenv("CLEAR_MIN", "5"))
# O'chirish hodisalarini yig'ish uchun kutish vaqti (soniya)
CLEAR_DEBOUNCE = float(os.getenv("CLEAR_DEBOUNCE", "3"))
# Guruhga ketma-ket yuborishlar orasidagi pauza (Telegram limiti: ~20 xabar/daqiqa)
SEND_PAUSE = float(os.getenv("SEND_PAUSE", "1.5"))
# Bir xil odamdan ruxsat so'rovi necha soatda bir marta adminga yuboriladi
REQUEST_COOLDOWN_H = 6

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("saver-bot")

MEDIA_KINDS = (
    "photo",
    "video",
    "video_note",
    "voice",
    "audio",
    "animation",
    "document",
    "sticker",
)
KIND_LABELS = {
    "photo": "🖼 Rasm",
    "video": "🎬 Video",
    "video_note": "⭕️ Dumaloq video",
    "voice": "🎤 Ovozli xabar",
    "audio": "🎵 Audio",
    "animation": "🎞 GIF",
    "document": "📄 Fayl",
    "sticker": "🔖 Stiker",
    "text": "💬 Matn",
}
FILE_EXT = {
    "photo": "jpg",
    "video": "mp4",
    "video_note": "mp4",
    "voice": "ogg",
    "audio": "mp3",
    "animation": "mp4",
    "document": "bin",
    "sticker": "webp",
}
NO_CAPTION_KINDS = {"video_note", "sticker"}
# Albom (media group) ichida birga yuborilishi mumkin bo'lgan turlar
ALBUM_GROUP = {"photo": "visual", "video": "visual", "document": "document", "audio": "audio"}
INPUT_MEDIA = {
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
    "document": InputMediaDocument,
    "audio": InputMediaAudio,
}


# --------------------------------------------------------------------------- #
# Ma'lumotlar bazasi (SQLite)
# --------------------------------------------------------------------------- #
MESSAGES_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    owner_id     INTEGER NOT NULL,
    chat_id      INTEGER NOT NULL,
    message_id   INTEGER NOT NULL,
    conn_id      TEXT,
    sender_id    INTEGER,
    sender_name  TEXT,
    chat_name    TEXT,
    kind         TEXT,
    file_id      TEXT,
    text         TEXT,
    date         INTEGER,
    saved_at     INTEGER,
    is_out       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (owner_id, chat_id, message_id)
);
"""


class Storage:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS connections (
                conn_id    TEXT PRIMARY KEY,
                user_id    INTEGER,
                is_enabled INTEGER,
                rights     TEXT
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                status       TEXT NOT NULL DEFAULT 'none',
                name         TEXT,
                username     TEXT,
                group_id     INTEGER,
                group_title  TEXT,
                added_at     INTEGER,
                requested_at INTEGER
            );
            """
        )
        self._migrate_messages()
        self.db.executescript(MESSAGES_SCHEMA)
        self.db.commit()

    def _migrate_messages(self) -> None:
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(messages)")}
        if not cols:
            return
        if "owner_id" not in cols:
            # 1-versiya (bitta foydalanuvchi) → ko'p foydalanuvchili jadval
            log.info("Baza yangi formatga o'tkazilmoqda (v1 → v3)...")
            self.db.execute("ALTER TABLE messages RENAME TO messages_old")
            self.db.executescript(MESSAGES_SCHEMA)
            self.db.execute(
                """
                INSERT OR IGNORE INTO messages
                    (owner_id, chat_id, message_id, conn_id, sender_id, sender_name,
                     chat_name, kind, file_id, text, date, saved_at)
                SELECT COALESCE(
                           (SELECT c.user_id FROM connections c WHERE c.conn_id = m.conn_id), ?
                       ),
                       chat_id, message_id, conn_id, sender_id, sender_name,
                       chat_name, kind, file_id, text, date, saved_at
                FROM messages_old m
                """,
                (OWNER_ID,),
            )
            self.db.execute("DROP TABLE messages_old")
        elif "is_out" not in cols:
            # 2-versiya → 3-versiya: chiquvchi xabarlar belgisi
            log.info("Baza yangi formatga o'tkazilmoqda (v2 → v3)...")
            self.db.execute(
                "ALTER TABLE messages ADD COLUMN is_out INTEGER NOT NULL DEFAULT 0"
            )
        self.db.commit()

    # --- xabarlar ---------------------------------------------------------- #
    def save_message(self, owner_id: int, msg: Message, is_out: bool) -> None:
        kind, file_id = extract_media(msg)
        self.db.execute(
            """
            INSERT OR REPLACE INTO messages
                (owner_id, chat_id, message_id, conn_id, sender_id, sender_name,
                 chat_name, kind, file_id, text, date, saved_at, is_out)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                msg.chat.id,
                msg.message_id,
                msg.business_connection_id,
                msg.from_user.id if msg.from_user else None,
                user_name(msg),
                chat_name(msg),
                kind,
                file_id,
                msg.text or msg.caption or "",
                int(msg.date.timestamp()) if msg.date else int(time.time()),
                int(time.time()),
                int(is_out),
            ),
        )
        self.db.commit()

    def get_message(self, owner_id: int, chat_id: int, message_id: int) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM messages WHERE owner_id = ? AND chat_id = ? AND message_id = ?",
            (owner_id, chat_id, message_id),
        ).fetchone()

    def get_messages(self, owner_id: int, chat_id: int, ids: list[int]) -> list[sqlite3.Row]:
        rows: list[sqlite3.Row] = []
        for i in range(0, len(ids), 500):
            part = ids[i : i + 500]
            marks = ",".join("?" * len(part))
            rows += self.db.execute(
                f"SELECT * FROM messages WHERE owner_id = ? AND chat_id = ? "
                f"AND message_id IN ({marks})",
                (owner_id, chat_id, *part),
            ).fetchall()
        rows.sort(key=lambda r: (r["date"] or 0, r["message_id"]))
        return rows

    def count_chat(self, owner_id: int, chat_id: int) -> int:
        return self.db.execute(
            "SELECT COUNT(*) FROM messages WHERE owner_id = ? AND chat_id = ?",
            (owner_id, chat_id),
        ).fetchone()[0]

    def delete_messages(self, owner_id: int, chat_id: int, ids: list[int]) -> None:
        self.db.executemany(
            "DELETE FROM messages WHERE owner_id = ? AND chat_id = ? AND message_id = ?",
            [(owner_id, chat_id, mid) for mid in ids],
        )
        self.db.commit()

    def cleanup(self, keep_days: int) -> int:
        border = int(time.time()) - keep_days * 86400
        cur = self.db.execute("DELETE FROM messages WHERE saved_at < ?", (border,))
        self.db.commit()
        return cur.rowcount

    def count(self, owner_id: int | None = None) -> int:
        if owner_id is None:
            return self.db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        return self.db.execute(
            "SELECT COUNT(*) FROM messages WHERE owner_id = ?", (owner_id,)
        ).fetchone()[0]

    # --- business ulanishlar ----------------------------------------------- #
    def save_connection(self, conn: BusinessConnection) -> None:
        rights = conn.rights.model_dump(exclude_none=True) if conn.rights else {}
        self.db.execute(
            "INSERT OR REPLACE INTO connections (conn_id, user_id, is_enabled, rights) "
            "VALUES (?, ?, ?, ?)",
            (conn.id, conn.user.id, int(conn.is_enabled), json.dumps(rights)),
        )
        self.db.commit()

    def connection_user(self, conn_id: str) -> int | None:
        row = self.db.execute(
            "SELECT user_id FROM connections WHERE conn_id = ?", (conn_id,)
        ).fetchone()
        return row[0] if row else None

    def is_connected(self, user_id: int) -> bool:
        row = self.db.execute(
            "SELECT MAX(is_enabled) FROM connections WHERE user_id = ?", (user_id,)
        ).fetchone()
        return bool(row and row[0])

    # --- foydalanuvchilar -------------------------------------------------- #
    def seed_users(self, ids: set[int]) -> None:
        now = int(time.time())
        for uid in ids:
            # Agar admin avval bot orqali o'chirgan bo'lsa — qayta qo'shilmaydi
            self.db.execute(
                "INSERT OR IGNORE INTO users (user_id, status, added_at) VALUES (?, 'allowed', ?)",
                (uid, now),
            )
        if OWNER_ID:
            self.set_status(OWNER_ID, "allowed")
        self.db.commit()

    def touch_user(self, user_id: int, name: str | None, username: str | None) -> None:
        self.db.execute(
            """
            INSERT INTO users (user_id, name, username) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = COALESCE(excluded.name, users.name),
                username = COALESCE(excluded.username, users.username)
            """,
            (user_id, name, username),
        )
        self.db.commit()

    def set_status(self, user_id: int, status: str) -> None:
        self.db.execute(
            """
            INSERT INTO users (user_id, status, added_at) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET status = excluded.status,
                added_at = CASE WHEN excluded.status = 'allowed'
                                THEN excluded.added_at ELSE users.added_at END
            """,
            (user_id, status, int(time.time())),
        )
        self.db.commit()

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def allowed_ids(self) -> set[int]:
        return {
            r[0] for r in self.db.execute("SELECT user_id FROM users WHERE status = 'allowed'")
        }

    def list_allowed(self) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT * FROM users WHERE status = 'allowed' "
            "ORDER BY user_id != ?, added_at",
            (OWNER_ID,),
        ).fetchall()

    def should_notify_request(self, user_id: int) -> bool:
        row = self.get_user(user_id)
        now = int(time.time())
        if row and row["requested_at"] and now - row["requested_at"] < REQUEST_COOLDOWN_H * 3600:
            return False
        self.db.execute("UPDATE users SET requested_at = ? WHERE user_id = ?", (now, user_id))
        self.db.commit()
        return True

    # --- guruhlar ----------------------------------------------------------- #
    def set_group(self, user_id: int, group_id: int | None, title: str | None) -> None:
        self.db.execute(
            "UPDATE users SET group_id = ?, group_title = ? WHERE user_id = ?",
            (group_id, title, user_id),
        )
        self.db.commit()

    def users_of_group(self, group_id: int) -> list[int]:
        return [
            r[0] for r in self.db.execute("SELECT user_id FROM users WHERE group_id = ?", (group_id,))
        ]

    def unlink_group(self, group_id: int) -> list[int]:
        uids = self.users_of_group(group_id)
        self.db.execute(
            "UPDATE users SET group_id = NULL, group_title = NULL WHERE group_id = ?", (group_id,)
        )
        self.db.commit()
        return uids

    def migrate_group(self, old_id: int, new_id: int) -> None:
        self.db.execute("UPDATE users SET group_id = ? WHERE group_id = ?", (new_id, old_id))
        self.db.commit()


# --------------------------------------------------------------------------- #
# Yordamchi funksiyalar
# --------------------------------------------------------------------------- #
storage: Storage  # main() ichida yaratiladi
_allowed: set[int] = set()
_conn_cache: dict[str, int] = {}


def refresh_allowed() -> None:
    global _allowed
    _allowed = storage.allowed_ids() | ({OWNER_ID} if OWNER_ID else set())


def is_allowed(user_id: int | None) -> bool:
    return user_id is not None and (user_id == OWNER_ID or user_id in _allowed)


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id == OWNER_ID


def extract_media(msg: Message) -> tuple[str, str | None]:
    """Xabardagi media turini va file_id ni qaytaradi."""
    for kind in MEDIA_KINDS:
        value = getattr(msg, kind, None)
        if not value:
            continue
        if kind == "photo":
            return kind, value[-1].file_id  # eng katta o'lcham
        return kind, value.file_id
    return "text", None


def user_name(msg: Message) -> str:
    u = msg.from_user
    if not u:
        return msg.chat.full_name or "Noma'lum"
    name = u.full_name
    if u.username:
        name += f" (@{u.username})"
    return name


def chat_name(msg: Message) -> str:
    return chat_label(msg.chat)


def chat_label(c: Chat) -> str:
    name = c.full_name or c.title or str(c.id)
    if c.username:
        name += f" (@{c.username})"
    return name


def person_label(user_id: int) -> str:
    row = storage.get_user(user_id)
    name = (row["name"] if row else None) or f"ID {user_id}"
    if row and row["username"]:
        name += f" (@{row['username']})"
    return name


def esc(text: str | None) -> str:
    return html.escape(text or "")


def cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def fmt_time(ts: int | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, TZ).strftime("%d.%m.%Y %H:%M")


async def call(func, *args, **kwargs):
    """Telegram "juda tez" (RetryAfter) desa — kutib, qayta urinadi."""
    for _ in range(5):
        try:
            return await func(*args, **kwargs)
        except TelegramRetryAfter as e:
            log.info("Telegram limit: %s s kutamiz", e.retry_after)
            await asyncio.sleep(e.retry_after + 1)
    return await func(*args, **kwargs)


async def send_media(
    bot: Bot, to: int, kind: str, file_id: str, caption: str, prefer_download: bool = False
) -> bool:
    """
    Mediani yuboradi. Avval file_id orqali (yoki teskari tartibda),
    bo'lmasa faylni yuklab olib, qayta yuklash orqali yuboradi.
    """
    caption = cut(caption, 1024)

    async def by_file_id() -> None:
        await _send(bot, to, kind, file_id, caption)

    async def by_download() -> None:
        buf = io.BytesIO()
        await bot.download(file_id, destination=buf)
        data = buf.getvalue()
        if not data:
            raise RuntimeError("bo'sh fayl")
        upload = BufferedInputFile(data, filename=f"{kind}.{FILE_EXT.get(kind, 'bin')}")
        await _send(bot, to, kind, upload, caption)

    attempts = (by_download, by_file_id) if prefer_download else (by_file_id, by_download)
    for attempt in attempts:
        try:
            await attempt()
            return True
        except TelegramMigrateToChat:
            raise
        except (TelegramAPIError, RuntimeError) as e:
            log.warning("Media yuborishda xato (%s, %s): %s", kind, attempt.__name__, e)
    return False


async def _send(bot: Bot, to: int, kind: str, media, caption: str) -> None:
    if kind in NO_CAPTION_KINDS:
        # Dumaloq video va stikerga izoh qo'shib bo'lmaydi — alohida yuboramiz
        await call(bot.send_message, to, caption)
        method = bot.send_video_note if kind == "video_note" else bot.send_sticker
        await call(method, to, media)
        return
    method = {
        "photo": bot.send_photo,
        "video": bot.send_video,
        "voice": bot.send_voice,
        "audio": bot.send_audio,
        "animation": bot.send_animation,
        "document": bot.send_document,
    }[kind]
    await call(method, to, media, caption=caption)


async def try_send(bot: Bot, to: int, text: str, **kwargs) -> bool:
    try:
        await call(bot.send_message, to, text, **kwargs)
        return True
    except TelegramAPIError as e:
        log.info("Xabar yuborilmadi (%s): %s", to, e)
        return False


# --------------------------------------------------------------------------- #
# Klaviaturalar va matnlar
# --------------------------------------------------------------------------- #
BTN_ADD = "➕ Odam qo'shish"
BTN_USERS = "👥 Foydalanuvchilar"
BTN_STATS = "📊 Statistika"
BTN_GROUP = "🗂 Guruh"
BTN_HELP = "ℹ️ Yordam"


def main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    if is_admin(user_id):
        rows.append(
            [
                KeyboardButton(
                    text=BTN_ADD,
                    request_users=KeyboardButtonRequestUsers(
                        request_id=1,
                        user_is_bot=False,
                        max_quantity=10,
                        request_name=True,
                        request_username=True,
                    ),
                )
            ]
        )
        rows.append([KeyboardButton(text=BTN_USERS), KeyboardButton(text=BTN_STATS)])
    else:
        rows.append([KeyboardButton(text=BTN_STATS)])
    rows.append([KeyboardButton(text=BTN_GROUP), KeyboardButton(text=BTN_HELP)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


HELP_TEXT = (
    "👋 <b>Saver Bot</b>\n\n"
    "<b>Ulash:</b>\n"
    "1. Telegram → <i>Sozlamalar → Telegram Business → Chatbotlar</i>\n"
    "2. Shu botning @username ini kiriting\n"
    "3. «Barcha shaxsiy chatlar»ga ruxsat bering\n"
    "4. Ruxsatlardan <i>«Xabarlarni o'qish»</i> va (ixtiyoriy) "
    "<i>«Barcha xabarlarni o'chirish»</i>ni yoqing\n\n"
    "<b>Nima qiladi:</b>\n"
    "🔥 <b>Maxfiy (bir martalik) rasm/video/ovoz</b> — ochmasdan oldin unga istalgan "
    "xabar bilan <b>reply</b> qiling (masalan «.»). Bot uni shu yerga yuboradi. "
    "Oddiy rasm/videoga reply qilsangiz — bot hech narsa qilmaydi.\n"
    "🗑 <b>O'chirilgan xabar</b> — suhbatdosh o'chirsa, shu yerga keladi.\n"
    "✏️ <b>Tahrirlangan xabar</b> — eski va yangi matn shu yerga keladi.\n"
    "🧹 <b>Chat tozalansa</b> — butun yozishma (matn + rasmlar) guruhingizga yuboriladi. "
    f"Guruhni ulash uchun «{BTN_GROUP}» tugmasini bosing."
)
ADMIN_HELP = (
    "\n\n👑 <b>Admin:</b>\n"
    f"• «{BTN_ADD}» — kontaktlardan odam tanlab ruxsat berish\n"
    "• Yoki odamning ID raqamini shunchaki yozib yuboring\n"
    f"• «{BTN_USERS}» — ro'yxat va ruxsatni olib tashlash\n"
    "• Ruxsatsiz odam botga /start yozsa — sizga so'rov keladi"
)
GROUP_HELP = (
    "🗂 <b>Guruhni ulash</b> (chat tozalanganda yozishma shu guruhga tushadi):\n"
    "1. Telegram'da yangi guruh yarating (yoki mavjudini oching)\n"
    "2. Guruhga shu botni qo'shing — bot o'zi ulanadi\n"
    "   (yoki guruhda /setgroup yozing)\n\n"
    "Guruhni uzish: guruhda /unsetgroup yozing yoki botni guruhdan chiqaring."
)
DENIED_TEXT = "⛔️ Sizga bu botdan foydalanishga ruxsat berilmagan."

PRIVATE = F.chat.type == ChatType.PRIVATE
GROUPS = F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})

router = Router()


# --------------------------------------------------------------------------- #
# Ruxsatlar (faqat bot orqali)
# --------------------------------------------------------------------------- #
async def grant_access(bot: Bot, user_id: int) -> bool:
    """Ruxsat beradi. Foydalanuvchiga xabar yetib borganini qaytaradi."""
    storage.set_status(user_id, "allowed")
    refresh_allowed()
    return await try_send(
        bot,
        user_id,
        "✅ <b>Sizga botdan foydalanishga ruxsat berildi!</b>\n\n" + HELP_TEXT,
        reply_markup=main_keyboard(user_id),
    )


async def revoke_access(bot: Bot, user_id: int) -> None:
    storage.set_status(user_id, "removed")
    refresh_allowed()
    await try_send(bot, user_id, "❌ Botdan foydalanish ruxsatingiz bekor qilindi.")


async def request_access(bot: Bot, user_id: int, name: str, username: str | None) -> None:
    if not OWNER_ID or not storage.should_notify_request(user_id):
        return
    label = esc(name) + (f" (@{esc(username)})" if username else "")
    await try_send(
        bot,
        OWNER_ID,
        f"🙋 <b>Ruxsat so'rovi</b>\n👤 {label}\n🆔 <code>{user_id}</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Ruxsat berish", callback_data=f"acc:ok:{user_id}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"acc:no:{user_id}"),
                ]
            ]
        ),
    )


def users_view() -> tuple[str, InlineKeyboardMarkup | None]:
    rows = storage.list_allowed()
    lines = [f"👥 <b>Ruxsat berilganlar: {len(rows)} ta</b>\n"]
    buttons: list[list[InlineKeyboardButton]] = []
    for i, r in enumerate(rows, 1):
        uid = r["user_id"]
        connected = "🟢 ulangan" if storage.is_connected(uid) else "⚪️ ulanmagan"
        group = f"🗂 {esc(r['group_title'])}" if r["group_id"] else "🗂 guruh yo'q"
        crown = " 👑" if uid == OWNER_ID else ""
        lines.append(
            f"{i}. {esc(person_label(uid))}{crown}\n"
            f"    🆔 <code>{uid}</code> · {connected} · {group}"
        )
        if uid != OWNER_ID:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"❌ {cut(person_label(uid), 30)}", callback_data=f"usr:rm:{uid}"
                    )
                ]
            )
    lines.append("\n➕ Qo'shish: «Odam qo'shish» tugmasi yoki ID raqamni yozib yuboring.")
    markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    return "\n".join(lines), markup


# --------------------------------------------------------------------------- #
# Shaxsiy chat: buyruqlar
# --------------------------------------------------------------------------- #
@router.message(CommandStart(), PRIVATE)
@router.message(Command("help"), PRIVATE)
@router.message(F.text == BTN_HELP, PRIVATE)
async def cmd_start(message: Message, bot: Bot) -> None:
    u = message.from_user
    if u is None:
        return
    storage.touch_user(u.id, u.full_name, u.username)
    if is_allowed(u.id):
        text = HELP_TEXT + (ADMIN_HELP if is_admin(u.id) else "")
        await message.answer(text, reply_markup=main_keyboard(u.id))
        return
    await message.answer(
        f"{DENIED_TEXT}\n🆔 Sizning ID: <code>{u.id}</code>\n\n"
        "📨 So'rovingiz adminga yuborildi. Ruxsat berilsa, sizga xabar keladi."
    )
    await request_access(bot, u.id, u.full_name, u.username)


@router.message(Command("stats"), PRIVATE)
@router.message(F.text == BTN_STATS, PRIVATE)
async def cmd_stats(message: Message) -> None:
    uid = message.from_user.id if message.from_user else None
    if not is_allowed(uid):
        return
    connected = "🟢 ulangan" if storage.is_connected(uid) else "⚪️ ulanmagan (Business → Chatbotlar)"
    text = (
        f"📊 <b>Statistika</b>\n"
        f"🔌 Akkauntingiz: {connected}\n"
        f"📦 Saqlangan xabarlaringiz: <b>{storage.count(uid)}</b>\n"
        f"🕒 Saqlash muddati: {KEEP_DAYS} kun"
    )
    if is_admin(uid):
        users = storage.list_allowed()
        online = sum(1 for r in users if storage.is_connected(r["user_id"]))
        text += (
            f"\n\n👑 <b>Admin</b>\n"
            f"👥 Ruxsat berilganlar: <b>{len(users)}</b> (ulangan: {online})\n"
            f"📦 Jami xabarlar: <b>{storage.count()}</b>"
        )
    await message.answer(text)


@router.message(Command("group"), PRIVATE)
@router.message(F.text == BTN_GROUP, PRIVATE)
async def cmd_group(message: Message) -> None:
    uid = message.from_user.id if message.from_user else None
    if not is_allowed(uid):
        return
    row = storage.get_user(uid)
    if row and row["group_id"]:
        current = f"✅ Ulangan guruh: <b>{esc(row['group_title'])}</b>\n\n"
    else:
        current = "⚠️ Guruh ulanmagan — tozalangan chatlar shu yerga (botga) keladi.\n\n"
    await message.answer(current + GROUP_HELP)


@router.message(Command("users"), PRIVATE)
@router.message(F.text == BTN_USERS, PRIVATE)
async def cmd_users(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    text, markup = users_view()
    await message.answer(text, reply_markup=markup)


@router.message(Command("add"), PRIVATE)
async def cmd_add(message: Message, command: CommandObject, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    ids = [int(x) for x in re.findall(r"\d{5,15}", command.args or "")]
    if not ids:
        await message.answer(f"Ishlatish: <code>/add 123456789</code> yoki «{BTN_ADD}» tugmasi.")
        return
    for uid in ids:
        delivered = await grant_access(bot, uid)
        await message.answer(added_text(uid, delivered))


@router.message(Command("remove"), PRIVATE)
async def cmd_remove(message: Message, command: CommandObject, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    ids = [int(x) for x in re.findall(r"\d{5,15}", command.args or "")]
    if not ids:
        await message.answer("Ishlatish: <code>/remove 123456789</code>")
        return
    for uid in ids:
        if uid == OWNER_ID:
            await message.answer("👑 Adminni o'chirib bo'lmaydi.")
            continue
        await revoke_access(bot, uid)
        await message.answer(f"❌ Ruxsat olib tashlandi: <code>{uid}</code>")


def added_text(uid: int, delivered: bool) -> str:
    text = f"✅ Ruxsat berildi: {esc(person_label(uid))} (<code>{uid}</code>)"
    if not delivered:
        text += (
            "\n\nℹ️ Unga xabar yubora olmadim — u hali botga /start yozmagan. "
            "Botga /start yozib, akkauntini Business orqali ulasin."
        )
    return text


@router.message(F.users_shared, PRIVATE)
async def on_users_shared(message: Message, bot: Bot) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        return
    for shared in message.users_shared.users:
        name = " ".join(x for x in (shared.first_name, shared.last_name) if x) or None
        storage.touch_user(shared.user_id, name, shared.username)
        delivered = await grant_access(bot, shared.user_id)
        await message.answer(added_text(shared.user_id, delivered))


@router.message(F.text.regexp(r"^\s*\d{5,15}\s*$"), PRIVATE)
async def on_admin_id_text(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        if not is_allowed(message.from_user.id if message.from_user else None):
            await message.answer(DENIED_TEXT)
        return
    uid = int(message.text.strip())
    await message.answer(
        f"🆔 <code>{uid}</code> ga botdan foydalanishga ruxsat berilsinmi?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Ha, ruxsat berish", callback_data=f"acc:ok:{uid}"),
                    InlineKeyboardButton(text="Bekor", callback_data="noop"),
                ]
            ]
        ),
    )


@router.message(PRIVATE)
async def other_private(message: Message) -> None:
    uid = message.from_user.id if message.from_user else None
    if not is_allowed(uid):
        await message.answer(f"{DENIED_TEXT}\nRuxsat so'rash uchun /start yozing.")


# --------------------------------------------------------------------------- #
# Inline tugmalar (admin)
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith("acc:") | F.data.startswith("usr:") | (F.data == "noop"))
async def on_admin_callback(cb: CallbackQuery, bot: Bot) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔️ Faqat admin uchun", show_alert=True)
        return
    parts = (cb.data or "").split(":")
    action = ":".join(parts[:2])
    uid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None

    if cb.data == "noop":
        await cb.answer("Bekor qilindi")
        await _safe_edit(cb, "Bekor qilindi.")
        return

    if action == "acc:ok" and uid:
        delivered = await grant_access(bot, uid)
        await cb.answer("✅ Ruxsat berildi")
        await _safe_edit(cb, added_text(uid, delivered))
    elif action == "acc:no" and uid:
        await cb.answer("Rad etildi")
        await _safe_edit(cb, f"❌ Rad etildi: {esc(person_label(uid))} (<code>{uid}</code>)")
        await try_send(bot, uid, "❌ Botdan foydalanish so'rovingiz rad etildi.")
    elif action == "usr:rm" and uid:
        await cb.answer()
        await _safe_edit(
            cb,
            f"⚠️ {esc(person_label(uid))} (<code>{uid}</code>) ning ruxsati olib tashlansinmi?",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="❌ Ha, olib tashlash", callback_data=f"usr:rmok:{uid}"),
                        InlineKeyboardButton(text="↩️ Orqaga", callback_data="usr:list"),
                    ]
                ]
            ),
        )
    elif action == "usr:rmok" and uid:
        if uid == OWNER_ID:
            await cb.answer("👑 Adminni o'chirib bo'lmaydi", show_alert=True)
            return
        await revoke_access(bot, uid)
        await cb.answer("Ruxsat olib tashlandi")
        text, markup = users_view()
        await _safe_edit(cb, text, markup)
    elif action == "usr:list":
        await cb.answer()
        text, markup = users_view()
        await _safe_edit(cb, text, markup)
    else:
        await cb.answer()


async def _safe_edit(cb: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except (TelegramAPIError, AttributeError):
        pass


# --------------------------------------------------------------------------- #
# Guruhlar: tozalangan chatlar shu yerga yuboriladi
# --------------------------------------------------------------------------- #
@router.my_chat_member(GROUPS)
async def on_bot_membership(event: ChatMemberUpdated, bot: Bot) -> None:
    chat = event.chat
    new = event.new_chat_member.status
    old = event.old_chat_member.status
    in_statuses = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR}
    out_statuses = {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}

    if new in in_statuses and old in out_statuses:
        adder = event.from_user
        if not is_allowed(adder.id):
            await try_send(bot, chat.id, "⛔️ Bu botni faqat ruxsat berilgan foydalanuvchilar qo'sha oladi.")
            try:
                await bot.leave_chat(chat.id)
            except TelegramAPIError:
                pass
            return
        await link_group(bot, adder.id, chat)
    elif new in out_statuses:
        for uid in storage.unlink_group(chat.id):
            await try_send(
                bot,
                uid,
                f"⚠️ Bot «{esc(chat.title)}» guruhidan chiqarildi. "
                "Tozalangan chatlar endi shu yerga (botga) keladi.",
            )


async def link_group(bot: Bot, user_id: int, chat: Chat) -> None:
    storage.set_group(user_id, chat.id, chat.title)
    await try_send(
        bot,
        chat.id,
        f"✅ Guruh ulandi: <b>{esc(person_label(user_id))}</b>\n"
        "🧹 Chat tozalansa, butun yozishma shu guruhga yuboriladi.",
    )
    if chat.id != user_id:
        await try_send(bot, user_id, f"✅ «{esc(chat.title)}» guruhi ulandi.")


@router.message(Command("setgroup"), GROUPS)
async def cmd_setgroup(message: Message, bot: Bot) -> None:
    uid = message.from_user.id if message.from_user else None
    if not is_allowed(uid):
        await message.reply(DENIED_TEXT)
        return
    await link_group(bot, uid, message.chat)


@router.message(Command("unsetgroup"), GROUPS)
async def cmd_unsetgroup(message: Message) -> None:
    uid = message.from_user.id if message.from_user else None
    if not is_allowed(uid):
        return
    row = storage.get_user(uid)
    if row and row["group_id"] == message.chat.id:
        storage.set_group(uid, None, None)
        await message.reply("🔌 Guruh uzildi. Tozalangan chatlar endi botga keladi.")
    else:
        await message.reply("Bu guruh sizga ulanmagan.")


@router.message(F.migrate_to_chat_id)
async def on_group_migrated(message: Message) -> None:
    # Guruh superguruhga aylanganda ID o'zgaradi
    storage.migrate_group(message.chat.id, message.migrate_to_chat_id)


# --------------------------------------------------------------------------- #
# Business: xabarlar
# --------------------------------------------------------------------------- #
async def connection_user(bot: Bot, conn_id: str | None) -> int | None:
    """Business ulanish egasining ID si (agar ruxsati bo'lsa), aks holda None."""
    if not conn_id:
        return None
    user_id = _conn_cache.get(conn_id) or storage.connection_user(conn_id)
    if user_id is None:
        try:
            conn = await bot.get_business_connection(conn_id)
            storage.save_connection(conn)
            user_id = conn.user.id
        except TelegramAPIError as e:
            log.warning("Business ulanishni olib bo'lmadi: %s", e)
            return None
    _conn_cache[conn_id] = user_id
    return user_id if is_allowed(user_id) else None


@router.business_connection()
async def on_business_connection(conn: BusinessConnection, bot: Bot) -> None:
    storage.save_connection(conn)
    _conn_cache[conn.id] = conn.user.id
    user = conn.user
    storage.touch_user(user.id, user.full_name, user.username)

    if not is_allowed(user.id):
        log.warning("Ruxsatsiz foydalanuvchi ulanishga urindi: %s", user.id)
        await try_send(
            bot,
            conn.user_chat_id,
            f"{DENIED_TEXT}\n📨 So'rovingiz adminga yuborildi. Ruxsat berilsa, bot ishlay boshlaydi.",
        )
        await request_access(bot, user.id, user.full_name, user.username)
        return

    if not conn.is_enabled:
        await try_send(bot, conn.user_chat_id, "🔌 Bot Telegram Business'dan uzildi.")
        return

    lines = ["✅ <b>Bot akkauntingizga ulandi!</b>"]
    rights = conn.rights
    if rights is not None and not rights.can_delete_all_messages and DELETE_TRIGGER_REPLY:
        lines.append(
            "\nℹ️ Reply xabaringiz avtomatik o'chishi uchun Business sozlamalarida "
            "«Barcha xabarlarni o'chirish» ruxsatini yoqing (ixtiyoriy)."
        )
    row = storage.get_user(user.id)
    if not (row and row["group_id"]):
        lines.append(f"\n🗂 Tozalangan chatlar uchun guruh ulang: «{BTN_GROUP}» tugmasi.")
    await try_send(bot, conn.user_chat_id, "\n".join(lines), reply_markup=main_keyboard(user.id))

    if not is_admin(user.id) and OWNER_ID:
        await try_send(
            bot, OWNER_ID, f"ℹ️ {esc(person_label(user.id))} (<code>{user.id}</code>) botni ulab oldi."
        )


@router.business_message()
async def on_business_message(message: Message, bot: Bot) -> None:
    user_id = await connection_user(bot, message.business_connection_id)
    if user_id is None:
        return

    is_out = message.from_user is not None and message.from_user.id == user_id
    storage.save_message(user_id, message, is_out)

    if is_out and message.reply_to_message is not None:
        await save_secret_media(bot, user_id, message, message.reply_to_message)


async def save_secret_media(bot: Bot, user_id: int, trigger: Message, replied: Message) -> None:
    """
    Maxfiy (bir martalik) media botga oddiy xabar sifatida KELMAYDI — Telegram uni
    faqat reply ichida ko'rsatadi. Shuning uchun: reply qilingan media bazada bo'lsa,
    bu oddiy media (saqlamaymiz); bazada bo'lmasa — maxfiy media (saqlaymiz).
    """
    kind, file_id = extract_media(replied)
    if file_id is None:
        return
    known = storage.get_message(user_id, replied.chat.id, replied.message_id)
    if known is not None and known["file_id"]:
        return  # oddiy rasm/video — bot uni avval ko'rgan

    caption = (
        f"🔥 <b>Maxfiy media saqlandi</b> — {KIND_LABELS.get(kind, kind)}\n"
        f"👤 {esc(user_name(replied))}\n"
        f"💬 Chat: {esc(chat_name(replied))}\n"
        f"🕒 {fmt_time(int(replied.date.timestamp()) if replied.date else None)}"
    )
    if replied.caption:
        caption += f"\n\n📝 {esc(cut(replied.caption, 600))}"

    ok = await send_media(bot, user_id, kind, file_id, caption, prefer_download=True)
    if not ok:
        await try_send(
            bot,
            user_id,
            "❌ Maxfiy mediani saqlab bo'lmadi. Ehtimol u allaqachon ochilgan yoki "
            "fayl 20 MB dan katta.",
        )
        return

    if DELETE_TRIGGER_REPLY and trigger.business_connection_id:
        try:
            await bot.delete_business_messages(trigger.business_connection_id, [trigger.message_id])
        except TelegramAPIError as e:
            log.info("Reply xabarni o'chirib bo'lmadi (ruxsat yo'q bo'lishi mumkin): %s", e)


@router.edited_business_message()
async def on_edited_business_message(message: Message, bot: Bot) -> None:
    user_id = await connection_user(bot, message.business_connection_id)
    if user_id is None:
        return
    is_out = message.from_user is not None and message.from_user.id == user_id
    old = storage.get_message(user_id, message.chat.id, message.message_id)
    storage.save_message(user_id, message, is_out)

    if is_out or message.location:
        return  # o'z xabaringiz yoki jonli lokatsiya — xabar bermaymiz

    new_text = message.text or message.caption or ""
    old_text = old["text"] if old else None
    if old is not None and old_text == new_text:
        return  # matn o'zgarmagan

    text = (
        f"✏️ <b>Xabar tahrirlandi</b>\n"
        f"👤 {esc(user_name(message))}\n"
        f"💬 Chat: {esc(chat_name(message))}\n\n"
        f"<b>Eski:</b>\n{esc(cut(old_text, 1800)) if old_text is not None else '<i>(bazada yoʻq)</i>'}\n\n"
        f"<b>Yangi:</b>\n{esc(cut(new_text, 1800)) or '<i>(boʻsh)</i>'}"
    )
    await try_send(bot, user_id, text)


# --- o'chirilgan xabarlar (bir necha soniya yig'ib, keyin ishlaymiz) -------- #
_pending_deletes: dict[tuple[int, int], dict] = {}


@router.deleted_business_messages()
async def on_deleted_business_messages(event: BusinessMessagesDeleted, bot: Bot) -> None:
    user_id = await connection_user(bot, event.business_connection_id)
    if user_id is None:
        return
    key = (user_id, event.chat.id)
    pending = _pending_deletes.get(key)
    if pending is None:
        pending = {"ids": set(), "chat": event.chat}
        _pending_deletes[key] = pending
    else:
        pending["task"].cancel()
    pending["ids"].update(event.message_ids)
    pending["task"] = asyncio.create_task(_flush_deletes_later(bot, key))


async def _flush_deletes_later(bot: Bot, key: tuple[int, int]) -> None:
    await asyncio.sleep(CLEAR_DEBOUNCE)
    pending = _pending_deletes.pop(key, None)
    if pending is None:
        return
    try:
        await process_deleted(bot, key[0], pending["chat"], sorted(pending["ids"]))
    except Exception:  # noqa: BLE001
        log.exception("O'chirilgan xabarlarni qayta ishlashda xato")


async def process_deleted(bot: Bot, user_id: int, chat: Chat, ids: list[int]) -> None:
    rows = storage.get_messages(user_id, chat.id, ids)
    remaining = storage.count_chat(user_id, chat.id) - len(rows)
    unknown = len(ids) - len(rows)
    is_clear = len(ids) >= CLEAR_MIN or (len(rows) >= 2 and remaining == 0)

    if is_clear:
        if rows:
            await send_chat_dump(bot, user_id, chat, rows, unknown)
        else:
            await try_send(
                bot,
                user_id,
                f"🧹 <b>{esc(chat_label(chat))}</b> bilan chat tozalandi ({len(ids)} ta xabar), "
                "lekin bu xabarlar bot ulanishidan oldin yozilgan — saqlanmagan.",
            )
    else:
        for row in rows:
            if row["is_out"]:
                continue  # o'zingiz o'chirgan xabaringiz — xabar bermaymiz
            await notify_deleted(bot, user_id, chat, row)

    storage.delete_messages(user_id, chat.id, [r["message_id"] for r in rows])


async def notify_deleted(bot: Bot, user_id: int, chat: Chat, row: sqlite3.Row) -> None:
    header = (
        f"🗑 <b>Xabar o'chirildi</b> — {KIND_LABELS.get(row['kind'], row['kind'])}\n"
        f"👤 {esc(row['sender_name'])}\n"
        f"💬 Chat: {esc(chat_label(chat))}\n"
        f"🕒 Yuborilgan: {fmt_time(row['date'])}"
    )
    body = row["text"] or ""
    if row["file_id"]:
        caption = header + (f"\n\n📝 {esc(cut(body, 600))}" if body else "")
        if not await send_media(bot, user_id, row["kind"], row["file_id"], caption):
            await try_send(bot, user_id, header + "\n\n<i>(media faylni yuborib bo'lmadi)</i>")
    else:
        await try_send(bot, user_id, f"{header}\n\n{esc(cut(body, 3500))}")


# --- chat tozalanganda: butun yozishma guruhga ------------------------------ #
async def send_chat_dump(
    bot: Bot, user_id: int, chat: Chat, rows: list[sqlite3.Row], unknown: int
) -> None:
    user_row = storage.get_user(user_id)
    group_id = user_row["group_id"] if user_row else None
    group_title = user_row["group_title"] if user_row else None
    dest = group_id or user_id

    media_rows = [r for r in rows if r["file_id"]]
    numbers = {r["message_id"]: i for i, r in enumerate(media_rows, 1)}
    label = chat_label(chat)
    account = person_label(user_id)

    header = (
        f"🧹 <b>Chat tozalandi</b>\n"
        f"💬 Suhbatdosh: <b>{esc(label)}</b>\n"
        f"👤 Akkaunt: {esc(account)}\n"
        f"📨 Xabarlar: <b>{len(rows)}</b> ta (media: {len(media_rows)} ta)\n"
        f"🕒 {fmt_time(rows[0]['date'])} — {fmt_time(rows[-1]['date'])}"
    )
    if unknown:
        header += f"\n⚠️ Yana {unknown} ta xabar bot ulanishidan oldin yozilgan — ular saqlanmagan."

    # 1) Sarlavha — guruhga (bo'lmasa — shaxsiy chatga)
    try:
        await call(bot.send_message, dest, header)
    except TelegramMigrateToChat as e:
        storage.migrate_group(dest, e.migrate_to_chat_id)
        dest = e.migrate_to_chat_id
        await call(bot.send_message, dest, header)
    except TelegramAPIError as e:
        if dest == user_id:
            raise
        log.warning("Guruhga yuborib bo'lmadi (%s): %s", dest, e)
        dest = user_id
        await call(
            bot.send_message,
            dest,
            header + f"\n\n⚠️ «{esc(group_title)}» guruhiga yuborib bo'lmadi — bot guruhda "
            "yo'qmi yoki yozish huquqi yo'qmi tekshiring.",
        )

    # 2) To'liq yozishma — HTML fayl
    html_bytes = build_transcript(label, account, rows, numbers)
    slug = re.sub(r"[^\w.-]+", "_", label, flags=re.UNICODE).strip("_")[:40] or "chat"
    filename = f"chat_{slug}_{datetime.now(TZ):%Y-%m-%d_%H-%M}.html"
    await asyncio.sleep(SEND_PAUSE)
    try:
        await call(
            bot.send_document,
            dest,
            BufferedInputFile(html_bytes, filename=filename),
            caption="📜 To'liq yozishma (brauzerda oching). Media quyida, raqamlari bilan.",
        )
    except TelegramAPIError as e:
        log.warning("Yozishma faylini yuborib bo'lmadi: %s", e)

    # 3) Media — albomlar bilan
    items = [
        (
            r["kind"],
            r["file_id"],
            f"#{numbers[r['message_id']]} · {r['sender_name']} · {fmt_time(r['date'])}"
            + (f"\n{cut(r['text'], 800)}" if r["text"] else ""),
        )
        for r in media_rows
    ]
    await send_media_list(bot, dest, items)

    if dest != user_id:
        await try_send(
            bot,
            user_id,
            f"🧹 <b>{esc(label)}</b> bilan chat tozalandi — {len(rows)} ta xabar "
            f"«{esc(group_title)}» guruhiga yuborildi.",
        )


async def send_media_list(bot: Bot, dest: int, items: list[tuple[str, str, str]]) -> None:
    batch: list[tuple[str, str, str]] = []
    batch_group: str | None = None

    async def flush() -> None:
        nonlocal batch, batch_group
        if not batch:
            return
        current, batch, batch_group = batch, [], None
        await asyncio.sleep(SEND_PAUSE)
        if len(current) == 1:
            kind, fid, cap = current[0]
            await send_media(bot, dest, kind, fid, esc(cap))
            return
        media = [INPUT_MEDIA[k](media=fid, caption=esc(cut(cap, 1000))) for k, fid, cap in current]
        try:
            await call(bot.send_media_group, dest, media)
        except TelegramAPIError as e:
            log.warning("Albom yuborilmadi, bittalab yuboramiz: %s", e)
            for kind, fid, cap in current:
                await asyncio.sleep(SEND_PAUSE)
                await send_media(bot, dest, kind, fid, esc(cap))

    for kind, fid, cap in items:
        group = ALBUM_GROUP.get(kind)
        if group is None:  # ovozli xabar, dumaloq video, GIF, stiker — alohida
            await flush()
            await asyncio.sleep(SEND_PAUSE)
            await send_media(bot, dest, kind, fid, esc(cap))
            continue
        if (batch_group not in (None, group)) or len(batch) == 10:
            await flush()
        batch.append((kind, fid, cap))
        batch_group = group
    await flush()


TRANSCRIPT_CSS = """
:root{--bg:#eef1f5;--in:#ffffff;--out:#dcf5c8;--text:#1b1f24;--muted:#6b7480;--accent:#2a7bd3}
@media (prefers-color-scheme:dark){:root{--bg:#0f1720;--in:#1d2733;--out:#2b4a2f;--text:#e7ecf2;--muted:#93a0ae;--accent:#6fb1ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
header{position:sticky;top:0;background:var(--accent);color:#fff;padding:12px 16px}
header h1{margin:0;font-size:17px}header p{margin:2px 0 0;font-size:13px;opacity:.9}
main{max-width:760px;margin:0 auto;padding:12px 16px 40px;display:flex;flex-direction:column;gap:6px}
.day{align-self:center;background:rgba(0,0,0,.18);color:#fff;border-radius:12px;padding:2px 10px;font-size:12px;margin:10px 0 4px}
.msg{max-width:82%;padding:6px 10px 4px;border-radius:12px;background:var(--in);box-shadow:0 1px 1px rgba(0,0,0,.08);word-wrap:break-word}
.msg.out{align-self:flex-end;background:var(--out)}.msg.in{align-self:flex-start}
.who{font-size:12px;font-weight:600;color:var(--accent)}.media{font-size:13px;font-weight:600;margin:2px 0}
.time{text-align:right;font-size:11px;color:var(--muted)}
"""


def build_transcript(label: str, account: str, rows: list[sqlite3.Row], numbers: dict[int, int]) -> bytes:
    parts = [
        '<!doctype html><html lang="uz"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(label)}</title><style>{TRANSCRIPT_CSS}</style></head><body>"
        f"<header><h1>💬 {esc(label)}</h1><p>Akkaunt: {esc(account)} · {len(rows)} ta xabar · "
        f"saqlangan: {datetime.now(TZ):%d.%m.%Y %H:%M}</p></header><main>"
    ]
    last_day = None
    for r in rows:
        dt = datetime.fromtimestamp(r["date"] or 0, TZ)
        day = dt.strftime("%d.%m.%Y")
        if day != last_day:
            parts.append(f'<div class="day">{day}</div>')
            last_day = day
        media = ""
        if r["file_id"]:
            media = (
                f'<div class="media">{KIND_LABELS.get(r["kind"], r["kind"])} '
                f'#{numbers[r["message_id"]]}</div>'
            )
        text = esc(r["text"]).replace("\n", "<br>")
        side = "out" if r["is_out"] else "in"
        parts.append(
            f'<div class="msg {side}"><div class="who">{esc(r["sender_name"])}</div>'
            f'{media}<div class="text">{text}</div><div class="time">{dt:%H:%M}</div></div>'
        )
    parts.append("</main></body></html>")
    return "".join(parts).encode("utf-8")


# --------------------------------------------------------------------------- #
# Ishga tushirish
# --------------------------------------------------------------------------- #
async def cleanup_loop() -> None:
    while True:
        try:
            removed = storage.cleanup(KEEP_DAYS)
            if removed:
                log.info("Eski xabarlar tozalandi: %s ta", removed)
        except Exception:  # noqa: BLE001
            log.exception("Tozalashda xato")
        await asyncio.sleep(6 * 3600)


async def set_commands(bot: Bot) -> None:
    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Boshlash / yordam"),
                BotCommand(command="stats", description="Statistika"),
                BotCommand(command="group", description="Guruhni ulash"),
            ],
            scope=BotCommandScopeAllPrivateChats(),
        )
        await bot.set_my_commands(
            [
                BotCommand(command="setgroup", description="Shu guruhni ulash"),
                BotCommand(command="unsetgroup", description="Guruhni uzish"),
            ],
            scope=BotCommandScopeAllGroupChats(),
        )
        if OWNER_ID:
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="Boshlash / yordam"),
                    BotCommand(command="users", description="Foydalanuvchilar ro'yxati"),
                    BotCommand(command="add", description="Ruxsat berish: /add ID"),
                    BotCommand(command="remove", description="Ruxsatni olish: /remove ID"),
                    BotCommand(command="stats", description="Statistika"),
                    BotCommand(command="group", description="Guruhni ulash"),
                ],
                scope=BotCommandScopeChat(chat_id=OWNER_ID),
            )
    except TelegramAPIError as e:
        log.warning("Buyruqlar menyusini o'rnatib bo'lmadi: %s", e)


async def main() -> None:
    global storage
    if not BOT_TOKEN or not OWNER_ID:
        raise SystemExit("BOT_TOKEN va OWNER_ID .env faylida ko'rsatilishi shart!")

    storage = Storage(DB_PATH)
    storage.seed_users(SEED_IDS)
    refresh_allowed()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    log.info("Bot ishga tushdi: @%s (admin: %s, ruxsat: %s)", me.username, OWNER_ID, sorted(_allowed))
    await set_commands(bot)
    await try_send(
        bot,
        OWNER_ID,
        f"🚀 @{esc(me.username)} ishga tushdi.\n"
        f"👥 Ruxsat berilganlar: {len(_allowed)} ta\n/start",
        reply_markup=main_keyboard(OWNER_ID),
    )

    cleaner = asyncio.create_task(cleanup_loop())
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        cleaner.cancel()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
