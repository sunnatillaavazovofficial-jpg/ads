"""Ishlar bilan bog'liq umumiy amallar (sayt, bot va inbox uchun bitta joyda)."""
from __future__ import annotations

import asyncio
import logging
import mimetypes
import re
import shutil
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import MAX_UPLOAD_MB, SITE_URL, UPLOAD_DIR
from .constants import STATUS_LABELS
from .db import utcnow
from .models import Job, JobEvent, JobFile, JobItem, User

log = logging.getLogger("services")

_bg_tasks: set[asyncio.Task] = set()


def fire(coro) -> None:
    """Fon vazifasini ishga tushirish (natijasini kutmasdan)."""
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


# ----------------------------- yordamchilar -----------------------------


def parse_float(value, default: float | None = None) -> float | None:
    if value is None:
        return default
    s = str(value).strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


_SIZE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*[xх×*]\s*(\d+(?:[.,]\d+)?)\s*(sm|cm|см|mm|мм|m|м)?",
    re.IGNORECASE,
)


def parse_size(text: str) -> tuple[float | None, float | None, str]:
    """'3x6', '300x600 sm', '3.5 × 2 m' kabi matndan o'lchamni ajratib oladi."""
    m = _SIZE_RE.search(text or "")
    if not m:
        return None, None, "m"
    w = float(m.group(1).replace(",", "."))
    h = float(m.group(2).replace(",", "."))
    unit = (m.group(3) or "").lower()
    if unit in ("mm", "мм"):
        return w / 10, h / 10, "sm"
    if unit in ("sm", "cm", "см"):
        return w, h, "sm"
    if unit in ("m", "м"):
        return w, h, "m"
    # Birlik yozilmagan: katta sonlar bo'lsa santimetr deb hisoblaymiz
    return (w, h, "sm") if max(w, h) > 50 else (w, h, "m")


def secure_filename(name: str) -> str:
    name = Path(name or "fayl").name
    name = re.sub(r"[^\w\-. ()\[\]]+", "_", name, flags=re.UNICODE).strip("._ ")
    if not name:
        name = "fayl"
    if len(name) > 120:
        stem, dot, ext = name.rpartition(".")
        name = (stem[:100] + "." + ext[:10]) if dot else name[:120]
    return name


def guess_mime(filename: str, given: str | None = None) -> str:
    if given and given not in ("application/octet-stream", ""):
        return given
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


class UploadTooLarge(Exception):
    pass


async def save_upload(job_id: int, upload: UploadFile, kind: str, user_id: int | None) -> JobFile | None:
    if upload is None or not upload.filename:
        return None
    safe = secure_filename(upload.filename)
    rel = f"{job_id}/{uuid.uuid4().hex[:10]}_{safe}"
    path = UPLOAD_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    limit = MAX_UPLOAD_MB * 1024 * 1024
    size = 0
    try:
        async with aiofiles.open(path, "wb") as f:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise UploadTooLarge(upload.filename)
                await f.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    if size == 0:
        path.unlink(missing_ok=True)
        return None
    return JobFile(
        job_id=job_id,
        kind=kind,
        original_name=upload.filename[:255],
        stored_path=rel,
        mime=guess_mime(safe, upload.content_type),
        size=size,
        uploaded_by_id=user_id,
    )


def register_local_file(
    job_id: int, src: Path, original_name: str, kind: str, user_id: int | None, move: bool = True,
    mime: str | None = None,
) -> JobFile:
    """Diskdagi faylni (bot yoki Telegramdan yuklangan) ishga biriktirish."""
    safe = secure_filename(original_name)
    rel = f"{job_id}/{uuid.uuid4().hex[:10]}_{safe}"
    dest = UPLOAD_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if move:
        shutil.move(str(src), dest)
    else:
        shutil.copy2(src, dest)
    return JobFile(
        job_id=job_id,
        kind=kind,
        original_name=original_name[:255],
        stored_path=rel,
        mime=guess_mime(safe, mime),
        size=dest.stat().st_size,
        uploaded_by_id=user_id,
    )


def delete_file_from_disk(jf: JobFile) -> None:
    try:
        (UPLOAD_DIR / jf.stored_path).unlink(missing_ok=True)
    except OSError:
        log.warning("Faylni o'chirib bo'lmadi: %s", jf.stored_path)


def delete_job_dir(job_id: int) -> None:
    shutil.rmtree(UPLOAD_DIR / str(job_id), ignore_errors=True)


# ----------------------------- narx qatorlari -----------------------------


def apply_items(job: Job, names, units, qtys, prices) -> None:
    """Formadan kelgan narx qatorlarini ishga yozadi (eskilarini almashtiradi)."""
    job.items.clear()
    pos = 0
    for name, unit, qty, price in zip(names, units, qtys, prices):
        name = (name or "").strip()
        q = parse_float(qty, 0) or 0
        p = parse_float(price, 0) or 0
        if not name and not p:
            continue
        job.items.append(
            JobItem(name=name or "Xizmat", unit=(unit or "dona").strip()[:32], quantity=q, unit_price=p, position=pos)
        )
        pos += 1


# ----------------------------- tarix va bildirishnomalar -----------------------------


def add_event(db: AsyncSession, job: Job, user: User | None, kind: str, text: str) -> None:
    db.add(JobEvent(job_id=job.id, user_id=user.id if user else None, kind=kind, text=text))


def job_url(job_id: int) -> str | None:
    return f"{SITE_URL}/jobs/{job_id}" if SITE_URL else None


def notify_users(users: list[User | None], text: str, job_id: int | None = None, exclude: User | None = None) -> None:
    """Bot orqali xabar yuborish (bot sozlanmagan bo'lsa jim o'tadi)."""
    from .bot import runtime

    seen: set[int] = set()
    targets = []
    for u in users:
        if not u or not u.telegram_id or not u.notify or not u.is_active:
            continue
        if exclude and u.id == exclude.id:
            continue
        if u.telegram_id in seen:
            continue
        seen.add(u.telegram_id)
        targets.append(u.telegram_id)
    if targets:
        fire(runtime.send_notifications(targets, text, job_id))


async def change_status(db: AsyncSession, job: Job, new_status: str, user: User | None) -> bool:
    if new_status not in STATUS_LABELS or new_status == job.status:
        return False
    old = job.status
    job.status = new_status
    job.status_changed_at = utcnow()
    if new_status == "done":
        job.done_at = utcnow()
    elif old == "done":
        job.done_at = None
    add_event(db, job, user, "status", f"{STATUS_LABELS.get(old, old)} → {STATUS_LABELS[new_status]}")
    await db.commit()
    who = user.display_name if user else "Tizim"
    notify_users(
        [job.manager, job.designer],
        f"🔄 <b>#{job.id} {_h(job.title)}</b>\nHolat: <b>{STATUS_LABELS[new_status]}</b>\n👤 {_h(who)}",
        job.id,
        exclude=user,
    )
    return True


async def assign(
    db: AsyncSession, job: Job, manager_id: int | None, designer_id: int | None, user: User | None
) -> None:
    changes = []
    new_designer = None
    if manager_id != job.manager_id:
        m = await db.get(User, manager_id) if manager_id else None
        job.manager_id = manager_id
        job.manager = m
        changes.append(f"Menejer: {m.display_name if m else '—'}")
    if designer_id != job.designer_id:
        d = await db.get(User, designer_id) if designer_id else None
        job.designer_id = designer_id
        job.designer = d
        new_designer = d
        changes.append(f"Dizayner: {d.display_name if d else '—'}")
    if not changes:
        return
    add_event(db, job, user, "assign", "; ".join(changes))
    await db.commit()
    if new_designer:
        notify_designer_assigned(job, user)


def notify_designer_assigned(job: Job, actor: User | None) -> None:
    if not job.designer:
        return
    lines = ["🆕 <b>Sizga yangi ish biriktirildi</b>", f"<b>#{job.id} {_h(job.title)}</b>"]
    if job.client_name:
        lines.append(f"👤 Mijoz: {_h(job.client_name)}")
    if job.size_text:
        lines.append(f"📐 O'lcham: {_h(job.size_text)}")
    if job.due_date:
        lines.append(f"⏰ Muddat: {job.due_date.strftime('%d.%m.%Y')}")
    if job.comment:
        lines.append(f"💬 {_h(job.comment[:500])}")
    if actor:
        lines.append(f"✍️ {_h(actor.display_name)}")
    notify_users([job.designer], "\n".join(lines), job.id, exclude=actor)


async def load_job(db: AsyncSession, job_id: int) -> Job | None:
    res = await db.execute(select(Job).where(Job.id == job_id))
    return res.scalar_one_or_none()


def _h(text: str | None) -> str:
    from html import escape

    return escape(text or "")
