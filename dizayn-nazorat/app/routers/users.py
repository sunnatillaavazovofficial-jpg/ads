from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import hash_password, require_admin
from ..constants import ACTIVE_STATUSES, ROLES
from ..db import get_db
from ..models import Job, User
from ..web import redirect, render

router = APIRouter(prefix="/users")


@router.get("")
async def users_list(request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(User).order_by(User.is_active.desc(), User.role, User.full_name))).scalars().all()
    active = dict(
        (
            await db.execute(
                select(Job.designer_id, func.count(Job.id))
                .where(Job.status.in_(ACTIVE_STATUSES))
                .group_by(Job.designer_id)
            )
        ).all()
    )
    managed = dict(
        (
            await db.execute(
                select(Job.manager_id, func.count(Job.id))
                .where(Job.status.in_(ACTIVE_STATUSES))
                .group_by(Job.manager_id)
            )
        ).all()
    )
    return render(request, "users/list.html", users=users, active=active, managed=managed)


@router.get("/new")
async def user_new(request: Request, user: User = Depends(require_admin)):
    return render(request, "users/form.html", u=None)


@router.post("/new")
async def user_create(request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    form = await request.form()
    username = (form.get("username") or "").strip().lower()
    password = form.get("password") or ""
    role = form.get("role") if form.get("role") in ROLES else "designer"
    if not username or len(password) < 6:
        return render(request, "users/form.html", u=None, error="Login va kamida 6 belgili parol kiriting", form=form)
    exists = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if exists:
        return render(request, "users/form.html", u=None, error="Bu login band", form=form)
    db.add(
        User(
            username=username,
            full_name=(form.get("full_name") or "").strip()[:128],
            phone=(form.get("phone") or "").strip()[:32] or None,
            role=role,
            password_hash=hash_password(password),
        )
    )
    await db.commit()
    return redirect("/users", f"Foydalanuvchi qo'shildi: {username}", request)


@router.get("/{uid}")
async def user_edit(uid: int, request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    u = await db.get(User, uid)
    if not u:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    return render(request, "users/form.html", u=u)


@router.post("/{uid}")
async def user_update(uid: int, request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    u = await db.get(User, uid)
    if not u:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    form = await request.form()
    username = (form.get("username") or "").strip().lower()
    if username and username != u.username:
        exists = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if exists:
            return render(request, "users/form.html", u=u, error="Bu login band")
        u.username = username
    u.full_name = (form.get("full_name") or "").strip()[:128]
    u.phone = (form.get("phone") or "").strip()[:32] or None
    role = form.get("role")
    if role in ROLES and not (u.id == user.id and role != "admin"):
        u.role = role
    if u.id != user.id:
        u.is_active = bool(form.get("is_active"))
    if form.get("unlink_tg"):
        u.telegram_id = None
        u.telegram_username = None
    pw = form.get("password") or ""
    if pw:
        if len(pw) < 6:
            return render(request, "users/form.html", u=u, error="Parol kamida 6 belgi bo'lsin")
        u.password_hash = hash_password(pw)
    await db.commit()
    return redirect("/users", "Saqlandi", request)


@router.post("/{uid}/delete")
async def user_delete(uid: int, request: Request, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    u = await db.get(User, uid)
    if not u or u.id == user.id:
        return redirect("/users", "O'zingizni o'chira olmaysiz", request, "error")
    await db.delete(u)
    await db.commit()
    return redirect("/users", "Foydalanuvchi o'chirildi (uning ishlari saqlanib qoldi)", request)
