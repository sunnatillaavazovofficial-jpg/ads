"""Bazadagi sozlamalar va birinchi ishga tushirish."""
import logging
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..models import Material, Setting, WorkType

log = logging.getLogger("dizaynhub")

KEY_ROLES = ("admin", "manager", "chief", "designer")

DEFAULT_WORK_TYPES = [
    "Banner", "Setka banner", "Logo", "Vizitka", "Flayer", "Buklet", "Stiker",
    "Lightbox", "Peshtaxta (vyveska)", "Roll-up", "Stend", "Qadoq dizayni",
    "Ijtimoiy tarmoq posti", "Boshqa",
]

DEFAULT_MATERIALS = [
    ("Banner 440 g", "m²"),
    ("Setka banner", "m²"),
    ("Orakal plyonka", "m²"),
    ("Kompozit panel", "m²"),
    ("Akril 3 mm", "m²"),
    ("Pechat (chop etish)", "m²"),
    ("Dizayn xizmati", "dona"),
    ("Montaj", "dona"),
]


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(Setting, key)
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))


def role_keys(db: Session) -> dict:
    return {role: get_setting(db, f"key_{role}") for role in KEY_ROLES}


def role_for_key(db: Session, key: str):
    key = (key or "").strip()
    if not key:
        return None
    for role, value in role_keys(db).items():
        if value and secrets.compare_digest(value, key):
            return role
    return None


def bootstrap(db: Session) -> None:
    """Kalitlar, ish turlari va namunaviy materiallarni yaratadi (faqat bir marta)."""
    created = {}
    for role in KEY_ROLES:
        if not get_setting(db, f"key_{role}"):
            value = config.INITIAL_KEYS.get(role) or secrets.token_hex(4).upper()
            set_setting(db, f"key_{role}", value)
            created[role] = value
    if not db.scalars(select(WorkType).limit(1)).first():
        for i, name in enumerate(DEFAULT_WORK_TYPES):
            db.add(WorkType(name=name, sort=i))
    if not get_setting(db, "materials_seeded"):
        if not db.scalars(select(Material).limit(1)).first():
            for name, unit in DEFAULT_MATERIALS:
                db.add(Material(name=name, unit=unit))
        set_setting(db, "materials_seeded", "1")
    db.commit()

    if created:
        keys = role_keys(db)
        lines = [
            "Ro'yxatdan o'tish kalitlari (admin panelida o'zgartirish mumkin):",
            f"  Admin:          {keys['admin']}",
            f"  Menejer:        {keys['manager']}",
            f"  Bosh dizayner:  {keys['chief']}",
            f"  Dizayner:       {keys['designer']}",
        ]
        text = "\n".join(lines)
        (config.DATA_DIR / "KALITLAR.txt").write_text(text + "\n", encoding="utf-8")
        log.warning("\n%s\n(Shu ma'lumot data/KALITLAR.txt fayliga ham yozildi)", text)
