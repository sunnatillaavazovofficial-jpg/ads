"""
Telegram Saver Bot — bir martalik (view-once), o'chirilgan va tahrirlangan
xabarlarni saqlab qoluvchi shaxsiy bot.

Telegram Business (Chatbotlar) orqali sizning akkauntingizga ulanadi va:
  * bir martalik rasm/video/ovozli xabarga REPLY qilsangiz — uni sizga yuboradi;
  * suhbatdoshingiz xabarni o'chirsa — o'chirilgan xabarni sizga yuboradi;
  * suhbatdoshingiz xabarni tahrirlasa — eski va yangi matnni yuboradi.
"""

from __future__ import annotations

import asyncio
import html
import io
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BufferedInputFile,
    BusinessConnection,
    BusinessMessagesDeleted,
    Message,
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


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).with_name("data") / "messages.db"))
KEEP_DAYS = int(os.getenv("KEEP_DAYS", "30"))
TZ = timezone(timedelta(hours=float(os.getenv("TZ_OFFSET", "5"))))  # Toshkent: UTC+5
# Reply-trigger xabaringizni chatdan avtomatik o'chirish
# (Business sozlamalarida "Barcha xabarlarni o'chirish" ruxsati kerak)
DELETE_TRIGGER_REPLY = _env_bool("DELETE_TRIGGER_REPLY", True)

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


# --------------------------------------------------------------------------- #
# Ma'lumotlar bazasi (SQLite)
# --------------------------------------------------------------------------- #
class Storage:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
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
                PRIMARY KEY (chat_id, message_id)
            );
            CREATE TABLE IF NOT EXISTS connections (
                conn_id    TEXT PRIMARY KEY,
                user_id    INTEGER,
                is_enabled INTEGER,
                rights     TEXT
            );
            """
        )
        self.db.commit()

    # --- xabarlar ---------------------------------------------------------- #
    def save_message(self, msg: Message) -> None:
        kind, file_id = extract_media(msg)
        self.db.execute(
            """
            INSERT OR REPLACE INTO messages
                (chat_id, message_id, conn_id, sender_id, sender_name, chat_name,
                 kind, file_id, text, date, saved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
            ),
        )
        self.db.commit()

    def get_message(self, chat_id: int, message_id: int) -> sqlite3.Row | None:
        cur = self.db.execute(
            "SELECT * FROM messages WHERE chat_id = ? AND message_id = ?",
            (chat_id, message_id),
        )
        return cur.fetchone()

    def delete_message(self, chat_id: int, message_id: int) -> None:
        self.db.execute(
            "DELETE FROM messages WHERE chat_id = ? AND message_id = ?",
            (chat_id, message_id),
        )
        self.db.commit()

    def cleanup(self, keep_days: int) -> int:
        border = int(time.time()) - keep_days * 86400
        cur = self.db.execute("DELETE FROM messages WHERE saved_at < ?", (border,))
        self.db.commit()
        return cur.rowcount

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

    # --- business ulanishlar ----------------------------------------------- #
    def save_connection(self, conn: BusinessConnection) -> None:
        rights = conn.rights.model_dump(exclude_none=True) if conn.rights else {}
        self.db.execute(
            "INSERT OR REPLACE INTO connections (conn_id, user_id, is_enabled, rights) "
            "VALUES (?, ?, ?, ?)",
            (conn.id, conn.user.id, int(conn.is_enabled), json.dumps(rights)),
        )
        self.db.commit()

    def connection_owner(self, conn_id: str) -> int | None:
        row = self.db.execute(
            "SELECT user_id FROM connections WHERE conn_id = ?", (conn_id,)
        ).fetchone()
        return row[0] if row else None


# --------------------------------------------------------------------------- #
# Yordamchi funksiyalar
# --------------------------------------------------------------------------- #
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
    c = msg.chat
    name = c.full_name or c.title or str(c.id)
    if c.username:
        name += f" (@{c.username})"
    return name


def esc(text: str | None) -> str:
    return html.escape(text or "")


def cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def fmt_time(ts: int | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, TZ).strftime("%d.%m.%Y %H:%M")


async def send_media(
    bot: Bot, kind: str, file_id: str, caption: str, prefer_download: bool = False
) -> bool:
    """
    Mediani egaga yuboradi. Avval file_id orqali (yoki teskari tartibda),
    bo'lmasa faylni yuklab olib, qayta yuklash orqali yuboradi.
    """
    caption = cut(caption, 1024)

    async def by_file_id() -> None:
        await _send(bot, kind, file_id, caption)

    async def by_download() -> None:
        buf = io.BytesIO()
        await bot.download(file_id, destination=buf)
        data = buf.getvalue()
        if not data:
            raise RuntimeError("bo'sh fayl")
        upload = BufferedInputFile(data, filename=f"{kind}.{FILE_EXT.get(kind, 'bin')}")
        await _send(bot, kind, upload, caption)

    attempts = (by_download, by_file_id) if prefer_download else (by_file_id, by_download)
    for attempt in attempts:
        try:
            await attempt()
            return True
        except (TelegramAPIError, RuntimeError) as e:
            log.warning("Media yuborishda xato (%s, %s): %s", kind, attempt.__name__, e)
    return False


async def _send(bot: Bot, kind: str, media, caption: str) -> None:
    if kind in NO_CAPTION_KINDS:
        # Dumaloq video va stikerga izoh qo'shib bo'lmaydi — alohida yuboramiz
        await bot.send_message(OWNER_ID, caption)
        method = bot.send_video_note if kind == "video_note" else bot.send_sticker
        await method(OWNER_ID, media)
        return
    method = {
        "photo": bot.send_photo,
        "video": bot.send_video,
        "voice": bot.send_voice,
        "audio": bot.send_audio,
        "animation": bot.send_animation,
        "document": bot.send_document,
    }[kind]
    await method(OWNER_ID, media, caption=caption)


# --------------------------------------------------------------------------- #
# Handlerlar
# --------------------------------------------------------------------------- #
router = Router()
storage: Storage  # main() ichida yaratiladi
_conn_cache: dict[str, int] = {}


async def is_owner_connection(bot: Bot, conn_id: str | None) -> bool:
    """Business ulanish aynan bot egasiga tegishli ekanini tekshiradi."""
    if not conn_id:
        return False
    owner = _conn_cache.get(conn_id) or storage.connection_owner(conn_id)
    if owner is None:
        try:
            conn = await bot.get_business_connection(conn_id)
            storage.save_connection(conn)
            owner = conn.user.id
        except TelegramAPIError as e:
            log.warning("Business ulanishni olib bo'lmadi: %s", e)
            return False
    _conn_cache[conn_id] = owner
    return owner == OWNER_ID


HELP_TEXT = (
    "👋 <b>Saver Bot</b> — bir martalik, o'chirilgan va tahrirlangan xabarlarni saqlaydi.\n\n"
    "<b>Ulash:</b>\n"
    "1. Telegram → <i>Sozlamalar → Telegram Business → Chatbotlar</i>\n"
    "2. Shu botning @username ini kiriting\n"
    "3. «Barcha shaxsiy chatlar»ga ruxsat bering\n"
    "4. Ruxsatlardan <i>«Xabarlarni o'qish»</i> va (ixtiyoriy) "
    "<i>«Barcha xabarlarni o'chirish»</i>ni yoqing\n\n"
    "<b>Ishlatish:</b>\n"
    "🔥 <b>Bir martalik rasm/video/ovoz</b> — ochmasdan oldin unga istalgan "
    "xabar bilan <b>reply</b> qiling (masalan «.»). Bot uni shu yerga yuboradi.\n"
    "🗑 <b>O'chirilgan xabarlar</b> — suhbatdosh xabarni o'chirsa, avtomatik keladi.\n"
    "✏️ <b>Tahrirlangan xabarlar</b> — eski va yangi matn avtomatik keladi.\n\n"
    "/stats — saqlangan xabarlar soni"
)


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: Message) -> None:
    if message.from_user is None or message.from_user.id != OWNER_ID:
        await message.answer("⛔️ Bu shaxsiy bot.")
        return
    await message.answer(HELP_TEXT)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if message.from_user is None or message.from_user.id != OWNER_ID:
        return
    await message.answer(
        f"📦 Bazada saqlangan xabarlar: <b>{storage.count()}</b>\n"
        f"🕒 Saqlash muddati: {KEEP_DAYS} kun"
    )


@router.message()
async def other_private(message: Message) -> None:
    if message.from_user is None or message.from_user.id != OWNER_ID:
        await message.answer("⛔️ Bu shaxsiy bot.")


@router.business_connection()
async def on_business_connection(conn: BusinessConnection, bot: Bot) -> None:
    storage.save_connection(conn)
    _conn_cache[conn.id] = conn.user.id

    if conn.user.id != OWNER_ID:
        log.warning("Begona foydalanuvchi ulanishga urindi: %s", conn.user.id)
        await bot.send_message(
            OWNER_ID,
            f"⚠️ Begona foydalanuvchi botni ulashga urindi: "
            f"{esc(conn.user.full_name)} (<code>{conn.user.id}</code>). E'tiborsiz qoldirildi.",
        )
        return

    if not conn.is_enabled:
        await bot.send_message(OWNER_ID, "🔌 Bot Telegram Business'dan uzildi.")
        return

    rights = conn.rights
    lines = ["✅ <b>Bot akkauntingizga ulandi!</b>"]
    if rights is not None and not rights.can_delete_all_messages and DELETE_TRIGGER_REPLY:
        lines.append(
            "\nℹ️ Reply xabaringiz avtomatik o'chishi uchun Business sozlamalarida "
            "«Barcha xabarlarni o'chirish» ruxsatini yoqing (ixtiyoriy)."
        )
    await bot.send_message(OWNER_ID, "\n".join(lines))


@router.business_message()
async def on_business_message(message: Message, bot: Bot) -> None:
    if not await is_owner_connection(bot, message.business_connection_id):
        return

    from_owner = message.from_user is not None and message.from_user.id == OWNER_ID

    if not from_owner:
        # Suhbatdoshning xabari — o'chirilsa/tahrirlansa ko'rsatish uchun saqlaymiz
        storage.save_message(message)
        return

    # Egasining xabari: media xabarga reply bo'lsa — o'sha mediani saqlaymiz
    replied = message.reply_to_message
    if replied is None:
        return
    kind, file_id = extract_media(replied)
    if file_id is None:
        return

    caption = (
        f"🔥 <b>Saqlandi</b> — {KIND_LABELS.get(kind, kind)}\n"
        f"👤 {esc(user_name(replied))}\n"
        f"💬 Chat: {esc(chat_name(replied))}\n"
        f"🕒 {fmt_time(int(replied.date.timestamp()) if replied.date else None)}"
    )
    if replied.caption:
        caption += f"\n\n📝 {esc(cut(replied.caption, 600))}"

    ok = await send_media(bot, kind, file_id, caption, prefer_download=True)
    if not ok:
        await bot.send_message(
            OWNER_ID,
            "❌ Mediani saqlab bo'lmadi. Ehtimol u allaqachon ochilgan yoki "
            "fayl 20 MB dan katta.",
        )
        return

    if DELETE_TRIGGER_REPLY and message.business_connection_id:
        try:
            await bot.delete_business_messages(
                message.business_connection_id, [message.message_id]
            )
        except TelegramAPIError as e:
            log.info("Reply xabarni o'chirib bo'lmadi (ruxsat yo'q bo'lishi mumkin): %s", e)


@router.edited_business_message()
async def on_edited_business_message(message: Message, bot: Bot) -> None:
    if not await is_owner_connection(bot, message.business_connection_id):
        return
    if message.from_user is not None and message.from_user.id == OWNER_ID:
        return
    if message.location:
        return  # jonli lokatsiya yangilanishlari

    old = storage.get_message(message.chat.id, message.message_id)
    new_text = message.text or message.caption or ""
    storage.save_message(message)

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
    await bot.send_message(OWNER_ID, text)


@router.deleted_business_messages()
async def on_deleted_business_messages(event: BusinessMessagesDeleted, bot: Bot) -> None:
    if not await is_owner_connection(bot, event.business_connection_id):
        return

    chat = event.chat
    chat_label = chat.full_name or chat.title or str(chat.id)
    if chat.username:
        chat_label += f" (@{chat.username})"

    unknown = 0
    for message_id in event.message_ids:
        row = storage.get_message(chat.id, message_id)
        if row is None:
            unknown += 1
            continue

        header = (
            f"🗑 <b>Xabar o'chirildi</b> — {KIND_LABELS.get(row['kind'], row['kind'])}\n"
            f"👤 {esc(row['sender_name'])}\n"
            f"💬 Chat: {esc(chat_label)}\n"
            f"🕒 Yuborilgan: {fmt_time(row['date'])}"
        )
        body = row["text"] or ""

        if row["file_id"]:
            caption = header + (f"\n\n📝 {esc(cut(body, 600))}" if body else "")
            ok = await send_media(bot, row["kind"], row["file_id"], caption)
            if not ok:
                await bot.send_message(
                    OWNER_ID, header + "\n\n<i>(media faylni yuborib bo'lmadi)</i>"
                )
        else:
            await bot.send_message(OWNER_ID, f"{header}\n\n{esc(cut(body, 3500))}")

        storage.delete_message(chat.id, message_id)

    if unknown:
        log.info("%s ta o'chirilgan xabar bazada topilmadi (chat %s)", unknown, chat.id)


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


async def main() -> None:
    global storage
    if not BOT_TOKEN or not OWNER_ID:
        raise SystemExit("BOT_TOKEN va OWNER_ID .env faylida ko'rsatilishi shart!")

    storage = Storage(DB_PATH)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    me = await bot.get_me()
    log.info("Bot ishga tushdi: @%s (egasi: %s)", me.username, OWNER_ID)
    try:
        await bot.send_message(OWNER_ID, f"🚀 @{esc(me.username)} ishga tushdi. /help")
    except TelegramAPIError:
        log.warning("Egaga xabar yuborib bo'lmadi — avval botga /start yozing.")

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
