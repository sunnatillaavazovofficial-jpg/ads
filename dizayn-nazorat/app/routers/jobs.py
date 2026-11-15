from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from ..auth import current_user
from ..constants import ACTIVE_STATUSES, FILE_KINDS, PRIORITIES, STATUS_CODES, STATUS_LABELS, UNITS
from ..db import get_db
from ..models import Job, JobEvent, PriceItem, TgChat, User
from ..services import (
    UploadTooLarge,
    add_event,
    apply_items,
    assign,
    change_status,
    delete_job_dir,
    notify_designer_assigned,
    notify_users,
    parse_float,
    save_upload,
    _h,
)
from ..config import MAX_UPLOAD_MB
from ..web import redirect, render

router = APIRouter()
PER_PAGE = 50


async def _staff(db: AsyncSession):
    res = await db.execute(select(User).where(User.is_active.is_(True)).order_by(User.full_name, User.username))
    users = res.scalars().all()
    managers = [u for u in users if u.role in ("admin", "manager")]
    designers = [u for u in users if u.role == "designer"]
    return users, managers, designers


async def _get_job(db: AsyncSession, job_id: int) -> Job:
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Ish topilmadi")
    return job


def _int_or_none(v) -> int | None:
    try:
        return int(v) if v not in (None, "", "0") else None
    except (TypeError, ValueError):
        return None


def _parse_date(v) -> date | None:
    try:
        return date.fromisoformat(v) if v else None
    except ValueError:
        return None


# ----------------------------- ro'yxat -----------------------------


def _apply_filters(q, f: dict, user: User):
    if f.get("q"):
        term = f"%{f['q'].strip()}%"
        conds = [
            Job.title.ilike(term),
            Job.client_name.ilike(term),
            Job.client_contact.ilike(term),
            Job.address.ilike(term),
            Job.comment.ilike(term),
        ]
        digits = f["q"].strip().lstrip("#")
        if digits.isdigit():
            conds.append(Job.id == int(digits))
        q = q.where(or_(*conds))
    st = f.get("status") or "active"
    if st == "active":
        q = q.where(Job.status.in_(ACTIVE_STATUSES))
    elif st == "overdue":
        from ..models import local_today

        q = q.where(Job.status.in_(ACTIVE_STATUSES), Job.due_date < local_today())
    elif st in STATUS_CODES:
        q = q.where(Job.status == st)
    if f.get("designer") == "none":
        q = q.where(Job.designer_id.is_(None))
    elif _int_or_none(f.get("designer")):
        q = q.where(Job.designer_id == int(f["designer"]))
    if _int_or_none(f.get("manager")):
        q = q.where(Job.manager_id == int(f["manager"]))
    if f.get("priority") in PRIORITIES:
        q = q.where(Job.priority == f["priority"])
    if f.get("mine"):
        q = q.where(or_(Job.designer_id == user.id, Job.manager_id == user.id, Job.created_by_id == user.id))
    return q


@router.get("/jobs")
async def jobs_list(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    f = dict(request.query_params)
    page = max(_int_or_none(f.get("page")) or 1, 1)
    q = _apply_filters(select(Job), f, user)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    sort = f.get("sort", "new")
    order = {
        "new": [Job.id.desc()],
        "old": [Job.id.asc()],
        "due": [Job.due_date.is_(None), Job.due_date.asc()],
        "updated": [Job.updated_at.desc()],
    }.get(sort, [Job.id.desc()])
    jobs = (await db.execute(q.order_by(*order).offset((page - 1) * PER_PAGE).limit(PER_PAGE))).scalars().all()
    _, managers, designers = await _staff(db)
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    return render(
        request, "jobs/list.html", jobs=jobs, f=f, total=total, page=page, pages=pages,
        managers=managers, designers=designers,
    )


@router.get("/jobs/board")
async def jobs_board(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    f = dict(request.query_params)
    show_closed = f.get("closed") == "1"
    f2 = {**f, "status": "all"}
    q = _apply_filters(select(Job), f2, user)
    if not show_closed:
        q = q.where(Job.status.in_(ACTIVE_STATUSES))
    else:
        from datetime import timedelta

        from ..db import utcnow

        # yakunlanganlardan faqat oxirgi 30 kunlik
        q = q.where(or_(Job.status.in_(ACTIVE_STATUSES), Job.status_changed_at >= utcnow() - timedelta(days=30)))
    jobs = (await db.execute(q.order_by(Job.priority.desc(), Job.due_date.is_(None), Job.due_date, Job.id.desc()))).scalars().all()
    columns = [s for s in STATUS_CODES if show_closed or s in ACTIVE_STATUSES]
    by_status = {s: [] for s in columns}
    for j in jobs:
        by_status.setdefault(j.status, []).append(j)
    _, managers, designers = await _staff(db)
    return render(
        request, "jobs/board.html", columns=columns, by_status=by_status, f=f,
        managers=managers, designers=designers, show_closed=show_closed,
    )


# ----------------------------- yaratish / tahrirlash -----------------------------


async def _form_ctx(db: AsyncSession):
    _, managers, designers = await _staff(db)
    prices = (
        await db.execute(select(PriceItem).where(PriceItem.is_active.is_(True)).order_by(PriceItem.position, PriceItem.name))
    ).scalars().all()
    return {
        "managers": managers,
        "designers": designers,
        "prices": prices,
        "prices_json": [{"name": p.name, "unit": p.unit, "price": p.price} for p in prices],
        "units": UNITS,
        "max_mb": MAX_UPLOAD_MB,
    }


@router.get("/jobs/new")
async def job_new(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    qp = request.query_params
    job = Job(
        title=qp.get("title", ""),
        client_name=qp.get("client_name", ""),
        client_contact=qp.get("client_contact", ""),
        status="new",
        priority="normal",
        size_unit="m",
        manager_id=user.id if user.can_manage else None,
        designer_id=user.id if user.role == "designer" else None,
        discount=0,
        paid=0,
    )
    tg_chat = None
    if _int_or_none(qp.get("tg_chat")):
        tg_chat = await db.get(TgChat, int(qp["tg_chat"]))
    ctx = await _form_ctx(db)
    return render(request, "jobs/form.html", job=job, is_new=True, tg_chat=tg_chat, **ctx)


def _fill_job(job: Job, form) -> None:
    job.title = (form.get("title") or "").strip()[:255] or "Nomsiz ish"
    job.client_name = (form.get("client_name") or "").strip()[:255]
    job.client_contact = (form.get("client_contact") or "").strip()[:255]
    job.address = (form.get("address") or "").strip()[:500]
    job.width = parse_float(form.get("width"))
    job.height = parse_float(form.get("height"))
    job.size_unit = form.get("size_unit") if form.get("size_unit") in ("m", "sm") else "m"
    job.size_note = (form.get("size_note") or "").strip()[:255]
    job.comment = (form.get("comment") or "").strip()
    job.priority = form.get("priority") if form.get("priority") in PRIORITIES else "normal"
    job.due_date = _parse_date(form.get("due_date"))
    job.discount = parse_float(form.get("discount"), 0) or 0
    job.paid = parse_float(form.get("paid"), 0) or 0
    apply_items(
        job,
        form.getlist("item_name"),
        form.getlist("item_unit"),
        form.getlist("item_qty"),
        form.getlist("item_price"),
    )


async def _save_files(db, job: Job, form, user: User) -> list[str]:
    errors = []
    for field, kind in (("place_files", "place"), ("logo_files", "logo"), ("design_files", "design")):
        for up in form.getlist(field):
            if not isinstance(up, UploadFile) or not up.filename:
                continue
            try:
                jf = await save_upload(job.id, up, kind, user.id)
                if jf:
                    db.add(jf)
            except UploadTooLarge:
                errors.append(f"{up.filename} — {MAX_UPLOAD_MB} MB dan katta")
    return errors


@router.post("/jobs/new")
async def job_create(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    form = await request.form()
    job = Job(created_by_id=user.id, source="web")
    _fill_job(job, form)
    job.manager_id = _int_or_none(form.get("manager_id"))
    job.designer_id = _int_or_none(form.get("designer_id"))
    st = form.get("status")
    job.status = st if st in STATUS_CODES else "new"
    if _int_or_none(form.get("tg_chat_id")):
        job.tg_chat_id = int(form["tg_chat_id"])
        job.source = "inbox"
    db.add(job)
    await db.flush()
    errors = await _save_files(db, job, form, user)
    add_event(db, job, user, "create", "Ish yaratildi")
    await db.commit()
    await db.refresh(job, ["designer", "manager", "files"])
    notify_designer_assigned(job, user)
    if errors:
        return redirect(f"/jobs/{job.id}", "Ish saqlandi, lekin ba'zi fayllar yuklanmadi: " + "; ".join(errors), request, "error")
    return redirect(f"/jobs/{job.id}", f"#{job.id} ish yaratildi", request)


@router.get("/jobs/{job_id}/edit")
async def job_edit(job_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job(db, job_id)
    ctx = await _form_ctx(db)
    tg_chat = await db.get(TgChat, job.tg_chat_id) if job.tg_chat_id else None
    return render(request, "jobs/form.html", job=job, is_new=False, tg_chat=tg_chat, **ctx)


@router.post("/jobs/{job_id}/edit")
async def job_update(job_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job(db, job_id)
    form = await request.form()
    old_total = job.total
    _fill_job(job, form)
    errors = await _save_files(db, job, form, user)
    add_event(db, job, user, "edit", "Ish ma'lumotlari tahrirlandi")
    if round(old_total) != round(job.total):
        from ..web import fmt_money

        add_event(db, job, user, "price", f"Narx: {fmt_money(old_total)} → {fmt_money(job.total)}")
    await db.commit()
    new_status = form.get("status")
    if new_status and new_status != job.status:
        await change_status(db, job, new_status, user)
    await assign(db, job, _int_or_none(form.get("manager_id")), _int_or_none(form.get("designer_id")), user)
    if errors:
        return redirect(f"/jobs/{job.id}", "Saqlandi, lekin ba'zi fayllar yuklanmadi: " + "; ".join(errors), request, "error")
    return redirect(f"/jobs/{job.id}", "O'zgarishlar saqlandi", request)


@router.post("/jobs/{job_id}/delete")
async def job_delete(job_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job(db, job_id)
    title = job.title
    await db.delete(job)
    await db.commit()
    delete_job_dir(job_id)
    return redirect("/jobs", f"#{job_id} «{title}» o'chirildi", request)


# ----------------------------- ko'rish va tezkor amallar -----------------------------


@router.get("/jobs/{job_id}")
async def job_detail(job_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job(db, job_id)
    events = (
        await db.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.desc()))
    ).scalars().all()
    _, managers, designers = await _staff(db)
    files_by_kind = {k: [f for f in job.files if f.kind == k] for k in FILE_KINDS}
    tg_chat = await db.get(TgChat, job.tg_chat_id) if job.tg_chat_id else None
    return render(
        request, "jobs/detail.html", job=job, events=events, managers=managers, designers=designers,
        files_by_kind=files_by_kind, tg_chat=tg_chat, max_mb=MAX_UPLOAD_MB,
    )


@router.post("/jobs/{job_id}/status")
async def job_status(job_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job(db, job_id)
    is_json = request.headers.get("content-type", "").startswith("application/json")
    if is_json:
        data = await request.json()
        status = data.get("status")
    else:
        form = await request.form()
        status = form.get("status")
    if status not in STATUS_LABELS:
        if is_json:
            return JSONResponse({"error": "Noto'g'ri holat"}, status_code=400)
        raise HTTPException(400, "Noto'g'ri holat")
    await change_status(db, job, status, user)
    if is_json:
        return {"ok": True, "status": status, "label": STATUS_LABELS[status]}
    return redirect(f"/jobs/{job.id}", f"Holat: {STATUS_LABELS[status]}", request)


@router.post("/jobs/{job_id}/assign")
async def job_assign(job_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job(db, job_id)
    form = await request.form()
    await assign(db, job, _int_or_none(form.get("manager_id")), _int_or_none(form.get("designer_id")), user)
    return redirect(f"/jobs/{job.id}", "Mas'ullar saqlandi", request)


@router.post("/jobs/{job_id}/comment")
async def job_comment(job_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await _get_job(db, job_id)
    form = await request.form()
    text = (form.get("text") or "").strip()
    errors = []
    has_files = any(isinstance(u, UploadFile) and u.filename for u in form.getlist("files"))
    if has_files:
        kind = form.get("kind") if form.get("kind") in FILE_KINDS else "logo"
        for up in form.getlist("files"):
            if isinstance(up, UploadFile) and up.filename:
                try:
                    jf = await save_upload(job.id, up, kind, user.id)
                    if jf:
                        db.add(jf)
                        add_event(db, job, user, "file", f"Fayl yuklandi ({FILE_KINDS[kind]}): {up.filename}")
                except UploadTooLarge:
                    errors.append(up.filename)
    if text:
        add_event(db, job, user, "comment", text)
    if not text and not has_files:
        return redirect(f"/jobs/{job.id}")
    await db.commit()
    if text:
        notify_users(
            [job.manager, job.designer],
            f"💬 <b>#{job.id} {_h(job.title)}</b>\n{_h(user.display_name)}: {_h(text[:800])}",
            job.id,
            exclude=user,
        )
    elif has_files:
        kind_label = FILE_KINDS.get(form.get("kind"), "Fayl")
        notify_users(
            [job.manager, job.designer],
            f"📎 <b>#{job.id} {_h(job.title)}</b>\n{_h(user.display_name)} yangi fayl yukladi: {kind_label}",
            job.id,
            exclude=user,
        )
    if errors:
        return redirect(f"/jobs/{job.id}", f"{MAX_UPLOAD_MB} MB dan katta fayllar yuklanmadi: " + ", ".join(errors), request, "error")
    return redirect(f"/jobs/{job.id}#activity")


@router.post("/jobs/{job_id}/payment")
async def job_payment(job_id: int, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Tezkor to'lov qo'shish."""
    from ..web import fmt_money

    job = await _get_job(db, job_id)
    form = await request.form()
    amount = parse_float(form.get("amount"), 0) or 0
    if amount:
        job.paid = (job.paid or 0) + amount
        add_event(db, job, user, "price", f"To'lov qabul qilindi: {fmt_money(amount)} (jami to'langan: {fmt_money(job.paid)})")
        await db.commit()
    return redirect(f"/jobs/{job.id}", "To'lov qo'shildi" if amount else None, request)
