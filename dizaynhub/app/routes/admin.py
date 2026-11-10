from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ROLES, User, WorkType
from ..security import flash, hash_password, require_admin
from ..services.settings import KEY_ROLES, role_keys, set_setting
from ..web import redirect, render

router = APIRouter(prefix="/admin")


@router.get("/users")
def users(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(User).order_by(User.role, User.first_name, User.last_name)))
    return render(request, "admin_users.html", users=rows)


def _admin_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))) or 0


@router.post("/users/{user_id}")
async def user_update(user_id: int, request: Request, user: User = Depends(require_admin),
                      db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    form = await request.form()
    role = str(form.get("role", target.role))
    active = bool(form.get("is_active"))
    if target.role == "admin" and (role != "admin" or not active) and _admin_count(db) <= 1:
        flash(request, "Oxirgi adminni o'zgartirib bo'lmaydi", "error")
        return redirect("/admin/users")
    if role in ROLES:
        target.role = role
    target.is_active = active
    db.commit()
    flash(request, f"{target.full_name}: saqlandi")
    return redirect("/admin/users")


@router.post("/users/{user_id}/password")
async def user_password(user_id: int, request: Request, user: User = Depends(require_admin),
                        db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    form = await request.form()
    pwd = str(form.get("password", ""))
    if len(pwd) < 6:
        flash(request, "Parol kamida 6 belgi", "error")
    else:
        target.password_hash = hash_password(pwd)
        db.commit()
        flash(request, f"{target.full_name}: yangi parol o'rnatildi")
    return redirect("/admin/users")


@router.post("/users/{user_id}/delete")
def user_delete(user_id: int, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    if target.id == user.id:
        flash(request, "O'zingizni o'chira olmaysiz", "error")
        return redirect("/admin/users")
    db.delete(target)
    db.commit()
    flash(request, f"{target.full_name} o'chirildi (uning ishlari saqlanib qoladi)")
    return redirect("/admin/users")


@router.get("/settings")
def settings(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    types = list(db.scalars(select(WorkType).order_by(WorkType.sort, WorkType.name)))
    return render(request, "admin_settings.html", keys=role_keys(db), types=types)


@router.post("/settings/keys")
async def settings_keys(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    form = await request.form()
    values = {r: str(form.get(f"key_{r}", "")).strip() for r in KEY_ROLES}
    if any(len(v) < 4 for v in values.values()):
        flash(request, "Har bir kalit kamida 4 belgidan iborat bo'lsin", "error")
        return redirect("/admin/settings")
    if len(set(values.values())) != len(values):
        flash(request, "Kalitlar bir-biridan farq qilishi kerak", "error")
        return redirect("/admin/settings")
    for r, v in values.items():
        set_setting(db, f"key_{r}", v)
    db.commit()
    flash(request, "Kalitlar saqlandi")
    return redirect("/admin/settings")


@router.post("/settings/types")
async def type_add(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    form = await request.form()
    name = str(form.get("name", "")).strip()[:100]
    if name:
        top = db.scalar(select(func.max(WorkType.sort))) or 0
        db.add(WorkType(name=name, sort=top + 1))
        try:
            db.commit()
            flash(request, f"«{name}» qo'shildi")
        except IntegrityError:
            db.rollback()
            flash(request, "Bunday tur bor", "error")
    return redirect("/admin/settings#turlar")


@router.post("/settings/types/{type_id}/delete")
def type_delete(type_id: int, request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    t = db.get(WorkType, type_id)
    if t:
        db.delete(t)
        db.commit()
        flash(request, f"«{t.name}» o'chirildi (eski ishlarda nomi saqlanib qoladi)")
    return redirect("/admin/settings#turlar")
