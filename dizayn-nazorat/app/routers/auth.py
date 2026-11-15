import secrets

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user, hash_password, verify_password
from ..bot import runtime
from ..db import get_db
from ..models import User
from ..web import redirect, render

router = APIRouter()


@router.get("/login")
async def login_page(request: Request, next: str = "/"):
    if request.session.get("uid"):
        return redirect("/")
    return render(request, "login.html", next=next)


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(User).where(User.username == username.strip().lower()))
    user = res.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return render(request, "login.html", status_code=400, next=next, error="Login yoki parol noto'g'ri",
                      username=username)
    request.session.clear()
    request.session["uid"] = user.id
    if not next.startswith("/") or next.startswith("//"):
        next = "/"
    return redirect(next)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return redirect("/login")


@router.get("/profile")
async def profile(request: Request, user: User = Depends(current_user)):
    link = None
    if runtime.bot_username and user.link_code:
        link = f"https://t.me/{runtime.bot_username}?start={user.link_code}"
    return render(request, "profile.html", bot_username=runtime.bot_username, link=link)


@router.post("/profile/telegram-link")
async def telegram_link(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    user.link_code = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
    await db.commit()
    return redirect("/profile")


@router.post("/profile/telegram-unlink")
async def telegram_unlink(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    user.telegram_id = None
    user.telegram_username = None
    user.link_code = None
    await db.commit()
    return redirect("/profile", "Telegram uzildi", request)


@router.post("/profile")
async def profile_save(
    request: Request,
    full_name: str = Form(""),
    phone: str = Form(""),
    notify: str | None = Form(None),
    old_password: str = Form(""),
    new_password: str = Form(""),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    user.full_name = full_name.strip()[:128] or user.full_name
    user.phone = phone.strip()[:32] or None
    user.notify = bool(notify)
    if new_password:
        if not verify_password(old_password, user.password_hash):
            return redirect("/profile", "Eski parol noto'g'ri", request, "error")
        if len(new_password) < 6:
            return redirect("/profile", "Parol kamida 6 belgidan iborat bo'lsin", request, "error")
        user.password_hash = hash_password(new_password)
    await db.commit()
    return redirect("/profile", "Saqlandi", request)
