"""Shablonlar, filtrlar va yordamchi funksiyalar."""
from datetime import date, datetime, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from . import constants as C
from .config import BASE_DIR, CURRENCY, TIMEZONE

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
TZ = ZoneInfo(TIMEZONE)


def to_local(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ)


def local_today() -> date:
    return datetime.now(TZ).date()


def fmt_dt(dt: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
    loc = to_local(dt)
    return loc.strftime(fmt) if loc else ""


def fmt_date(d: date | datetime | None) -> str:
    if d is None:
        return ""
    if isinstance(d, datetime):
        d = to_local(d)
    return d.strftime("%d.%m.%Y")


def fmt_num(v: float | int | None) -> str:
    if v is None:
        return ""
    v = round(float(v), 2)
    if v == int(v):
        return f"{int(v):,}".replace(",", " ")
    return f"{v:,.2f}".replace(",", " ")


def fmt_money(v: float | int | None) -> str:
    return f"{fmt_num(v or 0)} {CURRENCY}"


def fmt_size(n: int | None) -> str:
    n = n or 0
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def time_ago(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    sec = int((datetime.now(timezone.utc) - dt).total_seconds())
    if sec < 60:
        return "hozirgina"
    if sec < 3600:
        return f"{sec // 60} daqiqa oldin"
    if sec < 86400:
        return f"{sec // 3600} soat oldin"
    if sec < 86400 * 7:
        return f"{sec // 86400} kun oldin"
    return fmt_dt(dt, "%d.%m.%Y")


def contact_link(value: str | None) -> Markup:
    """Telefon raqam yoki Telegram username ni bosiladigan havolaga aylantiradi."""
    if not value:
        return Markup("")
    out = []
    for part in [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]:
        low = part.lower()
        if part.startswith("@") or "t.me/" in low:
            uname = part.split("t.me/")[-1].lstrip("@").strip("/")
            out.append(
                f'<a href="https://t.me/{quote(uname)}" target="_blank" rel="noopener">@{escape(uname)}</a>'
            )
        elif sum(ch.isdigit() for ch in part) >= 7:
            digits = "".join(ch for ch in part if ch.isdigit() or ch == "+")
            out.append(f'<a href="tel:{escape(digits)}">{escape(part)}</a>')
        else:
            out.append(str(escape(part)))
    return Markup(", ".join(out))


templates.env.filters.update(
    dt=fmt_dt,
    d=fmt_date,
    num=fmt_num,
    money=fmt_money,
    filesize=fmt_size,
    ago=time_ago,
    contact=contact_link,
)
templates.env.globals.update(
    C=C,
    STATUSES=C.STATUSES,
    STATUS_LABELS=C.STATUS_LABELS,
    STATUS_COLORS=C.STATUS_COLORS,
    ROLES=C.ROLES,
    PRIORITIES=C.PRIORITIES,
    FILE_KINDS=C.FILE_KINDS,
    CURRENCY=CURRENCY,
)


def flash(request: Request, message: str, category: str = "ok") -> None:
    request.session.setdefault("_flash", []).append([category, message])


def render(request: Request, name: str, status_code: int = 200, **ctx):
    messages = request.session.pop("_flash", [])
    ctx.setdefault("user", getattr(request.state, "user", None))
    ctx["messages"] = messages
    ctx["path"] = request.url.path
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def redirect(url: str, message: str | None = None, request: Request | None = None, category="ok"):
    if message and request is not None:
        flash(request, message, category)
    return RedirectResponse(url, status_code=303)
