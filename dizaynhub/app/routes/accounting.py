from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Material, User, Work, WorkExpense
from ..security import current_user, flash, require_admin, require_roles
from ..services import works as svc
from ..utils import money, num, parse_date, parse_float
from ..web import redirect, render

router = APIRouter()

UNITS = ["m²", "m", "dona", "list", "kg", "litr", "soat", "komplekt"]


# ------------------------------------------------------------------ ish xarajatlari
@router.post("/works/{work_id}/expenses")
async def expense_add(work_id: int, request: Request, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    work = db.get(Work, work_id)
    if work is None:
        raise HTTPException(404, "Ish topilmadi")
    if not svc.can_see_accounting(work, user):
        raise HTTPException(403, "Hisob bo'limi uchun ruxsat yo'q")
    form = await request.form()
    qty = parse_float(form.get("qty"))
    if not qty or qty <= 0:
        flash(request, "Miqdorni kiriting", "error")
        return redirect(f"/works/{work_id}#hisob")
    mat_id = str(form.get("material_id", ""))
    material = db.get(Material, int(mat_id)) if mat_id.isdigit() else None
    name = (str(form.get("name", "")).strip() or (material.name if material else ""))[:150]
    if not name:
        flash(request, "Material yoki xizmat nomini kiriting", "error")
        return redirect(f"/works/{work_id}#hisob")
    unit = (str(form.get("unit", "")).strip() or (material.unit if material else "dona"))[:20]
    cost = parse_float(form.get("cost_price"), material.cost_price if material else 0.0)
    price = parse_float(form.get("sell_price"), material.sell_price if material else 0.0)
    exp = WorkExpense(work_id=work.id, material_id=material.id if material else None, name=name, unit=unit,
                      qty=qty, cost_price=cost or 0, sell_price=price or 0, created_by_id=user.id)
    db.add(exp)
    svc.add_event(db, work, user, "expense",
                  f"Hisob: {name} — {num(qty)} {unit} (tannarx {money(exp.cost_total)}, narx {money(exp.price_total)})")
    db.commit()
    return redirect(f"/works/{work_id}#hisob")


@router.post("/works/{work_id}/expenses/{exp_id}/delete")
def expense_delete(work_id: int, exp_id: int, request: Request, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    work = db.get(Work, work_id)
    exp = db.get(WorkExpense, exp_id)
    if work is None or exp is None or exp.work_id != work.id:
        raise HTTPException(404, "Topilmadi")
    if not svc.can_see_accounting(work, user):
        raise HTTPException(403, "Ruxsat yo'q")
    svc.add_event(db, work, user, "expense", f"Hisobdan o'chirildi: {exp.name}")
    db.delete(exp)
    db.commit()
    return redirect(f"/works/{work_id}#hisob")


# ------------------------------------------------------------------ hisobot
@router.get("/accounting")
def report(request: Request, date_from: str = "", date_to: str = "", manager: str = "",
           with_cancelled: int = 0, user: User = Depends(require_roles("admin", "manager")),
           db: Session = Depends(get_db)):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    d_from = parse_date(date_from) or today.replace(day=1)
    d_to = parse_date(date_to) or today
    q = select(Work).options(selectinload(Work.expenses), selectinload(Work.manager)) \
        .where(Work.created_at >= d_from, Work.created_at < d_to + timedelta(days=1)).order_by(Work.id.desc())
    if not with_cancelled:
        q = q.where(Work.status != "cancelled")
    if user.is_manager:
        q = q.where(Work.manager_id == user.id)
    elif manager.isdigit():
        q = q.where(Work.manager_id == int(manager))
    works = list(db.scalars(q))

    totals = {"cost": 0.0, "price": 0.0, "profit": 0.0, "count": len(works)}
    mats: dict = defaultdict(lambda: {"qty": 0.0, "cost": 0.0, "price": 0.0})
    by_manager: dict = defaultdict(lambda: {"count": 0, "cost": 0.0, "price": 0.0})
    for w in works:
        totals["cost"] += w.total_cost
        totals["price"] += w.total_price
        m = by_manager[w.manager.full_name if w.manager else "—"]
        m["count"] += 1
        m["cost"] += w.total_cost
        m["price"] += w.total_price
        for e in w.expenses:
            row = mats[(e.name, e.unit)]
            row["qty"] += e.qty
            row["cost"] += e.cost_total
            row["price"] += e.price_total
    totals["profit"] = totals["price"] - totals["cost"]
    materials = sorted(mats.items(), key=lambda kv: -kv[1]["cost"])
    managers = list(db.scalars(select(User).where(User.role.in_(["manager", "admin"])).order_by(User.first_name))) \
        if user.is_admin else []
    return render(request, "accounting.html", works=works, totals=totals, materials=materials,
                  by_manager=sorted(by_manager.items()), d_from=d_from, d_to=d_to, manager=manager,
                  managers=managers, with_cancelled=with_cancelled)


# ------------------------------------------------------------------ materiallar katalogi
@router.get("/materials")
def materials(request: Request, user: User = Depends(require_roles("admin", "manager")),
              db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Material).order_by(Material.is_active.desc(), Material.name)))
    return render(request, "materials.html", materials=rows, units=UNITS)


def _material_from_form(form, m: Material) -> None:
    m.name = str(form.get("name", "")).strip()[:150] or m.name
    m.unit = str(form.get("unit", "")).strip()[:20] or "dona"
    m.cost_price = parse_float(form.get("cost_price"), 0.0) or 0.0
    m.sell_price = parse_float(form.get("sell_price"), 0.0) or 0.0


@router.post("/materials")
async def material_add(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    form = await request.form()
    if not str(form.get("name", "")).strip():
        flash(request, "Material nomini kiriting", "error")
        return redirect("/materials")
    m = Material(name="")
    _material_from_form(form, m)
    db.add(m)
    try:
        db.commit()
        flash(request, f"«{m.name}» qo'shildi")
    except IntegrityError:
        db.rollback()
        flash(request, "Bunday nomli material bor", "error")
    return redirect("/materials")


@router.post("/materials/{mat_id}")
async def material_update(mat_id: int, request: Request, user: User = Depends(require_admin),
                          db: Session = Depends(get_db)):
    m = db.get(Material, mat_id)
    if m is None:
        raise HTTPException(404, "Topilmadi")
    form = await request.form()
    if form.get("toggle"):
        m.is_active = not m.is_active
    else:
        _material_from_form(form, m)
    try:
        db.commit()
        flash(request, "Saqlandi")
    except IntegrityError:
        db.rollback()
        flash(request, "Bunday nomli material bor", "error")
    return redirect("/materials")
