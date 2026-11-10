import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import TgAccount, TgChat, User, Work
from ..security import current_user, flash, require_admin
from ..tg.manager import LoginError, tg_manager
from ..web import accessible_chats, can_view_chat, redirect, render, templates

log = logging.getLogger("dizaynhub.tg")
router = APIRouter(prefix="/telegram")


def _require_tg(request: Request, user: User):
    if not request.state.nav_telegram:
        raise HTTPException(403, "Telegram bo'limiga ruxsat yo'q")


def _chat(db: Session, user: User, chat_id: int) -> TgChat:
    chat = db.get(TgChat, chat_id)
    if chat is None:
        raise HTTPException(404, "Chat topilmadi")
    if not can_view_chat(db, user, chat):
        raise HTTPException(403, "Bu chatni ko'rishga ruxsat yo'q")
    return chat


# ------------------------------------------------------------------ chatlar ro'yxati
@router.get("")
def index(request: Request, partial: int = 0, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_tg(request, user)
    chats = accessible_chats(db, user)
    accounts = {a.id: a for a in db.scalars(select(TgAccount))}
    ctx = dict(chats=chats, accounts=accounts, status=tg_manager.status, user=user)
    if partial:
        return templates.TemplateResponse(request, "_tg_chat_list.html", ctx)
    return render(request, "tg_index.html", enabled=tg_manager.enabled, **ctx)


# ------------------------------------------------------------------ akkauntlar (admin)
@router.get("/accounts")
def accounts(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(TgAccount).order_by(TgAccount.id)))
    managers = list(db.scalars(select(User).where(User.role.in_(["manager", "admin"]), User.is_active.is_(True))
                               .order_by(User.first_name)))
    counts = {a.id: len(a.chats) for a in rows}
    return render(request, "tg_accounts.html", accounts=rows, managers=managers, counts=counts,
                  status=tg_manager.status, enabled=tg_manager.enabled)


@router.post("/accounts/add")
async def account_add(request: Request, user: User = Depends(require_admin)):
    if not tg_manager.enabled:
        flash(request, ".env faylida TG_API_ID va TG_API_HASH kiritilmagan", "error")
        return redirect("/telegram/accounts")
    form = await request.form()
    phone = str(form.get("phone", "")).strip()
    if len([c for c in phone if c.isdigit()]) < 9:
        flash(request, "Telefon raqamni to'liq kiriting (+998...)", "error")
        return redirect("/telegram/accounts")
    try:
        token = await tg_manager.begin_login(phone)
    except LoginError as exc:
        flash(request, str(exc), "error")
        return redirect("/telegram/accounts")
    except Exception as exc:
        log.exception("Kod yuborilmadi")
        flash(request, f"Telegramga ulanib bo'lmadi: {exc}", "error")
        return redirect("/telegram/accounts")
    return redirect(f"/telegram/login/{token}")


@router.get("/login/{token}")
def login_step(token: str, request: Request, step: str = "code", user: User = Depends(require_admin)):
    pending = tg_manager.get_pending(token)
    if not pending:
        flash(request, "Ulanish sessiyasi topilmadi yoki eskirgan", "error")
        return redirect("/telegram/accounts")
    return render(request, "tg_login.html", token=token, phone=pending.phone, step=step)


@router.post("/login/{token}")
async def login_submit(token: str, request: Request, user: User = Depends(require_admin)):
    form = await request.form()
    if form.get("cancel"):
        await tg_manager.cancel_login(token)
        return redirect("/telegram/accounts")
    try:
        if form.get("password") is not None:
            await tg_manager.submit_password(token, str(form.get("password")))
        else:
            res = await tg_manager.submit_code(token, str(form.get("code", "")))
            if res == "password":
                return redirect(f"/telegram/login/{token}?step=password")
    except LoginError as exc:
        flash(request, str(exc), "error")
        if tg_manager.get_pending(token):
            step = "password" if form.get("password") is not None else "code"
            return redirect(f"/telegram/login/{token}?step={step}")
        return redirect("/telegram/accounts")
    flash(request, "Akkaunt ulandi! Endi kerakli chatlarni tanlang.")
    return redirect("/telegram/accounts")


@router.post("/accounts/{acc_id}/owner")
async def account_owner(acc_id: int, request: Request, user: User = Depends(require_admin),
                        db: Session = Depends(get_db)):
    acc = db.get(TgAccount, acc_id)
    if acc is None:
        raise HTTPException(404, "Akkaunt topilmadi")
    form = await request.form()
    owner = str(form.get("owner_user_id", ""))
    acc.owner_user_id = int(owner) if owner.isdigit() else None
    db.commit()
    flash(request, "Saqlandi")
    return redirect("/telegram/accounts")


@router.post("/accounts/{acc_id}/delete")
async def account_delete(acc_id: int, request: Request, user: User = Depends(require_admin),
                         db: Session = Depends(get_db)):
    acc = db.get(TgAccount, acc_id)
    if acc is None:
        raise HTTPException(404, "Akkaunt topilmadi")
    session_name = acc.session_name
    db.delete(acc)
    db.commit()
    await tg_manager.remove_account(acc_id, session_name)
    flash(request, "Akkaunt uzildi va o'chirildi")
    return redirect("/telegram/accounts")


# ------------------------------------------------------------------ chat tanlash
@router.get("/accounts/{acc_id}/dialogs")
async def dialogs(acc_id: int, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    acc = db.get(TgAccount, acc_id)
    if acc is None:
        raise HTTPException(404, "Akkaunt topilmadi")
    try:
        items = await tg_manager.dialogs(acc_id)
    except LoginError as exc:
        flash(request, str(exc), "error")
        return redirect("/telegram/accounts")
    except Exception as exc:
        log.exception("Dialoglar olinmadi")
        flash(request, f"Chatlar ro'yxatini olib bo'lmadi: {exc}", "error")
        return redirect("/telegram/accounts")
    tracked = {c.peer_id for c in acc.chats}
    return render(request, "tg_dialogs.html", acc=acc, items=items, tracked=tracked)


@router.post("/accounts/{acc_id}/dialogs")
async def dialogs_save(acc_id: int, request: Request, user: User = Depends(require_admin),
                       db: Session = Depends(get_db)):
    acc = db.get(TgAccount, acc_id)
    if acc is None:
        raise HTTPException(404, "Akkaunt topilmadi")
    form = await request.form()
    shown = {int(x) for x in form.getlist("shown") if str(x).lstrip("-").isdigit()}
    selected = {int(x) for x in form.getlist("peer") if str(x).lstrip("-").isdigit()}
    existing = {c.peer_id: c for c in acc.chats}
    added = removed = 0
    for peer in shown:
        if peer in selected and peer not in existing:
            db.add(TgChat(account_id=acc.id, peer_id=peer,
                          title=str(form.get(f"title_{peer}", ""))[:255],
                          username=str(form.get(f"username_{peer}", ""))[:100],
                          kind=str(form.get(f"kind_{peer}", "user"))[:10],
                          last_text=str(form.get(f"last_{peer}", ""))[:500]))
            added += 1
        elif peer not in selected and peer in existing:
            db.delete(existing[peer])
            removed += 1
    db.commit()
    tg_manager.refresh_tracked(acc.id)
    flash(request, f"Saqlandi: {added} ta qo'shildi, {removed} ta olib tashlandi")
    return redirect("/telegram")


# ------------------------------------------------------------------ chatni ko'rish
@router.get("/chat/{chat_id}")
async def chat_view(chat_id: int, request: Request, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    _require_tg(request, user)
    chat = _chat(db, user, chat_id)
    error = ""
    msgs = []
    try:
        msgs = await tg_manager.messages(chat)
    except LoginError as exc:
        error = str(exc)
    except Exception as exc:
        log.exception("Xabarlar olinmadi")
        error = f"Xabarlarni olib bo'lmadi: {exc}"
    chat.unread = 0
    db.commit()
    works = list(db.scalars(select(Work).where(Work.tg_chat_id == chat.id).order_by(Work.id.desc()).limit(20)))
    others = accessible_chats(db, user)
    return render(request, "tg_chat.html", chat=chat, msgs=msgs, error=error, works=works, others=others,
                  account=db.get(TgAccount, chat.account_id))


@router.get("/chat/{chat_id}/messages")
async def chat_messages(chat_id: int, request: Request, after: int = 0, before: int = 0,
                        user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_tg(request, user)
    chat = _chat(db, user, chat_id)
    try:
        msgs = await tg_manager.messages(chat, before=before, after=after)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    if after and msgs:
        chat.unread = 0
        db.commit()
    html = templates.get_template("_tg_messages.html").render(msgs=msgs, chat=chat)
    return {"html": html, "count": len(msgs),
            "first_id": msgs[0]["id"] if msgs else None, "last_id": msgs[-1]["id"] if msgs else None}


@router.post("/chat/{chat_id}/send")
async def chat_send(chat_id: int, request: Request, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    _require_tg(request, user)
    chat = _chat(db, user, chat_id)
    form = await request.form()
    text = str(form.get("text", "")).strip()
    if text:
        try:
            await tg_manager.send_text(chat, text[:4096])
        except Exception as exc:
            if request.headers.get("x-requested-with") == "fetch":
                return JSONResponse({"error": str(exc)}, status_code=502)
            flash(request, f"Yuborilmadi: {exc}", "error")
    if request.headers.get("x-requested-with") == "fetch":
        return {"ok": True}
    return redirect(f"/telegram/chat/{chat_id}")


@router.post("/chat/{chat_id}/note")
async def chat_note(chat_id: int, request: Request, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    _require_tg(request, user)
    chat = _chat(db, user, chat_id)
    form = await request.form()
    chat.note = str(form.get("note", "")).strip()[:255]
    db.commit()
    return redirect(f"/telegram/chat/{chat_id}")


@router.post("/chat/{chat_id}/untrack")
def chat_untrack(chat_id: int, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    chat = _chat(db, user, chat_id)
    acc_id = chat.account_id
    db.delete(chat)
    db.commit()
    tg_manager.refresh_tracked(acc_id)
    flash(request, "Chat kuzatuvdan olib tashlandi")
    return redirect("/telegram")


@router.get("/media/{chat_id}/{msg_id}")
async def media(chat_id: int, msg_id: int, request: Request, thumb: int = 0, dl: int = 0,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_tg(request, user)
    chat = _chat(db, user, chat_id)
    try:
        path, name, mime = await tg_manager.download(chat, msg_id, thumb=bool(thumb))
    except LoginError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        log.exception("Media yuklanmadi")
        raise HTTPException(502, f"Media yuklanmadi: {exc}")
    inline = not dl and (mime.startswith("image/") or mime.startswith("video/") or mime.startswith("audio/")
                         or mime == "application/pdf")
    headers = {"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"}
    if mime != "application/pdf":
        headers["Content-Security-Policy"] = "sandbox"
    return FileResponse(path, media_type=mime, filename=name,
                        content_disposition_type="inline" if inline else "attachment", headers=headers)

