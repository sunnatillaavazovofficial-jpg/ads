"""Telegram foydalanuvchi akkauntlarini ulash va tanlangan chatlarni kuzatish."""
import asyncio
import logging
import mimetypes
import secrets
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from telethon import TelegramClient, events, utils
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError,
    PasswordHashInvalidError,
    SessionPasswordNeededError,
)
from telethon.tl import types

from .. import config
from ..db import db_session
from ..models import TgAccount, TgChat, now

log = logging.getLogger("dizaynhub.tg")

DEVICE = dict(device_model="DizaynHub", system_version="Server", app_version="1.0")


def new_client(session_name: str) -> TelegramClient:
    return TelegramClient(
        str(config.TG_SESSION_DIR / session_name), config.TG_API_ID, config.TG_API_HASH, **DEVICE
    )


def media_kind(msg) -> Optional[str]:
    if msg.photo:
        return "photo"
    if msg.sticker:
        return "sticker"
    if msg.voice:
        return "voice"
    if msg.video_note:
        return "video_note"
    if msg.video or msg.gif:
        return "video"
    if msg.audio:
        return "audio"
    if msg.document:
        return "document"
    if msg.geo:
        return "geo"
    if msg.contact:
        return "contact"
    if msg.poll:
        return "poll"
    if msg.media and not isinstance(msg.media, types.MessageMediaWebPage):
        return "other"
    return None


MEDIA_LABELS = {
    "photo": "🖼 Rasm",
    "sticker": "Stiker",
    "voice": "🎤 Ovozli xabar",
    "video_note": "📹 Video xabar",
    "video": "🎬 Video",
    "audio": "🎵 Audio",
    "document": "📎 Fayl",
    "geo": "📍 Joylashuv",
    "contact": "👤 Kontakt",
    "poll": "📊 So'rovnoma",
    "other": "Media",
}


def preview_text(msg) -> str:
    kind = media_kind(msg)
    text = (msg.message or "").strip()
    if kind:
        label = MEDIA_LABELS.get(kind, "Media")
        if kind == "document" and msg.file and msg.file.name:
            label += f": {msg.file.name}"
        if kind == "sticker" and msg.file and msg.file.emoji:
            label += f" {msg.file.emoji}"
        return f"{label}" + (f" — {text}" if text else "")
    if msg.action:
        return "ℹ️ Xizmat xabari"
    return text


def message_dict(msg) -> dict:
    kind = media_kind(msg)
    sender = msg.sender
    file_name = ""
    file_size = 0
    if msg.file:
        file_name = msg.file.name or ""
        file_size = msg.file.size or 0
    fwd = ""
    if msg.fwd_from:
        fwd = getattr(msg.fwd_from, "from_name", None) or "boshqa chat"
    return {
        "id": msg.id,
        "out": bool(msg.out),
        "date": msg.date.astimezone().replace(tzinfo=None) if msg.date else None,
        "sender": utils.get_display_name(sender) if sender else "",
        "text": msg.message or "",
        "kind": kind,
        "label": MEDIA_LABELS.get(kind, "") if kind else "",
        "file_name": file_name,
        "file_size": file_size,
        "service": bool(msg.action),
        "forwarded": fwd,
        "reply_to": msg.reply_to_msg_id,
    }


def dialog_kind(entity) -> str:
    if isinstance(entity, types.User):
        return "bot" if entity.bot else "user"
    if isinstance(entity, types.Channel):
        return "group" if entity.megagroup else "channel"
    return "group"


@dataclass
class PendingLogin:
    client: TelegramClient
    phone: str
    session_name: str
    phone_code_hash: str = ""
    created: float = field(default_factory=time.time)


class TelegramManager:
    def __init__(self) -> None:
        self.clients: dict[int, TelegramClient] = {}
        self.status: dict[int, str] = {}
        self.tracked: dict[int, dict[int, int]] = {}  # account_id -> {peer_id: TgChat.id}
        self.pending: dict[str, PendingLogin] = {}

    @property
    def enabled(self) -> bool:
        return config.TELEGRAM_ENABLED

    # ------------------------------------------------------------ hayot sikli
    async def start(self) -> None:
        if not self.enabled:
            log.warning("Telegram o'chirilgan: .env faylida TG_API_ID va TG_API_HASH kiritilmagan")
            return
        with db_session() as db:
            accounts = list(db.scalars(select(TgAccount).where(TgAccount.is_active.is_(True))))
        for acc in accounts:
            await self._start_account(acc.id, acc.session_name)

    async def stop(self) -> None:
        for p in list(self.pending.values()):
            await self._safe_disconnect(p.client)
        self.pending.clear()
        for client in list(self.clients.values()):
            await self._safe_disconnect(client)
        self.clients.clear()

    @staticmethod
    async def _safe_disconnect(client: TelegramClient) -> None:
        try:
            await client.disconnect()
        except Exception:
            pass

    async def _start_account(self, account_id: int, session_name: str,
                             client: Optional[TelegramClient] = None) -> None:
        try:
            if client is None:
                client = new_client(session_name)
                await client.connect()
            if not await client.is_user_authorized():
                self.status[account_id] = "Sessiya tugagan — akkauntni qayta ulang"
                await self._safe_disconnect(client)
                return
            self.clients[account_id] = client
            self.refresh_tracked(account_id)
            async def handler(event, aid=account_id):
                await self._on_message(aid, event)

            client.add_event_handler(handler, events.NewMessage())
            self.status[account_id] = "online"
            # entity keshini to'ldirish uchun (orqa fonda)
            asyncio.get_running_loop().create_task(self._warm(client))
        except Exception as exc:
            log.exception("Akkaunt %s ulanmadi", account_id)
            self.status[account_id] = f"Xato: {exc}"

    @staticmethod
    async def _warm(client: TelegramClient) -> None:
        try:
            await client.get_dialogs(limit=200)
        except Exception as exc:
            log.info("Dialoglar yuklanmadi: %s", exc)

    def refresh_tracked(self, account_id: int) -> None:
        with db_session() as db:
            rows = db.execute(
                select(TgChat.peer_id, TgChat.id).where(TgChat.account_id == account_id)
            ).all()
        self.tracked[account_id] = {peer: cid for peer, cid in rows}

    async def _on_message(self, account_id: int, event) -> None:
        cid = self.tracked.get(account_id, {}).get(event.chat_id)
        if cid is None:
            return
        try:
            text = preview_text(event.message)
            if not event.out and event.is_group:
                sender = await event.get_sender()
                if sender:
                    text = f"{utils.get_display_name(sender)}: {text}"
            with db_session() as db:
                chat = db.get(TgChat, cid)
                if chat is None:
                    return
                chat.last_text = text[:500]
                chat.last_at = now()
                if not event.out:
                    chat.unread = (chat.unread or 0) + 1
                db.commit()
        except Exception:
            log.exception("Yangi xabarni saqlashda xato")

    # ------------------------------------------------------------ ulash
    def _cleanup_pending(self) -> None:
        cutoff = time.time() - 15 * 60
        for token, p in list(self.pending.items()):
            if p.created < cutoff:
                self.pending.pop(token, None)
                asyncio.get_running_loop().create_task(self._safe_disconnect(p.client))
                _remove_session_file(p.session_name)

    async def begin_login(self, phone: str) -> str:
        self._cleanup_pending()
        phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        if not phone.startswith("+"):
            phone = "+" + phone
        session_name = f"acc_{uuid.uuid4().hex[:12]}"
        client = new_client(session_name)
        await client.connect()
        try:
            sent = await client.send_code_request(phone)
        except PhoneNumberInvalidError:
            await self._safe_disconnect(client)
            _remove_session_file(session_name)
            raise LoginError("Telefon raqam noto'g'ri")
        except FloodWaitError as e:
            await self._safe_disconnect(client)
            _remove_session_file(session_name)
            raise LoginError(f"Telegram cheklovi: {e.seconds} soniyadan keyin urinib ko'ring")
        token = secrets.token_urlsafe(16)
        self.pending[token] = PendingLogin(client, phone, session_name, sent.phone_code_hash)
        return token

    def get_pending(self, token: str) -> Optional[PendingLogin]:
        return self.pending.get(token)

    async def submit_code(self, token: str, code: str) -> str:
        p = self.pending.get(token)
        if not p:
            raise LoginError("Sessiya topilmadi, qaytadan boshlang")
        code = "".join(ch for ch in code if ch.isdigit())
        try:
            await p.client.sign_in(p.phone, code, phone_code_hash=p.phone_code_hash)
        except SessionPasswordNeededError:
            return "password"
        except PhoneCodeInvalidError:
            raise LoginError("Kod noto'g'ri")
        except PhoneCodeExpiredError:
            raise LoginError("Kodning muddati o'tgan, qaytadan boshlang")
        await self._finish_login(token)
        return "ok"

    async def submit_password(self, token: str, password: str) -> None:
        p = self.pending.get(token)
        if not p:
            raise LoginError("Sessiya topilmadi, qaytadan boshlang")
        try:
            await p.client.sign_in(password=password)
        except PasswordHashInvalidError:
            raise LoginError("2FA parol noto'g'ri")
        await self._finish_login(token)

    async def _finish_login(self, token: str) -> None:
        p = self.pending.pop(token)
        me = await p.client.get_me()
        with db_session() as db:
            existing = db.scalars(select(TgAccount).where(TgAccount.tg_id == me.id)).first()
            if existing:
                # Avvalgi sessiyani yangisi bilan almashtiramiz
                old_client = self.clients.pop(existing.id, None)
                if old_client:
                    await self._safe_disconnect(old_client)
                _remove_session_file(existing.session_name)
                acc = existing
                acc.session_name = p.session_name
                acc.is_active = True
            else:
                acc = TgAccount(session_name=p.session_name, phone=p.phone)
                db.add(acc)
            acc.tg_id = me.id
            acc.phone = p.phone
            acc.display_name = utils.get_display_name(me)
            acc.username = me.username or ""
            db.commit()
            account_id = acc.id
        await self._start_account(account_id, p.session_name, client=p.client)

    async def cancel_login(self, token: str) -> None:
        p = self.pending.pop(token, None)
        if p:
            await self._safe_disconnect(p.client)
            _remove_session_file(p.session_name)

    async def remove_account(self, account_id: int, session_name: str) -> None:
        client = self.clients.pop(account_id, None)
        if client:
            try:
                await client.log_out()  # Telegramdagi faol sessiyani ham yopadi
            except Exception:
                await self._safe_disconnect(client)
        self.tracked.pop(account_id, None)
        self.status.pop(account_id, None)
        _remove_session_file(session_name)

    # ------------------------------------------------------------ o'qish
    def client_for(self, account_id: int) -> TelegramClient:
        client = self.clients.get(account_id)
        if client is None:
            raise LoginError(self.status.get(account_id) or "Akkaunt ulanmagan")
        return client

    async def _entity(self, client: TelegramClient, peer_id: int):
        try:
            return await client.get_input_entity(peer_id)
        except ValueError:
            await client.get_dialogs(limit=None)
            return await client.get_input_entity(peer_id)

    async def dialogs(self, account_id: int, limit: int = 400) -> list[dict]:
        client = self.client_for(account_id)
        result = []
        async for d in client.iter_dialogs(limit=limit):
            ent = d.entity
            result.append({
                "peer_id": d.id,
                "title": d.name or "(nomsiz)",
                "username": getattr(ent, "username", None) or "",
                "kind": dialog_kind(ent),
                "unread": d.unread_count,
                "last": preview_text(d.message) if d.message else "",
                "date": d.date.astimezone().replace(tzinfo=None) if d.date else None,
                "archived": d.archived,
            })
        return result

    async def messages(self, chat: TgChat, before: int = 0, after: int = 0, limit: int = 40) -> list[dict]:
        client = self.client_for(chat.account_id)
        entity = await self._entity(client, chat.peer_id)
        if after:
            msgs = await client.get_messages(entity, min_id=after, limit=100, reverse=True)
        else:
            msgs = await client.get_messages(entity, max_id=before or 0, limit=limit)
            msgs = list(reversed(msgs))
        return [message_dict(m) for m in msgs if m is not None]

    async def send_text(self, chat: TgChat, text: str) -> None:
        client = self.client_for(chat.account_id)
        entity = await self._entity(client, chat.peer_id)
        await client.send_message(entity, text)

    async def download(self, chat: TgChat, msg_id: int, thumb: bool = False) -> tuple[Path, str, str]:
        client = self.client_for(chat.account_id)
        entity = await self._entity(client, chat.peer_id)
        msg = await client.get_messages(entity, ids=msg_id)
        if msg is None or not msg.media:
            raise LoginError("Media topilmadi")
        size = msg.file.size if msg.file else 0
        if size and size > config.TG_MEDIA_MAX_MB * 1024 * 1024 and not thumb:
            raise LoginError(f"Fayl juda katta ({size // (1024 * 1024)} MB). Telegramning o'zidan oching.")
        ext = (msg.file.ext if msg.file else "") or ""
        if thumb:
            ext = ".jpg"
        name = (msg.file.name if msg.file and msg.file.name else f"telegram_{msg_id}{ext}")
        cache_dir = config.TG_CACHE_DIR / f"acc_{chat.account_id}" / str(abs(chat.peer_id))
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"{msg_id}{'_t' if thumb else ''}{ext}"
        if not path.exists():
            tmp = path.with_suffix(path.suffix + ".part")
            if thumb:
                got = await client.download_media(msg, file=str(tmp), thumb=-1)
            else:
                got = await client.download_media(msg, file=str(tmp))
            if not got:
                raise LoginError("Yuklab bo'lmadi")
            Path(got).replace(path)
        mime = (msg.file.mime_type if msg.file and not thumb else None) or \
            mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return path, name, mime


class LoginError(Exception):
    pass


def _remove_session_file(session_name: str) -> None:
    for suffix in (".session", ".session-journal"):
        p = config.TG_SESSION_DIR / f"{session_name}{suffix}"
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass


tg_manager = TelegramManager()
