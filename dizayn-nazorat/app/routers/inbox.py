"""Barcha saralangan Telegram chatlar bitta joyda (yagona inbox)."""
import logging
import mimetypes
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from ..auth import require_manager
from ..config import MAX_UPLOAD_MB, TMP_DIR
from ..constants import FILE_KINDS
from ..db import get_db
from ..models import Job, TgAccount, TgChat, TgMessage, User
from ..services import add_event, register_local_file, secure_filename
from ..tg.manager import MEDIA_LABELS, TgError, manager
from ..web import render
from .files import _disposition

router = APIRouter()
log = logging.getLogger("inbox")


def _iso(dt):
    return dt.isoformat() + "Z" if dt else None


def chat_json(c: TgChat) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "username": c.username,
        "phone": c.phone,
        "kind": c.kind,
        "unread": c.unread or 0,
        "last_at": _iso(c.last_message_at),
        "last_text": c.last_message_text,
        "account": {"id": c.account.id, "name": c.account.name, "color": c.account.color} if c.account else None,
    }


def msg_json(m: TgMessage) -> dict:
    return {
        "id": m.id,
        "msg_id": m.msg_id,
        "out": m.out,
        "sender": m.sender_name,
        "text": m.text,
        "date": _iso(m.date),
        "media_type": m.media_type,
        "media_label": MEDIA_LABELS.get(m.media_type or "", ""),
        "media_name": m.media_name,
        "media_size": m.media_size,
    }


async def _chat(db: AsyncSession, chat_id: int) -> TgChat:
    c = await db.get(TgChat, chat_id)
    if not c:
        raise HTTPException(404, "Chat topilmadi")
    return c


@router.get("/inbox")
async def inbox_page(request: Request, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    accounts = (await db.execute(select(TgAccount).order_by(TgAccount.id))).scalars().all()
    return render(
        request, "tg/inbox.html", accounts=accounts, enabled=manager.enabled,
        open_chat=request.query_params.get("chat"), file_kinds=FILE_KINDS, max_mb=MAX_UPLOAD_MB,
    )


@router.get("/api/inbox/chats")
async def api_chats(user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(TgChat)
        .join(TgAccount, TgAccount.id == TgChat.account_id)
        .where(TgChat.is_selected.is_(True), TgAccount.is_active.is_(True))
        .order_by(TgChat.last_message_at.is_(None), TgChat.last_message_at.desc())
    )
    chats = res.scalars().all()
    return {
        "chats": [chat_json(c) for c in chats],
        "online": {str(a): manager.is_online(a) for a in {c.account_id for c in chats}},
    }


@router.get("/api/inbox/chats/{chat_id}/messages")
async def api_messages(
    chat_id: int, after: int = 0, before: int = 0, user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    chat = await _chat(db, chat_id)
    q = select(TgMessage).where(TgMessage.chat_id == chat.id)
    if after:
        q = q.where(TgMessage.id > after).order_by(TgMessage.date.asc(), TgMessage.id.asc()).limit(200)
        msgs = (await db.execute(q)).scalars().all()
    else:
        if before:
            ref = await db.get(TgMessage, before)
            if ref:
                q = q.where(TgMessage.date <= ref.date, TgMessage.id != ref.id)
        q = q.order_by(TgMessage.date.desc(), TgMessage.id.desc()).limit(60)
        msgs = list(reversed((await db.execute(q)).scalars().all()))
    if not before and chat.unread:
        chat.unread = 0
        await db.commit()
        if manager.is_online(chat.account_id):
            await manager.mark_read(chat)
    return {"chat": chat_json(chat), "messages": [msg_json(m) for m in msgs]}


@router.post("/api/inbox/chats/{chat_id}/older")
async def api_older(chat_id: int, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    """Telegramdan eskiroq xabarlarni yuklab olish."""
    chat = await _chat(db, chat_id)
    oldest = (
        await db.execute(
            select(TgMessage.msg_id).where(TgMessage.chat_id == chat.id).order_by(TgMessage.msg_id.asc()).limit(1)
        )
    ).scalar()
    try:
        n = await manager.fetch_history(chat, limit=50, offset_id=oldest or 0)
    except TgError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        log.exception("Tarix olinmadi")
        return JSONResponse({"error": str(e)}, status_code=500)
    return {"ok": True, "count": n}


@router.post("/api/inbox/chats/{chat_id}/send")
async def api_send(chat_id: int, request: Request, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    chat = await _chat(db, chat_id)
    form = await request.form()
    text = (form.get("text") or "").strip()
    up = form.get("file")
    tmp = None
    fname = None
    try:
        if isinstance(up, UploadFile) and up.filename:
            fname = up.filename
            tmp = TMP_DIR / f"send_{uuid.uuid4().hex}_{secure_filename(up.filename)}"
            size = 0
            with open(tmp, "wb") as fh:
                while chunk := await up.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_MB * 1024 * 1024:
                        return JSONResponse({"error": f"Fayl {MAX_UPLOAD_MB} MB dan katta"}, status_code=400)
                    fh.write(chunk)
        if not text and not tmp:
            return JSONResponse({"error": "Xabar bo'sh"}, status_code=400)
        msg = await manager.send(chat, text, file_path=tmp, user_id=user.id, file_name=fname)
    except TgError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        log.exception("Xabar yuborilmadi")
        return JSONResponse({"error": f"Yuborilmadi: {e}"}, status_code=500)
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)
    return {"ok": True, "message": msg_json(msg) if msg else None}


@router.post("/api/inbox/chats/{chat_id}/hide")
async def api_hide(chat_id: int, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    chat = await _chat(db, chat_id)
    chat.is_selected = False
    await db.commit()
    await manager.refresh_selected(chat.account_id)
    return {"ok": True}


@router.get("/inbox/media/{message_id}")
async def media(message_id: int, download: int = 0, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    msg = await db.get(TgMessage, message_id)
    if not msg or not msg.media_type:
        raise HTTPException(404, "Media topilmadi")
    chat = await db.get(TgChat, msg.chat_id)
    try:
        path = await manager.download_media(msg, chat)
    except TgError as e:
        raise HTTPException(503, str(e))
    if not path or not path.exists():
        raise HTTPException(404, "Media yuklab bo'lmadi")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    name = msg.media_name or path.name.split("_", 1)[-1]
    inline = not download and (mime.startswith(("image/", "video/", "audio/")) or mime == "application/pdf")
    return FileResponse(path, media_type=mime, headers={
        "Content-Disposition": _disposition(name, inline), "Cache-Control": "private, max-age=86400",
    })


@router.post("/api/inbox/messages/{message_id}/attach")
async def attach_to_job(message_id: int, request: Request, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    """Chatdagi fayl/rasmni ishga biriktirish."""
    data = await request.json()
    try:
        job_id = int(str(data.get("job_id", "")).lstrip("#"))
    except ValueError:
        return JSONResponse({"error": "Ish raqamini to'g'ri kiriting"}, status_code=400)
    kind = data.get("kind") if data.get("kind") in FILE_KINDS else "logo"
    job = await db.get(Job, job_id)
    if not job:
        return JSONResponse({"error": f"#{job_id} ish topilmadi"}, status_code=404)
    msg = await db.get(TgMessage, message_id)
    if not msg or not msg.media_type:
        return JSONResponse({"error": "Xabarda fayl yo'q"}, status_code=400)
    chat = await db.get(TgChat, msg.chat_id)
    try:
        path = await manager.download_media(msg, chat)
    except TgError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if not path:
        return JSONResponse({"error": "Faylni yuklab bo'lmadi"}, status_code=400)
    name = msg.media_name or path.name.split("_", 1)[-1]
    jf = register_local_file(job.id, path, name, kind, user.id, move=False)
    db.add(jf)
    add_event(db, job, user, "file", f"Telegram chatdan fayl biriktirildi ({FILE_KINDS[kind]}): {name}")
    await db.commit()
    return {"ok": True, "job_id": job.id, "title": job.title}
