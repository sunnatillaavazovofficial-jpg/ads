"""Telegram bot: menejerlar yangi ish joylaydi, hamma bildirishnoma oladi."""
import logging
import shutil
import uuid
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sqlalchemy import or_, select
from telethon import Button, TelegramClient, events

from .. import config
from ..db import db_session
from ..models import User, Work
from ..services import notify
from ..services import works as works_svc
from ..utils import parse_size, safe_filename

log = logging.getLogger("dizaynhub.bot")

BTN_NEW = "➕ Yangi ish"
BTN_MY = "📋 Ishlarim"
BTN_HELP = "ℹ️ Yordam"
BTN_NONE = "Yo'q"
BTN_DONE = "Tayyor ✅"
BTN_CANCEL = "❌ Bekor qilish"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".psd", ".svg", ".heic"}

STEPS = ["title", "work_type", "short_desc", "size", "image", "extra_info", "logo", "special_text", "file", "confirm"]

PROMPTS = {
    "title": "1/9. <b>Ish nomi</b>ni yozing:",
    "work_type": "2/9. <b>Ish turi</b>ni tanlang:",
    "short_desc": "3/9. <b>Qisqa ta'rif</b> yozing (yoki «Yo'q»):",
    "size": "4/9. <b>Ish o'lchami</b>: masalan <code>300x600 sm</code>, <code>3x6 m 2 dona</code> (yoki «Yo'q»):",
    "image": "5/9. <b>Ish rasmi</b>ni yuboring (bir nechta bo'lishi mumkin). Tugatgach «Tayyor ✅», rasm bo'lmasa «Yo'q»:",
    "extra_info": "6/9. <b>Qo'shimcha ma'lumotlar</b> (yoki «Yo'q»):",
    "logo": "7/9. <b>Logo</b> faylini yuboring. Tugatgach «Tayyor ✅», logo bo'lmasa «Yo'q»:",
    "special_text": "8/9. <b>Maxsus matn</b> (ishga yoziladigan matn) yoki «Yo'q»:",
    "file": "9/9. <b>Fayllar</b>ni yuboring (PSD, AI, CDR, PDF...). Tugatgach «Tayyor ✅», fayl bo'lmasa «Yo'q»:",
}

FILE_STEPS = {"image": "image", "logo": "logo", "file": "file"}
NONE_FLAG = {
    "short_desc": "short_desc_none", "size": "size_none", "image": "image_none",
    "extra_info": "extra_info_none", "logo": "logo_none", "special_text": "special_text_none",
    "file": "files_none",
}


@dataclass
class Draft:
    user_id: int
    step: str = "title"
    data: dict = field(default_factory=dict)
    files: dict = field(default_factory=lambda: {"image": [], "logo": [], "file": []})
    tmpdir: Path = field(default_factory=lambda: config.TMP_DIR / f"bot_{uuid.uuid4().hex[:10]}")
    last_group: Optional[int] = None

    def cleanup(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)


def esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Bot:
    def __init__(self) -> None:
        self.client: Optional[TelegramClient] = None
        self.drafts: dict[int, Draft] = {}
        self.username = ""

    async def start(self) -> None:
        if not config.BOT_ENABLED:
            log.warning("Bot o'chirilgan: .env faylida BOT_TOKEN (va TG_API_ID/HASH) kiritilmagan")
            return
        bot_id = config.BOT_TOKEN.split(":", 1)[0]
        self.client = TelegramClient(str(config.TG_SESSION_DIR / f"bot_{bot_id}"),
                                     config.TG_API_ID, config.TG_API_HASH)
        try:
            await self.client.start(bot_token=config.BOT_TOKEN)
            me = await self.client.get_me()
            self.username = me.username or ""
        except Exception:
            log.exception("Bot ishga tushmadi (BOT_TOKEN to'g'rimi?)")
            self.client = None
            return
        self.client.add_event_handler(self.on_message, events.NewMessage(incoming=True, func=lambda e: e.is_private))
        self.client.add_event_handler(self.on_callback, events.CallbackQuery())
        notify.set_sender(self.send)
        log.info("Bot ishga tushdi: @%s", self.username)

    async def stop(self) -> None:
        notify.set_sender(None)
        for d in self.drafts.values():
            d.cleanup()
        self.drafts.clear()
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass

    async def send(self, chat_id: int, text: str, buttons=None) -> None:
        if not self.client:
            return
        markup = None
        if buttons:
            markup = []
            for row in buttons:
                r = []
                for label, data in row:
                    if data.startswith("url:"):
                        r.append(Button.url(label, data[4:]))
                    else:
                        r.append(Button.inline(label, data.encode()))
                markup.append(r)
        await self.client.send_message(chat_id, text, buttons=markup, link_preview=False)

    # ------------------------------------------------------------ yordamchi
    @staticmethod
    def _user_by_tg(tg_id: int) -> Optional[User]:
        with db_session() as db:
            u = db.scalars(select(User).where(User.tg_user_id == tg_id)).first()
            if u and u.is_active:
                return u
        return None

    @staticmethod
    def _menu(user: User):
        row = [Button.text(BTN_NEW, resize=True)] if user.can_create_work else []
        row.append(Button.text(BTN_MY, resize=True))
        return [row, [Button.text(BTN_HELP, resize=True)]]

    @staticmethod
    def _kb(*labels):
        return [[Button.text(lbl, resize=True) for lbl in labels], [Button.text(BTN_CANCEL, resize=True)]]

    def _link_user(self, code: str, tg_id: int) -> Optional[User]:
        code = code.strip()
        if not code:
            return None
        with db_session() as db:
            user = db.scalars(select(User).where(User.tg_link_code == code)).first()
            if not user or not user.is_active:
                return None
            for other in db.scalars(select(User).where(User.tg_user_id == tg_id, User.id != user.id)):
                other.tg_user_id = None
            db.flush()
            user.tg_user_id = tg_id
            user.tg_link_code = None
            db.commit()
            return user

    # ------------------------------------------------------------ xabarlar
    async def on_message(self, event) -> None:
        try:
            await self._on_message(event)
        except Exception:
            log.exception("Bot xabarini qayta ishlashda xato")
            await event.respond("⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring.")

    async def _on_message(self, event) -> None:
        text = (event.raw_text or "").strip()
        tg_id = event.sender_id

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                linked = self._link_user(parts[1], tg_id)
                if linked:
                    await event.respond(
                        f"✅ Akkaunt bog'landi: <b>{esc(linked.full_name)}</b> ({linked.role_name}).",
                        parse_mode="html", buttons=self._menu(linked))
                    return
                await event.respond("❌ Kod noto'g'ri yoki eskirgan. Saytdagi profilingizdan yangi kod oling.")
                return

        user = self._user_by_tg(tg_id)
        if user is None:
            linked = self._link_user(text, tg_id) if text and not text.startswith("/") else None
            if linked:
                await event.respond(f"✅ Akkaunt bog'landi: <b>{esc(linked.full_name)}</b>.",
                                    parse_mode="html", buttons=self._menu(linked))
                return
            await event.respond(
                "Salom! Bu bot faqat xodimlar uchun.\n\n"
                "Saytga kiring → <b>Profil</b> → «Telegram botni bog'lash» tugmasini bosing "
                "yoki u yerdagi kodni shu yerga yuboring.", parse_mode="html")
            return

        draft = self.drafts.get(tg_id)
        if text in ("/cancel", BTN_CANCEL):
            if draft:
                draft.cleanup()
                self.drafts.pop(tg_id, None)
            await event.respond("Bekor qilindi.", buttons=self._menu(user))
            return
        if text in ("/new", BTN_NEW):
            if not user.can_create_work:
                await event.respond("Yangi ishni faqat menejerlar joylaydi.")
                return
            if draft:
                draft.cleanup()
            self.drafts[tg_id] = Draft(user_id=user.id)
            await self._ask(event, self.drafts[tg_id])
            return
        if draft:
            await self._wizard(event, user, draft, text)
            return
        if text in ("/my", BTN_MY):
            await self._my_works(event, user)
            return
        await event.respond(self._help(user), parse_mode="html", buttons=self._menu(user))

    def _help(self, user: User) -> str:
        lines = [f"👤 <b>{esc(user.full_name)}</b> — {user.role_name}", ""]
        if user.can_create_work:
            lines.append(f"«{BTN_NEW}» — yangi ish joylash (9 ta savol).")
        lines.append(f"«{BTN_MY}» — ishlar ro'yxati.")
        lines.append("/cancel — joriy amalni bekor qilish.")
        if config.PUBLIC_URL:
            lines.append(f"\n🌐 Sayt: {config.PUBLIC_URL}")
        return "\n".join(lines)

    async def _my_works(self, event, user: User) -> None:
        with db_session() as db:
            q = select(Work).order_by(Work.id.desc()).limit(15)
            if user.is_manager:
                q = q.where(Work.manager_id == user.id)
            elif user.is_chief:
                q = q.where(or_(Work.status == "new", Work.designer_id == user.id))
            elif user.role == "designer":
                q = q.where(Work.designer_id == user.id)
            works = list(db.scalars(q))
            if not works:
                await event.respond("Hozircha ish yo'q.")
                return
            lines = ["<b>Ishlar:</b>"]
            for w in works:
                link = works_svc.work_link(w)
                title = f'<a href="{link}">#{w.id} {esc(w.title)}</a>' if link else f"#{w.id} {esc(w.title)}"
                lines.append(f"• {title} — <i>{w.status_name}</i>")
        await event.respond("\n".join(lines), parse_mode="html", link_preview=False)

    # ------------------------------------------------------------ usta (wizard)
    async def _ask(self, event, draft: Draft) -> None:
        step = draft.step
        if step == "work_type":
            with db_session() as db:
                types_ = works_svc.work_types(db)
            rows, row = [], []
            for i, name in enumerate(types_):
                row.append(Button.inline(name, f"wt:{i}".encode()))
                if len(row) == 2:
                    rows.append(row)
                    row = []
            if row:
                rows.append(row)
            await event.respond(PROMPTS[step], parse_mode="html", buttons=rows)
            return
        if step == "title":
            kb = [[Button.text(BTN_CANCEL, resize=True)]]
        elif step in FILE_STEPS:
            kb = self._kb(BTN_DONE, BTN_NONE)
        else:
            kb = self._kb(BTN_NONE)
        await event.respond(PROMPTS[step], parse_mode="html", buttons=kb)

    def _next(self, draft: Draft) -> None:
        draft.step = STEPS[STEPS.index(draft.step) + 1]
        draft.last_group = None

    async def _wizard(self, event, user: User, draft: Draft, text: str) -> None:
        step = draft.step
        if step == "confirm":
            await event.respond("Pastdagi «✅ Saqlash» yoki «❌ Bekor qilish» tugmasini bosing.")
            return

        if step in FILE_STEPS:
            kind = FILE_STEPS[step]
            if event.message.media and (event.message.photo or event.message.document):
                await self._collect_file(event, draft, kind)
                return
            if text == BTN_DONE:
                if not draft.files[kind]:
                    await event.respond("Hali fayl yuborilmadi. Fayl yuboring yoki «Yo'q» ni bosing.")
                    return
                draft.data[NONE_FLAG[step]] = False
                self._next(draft)
                await self._after_step(event, draft)
                return
            if text == BTN_NONE:
                if draft.files[kind]:
                    await event.respond("Fayl allaqachon yuborilgan — «Tayyor ✅» ni bosing.")
                    return
                draft.data[NONE_FLAG[step]] = True
                self._next(draft)
                await self._after_step(event, draft)
                return
            await event.respond("Fayl yoki rasm yuboring, so'ng «Tayyor ✅». Bo'lmasa «Yo'q».")
            return

        if step == "work_type":
            with db_session() as db:
                types_ = works_svc.work_types(db)
            match = next((t for t in types_ if t.lower() == text.lower()), None)
            if not match:
                await event.respond("Tugmalardan birini tanlang.")
                return
            draft.data["work_type"] = match
            self._next(draft)
            await self._after_step(event, draft)
            return

        if not text:
            await event.respond("Matn yozing.")
            return

        if step == "title":
            draft.data["title"] = text[:200]
        elif text == BTN_NONE and step in NONE_FLAG:
            draft.data[NONE_FLAG[step]] = True
        elif step == "size":
            parsed = parse_size(text)
            if not parsed:
                await event.respond("O'lchamni tushunmadim. Masalan: <code>300x600 sm</code> yoki "
                                    "<code>3x6 m 2 dona</code>", parse_mode="html")
                return
            w, h, unit, qty = parsed
            draft.data.update(width=w, height=h, size_unit=unit, quantity=qty, size_none=False)
        else:
            draft.data[step] = text
            draft.data[NONE_FLAG[step]] = False
        self._next(draft)
        await self._after_step(event, draft)

    async def _after_step(self, event, draft: Draft) -> None:
        if draft.step == "confirm":
            await event.respond(self._summary(draft), parse_mode="html", buttons=[
                [Button.inline("✅ Saqlash", b"save"), Button.inline("❌ Bekor qilish", b"cancel")]
            ])
            await event.respond("Tekshirib chiqing 👆", buttons=Button.clear())
        else:
            await self._ask(event, draft)

    async def _collect_file(self, event, draft: Draft, kind: str) -> None:
        msg = event.message
        draft.tmpdir.mkdir(parents=True, exist_ok=True)
        if msg.photo:
            name = f"rasm_{msg.id}.jpg"
        else:
            name = safe_filename(msg.file.name or f"fayl_{msg.id}{msg.file.ext or ''}")
        if kind == "image" and not msg.photo:
            if Path(name).suffix.lower() not in IMAGE_EXT and not (msg.file.mime_type or "").startswith("image/"):
                await event.respond("Bu bosqichda rasm yuboring (yoki keyingi bosqichda fayl sifatida).")
                return
        target = draft.tmpdir / f"{uuid.uuid4().hex[:8]}_{name}"
        got = await event.client.download_media(msg, file=str(target))
        if not got:
            await event.respond("Faylni yuklab bo'lmadi, qayta yuboring.")
            return
        draft.files[kind].append((name, Path(got)))
        # Albom bo'lib kelsa, har biriga javob yozmaymiz
        if msg.grouped_id and msg.grouped_id == draft.last_group:
            return
        draft.last_group = msg.grouped_id
        await event.respond(f"📥 Qabul qilindi. Yana yuborishingiz yoki «{BTN_DONE}» ni bosishingiz mumkin.")

    def _summary(self, draft: Draft) -> str:
        d = draft.data

        def val(key, flag):
            return "<i>Yo'q</i>" if d.get(flag) else esc(d.get(key, ""))

        if d.get("size_none"):
            size = "<i>Yo'q</i>"
        else:
            size = f"{d['width']:g} × {d['height']:g} {d['size_unit']}"
            if d.get("quantity", 1) > 1:
                size += f", {d['quantity']} dona"

        def files(kind, flag):
            n = len(draft.files[kind])
            return f"{n} ta" if n else "<i>Yo'q</i>"

        return (
            "<b>Yangi ish — tekshiring:</b>\n\n"
            f"<b>Nomi:</b> {esc(d['title'])}\n"
            f"<b>Turi:</b> {esc(d['work_type'])}\n"
            f"<b>Qisqa ta'rif:</b> {val('short_desc', 'short_desc_none')}\n"
            f"<b>O'lchami:</b> {size}\n"
            f"<b>Rasm:</b> {files('image', 'image_none')}\n"
            f"<b>Qo'shimcha:</b> {val('extra_info', 'extra_info_none')}\n"
            f"<b>Logo:</b> {files('logo', 'logo_none')}\n"
            f"<b>Maxsus matn:</b> {val('special_text', 'special_text_none')}\n"
            f"<b>Fayllar:</b> {files('file', 'files_none')}"
        )

    async def _save(self, event, user: User, draft: Draft) -> None:
        with db_session() as db, ExitStack() as stack:
            form = dict(draft.data)
            for flag in NONE_FLAG.values():
                form[flag] = "1" if form.get(flag) else ""
            counts = {k: len(v) for k, v in draft.files.items()}
            cleaned, errors = works_svc.validate_work(db, form, counts)
            if errors:
                await event.respond("❌ Saqlanmadi:\n" + "\n".join(f"• {e}" for e in errors.values()))
                return
            uploads = {
                kind: [(name, stack.enter_context(open(path, "rb"))) for name, path in items]
                for kind, items in draft.files.items()
            }
            db_user = db.get(User, user.id)
            work = works_svc.create_work(db, db_user, cleaned, uploads, source="bot")
            work_id, link = work.id, works_svc.work_link(work)
        draft.cleanup()
        self.drafts.pop(event.sender_id, None)
        text = f"✅ Ish saqlandi: <b>#{work_id}</b>. Bosh dizaynerga yuborildi."
        if link:
            text += f'\n<a href="{link}">Saytda ochish</a>'
        await event.respond(text, parse_mode="html", buttons=self._menu(user), link_preview=False)

    # ------------------------------------------------------------ tugmalar
    async def on_callback(self, event) -> None:
        try:
            await self._on_callback(event)
        except Exception:
            log.exception("Bot callback xatosi")
            await event.answer("Xatolik yuz berdi", alert=True)

    async def _on_callback(self, event) -> None:
        data = event.data.decode()
        user = self._user_by_tg(event.sender_id)
        if user is None:
            await event.answer("Avval akkauntni bog'lang", alert=True)
            return
        draft = self.drafts.get(event.sender_id)

        if data.startswith("wt:"):
            if not draft or draft.step != "work_type":
                await event.answer()
                return
            with db_session() as db:
                types_ = works_svc.work_types(db)
            idx = int(data[3:])
            if idx >= len(types_):
                await event.answer("Qayta tanlang")
                return
            draft.data["work_type"] = types_[idx]
            await event.answer(types_[idx])
            await event.edit(f"2/9. Ish turi: <b>{esc(types_[idx])}</b>", parse_mode="html")
            self._next(draft)
            await self._ask(event, draft)
            return

        if data == "save":
            if not draft or draft.step != "confirm":
                await event.answer("Bu forma eskirgan")
                return
            await event.answer("Saqlanmoqda...")
            await event.edit(self._summary(draft), parse_mode="html")
            await self._save(event, user, draft)
            return

        if data == "cancel":
            if draft:
                draft.cleanup()
                self.drafts.pop(event.sender_id, None)
            await event.answer("Bekor qilindi")
            await event.edit("❌ Bekor qilindi.")
            await event.respond("Menyu:", buttons=self._menu(user))
            return

        if data.startswith("accept:"):
            await self._accept_menu(event, user, int(data.split(":")[1]))
            return

        if data.startswith("acc_to:"):
            _, work_id, designer_id = data.split(":")
            with db_session() as db:
                work = db.get(Work, int(work_id))
                db_user = db.get(User, user.id)
                if work is None:
                    await event.answer("Ish topilmadi", alert=True)
                    return
                try:
                    works_svc.apply_action(db, work, db_user, "accept", designer_id=int(designer_id))
                except works_svc.ActionError as exc:
                    await event.answer(str(exc), alert=True)
                    return
                designer_name = work.designer.full_name if work.designer else ""
                title = work.title
            await event.answer("Qabul qilindi")
            await event.edit(f"✅ #{work_id} «{esc(title)}» qabul qilindi.\nDizayner: <b>{esc(designer_name)}</b>",
                             parse_mode="html")
            return
        await event.answer()

    async def _accept_menu(self, event, user: User, work_id: int) -> None:
        with db_session() as db:
            work = db.get(Work, work_id)
            if work is None:
                await event.answer("Ish topilmadi", alert=True)
                return
            if not user.can_accept_work:
                await event.answer("Faqat bosh dizayner qabul qiladi", alert=True)
                return
            if work.status != "new":
                who = work.chief.full_name if work.chief else "—"
                await event.answer(f"Bu ish allaqachon: {work.status_name} ({who})", alert=True)
                return
            people = works_svc.designers(db)
            if user.is_admin and all(p.id != user.id for p in people):
                people.append(db.get(User, user.id))
        rows = [[Button.inline(("👤 " if p.id == user.id else "") + p.full_name,
                               f"acc_to:{work_id}:{p.id}".encode())] for p in people]
        await event.answer()
        await event.respond(f"#{work_id} uchun dizaynerni tanlang:", buttons=rows)


bot = Bot()
