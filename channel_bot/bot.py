"""
Kanalga avtomatik post joylovchi Telegram bot.

Admin botga istalgan post yuboradi (matn, rasm, video, albom, fayl, ovoz ...),
bot uni navbatga qo'yadi va belgilangan vaqtlarda kanalga o'zi joylaydi.
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import Command, CommandObject, CommandStart, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    KeyboardButton,
    LinkPreviewOptions,
    Message,
    ReplyKeyboardMarkup,
)
from dotenv import load_dotenv

from db import DB

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ENV_ADMINS = {int(x) for x in re.split(r"[,\s]+", os.getenv("ADMIN_IDS", "")) if x.strip().lstrip("-").isdigit()}
TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Tashkent"))
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts.db"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("channel_bot")

db = DB(DB_PATH)
router = Router()

MEDIA_TYPES = ("photo", "video", "animation", "document", "audio", "voice")

# Tugmalar matni
BTN_QUEUE = "📋 Navbat"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_NOW = "🚀 Hozir joylash"
BTN_PAUSE = "⏸ Pauza"
BTN_RESUME = "▶️ Davom ettirish"
BTN_HELP = "❓ Yordam"
MENU_BUTTONS = {BTN_QUEUE, BTN_SETTINGS, BTN_NOW, BTN_PAUSE, BTN_RESUME, BTN_HELP}


class SetDate(StatesGroup):
    waiting = State()


# ======================================================================
#                              Yordamchilar
# ======================================================================
def now() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def admins() -> set:
    saved = {int(x) for x in db.get("admins").split(",") if x.strip().lstrip("-").isdigit()}
    return ENV_ADMINS | saved


class IsAdmin(Filter):
    async def __call__(self, event) -> bool:
        user = event.from_user
        return bool(user) and user.id in admins()


def get_times() -> list:
    return sorted(t for t in db.get("times").split(",") if t)


def per_slot() -> int:
    try:
        return max(1, int(db.get("per_slot")))
    except ValueError:
        return 1


def is_paused() -> bool:
    return db.get("paused") == "1"


def next_slots(count: int, start: datetime | None = None) -> list:
    """Keyingi `count` ta joylash vaqtini qaytaradi."""
    times = get_times()
    if not times or count <= 0:
        return []
    start = start or now()
    result, day = [], start.date()
    while len(result) < count:
        for t in times:
            h, m = map(int, t.split(":"))
            dt = datetime(day.year, day.month, day.day, h, m)
            if dt > start:
                result.append(dt)
                if len(result) >= count:
                    break
        day += timedelta(days=1)
    return result


def eta_for_position(pos: int) -> datetime | None:
    """Navbatdagi pos-chi (0 dan) post qachon chiqishini hisoblaydi."""
    slots = next_slots(pos // per_slot() + 1)
    return slots[-1] if slots else None


def fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y %H:%M") if dt else "—"


def parse_when(text: str) -> datetime | None:
    """'14:00', '05.11 14:00', '05.11.2026 14:00', '2026-11-05 14:00', 'ertaga 14:00'."""
    text = text.strip().lower()
    n = now()
    m = re.fullmatch(r"(ertaga\s+)?(\d{1,2})[:.](\d{2})", text)
    if m:
        dt = n.replace(hour=int(m.group(2)), minute=int(m.group(3)), second=0, microsecond=0)
        if m.group(1):
            dt += timedelta(days=1)
        elif dt <= n:
            dt += timedelta(days=1)
        return dt
    m = re.fullmatch(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\s+(\d{1,2})[:.](\d{2})", text)
    if m:
        d, mo, y, h, mi = m.groups()
        y = int(y) if y else n.year
        if y < 100:
            y += 2000
        try:
            dt = datetime(y, int(mo), int(d), int(h), int(mi))
        except ValueError:
            return None
        if not m.group(3) and dt < n:
            dt = dt.replace(year=dt.year + 1)
        return dt
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2})[:.](\d{2})", text)
    if m:
        try:
            return datetime(*map(int, m.groups()))
        except ValueError:
            return None
    return None


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_QUEUE), KeyboardButton(text=BTN_NOW)],
            [KeyboardButton(text=BTN_SETTINGS), KeyboardButton(text=BTN_RESUME if is_paused() else BTN_PAUSE)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Post yuboring — navbatga qo'shiladi",
    )


def post_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👁 Ko'rish", callback_data=f"view:{post_id}"),
                InlineKeyboardButton(text="🚀 Hozir", callback_data=f"now:{post_id}"),
            ],
            [
                InlineKeyboardButton(text="📅 Sana belgilash", callback_data=f"date:{post_id}"),
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del:{post_id}"),
            ],
        ]
    )


def channel_button() -> InlineKeyboardMarkup | None:
    raw = db.get("button")
    if "|" not in raw:
        return None
    text, url = (p.strip() for p in raw.split("|", 1))
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, url=url)]])


def with_footer(html: str, limit: int) -> str:
    footer = db.get("footer")
    if not footer:
        return html
    combined = f"{html}\n\n{footer}" if html else footer
    return combined if len(combined) <= limit else html


def short_preview(row) -> str:
    data = json.loads(row["data"])
    icons = {"photo": "🖼", "video": "🎬", "animation": "🎞", "document": "📄", "audio": "🎵", "voice": "🎙"}
    if row["kind"] == "text":
        icon, text = "📝", data["html"]
    elif row["kind"] == "media":
        icon, text = icons.get(data["type"], "📎"), data.get("caption") or ""
    elif row["kind"] == "album":
        icon, text = f"🗂{len(data['items'])}", next((i["caption"] for i in data["items"] if i.get("caption")), "")
    else:
        icon, text = "📎", "(maxsus post)"
    text = re.sub(r"<[^>]+>", "", text).replace("\n", " ").strip()
    return f"{icon} {text[:40]}{'…' if len(text) > 40 else ''}"


# ======================================================================
#                         Postni yuborish (kanal/preview)
# ======================================================================
async def send_post(bot: Bot, chat_id, row) -> None:
    data = json.loads(row["data"])
    kind = row["kind"]
    markup = channel_button()

    if kind == "text":
        await bot.send_message(
            chat_id,
            with_footer(data["html"], 4096),
            reply_markup=markup,
            link_preview_options=LinkPreviewOptions(is_disabled=data.get("no_preview", False)),
        )
    elif kind == "media":
        t = data["type"]
        kwargs = {
            t: data["file_id"],
            "caption": with_footer(data.get("caption") or "", 1024) or None,
            "reply_markup": markup,
        }
        if data.get("spoiler") and t in ("photo", "video", "animation"):
            kwargs["has_spoiler"] = True
        await getattr(bot, f"send_{t}")(chat_id, **kwargs)
    elif kind == "album":
        classes = {
            "photo": InputMediaPhoto,
            "video": InputMediaVideo,
            "document": InputMediaDocument,
            "audio": InputMediaAudio,
        }
        items = data["items"]
        # Imzoni birinchi izohli elementga (bo'lmasa birinchisiga) qo'shamiz
        cap_idx = next((i for i, it in enumerate(items) if it.get("caption")), 0)
        media = []
        for i, it in enumerate(items):
            cap = it.get("caption") or ""
            if i == cap_idx:
                cap = with_footer(cap, 1024)
            media.append(classes[it["type"]](media=it["file_id"], caption=cap or None, parse_mode=ParseMode.HTML))
        await bot.send_media_group(chat_id, media=media)
    else:  # copy
        await bot.copy_message(chat_id, from_chat_id=data["chat_id"], message_id=data["message_id"])


async def publish(bot: Bot, row) -> bool:
    channel = db.get("channel_id")
    if not channel:
        await notify_admins(bot, "⚠️ Kanal sozlanmagan! <code>/kanal @kanal_nomi</code> buyrug'ini yuboring.")
        return False
    try:
        await send_post(bot, channel, row)
        db.mark_posted(row["id"], now())
        log.info("Post #%s kanalga joylandi", row["id"])
        return True
    except Exception as e:  # noqa: BLE001
        log.exception("Post #%s joylanmadi", row["id"])
        db.mark_failed(row["id"], str(e))
        await notify_admins(bot, f"❌ Post #{row['id']} joylanmadi:\n<code>{str(e)[:300]}</code>")
        return False


async def notify_admins(bot: Bot, text: str) -> None:
    for a in admins():
        try:
            await bot.send_message(a, text)
        except Exception:  # noqa: BLE001
            pass


# ======================================================================
#                              Rejalashtiruvchi
# ======================================================================
async def scheduler(bot: Bot) -> None:
    last_check = now()
    notified_empty = False
    while True:
        await asyncio.sleep(20)
        try:
            current = now()
            if is_paused():
                last_check = current
                continue

            # 1) Aniq sana belgilangan postlar
            for row in db.due_scheduled(current.strftime("%Y-%m-%d %H:%M")):
                await publish(bot, row)

            # 2) Jadval vaqtlari (last_check, current] oralig'ida kelgan bo'lsa
            slots = [s for s in next_slots(50, last_check) if s <= current]
            for _ in slots:
                q = db.queue()
                if not q:
                    if not notified_empty:
                        await notify_admins(bot, "📭 Navbat bo'sh — joylash vaqti keldi, lekin post yo'q. Yangi post yuboring!")
                        notified_empty = True
                    break
                for row in q[: per_slot()]:
                    await publish(bot, row)
                notified_empty = False
                left = len(db.queue())
                if left <= 2:
                    await notify_admins(bot, f"ℹ️ Navbatda {left} ta post qoldi.")
            last_check = current
        except Exception:  # noqa: BLE001
            log.exception("Scheduler xatosi")


# ======================================================================
#                                Buyruqlar
# ======================================================================
HELP = (
    "<b>🤖 Kanal post boti</b>\n\n"
    "Menga istalgan post yuboring yoki boshqa joydan <b>forward</b> qiling — "
    "matn, rasm, video, albom, fayl, audio. Post <b>navbatga</b> qo'shiladi va "
    "jadvaldagi vaqtlarda kanalga o'zi chiqadi.\n\n"
    "<b>Sozlash buyruqlari:</b>\n"
    "<code>/kanal @kanal_nomi</code> — kanalni ulash (bot kanalda admin bo'lsin)\n"
    "<code>/vaqt 09:00 13:00 18:00</code> — har kungi joylash vaqtlari\n"
    "<code>/son 2</code> — har bir vaqtda nechta post chiqsin\n"
    "<code>/imzo 👉 @kanal_nomi</code> — har post ostiga imzo (<code>/imzo off</code>)\n"
    "<code>/tugma Obuna bo'ling | https://t.me/kanal</code> — post ostida tugma (<code>/tugma off</code>)\n\n"
    "<b>Boshqarish:</b>\n"
    "<code>/navbat</code> — navbatdagi postlar\n"
    "<code>/reja 12 05.11 14:00</code> — #12 postni aniq sanaga qo'yish\n"
    "<code>/hozir</code> — navbatdagi birinchi postni darhol joylash\n"
    "<code>/ochir 12</code> — #12 postni o'chirish\n"
    "<code>/tozalash</code> — butun navbatni tozalash\n"
    "<code>/pauza</code>, <code>/davom</code> — to'xtatish / davom ettirish\n"
    "<code>/admin 123456789</code> — yangi admin qo'shish\n"
    "<code>/id</code> — Telegram ID'ingizni ko'rish"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    uid = message.from_user.id
    if not admins():
        # Hali admin yo'q — birinchi /start bosgan odam admin bo'ladi
        db.set("admins", str(uid))
        await message.answer("👑 Siz bot admini qilib belgilandingiz.")
    if uid not in admins():
        await message.answer(f"Bu bot faqat admin uchun.\nSizning ID: <code>{uid}</code>")
        return
    await message.answer(HELP, reply_markup=main_menu())
    await message.answer(settings_text())


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(f"Sizning ID: <code>{message.from_user.id}</code>")


admin_router = Router()
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())


@admin_router.message(Command("yordam", "help"))
@admin_router.message(F.text == BTN_HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(HELP, reply_markup=main_menu())


def settings_text() -> str:
    channel = db.get("channel_id") or "❗️ ulanmagan"
    times = ", ".join(get_times()) or "❗️ yo'q"
    footer = db.get("footer") or "yo'q"
    button = db.get("button").replace("|", "→") or "yo'q"
    st = db.stats()
    nxt = next_slots(1)
    return (
        "<b>⚙️ Sozlamalar</b>\n\n"
        f"📢 Kanal: <b>{channel}</b>\n"
        f"⏰ Vaqtlar: <b>{times}</b>\n"
        f"🔢 Har vaqtda: <b>{per_slot()} ta</b> post\n"
        f"✍️ Imzo: {footer}\n"
        f"🔘 Tugma: {button}\n"
        f"{'⏸ <b>PAUZADA</b>' if is_paused() else '▶️ Ishlayapti'}\n\n"
        f"📥 Navbatda: <b>{st.get('queued', 0)}</b> | ✅ Joylangan: <b>{st.get('posted', 0)}</b> | "
        f"❌ Xato: <b>{st.get('failed', 0)}</b>\n"
        f"⏭ Keyingi joylash: <b>{fmt_dt(nxt[0]) if nxt else '—'}</b>"
    )


@admin_router.message(Command("sozlamalar"))
@admin_router.message(F.text == BTN_SETTINGS)
async def cmd_settings(message: Message) -> None:
    await message.answer(settings_text(), reply_markup=main_menu())


@admin_router.message(Command("kanal"))
async def cmd_channel(message: Message, command: CommandObject, bot: Bot) -> None:
    arg = (command.args or "").strip()
    if not arg:
        await message.answer("Misol: <code>/kanal @kanal_nomi</code> yoki <code>/kanal -1001234567890</code>")
        return
    if arg.startswith("https://t.me/"):
        arg = "@" + arg.removeprefix("https://t.me/").strip("/")
    elif not arg.startswith("@") and not arg.lstrip("-").isdigit():
        arg = "@" + arg
    try:
        chat = await bot.get_chat(arg)
        me = await bot.get_me()
        member = await bot.get_chat_member(chat.id, me.id)
    except Exception as e:  # noqa: BLE001
        await message.answer(
            f"❌ Kanal topilmadi yoki bot unga qo'shilmagan.\n<code>{e}</code>\n\n"
            "Botni kanalga <b>admin</b> qilib qo'shing (post joylash huquqi bilan) va qayta urinib ko'ring."
        )
        return
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
        await message.answer("❌ Bot kanalda admin emas. Uni admin qiling (\"Post joylash\" huquqi bilan).")
        return
    db.set("channel_id", str(chat.id))
    await message.answer(f"✅ Kanal ulandi: <b>{chat.title}</b> (<code>{chat.id}</code>)")


@admin_router.message(Command("vaqt"))
async def cmd_times(message: Message, command: CommandObject) -> None:
    raw = re.findall(r"(\d{1,2})[:.](\d{2})", command.args or "")
    times = sorted({f"{int(h):02d}:{int(m):02d}" for h, m in raw if int(h) < 24 and int(m) < 60})
    if not times:
        await message.answer(
            f"Hozirgi vaqtlar: <b>{', '.join(get_times()) or 'yo‘q'}</b>\n\n"
            "O'zgartirish: <code>/vaqt 09:00 13:00 18:00</code>"
        )
        return
    db.set("times", ",".join(times))
    await message.answer(f"✅ Joylash vaqtlari: <b>{', '.join(times)}</b>\n⏭ Keyingisi: {fmt_dt(next_slots(1)[0])}")


@admin_router.message(Command("son"))
async def cmd_count(message: Message, command: CommandObject) -> None:
    arg = (command.args or "").strip()
    if not arg.isdigit() or not (1 <= int(arg) <= 20):
        await message.answer(f"Hozir har vaqtda <b>{per_slot()}</b> ta post.\nO'zgartirish: <code>/son 2</code> (1–20)")
        return
    db.set("per_slot", arg)
    daily = int(arg) * len(get_times())
    await message.answer(f"✅ Har vaqtda <b>{arg}</b> ta post. Kuniga jami: <b>{daily}</b> ta.")


@admin_router.message(Command("imzo"))
async def cmd_footer(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer(
            f"Hozirgi imzo: {db.get('footer') or 'yo‘q'}\n\n"
            "O'rnatish: <code>/imzo 👉 @kanal_nomi</code>\nO'chirish: <code>/imzo off</code>"
        )
        return
    if command.args.strip().lower() in ("off", "yoq", "yo'q", "o'chir"):
        db.set("footer", "")
        await message.answer("✅ Imzo o'chirildi.")
        return
    # Formatlashni saqlab qolish uchun HTML ko'rinishidan olamiz
    html = message.html_text.split(maxsplit=1)[1] if len(message.html_text.split(maxsplit=1)) > 1 else command.args
    db.set("footer", html)
    await message.answer(f"✅ Imzo o'rnatildi:\n\n{html}")


@admin_router.message(Command("tugma"))
async def cmd_button(message: Message, command: CommandObject) -> None:
    arg = (command.args or "").strip()
    if arg.lower() in ("off", "yoq", "yo'q"):
        db.set("button", "")
        await message.answer("✅ Tugma o'chirildi.")
        return
    if "|" not in arg or not re.match(r"https?://|tg://", arg.split("|", 1)[1].strip()):
        await message.answer(
            "Misol: <code>/tugma 📩 Buyurtma berish | https://t.me/username</code>\n"
            "O'chirish: <code>/tugma off</code>\n\n"
            "<i>Eslatma: albom postlarga Telegram tugma qo'shishga ruxsat bermaydi.</i>"
        )
        return
    db.set("button", arg)
    await message.answer("✅ Tugma o'rnatildi.")


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, command: CommandObject) -> None:
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer(f"Adminlar: <code>{', '.join(map(str, admins()))}</code>\nQo'shish: <code>/admin 123456789</code>")
        return
    saved = set(filter(None, db.get("admins").split(",")))
    saved.add(arg)
    db.set("admins", ",".join(saved))
    await message.answer(f"✅ <code>{arg}</code> admin qilindi.")


@admin_router.message(Command("pauza"))
@admin_router.message(F.text == BTN_PAUSE)
async def cmd_pause(message: Message) -> None:
    db.set("paused", "1")
    await message.answer("⏸ Avtomatik joylash to'xtatildi.", reply_markup=main_menu())


@admin_router.message(Command("davom"))
@admin_router.message(F.text == BTN_RESUME)
async def cmd_resume(message: Message) -> None:
    db.set("paused", "0")
    await message.answer("▶️ Avtomatik joylash davom etmoqda.", reply_markup=main_menu())


@admin_router.message(Command("navbat"))
@admin_router.message(F.text == BTN_QUEUE)
async def cmd_queue(message: Message) -> None:
    q, sch = db.queue(), db.scheduled()
    if not q and not sch:
        await message.answer("📭 Navbat bo'sh. Menga post yuboring!")
        return
    lines = [f"<b>📋 Navbat ({len(q)} ta)</b>"]
    slots = next_slots((len(q) + per_slot() - 1) // per_slot())
    for i, row in enumerate(q[:30]):
        eta = slots[i // per_slot()] if i // per_slot() < len(slots) else None
        lines.append(f"<b>#{row['id']}</b> {short_preview(row)}\n      ⏰ {fmt_dt(eta)}")
    if len(q) > 30:
        lines.append(f"… va yana {len(q) - 30} ta")
    if sch:
        lines.append(f"\n<b>📅 Aniq sanaga qo'yilgan ({len(sch)} ta)</b>")
        for row in sch[:20]:
            dt = datetime.strptime(row["scheduled_at"], "%Y-%m-%d %H:%M")
            lines.append(f"<b>#{row['id']}</b> {short_preview(row)}\n      ⏰ {fmt_dt(dt)}")
    if q:
        last = slots[-1] if slots else None
        lines.append(f"\n🏁 Navbat tugaydi: <b>{fmt_dt(last)}</b>")
    lines.append("\nPost ustida amal: <code>/post 12</code>")
    await message.answer("\n".join(lines))


@admin_router.message(Command("post"))
async def cmd_post(message: Message, command: CommandObject, bot: Bot) -> None:
    arg = (command.args or "").strip().lstrip("#")
    row = db.get_post(int(arg)) if arg.isdigit() else None
    if not row:
        await message.answer("Misol: <code>/post 12</code>")
        return
    await send_post(bot, message.chat.id, row)
    await message.answer(f"Post <b>#{row['id']}</b> — holati: {row['status']}", reply_markup=post_kb(row["id"]))


@admin_router.message(Command("hozir"))
@admin_router.message(F.text == BTN_NOW)
async def cmd_now(message: Message, bot: Bot) -> None:
    q = db.queue()
    if not q:
        await message.answer("📭 Navbat bo'sh.")
        return
    if await publish(bot, q[0]):
        await message.answer(f"✅ Post #{q[0]['id']} kanalga joylandi. Navbatda: {len(q) - 1} ta.")


@admin_router.message(Command("ochir"))
async def cmd_delete(message: Message, command: CommandObject) -> None:
    arg = (command.args or "").strip().lstrip("#")
    if not arg.isdigit() or not db.get_post(int(arg)):
        await message.answer("Misol: <code>/ochir 12</code>")
        return
    db.delete_post(int(arg))
    await message.answer(f"🗑 Post #{arg} o'chirildi.")


@admin_router.message(Command("tozalash"))
async def cmd_clear(message: Message) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Ha, tozalash", callback_data="clear:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="clear:no"),
        ]]
    )
    await message.answer(f"Navbatdagi <b>{len(db.queue()) + len(db.scheduled())}</b> ta post o'chirilsinmi?", reply_markup=kb)


@admin_router.callback_query(F.data.startswith("clear:"))
async def cb_clear(call: CallbackQuery) -> None:
    if call.data == "clear:yes":
        n = db.clear_queue()
        await call.message.edit_text(f"🗑 {n} ta post o'chirildi.")
    else:
        await call.message.edit_text("Bekor qilindi.")
    await call.answer()


@admin_router.message(Command("reja"))
async def cmd_plan(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[0].lstrip("#").isdigit():
        await message.answer(
            "Misol: <code>/reja 12 05.11 14:00</code>\n"
            "yoki <code>/reja 12 ertaga 10:00</code>\n"
            "Navbatga qaytarish: <code>/reja 12 off</code>"
        )
        return
    pid = int(parts[0].lstrip("#"))
    row = db.get_post(pid)
    if not row or row["status"] != "queued":
        await message.answer("Bunday navbatdagi post yo'q.")
        return
    if parts[1].strip().lower() == "off":
        db.set_schedule(pid, None)
        await message.answer(f"✅ Post #{pid} umumiy navbatga qaytarildi.")
        return
    dt = parse_when(parts[1])
    if not dt:
        await message.answer("❌ Sana noto'g'ri. Masalan: <code>05.11 14:00</code>")
        return
    db.set_schedule(pid, dt.strftime("%Y-%m-%d %H:%M"))
    await message.answer(f"📅 Post #{pid} <b>{fmt_dt(dt)}</b> da chiqadi.")


# ---------------------- Post tugmalari ----------------------
@admin_router.callback_query(F.data.regexp(r"^(view|now|del|date):\d+$"))
async def cb_post(call: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    action, pid = call.data.split(":")
    pid = int(pid)
    row = db.get_post(pid)
    if not row:
        await call.answer("Post topilmadi (o'chirilgan).", show_alert=True)
        return
    if action == "view":
        await send_post(bot, call.message.chat.id, row)
        await call.answer()
    elif action == "now":
        if row["status"] == "posted":
            await call.answer("Bu post allaqachon joylangan.", show_alert=True)
            return
        ok = await publish(bot, row)
        await call.answer("✅ Kanalga joylandi!" if ok else "❌ Xato", show_alert=not ok)
        if ok:
            await call.message.edit_text(f"✅ Post #{pid} kanalga joylandi.")
    elif action == "del":
        db.delete_post(pid)
        await call.message.edit_text(f"🗑 Post #{pid} o'chirildi.")
        await call.answer()
    elif action == "date":
        await state.set_state(SetDate.waiting)
        await state.update_data(post_id=pid)
        await call.message.answer(
            f"📅 Post #{pid} qachon chiqsin? Yozing:\n"
            "<code>14:00</code> — bugun/ertaga\n<code>ertaga 10:00</code>\n<code>05.11 18:30</code>\n\n"
            "Bekor qilish: <code>/bekor</code>"
        )
        await call.answer()


@admin_router.message(SetDate.waiting, Command("bekor"))
async def cancel_date(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu())


@admin_router.message(SetDate.waiting, F.text)
async def got_date(message: Message, state: FSMContext) -> None:
    dt = parse_when(message.text)
    if not dt:
        await message.answer("❌ Tushunmadim. Masalan: <code>05.11 14:00</code> yoki <code>/bekor</code>")
        return
    pid = (await state.get_data())["post_id"]
    await state.clear()
    if not db.get_post(pid):
        await message.answer("Post topilmadi.")
        return
    db.set_schedule(pid, dt.strftime("%Y-%m-%d %H:%M"))
    await message.answer(f"📅 Post #{pid} <b>{fmt_dt(dt)}</b> da chiqadi.", reply_markup=main_menu())


# ---------------------- Yangi postni qabul qilish ----------------------
_album_buffer: dict = {}


def media_of(message: Message):
    for t in MEDIA_TYPES:
        obj = getattr(message, t)
        if obj:
            file_id = obj[-1].file_id if t == "photo" else obj.file_id
            return t, file_id
    return None, None


async def confirm_added(message: Message, post_id: int) -> None:
    q = db.queue()
    pos = next((i for i, r in enumerate(q) if r["id"] == post_id), len(q) - 1)
    warn = "" if db.get("channel_id") else "\n\n⚠️ Kanal hali ulanmagan: <code>/kanal @kanal_nomi</code>"
    await message.answer(
        f"✅ Navbatga qo'shildi: <b>#{post_id}</b>\n"
        f"📥 Navbatda: <b>{len(q)}</b> ta\n"
        f"⏰ Taxminan chiqadi: <b>{fmt_dt(eta_for_position(pos))}</b>{warn}",
        reply_markup=post_kb(post_id),
    )


async def flush_album(group_id: str, post_id: int) -> None:
    await asyncio.sleep(1.5)
    messages = sorted(_album_buffer.pop(group_id, []), key=lambda m: m.message_id)
    if not messages:
        db.delete_post(post_id)
        return
    items = []
    for m in messages:
        t, fid = media_of(m)
        if t in ("animation", "voice"):  # albomda bo'lmaydi, lekin ehtiyot uchun
            t = "document" if t == "animation" else "audio"
        if t:
            items.append({"type": t, "file_id": fid, "caption": m.html_text if m.caption else ""})
    if not items:
        db.delete_post(post_id)
        return
    db.finish_post(post_id, {"items": items})
    await confirm_added(messages[0], post_id)


@admin_router.message(F.media_group_id)
async def got_album_part(message: Message) -> None:
    gid = message.media_group_id
    first = gid not in _album_buffer
    _album_buffer.setdefault(gid, []).append(message)
    if first:
        asyncio.create_task(flush_album(gid, db.reserve_post("album", now())))


@admin_router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(MENU_BUTTONS))
async def got_text(message: Message) -> None:
    no_preview = bool(message.link_preview_options and message.link_preview_options.is_disabled)
    pid = db.add_post("text", {"html": message.html_text, "no_preview": no_preview}, now())
    await confirm_added(message, pid)


@admin_router.message()
async def got_other(message: Message) -> None:
    t, fid = media_of(message)
    if t:
        data = {"type": t, "file_id": fid, "caption": message.html_text if message.caption else ""}
        if message.has_media_spoiler:
            data["spoiler"] = True
        pid = db.add_post("media", data, now())
    elif message.text:  # noma'lum buyruq
        await message.answer("Noma'lum buyruq. /yordam")
        return
    else:
        # Stiker, so'rovnoma, video-xabar, joylashuv va h.k. — nusxa sifatida
        pid = db.add_post("copy", {"chat_id": message.chat.id, "message_id": message.message_id}, now())
    await confirm_added(message, pid)


# ======================================================================
async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env fayliga BOT_TOKEN=... yozing.")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(admin_router)
    me = await bot.get_me()
    log.info("Bot ishga tushdi: @%s | adminlar: %s", me.username, admins() or "yo'q (birinchi /start)")
    asyncio.create_task(scheduler(bot))
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
