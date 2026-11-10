"""Jinja2 shablonlari va umumiy yordamchilar."""
from pathlib import Path
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .models import ROLES, SIZE_UNITS, STATUSES, TgAccount, TgChat, User
from .security import pop_flashes
from .utils import dt, money, num

TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
env = templates.env
env.filters["money"] = money
env.filters["num"] = num
env.filters["dt"] = dt
env.filters["date"] = lambda v: dt(v, with_time=False)
env.filters["urlq"] = lambda v: quote(str(v or ""))
env.globals.update(
    SITE_NAME=config.SITE_NAME,
    STATUSES=STATUSES,
    ROLES=ROLES,
    SIZE_UNITS=SIZE_UNITS,
    TELEGRAM_ENABLED=config.TELEGRAM_ENABLED,
)


def render(request: Request, name: str, status_code: int = 200, **ctx):
    user = getattr(request.state, "user", None)
    ctx.setdefault("user", user)
    ctx.setdefault("flashes", pop_flashes(request))
    ctx.setdefault("nav_telegram", getattr(request.state, "nav_telegram", False))
    ctx["path"] = request.url.path
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


# --------------------------------------------------------------- Telegram ruxsat

def tg_account_ids_for(db: Session, user: User) -> list[int]:
    q = select(TgAccount.id)
    if not user.is_admin:
        q = q.where(TgAccount.owner_user_id == user.id)
    return list(db.scalars(q))


def can_view_chat(db: Session, user: User, chat: TgChat) -> bool:
    if user.is_admin:
        return True
    acc = db.get(TgAccount, chat.account_id)
    return bool(acc and acc.owner_user_id == user.id)


def accessible_chats(db: Session, user: User) -> list[TgChat]:
    ids = tg_account_ids_for(db, user)
    if not ids:
        return []
    return list(db.scalars(
        select(TgChat).where(TgChat.account_id.in_(ids)).order_by(TgChat.last_at.desc().nulls_last(), TgChat.title)
    ))
