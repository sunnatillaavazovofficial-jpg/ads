import hashlib
import hmac
import os

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import User

_ITER = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITER)
    return f"pbkdf2_sha256${_ITER}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


class LoginRequired(Exception):
    """Foydalanuvchi tizimga kirmagan."""


class Forbidden(Exception):
    """Ruxsat yo'q."""


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    uid = request.session.get("uid")
    if not uid:
        raise LoginRequired()
    user = await db.get(User, uid)
    if not user or not user.is_active:
        request.session.clear()
        raise LoginRequired()
    request.state.user = user
    return user


def require_roles(*roles: str):
    async def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise Forbidden()
        return user

    return dep


require_admin = require_roles("admin")
require_manager = require_roles("admin", "manager")
