"""Bot obyekti va bildirishnoma yuborish (bot o'chiq bo'lsa hech narsa qilmaydi)."""
from __future__ import annotations

import logging

log = logging.getLogger("bot")

bot = None  # aiogram.Bot
bot_username: str | None = None


def job_keyboard(job_id: int | None):
    if job_id is None:
        return None
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    from ..services import job_url

    row = [InlineKeyboardButton(text="📄 Ishni ochish", callback_data=f"job:{job_id}")]
    url = job_url(job_id)
    if url and url.startswith("https://"):
        row.append(InlineKeyboardButton(text="🌐 Saytda", url=url))
    return InlineKeyboardMarkup(inline_keyboard=[row])


async def send_notifications(chat_ids: list[int], text: str, job_id: int | None = None) -> None:
    if bot is None:
        return
    kb = job_keyboard(job_id)
    for cid in chat_ids:
        try:
            await bot.send_message(cid, text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:  # foydalanuvchi botni bloklagan bo'lishi mumkin
            log.warning("Bildirishnoma yuborilmadi (%s): %s", cid, e)
