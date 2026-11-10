import re
from datetime import datetime
from typing import Optional


def money(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    txt = f"{v:,.2f}".rstrip("0").rstrip(".")
    return txt.replace(",", " ")


def num(value) -> str:
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{v:,.3f}".rstrip("0").rstrip(".").replace(",", " ")


def dt(value: Optional[datetime], with_time: bool = True) -> str:
    if not value:
        return "—"
    if value.tzinfo is not None:
        value = value.astimezone().replace(tzinfo=None)
    return value.strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")


def parse_float(value, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    s = str(value).strip().replace(" ", "").replace(",", ".")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def parse_int(value, default: Optional[int] = None) -> Optional[int]:
    f = parse_float(value)
    if f is None:
        return default
    return int(f)


def parse_date(value: str) -> Optional[datetime]:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


_SIZE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*[x×х*]\s*(\d+(?:[.,]\d+)?)\s*(mm|sm|cm|см|мм|m|м)?"
    r"(?:[\s,;]+(\d+)\s*(?:dona|ta|шт|x)?)?",
    re.IGNORECASE,
)


def parse_size(text: str):
    """'300x600 sm 2 dona' -> (300.0, 600.0, 'sm', 2). Topilmasa None."""
    m = _SIZE_RE.search(text or "")
    if not m:
        return None
    w = parse_float(m.group(1))
    h = parse_float(m.group(2))
    unit = (m.group(3) or "sm").lower()
    unit = {"cm": "sm", "см": "sm", "мм": "mm", "м": "m"}.get(unit, unit)
    qty = int(m.group(4)) if m.group(4) else 1
    if not w or not h:
        return None
    return w, h, unit, max(qty, 1)


def safe_filename(name: str) -> str:
    name = (name or "fayl").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f<>:\"|?*]", "_", name).strip(" .")
    return name[:180] or "fayl"
