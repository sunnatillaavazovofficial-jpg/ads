from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

ROLES = {
    "admin": "Admin",
    "manager": "Menejer",
    "chief": "Bosh dizayner",
    "designer": "Dizayner",
}

STATUSES = {
    "new": "Yangi",
    "accepted": "Qabul qilindi",
    "in_progress": "Jarayonda",
    "done": "Tayyor",
    "delivered": "Topshirildi",
    "cancelled": "Bekor qilindi",
}

SIZE_UNITS = ["mm", "sm", "m"]

FILE_KINDS = {
    "image": "Ish rasmi",
    "logo": "Logo",
    "file": "Fayl",
    "result": "Tayyor ish",
}


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    # "ism familiya" — kichik harflarda, takrorlanmas
    login: Mapped[str] = mapped_column(String(170), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tg_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)
    tg_link_code: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def role_name(self) -> str:
        return ROLES.get(self.role, self.role)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_manager(self) -> bool:
        return self.role == "manager"

    @property
    def is_chief(self) -> bool:
        return self.role == "chief"

    @property
    def is_designer(self) -> bool:
        return self.role in ("designer", "chief")

    @property
    def can_create_work(self) -> bool:
        return self.role in ("admin", "manager")

    @property
    def can_accept_work(self) -> bool:
        return self.role in ("admin", "chief")

    @property
    def sees_prices(self) -> bool:
        return self.role in ("admin", "manager")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class WorkType(Base):
    __tablename__ = "work_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Work(Base):
    __tablename__ = "works"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    work_type: Mapped[str] = mapped_column(String(100))

    short_desc: Mapped[str] = mapped_column(Text, default="")
    short_desc_none: Mapped[bool] = mapped_column(Boolean, default=False)

    width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    size_unit: Mapped[str] = mapped_column(String(8), default="sm")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    size_none: Mapped[bool] = mapped_column(Boolean, default=False)

    image_none: Mapped[bool] = mapped_column(Boolean, default=False)

    extra_info: Mapped[str] = mapped_column(Text, default="")
    extra_info_none: Mapped[bool] = mapped_column(Boolean, default=False)

    logo_none: Mapped[bool] = mapped_column(Boolean, default=False)

    special_text: Mapped[str] = mapped_column(Text, default="")
    special_text_none: Mapped[bool] = mapped_column(Boolean, default=False)

    files_none: Mapped[bool] = mapped_column(Boolean, default=False)

    # Ixtiyoriy maydonlar
    client_name: Mapped[str] = mapped_column(String(200), default="")
    client_phone: Mapped[str] = mapped_column(String(50), default="")
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tg_chat_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tg_chats.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    chief_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    designer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="web")  # web | bot

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    done_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    manager: Mapped[Optional[User]] = relationship(foreign_keys=[manager_id])
    chief: Mapped[Optional[User]] = relationship(foreign_keys=[chief_id])
    designer: Mapped[Optional[User]] = relationship(foreign_keys=[designer_id])
    tg_chat: Mapped[Optional["TgChat"]] = relationship()
    files: Mapped[list["WorkFile"]] = relationship(
        back_populates="work", cascade="all, delete-orphan", order_by="WorkFile.id"
    )
    events: Mapped[list["WorkEvent"]] = relationship(
        back_populates="work", cascade="all, delete-orphan", order_by="WorkEvent.id"
    )
    expenses: Mapped[list["WorkExpense"]] = relationship(
        back_populates="work", cascade="all, delete-orphan", order_by="WorkExpense.id"
    )

    @property
    def status_name(self) -> str:
        return STATUSES.get(self.status, self.status)

    @property
    def size_text(self) -> str:
        if self.size_none:
            return "Yo'q"
        if not self.width or not self.height:
            return "—"
        w = f"{self.width:g}"
        h = f"{self.height:g}"
        txt = f"{w} × {h} {self.size_unit}"
        if self.quantity and self.quantity > 1:
            txt += f", {self.quantity} dona"
        return txt

    @property
    def area_m2(self) -> float:
        """Umumiy maydon (m²), soni bilan birga."""
        if self.size_none or not self.width or not self.height:
            return 0.0
        k = {"mm": 0.001, "sm": 0.01, "m": 1.0}.get(self.size_unit, 0.01)
        return round(self.width * k * self.height * k * max(self.quantity or 1, 1), 4)

    def files_of(self, kind: str) -> list["WorkFile"]:
        return [f for f in self.files if f.kind == kind]

    @property
    def cover(self) -> Optional["WorkFile"]:
        for kind in ("result", "image", "logo"):
            for f in self.files:
                if f.kind == kind and f.thumb_name:
                    return f
        return None

    @property
    def total_cost(self) -> float:
        return round(sum(e.cost_total for e in self.expenses), 2)

    @property
    def total_price(self) -> float:
        return round(sum(e.price_total for e in self.expenses), 2)

    @property
    def profit(self) -> float:
        return round(self.total_price - self.total_cost, 2)


class WorkFile(Base):
    __tablename__ = "work_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("works.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # image | logo | file | result
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    thumb_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    mime: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    work: Mapped[Work] = relationship(back_populates="files")
    uploaded_by: Mapped[Optional[User]] = relationship()

    @property
    def is_image(self) -> bool:
        return bool(self.thumb_name)

    @property
    def size_text(self) -> str:
        size = float(self.size or 0)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return ""


class WorkEvent(Base):
    __tablename__ = "work_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("works.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20))  # created | status | comment | file | edit | expense
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    work: Mapped[Work] = relationship(back_populates="events")
    user: Mapped[Optional[User]] = relationship()


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    unit: Mapped[str] = mapped_column(String(20), default="m²")
    cost_price: Mapped[float] = mapped_column(Float, default=0)
    sell_price: Mapped[float] = mapped_column(Float, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkExpense(Base):
    __tablename__ = "work_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("works.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[Optional[int]] = mapped_column(ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(150))
    unit: Mapped[str] = mapped_column(String(20), default="dona")
    qty: Mapped[float] = mapped_column(Float, default=1)
    cost_price: Mapped[float] = mapped_column(Float, default=0)
    sell_price: Mapped[float] = mapped_column(Float, default=0)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    work: Mapped[Work] = relationship(back_populates="expenses")
    material: Mapped[Optional[Material]] = relationship()

    @property
    def cost_total(self) -> float:
        return round((self.qty or 0) * (self.cost_price or 0), 2)

    @property
    def price_total(self) -> float:
        return round((self.qty or 0) * (self.sell_price or 0), 2)


class TgAccount(Base):
    __tablename__ = "tg_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_name: Mapped[str] = mapped_column(String(64), unique=True)
    phone: Mapped[str] = mapped_column(String(32))
    tg_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    username: Mapped[str] = mapped_column(String(100), default="")
    # Ushbu akkauntning tanlangan chatlarini ko'ra oladigan menejer (ixtiyoriy)
    owner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    owner: Mapped[Optional[User]] = relationship()
    chats: Mapped[list["TgChat"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class TgChat(Base):
    """Admin tanlab olgan (kuzatiladigan) chat."""

    __tablename__ = "tg_chats"
    __table_args__ = (UniqueConstraint("account_id", "peer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("tg_accounts.id", ondelete="CASCADE"), index=True)
    peer_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(100), default="")
    kind: Mapped[str] = mapped_column(String(10), default="user")  # user | group | channel | bot
    note: Mapped[str] = mapped_column(String(255), default="")
    unread: Mapped[int] = mapped_column(Integer, default=0)
    last_text: Mapped[str] = mapped_column(Text, default="")
    last_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    account: Mapped[TgAccount] = relationship(back_populates="chats")
