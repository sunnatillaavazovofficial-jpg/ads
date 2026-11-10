from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from starlette.datastructures import UploadFile

from ..db import get_db
from ..models import STATUSES, Material, User, Work, WorkFile, now
from ..security import current_user, flash, require_admin
from ..services import works as svc
from ..services.files import delete_stored, delete_work_dir, file_path, store_file, thumb_path
from ..web import accessible_chats, redirect, render

router = APIRouter()

UPLOAD_FIELDS = {"image": "image_files", "logo": "logo_files", "file": "other_files"}
ACTIVE = ("new", "accepted", "in_progress", "done")


def _get_work(db: Session, work_id: int) -> Work:
    work = db.get(Work, work_id, options=[selectinload(Work.files), selectinload(Work.events),
                                          selectinload(Work.expenses)])
    if work is None:
        raise HTTPException(404, "Ish topilmadi")
    return work


def _uploads(form) -> dict[str, list[UploadFile]]:
    out = {}
    for kind, field in UPLOAD_FIELDS.items():
        out[kind] = [f for f in form.getlist(field) if isinstance(f, UploadFile) and f.filename]
    return out


# ------------------------------------------------------------------ bosh sahifa
@router.get("/")
def dashboard(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Work.status, func.count()).group_by(Work.status)).all())
    base = select(Work).options(selectinload(Work.files)).order_by(Work.id.desc())
    waiting = list(db.scalars(base.where(Work.status == "new").limit(12)))
    mine: list[Work] = []
    if user.is_designer:
        mine = list(db.scalars(base.where(Work.designer_id == user.id, Work.status.in_(["accepted", "in_progress"]))))
    elif user.is_manager:
        mine = list(db.scalars(base.where(Work.manager_id == user.id, Work.status.in_(ACTIVE)).limit(12)))
    recent = list(db.scalars(base.limit(12)))
    week_ago = now() - timedelta(days=7)
    week_done = db.scalar(select(func.count()).select_from(Work).where(Work.done_at >= week_ago)) or 0
    return render(request, "dashboard.html", counts=counts, waiting=waiting, mine=mine, recent=recent,
                  week_done=week_done)


# ------------------------------------------------------------------ ro'yxat
@router.get("/works")
def works_list(request: Request, q: str = "", status: str = "", type: str = "", who: str = "",
               page: int = 1, user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Work).options(selectinload(Work.files))
    if q.strip():
        like = f"%{q.strip()}%"
        conds = [Work.title.ilike(like), Work.short_desc.ilike(like), Work.client_name.ilike(like),
                 Work.special_text.ilike(like), Work.client_phone.ilike(like)]
        if q.strip().lstrip("#").isdigit():
            conds.append(Work.id == int(q.strip().lstrip("#")))
        query = query.where(or_(*conds))
    if status == "active":
        query = query.where(Work.status.in_(ACTIVE))
    elif status in STATUSES:
        query = query.where(Work.status == status)
    if type:
        query = query.where(Work.work_type == type)
    if who == "mine":
        query = query.where(or_(Work.manager_id == user.id, Work.designer_id == user.id))
    per_page = 24
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = max(page, 1)
    works = list(db.scalars(query.order_by(Work.id.desc()).offset((page - 1) * per_page).limit(per_page)))
    pages = max((total + per_page - 1) // per_page, 1)
    return render(request, "works_list.html", works=works, q=q, status=status, type=type, who=who,
                  page=page, pages=pages, total=total, types=svc.work_types(db))


# ------------------------------------------------------------------ yangi ish
def _form_ctx(db: Session, user: User, **extra):
    return dict(types=svc.work_types(db), chats=accessible_chats(db, user), **extra)


@router.get("/works/new")
def work_new(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not user.can_create_work:
        raise HTTPException(403, "Yangi ishni faqat menejer joylaydi")
    return render(request, "work_form.html", **_form_ctx(db, user, work=None, form={}, errors={}))


@router.post("/works/new")
async def work_create(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not user.can_create_work:
        raise HTTPException(403, "Yangi ishni faqat menejer joylaydi")
    form = await request.form()
    data = {k: v for k, v in form.items() if isinstance(v, str)}
    uploads = _uploads(form)
    cleaned, errors = svc.validate_work(db, data, {k: len(v) for k, v in uploads.items()})
    if cleaned.get("tg_chat_id") and cleaned["tg_chat_id"] not in {c.id for c in accessible_chats(db, user)}:
        cleaned["tg_chat_id"] = None
    if errors:
        return render(request, "work_form.html", status_code=400,
                      **_form_ctx(db, user, work=None, form=data, errors=errors))
    files = {k: [(f.filename, f.file) for f in v] for k, v in uploads.items()}
    work = await run_in_threadpool(svc.create_work, db, user, cleaned, files)
    flash(request, f"Ish #{work.id} saqlandi va bosh dizaynerga yuborildi")
    return redirect(f"/works/{work.id}")


# ------------------------------------------------------------------ ish sahifasi
@router.get("/works/{work_id}")
def work_detail(work_id: int, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    show_acc = svc.can_see_accounting(work, user)
    materials = list(db.scalars(select(Material).where(Material.is_active.is_(True)).order_by(Material.name))) \
        if show_acc else []
    show_chat = bool(work.tg_chat_id) and work.tg_chat_id in {c.id for c in accessible_chats(db, user)}
    return render(request, "work_detail.html", work=work, actions=svc.actions_for(work, user),
                  labels=svc.ACTION_LABELS, designers=svc.designers(db), can_edit=svc.can_edit(work, user),
                  can_result=svc.can_upload_result(work, user), show_acc=show_acc, materials=materials,
                  show_chat=show_chat)


@router.get("/works/{work_id}/edit")
def work_edit(work_id: int, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    if not svc.can_edit(work, user):
        raise HTTPException(403, "Bu ishni tahrirlash mumkin emas")
    form = {c: getattr(work, c) for c in (
        "title", "work_type", "short_desc", "width", "height", "size_unit", "quantity", "extra_info",
        "special_text", "client_name", "client_phone", "tg_chat_id", *svc.NONE_FLAGS)}
    form["deadline"] = work.deadline.strftime("%Y-%m-%d") if work.deadline else ""
    for k in ("width", "height"):
        form[k] = f"{form[k]:g}" if form[k] else ""
    return render(request, "work_form.html", **_form_ctx(db, user, work=work, form=form, errors={}))


@router.post("/works/{work_id}/edit")
async def work_update(work_id: int, request: Request, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    if not svc.can_edit(work, user):
        raise HTTPException(403, "Bu ishni tahrirlash mumkin emas")
    form = await request.form()
    data = {k: v for k, v in form.items() if isinstance(v, str)}
    uploads = _uploads(form)
    remove_ids = {int(x) for x in form.getlist("remove_file") if str(x).isdigit()}
    counts = {}
    for kind in UPLOAD_FIELDS:
        existing = [f for f in work.files_of(kind) if f.id not in remove_ids]
        counts[kind] = len(existing) + len(uploads[kind])
    cleaned, errors = svc.validate_work(db, data, counts)
    if cleaned.get("tg_chat_id") and cleaned["tg_chat_id"] not in {c.id for c in accessible_chats(db, user)}:
        cleaned["tg_chat_id"] = work.tg_chat_id
    if errors:
        return render(request, "work_form.html", status_code=400,
                      **_form_ctx(db, user, work=work, form=data, errors=errors))

    def apply():
        for key, value in cleaned.items():
            setattr(work, key, value)
        for wf in list(work.files):
            if wf.id in remove_ids and wf.kind in UPLOAD_FIELDS:
                delete_stored(wf)
                work.files.remove(wf)
        for kind, items in uploads.items():
            for f in items:
                work.files.append(store_file(work.id, kind, f.filename, f.file, user.id))
        svc.add_event(db, work, user, "edit", "Ish ma'lumotlari tahrirlandi")
        db.commit()

    await run_in_threadpool(apply)
    flash(request, "O'zgarishlar saqlandi")
    return redirect(f"/works/{work.id}")


@router.post("/works/{work_id}/action")
async def work_action(work_id: int, request: Request, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    form = await request.form()
    action = str(form.get("action", ""))
    designer_id = form.get("designer_id")
    try:
        svc.apply_action(db, work, user, action,
                         designer_id=int(designer_id) if str(designer_id or "").isdigit() else None,
                         comment=str(form.get("comment", "")))
        flash(request, f"Holat: {work.status_name}")
    except svc.ActionError as exc:
        flash(request, str(exc), "error")
    return redirect(f"/works/{work.id}")


@router.post("/works/{work_id}/reassign")
async def work_reassign(work_id: int, request: Request, user: User = Depends(current_user),
                        db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    form = await request.form()
    try:
        svc.reassign(db, work, user, int(form.get("designer_id") or 0))
        flash(request, "Dizayner almashtirildi")
    except (svc.ActionError, ValueError) as exc:
        flash(request, str(exc), "error")
    return redirect(f"/works/{work.id}")


@router.post("/works/{work_id}/comment")
async def work_comment(work_id: int, request: Request, user: User = Depends(current_user),
                       db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    form = await request.form()
    svc.add_comment(db, work, user, str(form.get("text", "")))
    return redirect(f"/works/{work.id}#tarix")


@router.post("/works/{work_id}/result")
async def work_result(work_id: int, request: Request, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    if not svc.can_upload_result(work, user):
        raise HTTPException(403, "Tayyor ishni faqat biriktirilgan dizayner yuklaydi")
    form = await request.form()
    files = [f for f in form.getlist("result_files") if isinstance(f, UploadFile) and f.filename]
    if not files:
        flash(request, "Fayl tanlanmadi", "error")
        return redirect(f"/works/{work.id}")

    def save():
        for f in files:
            work.files.append(store_file(work.id, "result", f.filename, f.file, user.id))
        svc.add_event(db, work, user, "file", f"Tayyor ish yuklandi: {', '.join(f.filename for f in files)}")
        db.commit()

    await run_in_threadpool(save)
    if form.get("mark_done") and "done" in svc.actions_for(work, user):
        try:
            svc.apply_action(db, work, user, "done", comment=str(form.get("comment", "")))
        except svc.ActionError as exc:
            flash(request, str(exc), "error")
    flash(request, "Fayl(lar) yuklandi")
    return redirect(f"/works/{work.id}")


@router.post("/works/{work_id}/files/{file_id}/delete")
def file_delete(work_id: int, file_id: int, request: Request, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    wf = db.get(WorkFile, file_id)
    if wf is None or wf.work_id != work.id:
        raise HTTPException(404, "Fayl topilmadi")
    allowed = user.is_admin or (wf.kind == "result" and wf.uploaded_by_id == user.id) or \
        (wf.kind == "result" and user.is_chief)
    if not allowed:
        raise HTTPException(403, "Faylni o'chirish mumkin emas")
    delete_stored(wf)
    svc.add_event(db, work, user, "file", f"Fayl o'chirildi: {wf.original_name}")
    db.delete(wf)
    db.commit()
    flash(request, "Fayl o'chirildi")
    return redirect(f"/works/{work.id}")


@router.post("/works/{work_id}/delete")
def work_delete(work_id: int, request: Request, user: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    work = _get_work(db, work_id)
    db.delete(work)
    db.commit()
    delete_work_dir(work_id)
    flash(request, f"Ish #{work_id} o'chirildi")
    return redirect("/works")


# ------------------------------------------------------------------ fayllar
@router.get("/files/{file_id}")
def file_get(file_id: int, thumb: int = 0, dl: int = 0, user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    wf: Optional[WorkFile] = db.get(WorkFile, file_id)
    if wf is None:
        raise HTTPException(404, "Fayl topilmadi")
    if thumb and wf.thumb_name:
        path = thumb_path(wf)
        media = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/jpeg"
        return FileResponse(path, media_type=media, headers={
            "Cache-Control": "private, max-age=86400", "Content-Security-Policy": "sandbox"})
    path = file_path(wf)
    if not path.exists():
        raise HTTPException(404, "Fayl diskda topilmadi")
    is_pdf = wf.mime == "application/pdf"
    inline = not dl and (wf.mime.startswith("image/") or is_pdf)
    headers = {"X-Content-Type-Options": "nosniff"}
    if not is_pdf:
        headers["Content-Security-Policy"] = "sandbox"  # SVG/HTML ichidagi skriptlar ishlamasin
    return FileResponse(path, media_type=wf.mime, filename=wf.original_name,
                        content_disposition_type="inline" if inline else "attachment", headers=headers)
