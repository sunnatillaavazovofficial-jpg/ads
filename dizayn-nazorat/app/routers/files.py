import asyncio
import uuid
import zipfile
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user
from ..config import TMP_DIR, UPLOAD_DIR
from ..constants import FILE_KINDS
from ..db import get_db
from ..models import Job, JobFile, User
from ..services import add_event, delete_file_from_disk, secure_filename
from ..web import redirect

router = APIRouter()


def _disposition(name: str, inline: bool) -> str:
    kind = "inline" if inline else "attachment"
    ascii_name = name.encode("ascii", "ignore").decode() or "fayl"
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"


@router.get("/files/{file_id}")
async def get_file(file_id: int, download: int = 0, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    jf = await db.get(JobFile, file_id)
    if not jf:
        raise HTTPException(404, "Fayl topilmadi")
    path = UPLOAD_DIR / jf.stored_path
    if not path.exists():
        raise HTTPException(404, "Fayl diskda topilmadi")
    inline = not download and (jf.is_image or jf.mime in ("application/pdf",) or jf.mime.startswith("video/"))
    return FileResponse(
        path,
        media_type=jf.mime,
        headers={"Content-Disposition": _disposition(jf.original_name, inline), "Cache-Control": "private, max-age=86400"},
    )


@router.post("/files/{file_id}/delete")
async def delete_file(file_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    jf = await db.get(JobFile, file_id)
    if not jf:
        raise HTTPException(404, "Fayl topilmadi")
    job = await db.get(Job, jf.job_id)
    name = jf.original_name
    delete_file_from_disk(jf)
    await db.delete(jf)
    if job:
        add_event(db, job, user, "file", f"Fayl o'chirildi: {name}")
    await db.commit()
    return redirect(f"/jobs/{jf.job_id}", "Fayl o'chirildi", request)


@router.post("/files/{file_id}/kind")
async def change_kind(file_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    jf = await db.get(JobFile, file_id)
    if not jf:
        raise HTTPException(404, "Fayl topilmadi")
    form = await request.form()
    kind = form.get("kind")
    if kind in FILE_KINDS:
        jf.kind = kind
        await db.commit()
    return redirect(f"/jobs/{jf.job_id}")


def _build_zip(job: Job, dest) -> None:
    used: set[str] = set()
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for f in job.files:
            src = UPLOAD_DIR / f.stored_path
            if not src.exists():
                continue
            folder = secure_filename(FILE_KINDS.get(f.kind, f.kind))
            name = f"{folder}/{secure_filename(f.original_name)}"
            base, n = name, 1
            while name in used:
                stem, dot, ext = base.rpartition(".")
                name = f"{stem}_{n}.{ext}" if dot else f"{base}_{n}"
                n += 1
            used.add(name)
            zf.write(src, name)


@router.get("/jobs/{job_id}/files.zip")
async def job_zip(job_id: int, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job or not job.files:
        raise HTTPException(404, "Fayllar yo'q")
    tmp = TMP_DIR / f"zip_{uuid.uuid4().hex}.zip"
    await asyncio.to_thread(_build_zip, job, tmp)
    name = f"ish_{job.id}_{secure_filename(job.title)}.zip"
    return FileResponse(
        tmp,
        media_type="application/zip",
        headers={"Content-Disposition": _disposition(name, False)},
        background=BackgroundTask(lambda: tmp.unlink(missing_ok=True)),
    )
