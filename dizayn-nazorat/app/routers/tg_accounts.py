import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_admin
from ..constants import ACCOUNT_COLORS
from ..db import get_db
from ..models import TgAccount, TgChat, User
from ..tg.manager import TgError, manager
from ..web import redirect, render

router = APIRouter(prefix="/tg")
log = logging.getLogger("tg")


@router.get("/accounts")
async def accounts(request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    accs = (await db.execute(select(TgAccount).order_by(TgAccount.id))).scalars().all()
    counts = dict(
        (
            await db.execute(
                select(TgChat.account_id, func.count(TgChat.id))
                .where(TgChat.is_selected.is_(True))
                .group_by(TgChat.account_id)
            )
        ).all()
    )
    return render(
        request, "tg/accounts.html", accounts=accs, counts=counts, enabled=manager.enabled,
        online={a.id: manager.is_online(a.id) for a in accs}, colors=ACCOUNT_COLORS,
    )


@router.post("/accounts/add")
async def account_add(request: Request, user: User = Depends(require_admin)):
    form = await request.form()
    phone = (form.get("phone") or "").strip()
    if not phone:
        return redirect("/tg/accounts", "Telefon raqamni kiriting", request, "error")
    try:
        token = await manager.begin_login(phone)
    except TgError as e:
        return redirect("/tg/accounts", str(e), request, "error")
    return redirect(f"/tg/accounts/verify?token={token}")


@router.get("/accounts/verify")
async def verify_page(request: Request, token: str, user: User = Depends(require_admin)):
    p = manager.get_pending(token)
    if not p:
        return redirect("/tg/accounts", "Ulanish sessiyasi eskirgan, qaytadan boshlang", request, "error")
    return render(request, "tg/verify.html", token=token, phone=p.phone, need_password=p.need_password)


@router.post("/accounts/verify")
async def verify(request: Request, user: User = Depends(require_admin)):
    form = await request.form()
    token = form.get("token") or ""
    p = manager.get_pending(token)
    if not p:
        return redirect("/tg/accounts", "Ulanish sessiyasi eskirgan, qaytadan boshlang", request, "error")
    try:
        if p.need_password:
            acc = await manager.submit_password(token, form.get("password") or "")
        else:
            acc = await manager.submit_code(token, form.get("code") or "")
            if acc is None:
                return redirect(f"/tg/accounts/verify?token={token}", "Ikki bosqichli parolni kiriting", request)
    except TgError as e:
        if manager.get_pending(token):
            return redirect(f"/tg/accounts/verify?token={token}", str(e), request, "error")
        return redirect("/tg/accounts", str(e), request, "error")
    except Exception as e:
        log.exception("Login xatosi")
        return redirect("/tg/accounts", f"Xato: {e}", request, "error")
    return redirect(f"/tg/accounts/{acc.id}/chats", f"Akkaunt ulandi: {acc.name}. Endi kerakli chatlarni tanlang.", request)


@router.post("/accounts/{acc_id}/settings")
async def account_settings(acc_id: int, request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    acc = await db.get(TgAccount, acc_id)
    if not acc:
        raise HTTPException(404, "Akkaunt topilmadi")
    form = await request.form()
    acc.label = (form.get("label") or "").strip()[:64]
    if (form.get("color") or "").startswith("#"):
        acc.color = form["color"][:16]
    acc.auto_add_private = bool(form.get("auto_add_private"))
    await db.commit()
    await manager.refresh_selected(acc.id)
    return redirect("/tg/accounts", "Saqlandi", request)


@router.post("/accounts/{acc_id}/restart")
async def account_restart(acc_id: int, request: Request, user: User = Depends(require_admin)):
    try:
        await manager.restart_account(acc_id)
    except Exception as e:
        return redirect("/tg/accounts", f"Qayta ulanmadi: {e}", request, "error")
    return redirect("/tg/accounts", "Qayta ulandi", request)


@router.post("/accounts/{acc_id}/delete")
async def account_delete(acc_id: int, request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    acc = await db.get(TgAccount, acc_id)
    if not acc:
        raise HTTPException(404, "Akkaunt topilmadi")
    form = await request.form()
    await manager.remove_account(acc_id, logout=bool(form.get("logout")))
    await db.delete(acc)
    await db.commit()
    return redirect("/tg/accounts", "Akkaunt o'chirildi", request)


@router.get("/accounts/{acc_id}/chats")
async def account_chats(acc_id: int, request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    acc = await db.get(TgAccount, acc_id)
    if not acc:
        raise HTTPException(404, "Akkaunt topilmadi")
    selected = set(
        (
            await db.execute(select(TgChat.chat_id).where(TgChat.account_id == acc_id, TgChat.is_selected.is_(True)))
        ).scalars()
    )
    error = None
    dialogs = []
    try:
        dialogs = await manager.list_dialogs(acc_id)
    except TgError as e:
        error = str(e)
    except Exception as e:
        log.exception("Dialoglar olinmadi")
        error = f"Chatlar ro'yxatini olib bo'lmadi: {e}"
    return render(request, "tg/chats.html", acc=acc, dialogs=dialogs, selected=selected, error=error)


@router.post("/accounts/{acc_id}/chats")
async def account_chats_save(acc_id: int, request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    acc = await db.get(TgAccount, acc_id)
    if not acc:
        raise HTTPException(404, "Akkaunt topilmadi")
    form = await request.form()
    ids = set()
    for v in form.getlist("chat"):
        try:
            ids.add(int(v))
        except ValueError:
            pass
    try:
        await manager.save_selection(acc_id, ids)
    except TgError as e:
        return redirect(f"/tg/accounts/{acc_id}/chats", str(e), request, "error")
    return redirect("/inbox", f"{len(ids)} ta chat saralandi", request)
