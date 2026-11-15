from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import TIMEZONE
from .constants import CLOSED_STATUSES
from .db import Base, utcnow

_TZ = ZoneInfo(TIMEZONE)


def local_today() -> date:
    return datetime.now(_TZ).date()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="designer")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    link_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    notify: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def display_name(self) -> str:
        return self.full_name or self.username

    @property
    def initials(self) -> str:
        parts = (self.full_name or self.username).split()
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def can_manage(self) -> bool:
        """Admin yoki menejer."""
        return self.role in ("admin", "manager")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    client_name: Mapped[str] = mapped_column(String(255), default="")
    client_contact: Mapped[str] = mapped_column(String(255), default="")
    address: Mapped[str] = mapped_column(String(500), default="")
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    size_unit: Mapped[str] = mapped_column(String(8), default="m")
    size_note: Mapped[str] = mapped_column(String(255), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="web")

    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    designer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tg_chat_id: Mapped[int | None] = mapped_column(
        ForeignKey("tg_chats.id", ondelete="SET NULL"), nullable=True
    )

    discount: Mapped[float] = mapped_column(Float, default=0)
    paid: Mapped[float] = mapped_column(Float, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    status_changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    manager: Mapped[User | None] = relationship(foreign_keys=[manager_id], lazy="selectin")
    designer: Mapped[User | None] = relationship(foreign_keys=[designer_id], lazy="selectin")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id], lazy="selectin")
    files: Mapped[list[JobFile]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="JobFile.id",
    )
    items: Mapped[list[JobItem]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="JobItem.position",
    )

    # --- hisoblanadigan maydonlar ---
    @property
    def area_m2(self) -> float | None:
        if not self.width or not self.height:
            return None
        k = 10000 if self.size_unit == "sm" else 1
        return round(self.width * self.height / k, 3)

    @property
    def size_text(self) -> str:
        if not self.width or not self.height:
            return self.size_note or ""

        def f(v: float) -> str:
            return f"{v:g}"

        txt = f"{f(self.width)} × {f(self.height)} {self.size_unit}"
        if self.size_note:
            txt += f" ({self.size_note})"
        return txt

    @property
    def subtotal(self) -> float:
        return sum(i.total for i in self.items)

    @property
    def total(self) -> float:
        return max(self.subtotal - (self.discount or 0), 0)

    @property
    def debt(self) -> float:
        return self.total - (self.paid or 0)

    @property
    def is_closed(self) -> bool:
        return self.status in CLOSED_STATUSES

    @property
    def is_overdue(self) -> bool:
        return bool(self.due_date and not self.is_closed and self.due_date < local_today())

    @property
    def place_files(self) -> list[JobFile]:
        return [f for f in self.files if f.kind == "place"]

    @property
    def cover(self) -> JobFile | None:
        for f in self.files:
            if f.kind == "design" and f.is_image:
                return f
        for f in self.files:
            if f.kind == "place" and f.is_image:
                return f
        return None


class JobItem(Base):
    """Narx hisob-kitobi qatori."""

    __tablename__ = "job_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(32), default="dona")
    quantity: Mapped[float] = mapped_column(Float, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    position: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped[Job] = relationship(back_populates="items")

    @property
    def total(self) -> float:
        return round((self.quantity or 0) * (self.unit_price or 0), 2)


class JobFile(Base):
    __tablename__ = "job_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="logo")
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    mime: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    job: Mapped[Job] = relationship(back_populates="files")
    uploaded_by: Mapped[User | None] = relationship(lazy="selectin")

    @property
    def is_image(self) -> bool:
        return self.mime.startswith("image/") and not self.mime.endswith(
            ("photoshop", "x-photoshop", "vnd.adobe.photoshop", "x-xcf")
        )

    @property
    def ext(self) -> str:
        if "." in self.original_name:
            return self.original_name.rsplit(".", 1)[-1].upper()[:5]
        return "FAYL"


class JobEvent(Base):
    """Ish tarixi: holat o'zgarishi, tayinlash, izohlar va h.k."""

    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(16), default="edit")
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped[User | None] = relationship(lazy="selectin")
    job: Mapped[Job] = relationship(lazy="selectin", viewonly=True)


class PriceItem(Base):
    """Narxlar ro'yxati (xizmat va materiallar)."""

    __tablename__ = "price_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(32), default="m²")
    price: Mapped[float] = mapped_column(Float, default=0)
    note: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------- Telegram akkauntlar ----------------------


class TgAccount(Base):
    __tablename__ = "tg_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(64), default="")
    first_name: Mapped[str] = mapped_column(String(128), default="")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tg_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    session_string: Mapped[str] = mapped_column(Text, default="")
    color: Mapped[str] = mapped_column(String(16), default="#3b82f6")
    auto_add_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    state: Mapped[str] = mapped_column(String(16), default="ok")  # ok / error / unauthorized
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def name(self) -> str:
        return self.label or self.first_name or self.phone


class TgChat(Base):
    """Saralangan (kuzatiladigan) chatlar."""

    __tablename__ = "tg_chats"
    __table_args__ = (UniqueConstraint("account_id", "chat_id", name="uq_account_chat"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("tg_accounts.id", ondelete="CASCADE"), index=True
    )
    chat_id: Mapped[int] = mapped_column(BigInteger)  # Telethon "marked" id
    access_hash: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), default="user")  # user / group / channel / bot
    is_selected: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    unread: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_message_text: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    account: Mapped[TgAccount] = relationship(lazy="selectin")


class TgMessage(Base):
    __tablename__ = "tg_messages"
    __table_args__ = (UniqueConstraint("chat_id", "msg_id", name="uq_chat_msg"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("tg_chats.id", ondelete="CASCADE"), index=True)
    msg_id: Mapped[int] = mapped_column(BigInteger)
    sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sender_name: Mapped[str] = mapped_column(String(255), default="")
    out: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str] = mapped_column(Text, default="")
    date: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    media_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    media_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    media_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    chat: Mapped[TgChat] = relationship(lazy="selectin", viewonly=True)
