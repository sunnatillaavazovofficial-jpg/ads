"""Parol hash, sessiya, ruxsatlar."""
import base64
import hashlib
import hmac
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import TgAccount, User

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return "scrypt${}${}".format(base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_b64, dk_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def normalize_login(first_name: str, last_name: str) -> str:
    return make_login(f"{first_name} {last_name}")


def make_login(text: str) -> str:
    # Apostroflarni bir xil ko'rinishga keltiramiz (o‘, oʻ, o' ...)
    for ch in ("‘", "’", "ʻ", "ʼ", "`", "´"):
        text = text.replace(ch, "'")
    return " ".join(text.strip().lower().split())


class LoginRequired(Exception):
    pass


def current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    uid = request.session.get("uid")
    if not uid:
        return None
    user = db.get(User, uid)
    if not user or not user.is_active:
        request.session.clear()
        return None
    return user


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user_optional(request, db)
    if user is None:
        raise LoginRequired()
    request.state.user = user
    if user.is_admin:
        request.state.nav_telegram = True
    else:
        request.state.nav_telegram = db.scalars(
            select(TgAccount.id).where(TgAccount.owner_user_id == user.id).limit(1)
        ).first() is not None
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Bu bo'lim uchun ruxsat yo'q")
        return user

    return dep


require_admin = require_roles("admin")


def flash(request: Request, message: str, kind: str = "ok") -> None:
    msgs = request.session.get("_flash", [])
    msgs.append([kind, message])
    request.session["_flash"] = msgs


def pop_flashes(request: Request) -> list:
    return request.session.pop("_flash", [])
