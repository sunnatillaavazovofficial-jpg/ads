"""Ishlar bilan bog'liq umumiy mantiq (sayt va bot uchun bitta)."""
from typing import BinaryIO, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..models import SIZE_UNITS, STATUSES, User, Work, WorkEvent, WorkType, now
from ..utils import parse_date, parse_float, parse_int
from . import notify
from .files import delete_work_dir, store_file

# Majburiy maydonlar: (kalit, nomi, "Yo'q" belgisi maydoni yoki None)
REQUIRED_FIELDS = [
    ("title", "Ish nomi", None),
    ("work_type", "Ish turi", None),
    ("short_desc", "Qisqa ta'rif", "short_desc_none"),
    ("size", "Ish o'lchami", "size_none"),
    ("image", "Ish rasmi", "image_none"),
    ("extra_info", "Qo'shimcha ma'lumotlar", "extra_info_none"),
    ("logo", "Logo", "logo_none"),
    ("special_text", "Maxsus matn", "special_text_none"),
    ("file", "Fayllar", "files_none"),
]

NONE_FLAGS = [f for _, _, f in REQUIRED_FIELDS if f]


def work_types(db: Session) -> list[str]:
    return list(db.scalars(select(WorkType.name).order_by(WorkType.sort, WorkType.name)))


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in ("1", "on", "true", "yes", "ha")


def validate_work(db: Session, data: dict, file_counts: dict) -> tuple[dict, dict]:
    """Formani tekshiradi. (tozalangan_qiymatlar, xatolar) qaytaradi.

    file_counts: {"image": n, "logo": n, "file": n} — mavjud + yangi fayllar soni.
    """
    errors: dict = {}
    c: dict = {}

    c["title"] = (data.get("title") or "").strip()[:200]
    if not c["title"]:
        errors["title"] = "Ish nomini kiriting"

    c["work_type"] = (data.get("work_type") or "").strip()[:100]
    if not c["work_type"]:
        errors["work_type"] = "Ish turini tanlang"
    elif c["work_type"] not in work_types(db):
        errors["work_type"] = "Ro'yxatdagi ish turini tanlang"

    for flag in NONE_FLAGS:
        c[flag] = _truthy(data.get(flag))

    def text_field(key: str, flag: str, label: str):
        val = (data.get(key) or "").strip()
        c[key] = "" if c[flag] else val
        if not c[flag] and not val:
            errors[key] = f"{label}ni kiriting yoki «Yo'q» deb belgilang"

    text_field("short_desc", "short_desc_none", "Qisqa ta'rif")
    text_field("extra_info", "extra_info_none", "Qo'shimcha ma'lumot")
    text_field("special_text", "special_text_none", "Maxsus matn")

    if c["size_none"]:
        c.update(width=None, height=None, size_unit="sm", quantity=1)
    else:
        c["width"] = parse_float(data.get("width"))
        c["height"] = parse_float(data.get("height"))
        unit = (data.get("size_unit") or "sm").strip()
        c["size_unit"] = unit if unit in SIZE_UNITS else "sm"
        c["quantity"] = max(parse_int(data.get("quantity"), 1) or 1, 1)
        if not c["width"] or not c["height"] or c["width"] <= 0 or c["height"] <= 0:
            errors["size"] = "O'lchamni (eni va bo'yi) kiriting yoki «Yo'q» deb belgilang"

    for kind, flag, label in (("image", "image_none", "Ish rasmi"), ("logo", "logo_none", "Logo"),
                              ("file", "files_none", "Fayllar")):
        n = file_counts.get(kind, 0)
        if c[flag] and n:
            c[flag] = False  # fayl yuklangan bo'lsa "Yo'q" belgisi bekor
        if not c[flag] and not n:
            errors[kind] = f"{label}: fayl yuklang yoki «Yo'q» deb belgilang"

    c["client_name"] = (data.get("client_name") or "").strip()[:200]
    c["client_phone"] = (data.get("client_phone") or "").strip()[:50]
    c["deadline"] = parse_date(data.get("deadline") or "")
    c["tg_chat_id"] = parse_int(data.get("tg_chat_id")) or None
    return c, errors


def add_event(db: Session, work: Work, user: Optional[User], kind: str, text: str) -> None:
    db.add(WorkEvent(work_id=work.id, user_id=user.id if user else None, kind=kind, text=text))


def work_link(work: Work) -> str:
    return f"{config.PUBLIC_URL}/works/{work.id}" if config.PUBLIC_URL else ""


def _buttons_for_new(work: Work):
    rows = [[("✅ Qabul qilish", f"accept:{work.id}")]]
    link = work_link(work)
    if link:
        rows.append([("🌐 Saytda ochish", f"url:{link}")])
    return rows


def _open_button(work: Work):
    link = work_link(work)
    return [[("🌐 Saytda ochish", f"url:{link}")]] if link else None


def create_work(db: Session, user: User, cleaned: dict,
                uploads: dict[str, list[tuple[str, BinaryIO]]], source: str = "web") -> Work:
    work = Work(manager_id=user.id, status="new", source=source, **cleaned)
    db.add(work)
    db.flush()
    try:
        for kind, items in uploads.items():
            for name, fh in items:
                db.add(store_file(work.id, kind, name, fh, user.id))
        add_event(db, work, user, "created",
                  "Ish yaratildi" + (" (Telegram bot orqali)" if source == "bot" else ""))
        db.commit()
    except Exception:
        db.rollback()
        delete_work_dir(work.id)
        raise
    db.refresh(work)
    notify.notify_roles(
        ["chief", "admin"],
        f"🆕 Yangi ish #{work.id}: {work.title}\nTuri: {work.work_type}\n"
        f"O'lchami: {work.size_text}\nMenejer: {user.full_name}",
        _buttons_for_new(work),
        exclude=user.id,
    )
    return work


# ---------------------------------------------------------------- holatlar

ACTION_LABELS = {
    "accept": "Qabul qilish",
    "start": "Ishni boshlash",
    "done": "Tayyor",
    "reopen": "Qayta ishlashga qaytarish",
    "deliver": "Mijozga topshirildi",
    "cancel": "Bekor qilish",
    "restore": "Qayta tiklash",
}


def can_edit(work: Work, user: User) -> bool:
    if user.is_admin:
        return True
    return user.is_manager and work.manager_id == user.id and work.status not in ("delivered",)


def can_see_accounting(work: Work, user: User) -> bool:
    return user.is_admin or (user.is_manager and work.manager_id == user.id) or (
        user.is_manager and work.manager_id is None)


def can_upload_result(work: Work, user: User) -> bool:
    if work.status not in ("accepted", "in_progress", "done"):
        return False
    return user.is_admin or user.is_chief or work.designer_id == user.id


def actions_for(work: Work, user: User) -> list[str]:
    s = work.status
    owner = user.is_admin or (user.is_manager and work.manager_id == user.id)
    designer = user.is_admin or user.is_chief or work.designer_id == user.id
    acts = []
    if s == "new" and user.can_accept_work:
        acts.append("accept")
    if s == "accepted" and designer:
        acts.append("start")
    if s in ("accepted", "in_progress") and designer:
        acts.append("done")
    if s == "done" and (owner or user.is_chief):
        acts.append("reopen")
    if s == "done" and owner:
        acts.append("deliver")
    if s not in ("delivered", "cancelled") and owner:
        acts.append("cancel")
    if s == "cancelled" and owner:
        acts.append("restore")
    return acts


class ActionError(Exception):
    pass


def apply_action(db: Session, work: Work, user: User, action: str,
                 designer_id: Optional[int] = None, comment: str = "") -> None:
    if action not in actions_for(work, user):
        raise ActionError("Bu amalni bajarish mumkin emas")
    old = work.status
    designer: Optional[User] = None

    if action == "accept":
        designer = db.get(User, designer_id) if designer_id else user
        if designer is None or designer.role not in ("designer", "chief", "admin") or not designer.is_active:
            raise ActionError("Dizaynerni tanlang")
        work.status = "accepted"
        work.chief_id = user.id
        work.designer_id = designer.id
        work.accepted_at = now()
    elif action == "start":
        work.status = "in_progress"
    elif action == "done":
        if not work.files_of("result"):
            raise ActionError("Avval tayyor ish faylini yuklang")
        work.status = "done"
        work.done_at = now()
    elif action == "reopen":
        work.status = "in_progress"
        work.done_at = None
    elif action == "deliver":
        work.status = "delivered"
    elif action == "cancel":
        work.status = "cancelled"
    elif action == "restore":
        work.status = "new"
        work.chief_id = None
        work.designer_id = None
        work.accepted_at = None
        work.done_at = None

    text = f"Holat: {STATUSES[old]} → {STATUSES[work.status]}"
    if action == "accept" and designer:
        text += f". Dizayner: {designer.full_name}"
    if comment.strip():
        text += f"\nIzoh: {comment.strip()}"
    add_event(db, work, user, "status", text)
    db.commit()

    head = f"#{work.id} «{work.title}»"
    btn = _open_button(work)
    if action == "accept":
        notify.notify_users([work.manager_id], f"✅ {head} qabul qilindi.\nDizayner: {designer.full_name}",
                            btn, exclude=user.id)
        notify.notify_users([work.designer_id], f"🎨 Sizga yangi ish biriktirildi: {head}\n"
                            f"Turi: {work.work_type}, o'lchami: {work.size_text}", btn, exclude=user.id)
    elif action == "done":
        notify.notify_users([work.manager_id, work.chief_id], f"🏁 {head} tayyor!", btn, exclude=user.id)
    elif action == "reopen":
        notify.notify_users([work.designer_id], f"🔁 {head} qayta ishlashga qaytarildi."
                            + (f"\nIzoh: {comment.strip()}" if comment.strip() else ""), btn, exclude=user.id)
    elif action in ("deliver", "cancel"):
        notify.notify_users([work.designer_id, work.chief_id],
                            f"{'📦' if action == 'deliver' else '❌'} {head}: {work.status_name}", btn,
                            exclude=user.id)
    elif action == "restore":
        notify.notify_roles(["chief", "admin"], f"🆕 Ish qayta tiklandi #{work.id}: {work.title}",
                            _buttons_for_new(work), exclude=user.id)


def reassign(db: Session, work: Work, user: User, designer_id: int) -> None:
    if not user.can_accept_work or work.status not in ("accepted", "in_progress"):
        raise ActionError("Dizaynerni almashtirib bo'lmaydi")
    designer = db.get(User, designer_id)
    if designer is None or designer.role not in ("designer", "chief", "admin") or not designer.is_active:
        raise ActionError("Dizaynerni tanlang")
    work.designer_id = designer.id
    add_event(db, work, user, "status", f"Dizayner almashtirildi: {designer.full_name}")
    db.commit()
    notify.notify_users([designer.id], f"🎨 Sizga ish biriktirildi: #{work.id} «{work.title}»",
                        _open_button(work), exclude=user.id)


def add_comment(db: Session, work: Work, user: User, text: str) -> None:
    text = text.strip()
    if not text:
        return
    add_event(db, work, user, "comment", text[:4000])
    db.commit()
    notify.notify_users([work.manager_id, work.designer_id, work.chief_id],
                        f"💬 #{work.id} «{work.title}»\n{user.full_name}: {text[:500]}",
                        _open_button(work), exclude=user.id)


def designers(db: Session) -> list[User]:
    return list(db.scalars(
        select(User).where(User.role.in_(["designer", "chief"]), User.is_active.is_(True))
        .order_by(User.first_name, User.last_name)
    ))
