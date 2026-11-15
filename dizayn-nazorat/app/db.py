from datetime import datetime, timezone

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"timeout": 30} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)

if _is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()


SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Bazada vaqt UTC (timezone siz) ko'rinishida saqlanadi."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    from . import models  # noqa: F401  (jadvallarni ro'yxatdan o'tkazish)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
