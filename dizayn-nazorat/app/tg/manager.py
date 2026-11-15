"""Bir nechta Telegram akkauntni (Telethon) boshqarish: ulash, chatlarni saralash,
xabarlarni qabul qilish va yuborish."""
from __future__ import annotations

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import func, select, update

from ..config import TG_API_HASH, TG_API_ID, TG_MARK_READ, TG_MEDIA_DIR
from ..constants import ACCOUNT_COLORS
from ..db import SessionLocal
from ..models import TgAccount, TgChat, TgMessage

log = logging.getLogger("tg")

try:  # Telethon o'rnatilmagan bo'lsa ham sayt ishlayversin
    from telethon import TelegramClient, events, types, utils
    from telethon.errors import (
        PasswordHashInvalidError,
        PhoneCodeExpiredError,
        PhoneCodeInvalidError,
        PhoneNumberInvalidError,
        SessionPasswordNeededError,
    )
    from telethon.sessions import StringSession

    HAVE_TELETHON = True
except ImportError:  # pragma: no cover
    HAVE_TELETHON = False


class TgError(Exception):
    pass


@dataclass
class PendingLogin:
    client: "TelegramClient"
    phone: str
    phone_code_hash: str
    created: float = field(default_factory=time.time)
    need_password: bool = False


def _short(text: str, n: int = 300) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _naive(dt):
    return dt.replace(tzinfo=None) if dt is not None and dt.tzinfo else dt


MEDIA_LABELS = {
    "photo": "🖼 Rasm",
    "video": "🎬 Video",
    "voice": "🎤 Ovozli xabar",
    "video_note": "⏺ Video xabar",
    "audio": "🎵 Audio",
    "document": "📎 Fayl",
    "sticker": "Stiker",
    "gif": "GIF",
    "geo": "📍 Joylashuv",
    "contact": "👤 Kontakt",
    "poll": "📊 So'rovnoma",
    "other": "Media",
}


class TgManager:
    def __init__(self):
        self.clients: dict[int, TelegramClient] = {}
        self.pending: dict[str, PendingLogin] = {}
        self.selected: dict[int, set[int]] = {}
        self.auto_add: dict[int, bool] = {}
        self.me_names: dict[int, str] = {}
        self._lock = asyncio.Lock()

    # ----------------------------- umumiy -----------------------------

    @property
    def enabled(self) -> bool:
        return HAVE_TELETHON and bool(TG_API_ID and TG_API_HASH)

    def _new_client(self, session: str = "") -> TelegramClient:
        return TelegramClient(
            StringSession(session),
            TG_API_ID,
            TG_API_HASH,
            device_model="Dizayn Nazorat CRM",
            system_version="Server",
            app_version="1.0",
            lang_code="uz",
            system_lang_code="uz",
        )

    def is_online(self, account_id: int) -> bool:
        c = self.clients.get(account_id)
        return bool(c and c.is_connected())

    async def start_all(self):
        if not self.enabled:
            log.info("Telegram akkauntlar o'chiq (TG_API_ID / TG_API_HASH berilmagan)")
            return
        async with SessionLocal() as db:
            res = await db.execute(select(TgAccount).where(TgAccount.is_active.is_(True)))
            accounts = res.scalars().all()
        for acc in accounts:
            try:
                await self.start_account(acc)
            except Exception as e:
                log.exception("Akkaunt %s ishga tushmadi", acc.phone)
                await self._set_state(acc.id, "error", str(e))

    async def stop_all(self):
        for c in list(self.clients.values()):
            try:
                await c.disconnect()
            except Exception:
                pass
        self.clients.clear()
        for p in list(self.pending.values()):
            try:
                await p.client.disconnect()
            except Exception:
                pass
        self.pending.clear()

    async def _set_state(self, account_id: int, state: str, error: str = ""):
        async with SessionLocal() as db:
            await db.execute(
                update(TgAccount).where(TgAccount.id == account_id).values(state=state, last_error=error[:1000])
            )
            await db.commit()

    async def start_account(self, acc: TgAccount):
        if acc.id in self.clients:
            return
        client = self._new_client(acc.session_string)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            await self._set_state(acc.id, "unauthorized", "Sessiya yaroqsiz. Akkauntni qayta ulang.")
            return
        me = await client.get_me()
        self.me_names[acc.id] = utils.get_display_name(me)
        self.auto_add[acc.id] = acc.auto_add_private
        await self.refresh_selected(acc.id)

        async def on_new(event, _aid=acc.id):
            try:
                await self._on_new_message(_aid, event)
            except Exception:
                log.exception("Yangi xabarni saqlashda xato")

        async def on_edit(event, _aid=acc.id):
            try:
                await self._on_edit(_aid, event)
            except Exception:
                log.exception("Tahrirlangan xabarni saqlashda xato")

        client.add_event_handler(on_new, events.NewMessage())
        client.add_event_handler(on_edit, events.MessageEdited())
        self.clients[acc.id] = client
        await self._set_state(acc.id, "ok")
        log.info("Telegram akkaunt ulandi: %s (%s)", acc.phone, self.me_names[acc.id])
        # Server o'chiq bo'lgan paytdagi xabarlarni tortib olish
        asyncio.create_task(self._initial_sync(acc.id))

    async def _initial_sync(self, account_id: int):
        client = self.clients.get(account_id)
        if not client:
            return
        try:
            # Entity keshini to'ldirish uchun
            await client.get_dialogs(limit=100)
        except Exception as e:
            log.warning("Dialoglarni olishda xato: %s", e)
        async with SessionLocal() as db:
            res = await db.execute(
                select(TgChat).where(TgChat.account_id == account_id, TgChat.is_selected.is_(True))
            )
            chats = res.scalars().all()
        for chat in chats:
            try:
                await self.sync_new(chat)
            except Exception as e:
                log.warning("Chat %s sinxronlanmadi: %s", chat.title, e)
            await asyncio.sleep(0.3)

    async def refresh_selected(self, account_id: int):
        async with SessionLocal() as db:
            res = await db.execute(
                select(TgChat.chat_id).where(TgChat.account_id == account_id, TgChat.is_selected.is_(True))
            )
            self.selected[account_id] = set(res.scalars().all())
            acc = await db.get(TgAccount, account_id)
            if acc:
                self.auto_add[account_id] = acc.auto_add_private

    def client(self, account_id: int) -> TelegramClient:
        c = self.clients.get(account_id)
        if not c:
            raise TgError("Akkaunt ulanmagan yoki ishlamayapti")
        return c

    # ----------------------------- login -----------------------------

    def _cleanup_pending(self):
        now = time.time()
        for token, p in list(self.pending.items()):
            if now - p.created > 900:
                self.pending.pop(token, None)
                asyncio.create_task(p.client.disconnect())

    async def begin_login(self, phone: str) -> str:
        if not self.enabled:
            raise TgError("TG_API_ID va TG_API_HASH sozlanmagan (.env faylini tekshiring)")
        self._cleanup_pending()
        phone = phone.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = "+" + phone
        client = self._new_client()
        await client.connect()
        try:
            sent = await client.send_code_request(phone)
        except PhoneNumberInvalidError:
            await client.disconnect()
            raise TgError("Telefon raqam noto'g'ri")
        except Exception as e:
            await client.disconnect()
            raise TgError(f"Kod yuborilmadi: {e}")
        token = secrets.token_urlsafe(16)
        self.pending[token] = PendingLogin(client=client, phone=phone, phone_code_hash=sent.phone_code_hash)
        return token

    def get_pending(self, token: str) -> PendingLogin | None:
        return self.pending.get(token)

    async def submit_code(self, token: str, code: str) -> TgAccount | None:
        """Kod to'g'ri bo'lsa akkauntni qaytaradi; 2FA parol kerak bo'lsa None."""
        p = self.pending.get(token)
        if not p:
            raise TgError("Ulanish sessiyasi eskirgan, qaytadan boshlang")
        code = "".join(ch for ch in code if ch.isdigit())
        try:
            await p.client.sign_in(phone=p.phone, code=code, phone_code_hash=p.phone_code_hash)
        except SessionPasswordNeededError:
            p.need_password = True
            return None
        except PhoneCodeInvalidError:
            raise TgError("Kod noto'g'ri")
        except PhoneCodeExpiredError:
            raise TgError("Kod eskirgan, qaytadan boshlang")
        return await self._finish_login(token)

    async def submit_password(self, token: str, password: str) -> TgAccount:
        p = self.pending.get(token)
        if not p:
            raise TgError("Ulanish sessiyasi eskirgan, qaytadan boshlang")
        try:
            await p.client.sign_in(password=password)
        except PasswordHashInvalidError:
            raise TgError("Parol noto'g'ri")
        return await self._finish_login(token)

    async def _finish_login(self, token: str) -> TgAccount:
        p = self.pending.pop(token)
        client = p.client
        me = await client.get_me()
        session_str = client.session.save()
        await client.disconnect()
        async with SessionLocal() as db:
            res = await db.execute(select(TgAccount).where(TgAccount.tg_user_id == me.id))
            acc = res.scalar_one_or_none()
            if acc is None:
                cnt = (await db.execute(select(func.count(TgAccount.id)))).scalar() or 0
                acc = TgAccount(phone=p.phone, color=ACCOUNT_COLORS[cnt % len(ACCOUNT_COLORS)])
                db.add(acc)
            acc.phone = p.phone
            acc.first_name = utils.get_display_name(me)
            acc.username = me.username
            acc.tg_user_id = me.id
            acc.session_string = session_str
            acc.is_active = True
            acc.state = "ok"
            acc.last_error = ""
            await db.commit()
            await db.refresh(acc)
        old = self.clients.pop(acc.id, None)
        if old:
            await old.disconnect()
        await self.start_account(acc)
        return acc

    async def remove_account(self, account_id: int, logout: bool = True):
        client = self.clients.pop(account_id, None)
        if client:
            try:
                if logout:
                    await client.log_out()
                else:
                    await client.disconnect()
            except Exception as e:
                log.warning("Log out xatosi: %s", e)
        self.selected.pop(account_id, None)

    async def restart_account(self, account_id: int):
        client = self.clients.pop(account_id, None)
        if client:
            await client.disconnect()
        async with SessionLocal() as db:
            acc = await db.get(TgAccount, account_id)
        if acc and acc.is_active:
            await self.start_account(acc)

    # ----------------------------- chatlar -----------------------------

    @staticmethod
    def _entity_info(entity) -> dict:
        if isinstance(entity, types.User):
            kind = "bot" if entity.bot else "user"
        elif isinstance(entity, types.Channel):
            kind = "group" if entity.megagroup or entity.gigagroup else "channel"
        else:
            kind = "group"
        return {
            "chat_id": utils.get_peer_id(entity),
            "access_hash": getattr(entity, "access_hash", None),
            "title": utils.get_display_name(entity) or "Nomsiz",
            "username": getattr(entity, "username", None),
            "phone": getattr(entity, "phone", None),
            "kind": kind,
        }

    async def list_dialogs(self, account_id: int, limit: int = 500) -> list[dict]:
        client = self.client(account_id)
        out = []
        async for d in client.iter_dialogs(limit=limit):
            info = self._entity_info(d.entity)
            info["unread"] = d.unread_count
            info["date"] = _naive(d.date)
            info["last"] = _short(d.message.message if d.message and d.message.message else "", 80)
            info["archived"] = bool(d.archived)
            out.append(info)
        return out

    async def save_selection(self, account_id: int, selected_ids: set[int]):
        """Saralangan chatlarni saqlash. Yangi tanlanganlar uchun oxirgi xabarlar tortiladi."""
        dialogs = {d["chat_id"]: d for d in await self.list_dialogs(account_id)}
        new_chats: list[TgChat] = []
        async with SessionLocal() as db:
            res = await db.execute(select(TgChat).where(TgChat.account_id == account_id))
            existing = {c.chat_id: c for c in res.scalars()}
            for cid, chat in existing.items():
                if cid not in dialogs:
                    # ro'yxatda ko'rinmagan (masalan avtomatik qo'shilgan) chatga tegmaymiz
                    continue
                want = cid in selected_ids
                if chat.is_selected != want:
                    chat.is_selected = want
                    if want:
                        new_chats.append(chat)
            for cid in selected_ids:
                if cid in existing or cid not in dialogs:
                    continue
                d = dialogs[cid]
                chat = TgChat(
                    account_id=account_id,
                    chat_id=cid,
                    access_hash=d["access_hash"],
                    title=d["title"][:255],
                    username=d["username"],
                    phone=d["phone"],
                    kind=d["kind"],
                    is_selected=True,
                    unread=d["unread"],
                    last_message_at=d["date"],
                    last_message_text=d["last"],
                )
                db.add(chat)
                new_chats.append(chat)
            await db.commit()
        await self.refresh_selected(account_id)
        for chat in new_chats:
            try:
                await self.fetch_history(chat, limit=40)
            except Exception as e:
                log.warning("Tarix olinmadi (%s): %s", chat.title, e)

    def input_peer(self, chat: TgChat):
        real_id, peer_cls = utils.resolve_id(chat.chat_id)
        if peer_cls is types.PeerUser:
            return types.InputPeerUser(real_id, chat.access_hash or 0)
        if peer_cls is types.PeerChat:
            return types.InputPeerChat(real_id)
        return types.InputPeerChannel(real_id, chat.access_hash or 0)

    async def _peer(self, chat: TgChat):
        if chat.access_hash or utils.resolve_id(chat.chat_id)[1] is types.PeerChat:
            return self.input_peer(chat)
        return await self.client(chat.account_id).get_input_entity(chat.chat_id)

    # ----------------------------- xabarlar -----------------------------

    def _msg_fields(self, account_id: int, m) -> dict:
        media_type = media_name = None
        media_size = None
        text = m.message or ""
        if m.media:
            if m.photo:
                media_type = "photo"
            elif m.sticker:
                media_type = "sticker"
                text = text or (m.file.emoji if m.file and m.file.emoji else "Stiker")
            elif m.voice:
                media_type = "voice"
            elif m.video_note:
                media_type = "video_note"
            elif m.gif:
                media_type = "gif"
            elif m.video:
                media_type = "video"
            elif m.audio:
                media_type = "audio"
            elif m.document:
                media_type = "document"
            elif m.geo:
                media_type = "geo"
                text = text or f"https://maps.google.com/?q={m.geo.lat},{m.geo.long}"
            elif m.contact:
                media_type = "contact"
                c = m.contact
                text = text or f"{c.first_name or ''} {c.last_name or ''} {c.phone_number or ''}".strip()
            elif m.poll:
                media_type = "poll"
                try:
                    text = text or str(m.poll.poll.question.text if hasattr(m.poll.poll.question, "text") else m.poll.poll.question)
                except Exception:
                    pass
            elif isinstance(m.media, types.MessageMediaWebPage):
                media_type = None
            else:
                media_type = "other"
            if m.file and media_type in ("photo", "video", "voice", "video_note", "audio", "document", "gif", "sticker"):
                media_name = m.file.name
                media_size = m.file.size
        if m.out:
            sender_name = self.me_names.get(account_id, "Siz")
        elif m.sender is not None:
            sender_name = utils.get_display_name(m.sender)
        else:
            sender_name = m.post_author or ""
        if m.action is not None and not text:
            text = f"[{type(m.action).__name__.replace('MessageAction', '')}]"
        return {
            "msg_id": m.id,
            "sender_id": m.sender_id,
            "sender_name": (sender_name or "")[:255],
            "out": bool(m.out),
            "text": text,
            "date": _naive(m.date),
            "media_type": media_type,
            "media_name": (media_name or None) and media_name[:255],
            "media_size": media_size,
        }

    @staticmethod
    def preview_text(fields: dict) -> str:
        label = MEDIA_LABELS.get(fields.get("media_type") or "", "")
        txt = fields.get("text") or ""
        if label and fields.get("media_type") not in ("geo", "contact", "sticker"):
            return _short(f"{label} {txt}".strip())
        return _short(txt or label)

    async def _store(self, db, chat: TgChat, fields: dict, sent_by_id: int | None = None) -> TgMessage | None:
        res = await db.execute(
            select(TgMessage).where(TgMessage.chat_id == chat.id, TgMessage.msg_id == fields["msg_id"])
        )
        if res.scalar_one_or_none():
            return None
        msg = TgMessage(chat_id=chat.id, sent_by_id=sent_by_id, **fields)
        db.add(msg)
        if chat.last_message_at is None or fields["date"] >= chat.last_message_at:
            chat.last_message_at = fields["date"]
            chat.last_message_text = self.preview_text(fields)
        return msg

    async def _on_new_message(self, account_id: int, event):
        chat_id = event.chat_id
        if chat_id is None:
            return
        if chat_id not in self.selected.get(account_id, set()):
            if not (self.auto_add.get(account_id) and event.is_private):
                return
            entity = await event.get_chat()
            if entity is None or getattr(entity, "bot", False) or getattr(entity, "is_self", False):
                return
            if isinstance(entity, types.User) and entity.id == 777000:  # Telegram xizmat xabarlari
                return
            info = self._entity_info(entity)
            async with SessionLocal() as db:
                res = await db.execute(
                    select(TgChat).where(TgChat.account_id == account_id, TgChat.chat_id == chat_id)
                )
                chat = res.scalar_one_or_none()
                if chat is None:
                    chat = TgChat(account_id=account_id, **info)
                    db.add(chat)
                chat.is_selected = True
                if not chat.access_hash and info["access_hash"]:
                    chat.access_hash = info["access_hash"]
                await db.commit()
            self.selected.setdefault(account_id, set()).add(chat_id)
        m = event.message
        if not m.out and m.sender is None:
            try:
                await event.get_sender()
            except Exception:
                pass
        fields = self._msg_fields(account_id, m)
        async with SessionLocal() as db:
            res = await db.execute(
                select(TgChat).where(TgChat.account_id == account_id, TgChat.chat_id == chat_id)
            )
            chat = res.scalar_one_or_none()
            if chat is None:
                return
            stored = await self._store(db, chat, fields)
            if stored and not m.out:
                chat.unread = (chat.unread or 0) + 1
            if stored and m.out:
                chat.unread = 0
            if not chat.access_hash:
                try:
                    ip = await event.get_input_chat()
                    chat.access_hash = getattr(ip, "access_hash", None)
                except Exception:
                    pass
            await db.commit()

    async def _on_edit(self, account_id: int, event):
        if event.chat_id not in self.selected.get(account_id, set()):
            return
        async with SessionLocal() as db:
            res = await db.execute(
                select(TgMessage)
                .join(TgChat, TgChat.id == TgMessage.chat_id)
                .where(
                    TgChat.account_id == account_id,
                    TgChat.chat_id == event.chat_id,
                    TgMessage.msg_id == event.message.id,
                )
            )
            msg = res.scalar_one_or_none()
            if msg:
                msg.text = event.message.message or msg.text
                await db.commit()

    async def fetch_history(self, chat: TgChat, limit: int = 40, offset_id: int = 0) -> int:
        """Telegramdan eski xabarlarni yuklab olish. Nechta yangi xabar saqlanganini qaytaradi."""
        client = self.client(chat.account_id)
        peer = await self._peer(chat)
        count = 0
        async with SessionLocal() as db:
            chat = await db.get(TgChat, chat.id)
            async for m in client.iter_messages(peer, limit=limit, offset_id=offset_id):
                if await self._store(db, chat, self._msg_fields(chat.account_id, m)):
                    count += 1
            await db.commit()
        return count

    async def sync_new(self, chat: TgChat):
        """Bazadagi oxirgi xabardan keyingi xabarlarni tortib olish."""
        client = self.client(chat.account_id)
        async with SessionLocal() as db:
            last = (
                await db.execute(select(func.max(TgMessage.msg_id)).where(TgMessage.chat_id == chat.id))
            ).scalar()
        if not last:
            await self.fetch_history(chat, limit=40)
            return
        peer = await self._peer(chat)
        async with SessionLocal() as db:
            chat = await db.get(TgChat, chat.id)
            new_in = 0
            async for m in client.iter_messages(peer, min_id=last, limit=200):
                if await self._store(db, chat, self._msg_fields(chat.account_id, m)) and not m.out:
                    new_in += 1
            chat.unread = (chat.unread or 0) + new_in
            await db.commit()

    async def send(self, chat: TgChat, text: str, file_path: Path | None = None, user_id: int | None = None,
                   file_name: str | None = None) -> TgMessage | None:
        client = self.client(chat.account_id)
        peer = await self._peer(chat)
        if file_path:
            m = await client.send_file(
                peer, str(file_path), caption=text or None, force_document=not _is_photo(file_name or file_path.name),
                attributes=_file_attrs(file_name),
            )
        else:
            m = await client.send_message(peer, text)
        if isinstance(m, list):
            m = m[0]
        fields = self._msg_fields(chat.account_id, m)
        async with SessionLocal() as db:
            chat = await db.get(TgChat, chat.id)
            msg = await self._store(db, chat, fields, sent_by_id=user_id)
            chat.unread = 0
            await db.commit()
            return msg

    async def mark_read(self, chat: TgChat):
        if not TG_MARK_READ:
            return
        try:
            client = self.client(chat.account_id)
            await client.send_read_acknowledge(await self._peer(chat))
        except Exception as e:
            log.debug("O'qildi belgisi qo'yilmadi: %s", e)

    async def download_media(self, msg: TgMessage, chat: TgChat) -> Path | None:
        if msg.media_path:
            p = TG_MEDIA_DIR / msg.media_path
            if p.exists():
                return p
        client = self.client(chat.account_id)
        peer = await self._peer(chat)
        tm = await client.get_messages(peer, ids=msg.msg_id)
        if not tm or not tm.media:
            return None
        folder = TG_MEDIA_DIR / str(chat.id)
        folder.mkdir(parents=True, exist_ok=True)
        path = await client.download_media(tm, file=str(folder / f"{msg.msg_id}_"))
        if not path:
            return None
        path = Path(path)
        async with SessionLocal() as db:
            m = await db.get(TgMessage, msg.id)
            if m:
                m.media_path = str(path.relative_to(TG_MEDIA_DIR))
                await db.commit()
        return path


def _is_photo(name: str) -> bool:
    return str(name).lower().endswith((".jpg", ".jpeg", ".png", ".webp"))


def _file_attrs(name: str | None):
    if not name:
        return None
    return [types.DocumentAttributeFilename(file_name=name)]


manager = TgManager()
