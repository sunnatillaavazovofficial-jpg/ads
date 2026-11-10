"""Telegram bot orqali bildirishnomalar.

Bot ishga tushganda `set_sender` chaqiriladi. Saytning sinxron
(thread) qismidan ham, asinxron qismidan ham xavfsiz chaqirish mumkin.
"""
import asyncio
import logging
from typing import Awaitable, Callable, Iterable, Optional

from sqlalchemy import select

from ..db import db_session
from ..models import User

log = logging.getLogger("dizaynhub")

# sender(chat_id, text, buttons) -> coroutine
_sender: Optional[Callable[..., Awaitable]] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_tasks: set = set()


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def set_sender(sender: Optional[Callable[..., Awaitable]]) -> None:
    global _sender
    _sender = sender


def _schedule(coro) -> None:
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None and running is _loop:
        task = running.create_task(coro)
        _tasks.add(task)  # vazifa tugaguncha havolani saqlaymiz
        task.add_done_callback(_tasks.discard)
    elif _loop is not None and _loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, _loop)
    else:
        coro.close()


async def _send_many(chat_ids: list, text: str, buttons) -> None:
    for cid in chat_ids:
        try:
            await _sender(cid, text, buttons)
        except Exception as exc:
            log.info("Bildirishnoma yuborilmadi (%s): %s", cid, exc)


def notify_users(user_ids: Iterable[Optional[int]], text: str, buttons=None, exclude: Optional[int] = None) -> None:
    if _sender is None:
        return
    ids = {u for u in user_ids if u and u != exclude}
    if not ids:
        return
    with db_session() as db:
        chat_ids = [
            u.tg_user_id
            for u in db.scalars(select(User).where(User.id.in_(ids), User.is_active.is_(True)))
            if u.tg_user_id
        ]
    if chat_ids:
        _schedule(_send_many(chat_ids, text, buttons))


def notify_roles(roles: Iterable[str], text: str, buttons=None, exclude: Optional[int] = None) -> None:
    if _sender is None:
        return
    with db_session() as db:
        ids = list(db.scalars(select(User.id).where(User.role.in_(list(roles)), User.is_active.is_(True))))
    notify_users(ids, text, buttons, exclude=exclude)
