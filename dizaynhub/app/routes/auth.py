import secrets

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import (
    current_user,
    current_user_optional,
    flash,
    hash_password,
    make_login,
    normalize_login,
    verify_password,
)
from ..services.settings import role_for_key
from ..tg.bot import bot
from ..web import redirect, render

router = APIRouter()


def _safe_next(url: str) -> str:
    return url if url and url.startswith("/") and not url.startswith("//") else "/"


@router.get("/login")
def login_page(request: Request, next: str = "/", user=Depends(current_user_optional)):
    if user:
        return redirect(_safe_next(next))
    return render(request, "login.html", next=next, login="")


@router.post("/login")
async def login_submit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    login = make_login(str(form.get("login", "")))
    password = str(form.get("password", ""))
    nxt = _safe_next(str(form.get("next", "/")))
    user = db.scalars(select(User).where(User.login == login)).first()
    if not user or not verify_password(password, user.password_hash):
        return render(request, "login.html", status_code=400, next=nxt, login=form.get("login", ""),
                      error="Login (Ism Familiya) yoki parol noto'g'ri")
    if not user.is_active:
        return render(request, "login.html", status_code=403, next=nxt, login=form.get("login", ""),
                      error="Akkauntingiz bloklangan. Admin bilan bog'laning.")
    request.session.clear()
    request.session["uid"] = user.id
    return redirect(nxt)


@router.get("/register")
def register_page(request: Request):
    return render(request, "register.html", form={}, errors={})


@router.post("/register")
async def register_submit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = {k: str(form.get(k, "")).strip() for k in ("key", "first_name", "last_name")}
    password = str(form.get("password", ""))
    password2 = str(form.get("password2", ""))
    errors = {}
    role = role_for_key(db, data["key"])
    if not role:
        errors["key"] = "Kalit noto'g'ri"
    if len(data["first_name"]) < 2:
        errors["first_name"] = "Ismni kiriting"
    if len(data["last_name"]) < 2:
        errors["last_name"] = "Familiyani kiriting"
    if len(password) < 6:
        errors["password"] = "Parol kamida 6 belgidan iborat bo'lsin"
    elif password != password2:
        errors["password2"] = "Parollar mos emas"
    login = normalize_login(data["first_name"], data["last_name"])
    if not errors and db.scalars(select(User).where(User.login == login)).first():
        errors["first_name"] = "Bu ism-familiya bilan foydalanuvchi bor. Admin bilan bog'laning."
    if errors:
        return render(request, "register.html", status_code=400, form=data, errors=errors)
    first = " ".join(data["first_name"].split())
    last = " ".join(data["last_name"].split())
    user = User(first_name=first[:1].upper() + first[1:], last_name=last[:1].upper() + last[1:],
                login=login, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    request.session.clear()
    request.session["uid"] = user.id
    flash(request, f"Xush kelibsiz, {user.full_name}! Rolingiz: {user.role_name}. "
                   f"Keyingi safar login sifatida «{user.full_name}» ni kiriting.")
    return redirect("/")


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")


@router.get("/profile")
def profile(request: Request, user: User = Depends(current_user)):
    bot_link = ""
    if bot.username and user.tg_link_code:
        bot_link = f"https://t.me/{bot.username}?start={user.tg_link_code}"
    return render(request, "profile.html", bot_username=bot.username, bot_link=bot_link)


@router.post("/profile/password")
async def change_password(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    form = await request.form()
    old, new, new2 = (str(form.get(k, "")) for k in ("old", "new", "new2"))
    if not verify_password(old, user.password_hash):
        flash(request, "Joriy parol noto'g'ri", "error")
    elif len(new) < 6:
        flash(request, "Yangi parol kamida 6 belgi bo'lsin", "error")
    elif new != new2:
        flash(request, "Yangi parollar mos emas", "error")
    else:
        user.password_hash = hash_password(new)
        db.commit()
        flash(request, "Parol o'zgartirildi")
    return redirect("/profile")


@router.post("/profile/tg-link")
def tg_link(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.tg_link_code = secrets.token_hex(5).upper()
    db.commit()
    return redirect("/profile")


@router.post("/profile/tg-unlink")
def tg_unlink(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.tg_user_id = None
    user.tg_link_code = None
    db.commit()
    flash(request, "Telegram bog'lanishi o'chirildi")
    return redirect("/profile")
