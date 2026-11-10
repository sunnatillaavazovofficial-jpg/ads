"""Fayllarni diskka saqlash va rasm uchun kichik nusxa (thumbnail) yaratish."""
import logging
import mimetypes
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

from ..config import UPLOAD_DIR
from ..models import WorkFile
from ..utils import safe_filename

log = logging.getLogger("dizaynhub")

try:
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = 400_000_000  # katta bannerlar uchun
    _PIL = True
except Exception:  # pragma: no cover
    _PIL = False

THUMB_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".psd"}
INLINE_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"}


def work_dir(work_id: int) -> Path:
    d = UPLOAD_DIR / f"work_{work_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def file_path(wf: WorkFile) -> Path:
    return UPLOAD_DIR / f"work_{wf.work_id}" / wf.stored_name


def thumb_path(wf: WorkFile) -> Optional[Path]:
    if not wf.thumb_name:
        return None
    return UPLOAD_DIR / f"work_{wf.work_id}" / wf.thumb_name


def _make_thumb(src: Path, dst: Path) -> bool:
    if not _PIL:
        return False
    try:
        with Image.open(src) as im:
            im.draft("RGB", (1200, 1200))
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "L"):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                rgba = im.convert("RGBA")
                bg.paste(rgba, mask=rgba.split()[-1])
                im = bg
            im.thumbnail((640, 640))
            im.save(dst, "JPEG", quality=82)
        return True
    except Exception as exc:
        log.info("Thumbnail yaratilmadi (%s): %s", src.name, exc)
        return False


def store_file(work_id: int, kind: str, original_name: str, src: BinaryIO, user_id: Optional[int]) -> WorkFile:
    """Fayl oqimini diskka yozadi va WorkFile obyektini qaytaradi (bazaga qo'shilmagan)."""
    original_name = safe_filename(original_name)
    ext = Path(original_name).suffix.lower()[:10]
    stored = f"{uuid.uuid4().hex}{ext}"
    dst = work_dir(work_id) / stored
    with open(dst, "wb") as out:
        shutil.copyfileobj(src, out, length=1024 * 1024)
    thumb_name = None
    if ext in THUMB_EXT or ext == ".svg":
        if ext == ".svg":
            thumb_name = stored  # SVG brauzerda o'zi ko'rinadi
        else:
            tname = f"{uuid.uuid4().hex}_t.jpg"
            if _make_thumb(dst, dst.parent / tname):
                thumb_name = tname
    mime = mimetypes.guess_type(original_name)[0] or "application/octet-stream"
    return WorkFile(
        work_id=work_id,
        kind=kind,
        original_name=original_name,
        stored_name=stored,
        thumb_name=thumb_name,
        size=dst.stat().st_size,
        mime=mime,
        uploaded_by_id=user_id,
    )


def store_path(work_id: int, kind: str, original_name: str, path: Path, user_id: Optional[int]) -> WorkFile:
    with open(path, "rb") as fh:
        return store_file(work_id, kind, original_name, fh, user_id)


def delete_stored(wf: WorkFile) -> None:
    for p in (file_path(wf), thumb_path(wf)):
        try:
            if p and p.exists():
                p.unlink()
        except OSError:
            pass


def delete_work_dir(work_id: int) -> None:
    d = UPLOAD_DIR / f"work_{work_id}"
    shutil.rmtree(d, ignore_errors=True)
