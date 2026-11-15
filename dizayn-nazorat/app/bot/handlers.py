"""Telegram bot: yangi ish kiritish, ishlarni ko'rish, holatni o'zgartirish."""
from __future__ import annotations

import logging
import uuid
from html import escape

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import or_, select

from ..config import TMP_DIR
from ..constants import ACTIVE_STATUSES, FILE_KINDS, STATUS_LABELS, STATUSES
from ..db import SessionLocal
from ..models import Job, JobItem, User
from ..services import (
    add_event,
    change_status,
    notify_designer_assigned,
    parse_float,
    parse_size,
    register_local_file,
)
from . import runtime

log = logging.getLogger("bot")
router = Router()

BTN_NEW = "➕ Yangi ish"
BTN_MY = "📋 Mening ishlarim"
BTN_ACTIVE = "🔥 Barcha faol ishlar"
BTN_SKIP = "⏭ O'tkazib yuborish"
BTN_DONE = "✅ Tayyor"
BTN_CANCEL = "❌ Bekor qilish"


def main_kb(user: User) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=BTN_NEW), KeyboardButton(text=BTN_MY)]]
    if user.can_manage:
        rows.append([KeyboardButton(text=BTN_ACTIVE)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def step_kb(*buttons: str) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=b)] for b in buttons]
    rows.append([KeyboardButton(text=BTN_CANCEL)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


class NewJob(StatesGroup):
    title = State()
    client_name = State()
    client_contact = State()
    size = State()
    address = State()
    comment = State()
    place = State()
    files = State()
    price = State()
    designer = State()
    confirm = State()


async def get_user(tg_id: int) -> User | None:
    async with SessionLocal() as db:
        res = await db.execute(select(User).where(User.telegram_id == tg_id, User.is_active.is_(True)))
        return res.scalar_one_or_none()


NOT_LINKED = (
    "Siz hali tizimga ulanmagansiz.\n\n"
    "Saytga kiring → <b>Profil</b> → <b>Telegramni ulash</b> tugmasini bosing."
)


# ----------------------------- /start va ulash -----------------------------


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    code = (command.args or "").strip()
    async with SessionLocal() as db:
        if code:
            res = await db.execute(select(User).where(User.link_code == code))
            user = res.scalar_one_or_none()
            if user:
                # boshqa foydalanuvchida shu telegram bo'lsa uzamiz
                res2 = await db.execute(
                    select(User).where(User.telegram_id == message.from_user.id, User.id != user.id)
                )
                for other in res2.scalars():
                    other.telegram_id = None
                user.telegram_id = message.from_user.id
                user.telegram_username = message.from_user.username
                user.link_code = None
                await db.commit()
                await message.answer(
                    f"✅ Telegram muvaffaqiyatli ulandi!\nXush kelibsiz, <b>{escape(user.display_name)}</b>.\n\n"
                    "Endi sizga yangi ishlar va o'zgarishlar haqida xabar keladi.",
                    reply_markup=main_kb(user),
                )
                return
            await message.answer("❗ Ulash kodi noto'g'ri yoki eskirgan. Saytdan yangi havola oling.")
            return
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer(NOT_LINKED, reply_markup=ReplyKeyboardRemove())
        return
    await message.answer(
        f"Salom, <b>{escape(user.display_name)}</b>! Quyidagi tugmalardan foydalaning.",
        reply_markup=main_kb(user),
    )


@router.message(Command("cancel"))
@router.message(F.text == BTN_CANCEL)
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    await message.answer("Bekor qilindi.", reply_markup=main_kb(user) if user else ReplyKeyboardRemove())


# ----------------------------- yangi ish -----------------------------


@router.message(Command("new"))
@router.message(F.text == BTN_NEW)
async def new_job(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer(NOT_LINKED)
        return
    await state.clear()
    await state.update_data(files=[])
    await state.set_state(NewJob.title)
    await message.answer("📝 <b>Ish nomini</b> yozing:", reply_markup=step_kb())


@router.message(NewJob.title, F.text)
async def nj_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip()[:255])
    await state.set_state(NewJob.client_name)
    await message.answer("👤 <b>Mijoz ismi</b>:", reply_markup=step_kb(BTN_SKIP))


@router.message(NewJob.client_name, F.text)
async def nj_client(message: Message, state: FSMContext):
    val = "" if message.text == BTN_SKIP else message.text.strip()[:255]
    await state.update_data(client_name=val)
    await state.set_state(NewJob.client_contact)
    await message.answer(
        "📞 Mijozning <b>telefon raqami yoki Telegram username</b>i (masalan +998901234567 yoki @username).\n"
        "Kontaktni yuborsangiz ham bo'ladi.",
        reply_markup=step_kb(BTN_SKIP),
    )


@router.message(NewJob.client_contact, F.contact)
async def nj_contact_shared(message: Message, state: FSMContext):
    c = message.contact
    data = await state.get_data()
    if not data.get("client_name"):
        await state.update_data(client_name=" ".join(filter(None, [c.first_name, c.last_name])))
    await state.update_data(client_contact=c.phone_number)
    await _ask_size(message, state)


@router.message(NewJob.client_contact, F.text)
async def nj_contact(message: Message, state: FSMContext):
    val = "" if message.text == BTN_SKIP else message.text.strip()[:255]
    await state.update_data(client_contact=val)
    await _ask_size(message, state)


async def _ask_size(message: Message, state: FSMContext):
    await state.set_state(NewJob.size)
    await message.answer(
        "📐 <b>Joy o'lchami</b> (eni × bo'yi). Masalan: <code>3x6</code>, <code>3.5x2 m</code>, "
        "<code>300x150 sm</code>",
        reply_markup=step_kb(BTN_SKIP),
    )


@router.message(NewJob.size, F.text)
async def nj_size(message: Message, state: FSMContext):
    if message.text != BTN_SKIP:
        w, h, unit = parse_size(message.text)
        await state.update_data(width=w, height=h, size_unit=unit, size_note="" if w else message.text[:255])
    await state.set_state(NewJob.address)
    await message.answer("📍 <b>Manzil / joy</b> (qayerga o'rnatiladi):", reply_markup=step_kb(BTN_SKIP))


@router.message(NewJob.address, F.text)
async def nj_address(message: Message, state: FSMContext):
    await state.update_data(address="" if message.text == BTN_SKIP else message.text.strip()[:500])
    await state.set_state(NewJob.comment)
    await message.answer("💬 <b>Izoh</b> (dizaynerga ko'rsatmalar):", reply_markup=step_kb(BTN_SKIP))


@router.message(NewJob.comment, F.text)
async def nj_comment(message: Message, state: FSMContext):
    await state.update_data(comment="" if message.text == BTN_SKIP else message.text.strip())
    await state.set_state(NewJob.place)
    await message.answer(
        "🖼 <b>Dizayn qilinadigan joy rasmi</b>ni yuboring (bir nechta bo'lishi mumkin).\n"
        f"Tugatgach <b>{BTN_DONE}</b> ni bosing.",
        reply_markup=step_kb(BTN_DONE, BTN_SKIP),
    )


def _extract_file(message: Message) -> dict | None:
    """Xabardagi istalgan faylni (rasm, hujjat, video, audio...) ajratib olish."""
    if message.photo:
        p = message.photo[-1]
        return {"file_id": p.file_id, "name": f"rasm_{p.file_unique_id}.jpg", "mime": "image/jpeg", "size": p.file_size}
    for attr in ("document", "video", "audio", "voice", "animation", "video_note"):
        obj = getattr(message, attr, None)
        if obj:
            name = getattr(obj, "file_name", None)
            mime = getattr(obj, "mime_type", None)
            if not name:
                ext = {"video": "mp4", "audio": "mp3", "voice": "ogg", "animation": "mp4", "video_note": "mp4"}.get(attr, "bin")
                name = f"{attr}_{obj.file_unique_id}.{ext}"
            return {"file_id": obj.file_id, "name": name, "mime": mime, "size": getattr(obj, "file_size", None)}
    return None


async def _collect_file(message: Message, state: FSMContext, kind: str):
    info = _extract_file(message)
    if not info:
        return False
    info["kind"] = kind
    data = await state.get_data()
    files = data.get("files", [])
    files.append(info)
    await state.update_data(files=files)
    cnt = sum(1 for f in files if f["kind"] == kind)
    big = info.get("size") and info["size"] > 20 * 1024 * 1024
    warn = "\n⚠️ Fayl 20 MB dan katta — bot uni yuklay olmasligi mumkin, saytdan yuklang." if big else ""
    await message.reply(f"📎 Qabul qilindi ({cnt} ta). Yana yuboring yoki {BTN_DONE} ni bosing.{warn}")
    return True


@router.message(NewJob.place, F.text.in_({BTN_DONE, BTN_SKIP}))
async def nj_place_done(message: Message, state: FSMContext):
    await state.set_state(NewJob.files)
    await message.answer(
        "📁 <b>Logo va qo'shimcha fayllar</b>ni yuboring (har qanday format: PDF, PSD, AI, CDR, ZIP, rasm...).\n"
        f"Tugatgach <b>{BTN_DONE}</b> ni bosing.",
        reply_markup=step_kb(BTN_DONE, BTN_SKIP),
    )


@router.message(NewJob.place)
async def nj_place_file(message: Message, state: FSMContext):
    if not await _collect_file(message, state, "place"):
        await message.answer(f"Rasm yoki fayl yuboring, yoki {BTN_DONE} ni bosing.")


@router.message(NewJob.files, F.text.in_({BTN_DONE, BTN_SKIP}))
async def nj_files_done(message: Message, state: FSMContext):
    await state.set_state(NewJob.price)
    await message.answer(
        "💰 <b>Umumiy narx</b> (so'mda, faqat raqam). Batafsil hisob-kitobni saytda qilish mumkin.",
        reply_markup=step_kb(BTN_SKIP),
    )


@router.message(NewJob.files)
async def nj_files_file(message: Message, state: FSMContext):
    if not await _collect_file(message, state, "logo"):
        await message.answer(f"Fayl yuboring, yoki {BTN_DONE} ni bosing.")


@router.message(NewJob.price, F.text)
async def nj_price(message: Message, state: FSMContext):
    if message.text != BTN_SKIP:
        price = parse_float(message.text.replace("so'm", "").replace("сум", ""))
        if price is None:
            await message.answer("Faqat raqam kiriting (masalan 450000) yoki o'tkazib yuboring.")
            return
        await state.update_data(price=price)
    await state.set_state(NewJob.designer)
    async with SessionLocal() as db:
        res = await db.execute(
            select(User).where(User.role == "designer", User.is_active.is_(True)).order_by(User.full_name)
        )
        designers = res.scalars().all()
    rows = [[InlineKeyboardButton(text=f"🎨 {d.display_name}", callback_data=f"nj_d:{d.id}")] for d in designers]
    rows.append([InlineKeyboardButton(text="Hozircha tayinlanmasin", callback_data="nj_d:0")])
    await message.answer("Qadamlar deyarli tugadi.", reply_markup=step_kb())
    await message.answer("🎨 <b>Dizaynerni tanlang:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(NewJob.designer, F.data.startswith("nj_d:"))
async def nj_designer(cb: CallbackQuery, state: FSMContext):
    did = int(cb.data.split(":")[1])
    await state.update_data(designer_id=did or None)
    await state.set_state(NewJob.confirm)
    data = await state.get_data()
    designer_name = "—"
    if did:
        async with SessionLocal() as db:
            d = await db.get(User, did)
            designer_name = d.display_name if d else "—"
    await cb.message.edit_reply_markup()
    await cb.message.answer(
        _summary(data, designer_name),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Saqlash", callback_data="nj_save"),
                    InlineKeyboardButton(text="🔥 Shoshilinch saqlash", callback_data="nj_save_urgent"),
                ],
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="nj_cancel")],
            ]
        ),
    )
    await cb.answer()


def _summary(data: dict, designer_name: str) -> str:
    lines = ["<b>Tekshiring:</b>", f"📝 <b>{escape(data.get('title', ''))}</b>"]
    if data.get("client_name"):
        lines.append(f"👤 {escape(data['client_name'])}")
    if data.get("client_contact"):
        lines.append(f"📞 {escape(data['client_contact'])}")
    if data.get("width"):
        lines.append(f"📐 {data['width']:g} × {data['height']:g} {data.get('size_unit', 'm')}")
    elif data.get("size_note"):
        lines.append(f"📐 {escape(data['size_note'])}")
    if data.get("address"):
        lines.append(f"📍 {escape(data['address'])}")
    if data.get("comment"):
        lines.append(f"💬 {escape(data['comment'][:300])}")
    files = data.get("files", [])
    if files:
        n_place = sum(1 for f in files if f["kind"] == "place")
        lines.append(f"📎 Fayllar: {n_place} ta joy rasmi, {len(files) - n_place} ta qo'shimcha")
    if data.get("price"):
        lines.append(f"💰 {data['price']:,.0f} so'm".replace(",", " "))
    lines.append(f"🎨 Dizayner: {escape(designer_name)}")
    return "\n".join(lines)


@router.callback_query(NewJob.confirm, F.data == "nj_cancel")
async def nj_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_reply_markup()
    user = await get_user(cb.from_user.id)
    await cb.message.answer("Bekor qilindi.", reply_markup=main_kb(user) if user else None)
    await cb.answer()


@router.callback_query(NewJob.confirm, F.data.in_({"nj_save", "nj_save_urgent"}))
async def nj_save(cb: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    await cb.message.edit_reply_markup()
    await cb.answer("Saqlanmoqda...")
    user = await get_user(cb.from_user.id)
    if not user:
        await cb.message.answer(NOT_LINKED)
        return
    failed: list[str] = []
    async with SessionLocal() as db:
        job = Job(
            title=data.get("title") or "Nomsiz ish",
            client_name=data.get("client_name", ""),
            client_contact=data.get("client_contact", ""),
            address=data.get("address", ""),
            width=data.get("width"),
            height=data.get("height"),
            size_unit=data.get("size_unit", "m"),
            size_note=data.get("size_note", ""),
            comment=data.get("comment", ""),
            priority="urgent" if cb.data == "nj_save_urgent" else "normal",
            designer_id=data.get("designer_id"),
            manager_id=user.id if user.can_manage else None,
            created_by_id=user.id,
            source="bot",
            status="new",
        )
        if data.get("price"):
            job.items.append(JobItem(name="Umumiy narx", unit="xizmat", quantity=1, unit_price=data["price"]))
        db.add(job)
        await db.flush()
        for f in data.get("files", []):
            tmp = TMP_DIR / f"bot_{uuid.uuid4().hex}"
            try:
                await bot.download(f["file_id"], destination=tmp)
                db.add(register_local_file(job.id, tmp, f["name"], f["kind"], user.id, mime=f.get("mime")))
            except Exception as e:
                log.warning("Fayl yuklanmadi %s: %s", f["name"], e)
                failed.append(f["name"])
                tmp.unlink(missing_ok=True)
        add_event(db, job, user, "create", "Ish Telegram bot orqali yaratildi")
        await db.commit()
        job = await db.get(Job, job.id)
        await db.refresh(job, ["designer", "manager", "files"])
        notify_designer_assigned(job, user)
        text = f"✅ Ish saqlandi: <b>#{job.id} {escape(job.title)}</b>"
        if failed:
            text += "\n\n⚠️ Quyidagi fayllar yuklanmadi (20 MB dan katta bo'lishi mumkin), saytdan qo'shing:\n" + "\n".join(
                f"• {escape(n)}" for n in failed
            )
        await cb.message.answer(text, reply_markup=main_kb(user))
        await _send_job_card(cb.message, job, user)


# ----------------------------- ishlar ro'yxati -----------------------------


@router.message(Command("jobs"))
@router.message(F.text == BTN_MY)
async def my_jobs(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer(NOT_LINKED)
        return
    async with SessionLocal() as db:
        q = select(Job).where(Job.status.in_(ACTIVE_STATUSES))
        q = q.where(or_(Job.designer_id == user.id, Job.manager_id == user.id, Job.created_by_id == user.id))
        res = await db.execute(q.order_by(Job.created_at.desc()).limit(30))
        jobs = res.scalars().all()
    await _send_list(message, jobs, "Sizning faol ishlaringiz")


@router.message(F.text == BTN_ACTIVE)
async def all_active(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user.can_manage:
        return
    async with SessionLocal() as db:
        res = await db.execute(
            select(Job).where(Job.status.in_(ACTIVE_STATUSES)).order_by(Job.created_at.desc()).limit(40)
        )
        jobs = res.scalars().all()
    await _send_list(message, jobs, "Barcha faol ishlar")


async def _send_list(message: Message, jobs: list[Job], title: str):
    if not jobs:
        await message.answer("Faol ishlar yo'q 🎉")
        return
    rows = []
    for j in jobs:
        flag = "🔥" if j.priority == "urgent" else ""
        late = "⏰" if j.is_overdue else ""
        label = f"{flag}{late}#{j.id} {j.title[:28]} · {STATUS_LABELS.get(j.status, j.status)}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"job:{j.id}")])
    await message.answer(f"<b>{title}</b> ({len(jobs)} ta):", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


def _card_text(job: Job) -> str:
    lines = [
        f"<b>#{job.id} {escape(job.title)}</b>",
        f"📌 Holat: <b>{STATUS_LABELS.get(job.status, job.status)}</b>"
        + ("  🔥 Shoshilinch" if job.priority == "urgent" else ""),
    ]
    if job.client_name or job.client_contact:
        lines.append(f"👤 {escape(job.client_name)} {escape(job.client_contact)}".strip())
    if job.size_text:
        lines.append(f"📐 {escape(job.size_text)}" + (f" = {job.area_m2:g} m²" if job.area_m2 else ""))
    if job.address:
        lines.append(f"📍 {escape(job.address)}")
    if job.due_date:
        lines.append(f"⏰ Muddat: {job.due_date.strftime('%d.%m.%Y')}" + (" (o'tib ketgan!)" if job.is_overdue else ""))
    lines.append(f"👔 Menejer: {escape(job.manager.display_name) if job.manager else '—'}")
    lines.append(f"🎨 Dizayner: {escape(job.designer.display_name) if job.designer else '—'}")
    if job.items:
        lines.append(f"💰 Jami: {job.total:,.0f} so'm".replace(",", " ") + (f" · Qoldiq: {job.debt:,.0f}".replace(",", " ") if job.paid else ""))
    if job.comment:
        lines.append(f"💬 {escape(job.comment[:700])}")
    if job.files:
        lines.append(f"📎 Fayllar: {len(job.files)} ta")
    return "\n".join(lines)


def _card_kb(job: Job) -> InlineKeyboardMarkup:
    rows, row = [], []
    for code, label, _ in STATUSES:
        if code == job.status:
            continue
        row.append(InlineKeyboardButton(text=label, callback_data=f"st:{job.id}:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    extra = []
    if job.files:
        extra.append(InlineKeyboardButton(text="📎 Fayllarni olish", callback_data=f"files:{job.id}"))
    from ..services import job_url

    url = job_url(job.id)
    if url and url.startswith("https://"):
        extra.append(InlineKeyboardButton(text="🌐 Saytda ochish", url=url))
    if extra:
        rows.append(extra)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_job_card(message: Message, job: Job, user: User):
    await message.answer(_card_text(job), reply_markup=_card_kb(job))


@router.callback_query(F.data.startswith("job:"))
async def cb_job(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not user:
        await cb.answer("Tizimga ulanmagansiz", show_alert=True)
        return
    async with SessionLocal() as db:
        job = await db.get(Job, int(cb.data.split(":")[1]))
    if not job:
        await cb.answer("Ish topilmadi (o'chirilgan bo'lishi mumkin)", show_alert=True)
        return
    await _send_job_card(cb.message, job, user)
    await cb.answer()


@router.callback_query(F.data.startswith("st:"))
async def cb_status(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not user:
        await cb.answer("Tizimga ulanmagansiz", show_alert=True)
        return
    _, jid, status = cb.data.split(":")
    async with SessionLocal() as db:
        job = await db.get(Job, int(jid))
        if not job:
            await cb.answer("Ish topilmadi", show_alert=True)
            return
        changed = await change_status(db, job, status, user)
        if changed:
            await cb.message.edit_text(_card_text(job), reply_markup=_card_kb(job))
    await cb.answer(f"Holat: {STATUS_LABELS.get(status, status)}" if changed else "O'zgarmadi")


@router.callback_query(F.data.startswith("files:"))
async def cb_files(cb: CallbackQuery, bot: Bot):
    from aiogram.types import FSInputFile

    from ..config import UPLOAD_DIR

    user = await get_user(cb.from_user.id)
    if not user:
        await cb.answer("Tizimga ulanmagansiz", show_alert=True)
        return
    async with SessionLocal() as db:
        job = await db.get(Job, int(cb.data.split(":")[1]))
    if not job:
        await cb.answer("Ish topilmadi", show_alert=True)
        return
    await cb.answer("Yuborilmoqda...")
    for f in job.files[:30]:
        path = UPLOAD_DIR / f.stored_path
        if not path.exists():
            continue
        caption = f"#{job.id} · {FILE_KINDS.get(f.kind, f.kind)}"
        try:
            if f.size > 50 * 1024 * 1024:
                await cb.message.answer(f"⚠️ {escape(f.original_name)} — 50 MB dan katta, saytdan yuklab oling.")
                continue
            await bot.send_document(cb.message.chat.id, FSInputFile(path, filename=f.original_name), caption=caption)
        except Exception as e:
            log.warning("Fayl yuborilmadi: %s", e)


@router.message(NewJob.title)
@router.message(NewJob.client_name)
@router.message(NewJob.address)
@router.message(NewJob.comment)
@router.message(NewJob.price)
@router.message(NewJob.size)
async def expect_text(message: Message):
    await message.answer("Iltimos, matn yozing yoki tugmalardan foydalaning.")


@router.message()
async def fallback(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer(NOT_LINKED)
        return
    await message.answer("Tugmalardan foydalaning 👇", reply_markup=main_kb(user))


# ----------------------------- ishga tushirish -----------------------------


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return dp


async def run_bot(token: str):
    from aiogram.client.default import DefaultBotProperties

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    me = await bot.get_me()
    runtime.bot = bot
    runtime.bot_username = me.username
    log.info("Bot ishga tushdi: @%s", me.username)
    dp = build_dispatcher()
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, handle_signals=False)
    finally:
        runtime.bot = None
        await bot.session.close()

