from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user
from ..constants import ACTIVE_STATUSES, STATUS_CODES
from ..db import get_db
from ..models import Job, JobEvent, User
from ..web import TZ, local_today, render

router = APIRouter()


def _local_midnight_utc(d) -> datetime:
    return datetime.combine(d, time.min, tzinfo=TZ).astimezone(timezone.utc).replace(tzinfo=None)


@router.get("/")
async def dashboard(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    today = local_today()
    month_start = _local_midnight_utc(today.replace(day=1))
    today_start = _local_midnight_utc(today)

    counts = dict(
        (await db.execute(select(Job.status, func.count(Job.id)).group_by(Job.status))).all()
    )
    status_counts = [(s, counts.get(s, 0)) for s in STATUS_CODES]
    active_total = sum(counts.get(s, 0) for s in ACTIVE_STATUSES)

    created_today = (
        await db.execute(select(func.count(Job.id)).where(Job.created_at >= today_start))
    ).scalar() or 0
    done_month = (
        await db.execute(select(func.count(Job.id)).where(Job.status == "done", Job.done_at >= month_start))
    ).scalar() or 0

    active_jobs = (
        await db.execute(select(Job).where(Job.status.in_(ACTIVE_STATUSES)).order_by(Job.due_date.is_(None), Job.due_date))
    ).scalars().all()
    overdue = [j for j in active_jobs if j.is_overdue]
    due_soon = [
        j for j in active_jobs if j.due_date and not j.is_overdue and j.due_date <= today + timedelta(days=2)
    ]
    urgent = [j for j in active_jobs if j.priority == "urgent"]

    # Dizaynerlar bandligi
    designers = (
        await db.execute(select(User).where(User.role == "designer", User.is_active.is_(True)).order_by(User.full_name))
    ).scalars().all()
    workload = []
    for d in designers:
        mine = [j for j in active_jobs if j.designer_id == d.id]
        done_cnt = (
            await db.execute(
                select(func.count(Job.id)).where(
                    Job.designer_id == d.id, Job.status == "done", Job.done_at >= month_start
                )
            )
        ).scalar() or 0
        workload.append(
            {
                "user": d,
                "active": len(mine),
                "design": sum(1 for j in mine if j.status in ("new", "design", "revision")),
                "review": sum(1 for j in mine if j.status == "review"),
                "overdue": sum(1 for j in mine if j.is_overdue),
                "done": done_cnt,
            }
        )
    unassigned = [j for j in active_jobs if not j.designer_id]

    # Moliya (shu oy yaratilgan ishlar bo'yicha)
    month_jobs = (
        await db.execute(select(Job).where(Job.created_at >= month_start, Job.status != "cancelled"))
    ).scalars().all()
    finance = {
        "total": sum(j.total for j in month_jobs),
        "paid": sum(j.paid or 0 for j in month_jobs),
    }
    finance["debt"] = finance["total"] - finance["paid"]
    all_debt = sum(max(j.debt, 0) for j in active_jobs)

    events = (
        await db.execute(select(JobEvent).order_by(JobEvent.id.desc()).limit(15))
    ).scalars().all()

    my_jobs = [j for j in active_jobs if j.designer_id == user.id or j.manager_id == user.id]

    return render(
        request,
        "dashboard.html",
        status_counts=status_counts,
        active_total=active_total,
        created_today=created_today,
        done_month=done_month,
        overdue=overdue,
        due_soon=due_soon,
        urgent=urgent,
        workload=workload,
        unassigned=unassigned,
        finance=finance,
        all_debt=all_debt,
        events=events,
        my_jobs=my_jobs,
    )
