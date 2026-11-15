from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user, require_manager
from ..constants import UNITS
from ..db import get_db
from ..models import PriceItem, User
from ..services import parse_float
from ..web import redirect, render

router = APIRouter(prefix="/prices")


@router.get("")
async def prices_list(request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(PriceItem).order_by(PriceItem.position, PriceItem.name))).scalars().all()
    return render(request, "prices/list.html", items=items, units=UNITS)


@router.post("")
async def price_add(request: Request, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    form = await request.form()
    name = (form.get("name") or "").strip()
    if not name:
        return redirect("/prices", "Nomini kiriting", request, "error")
    db.add(
        PriceItem(
            name=name[:255],
            unit=(form.get("unit") or "m²")[:32],
            price=parse_float(form.get("price"), 0) or 0,
            note=(form.get("note") or "").strip()[:255],
            position=int(parse_float(form.get("position"), 0) or 0),
        )
    )
    await db.commit()
    return redirect("/prices", "Qo'shildi", request)


@router.post("/{item_id}")
async def price_update(item_id: int, request: Request, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    item = await db.get(PriceItem, item_id)
    if not item:
        raise HTTPException(404, "Topilmadi")
    form = await request.form()
    item.name = (form.get("name") or item.name).strip()[:255]
    item.unit = (form.get("unit") or item.unit)[:32]
    item.price = parse_float(form.get("price"), item.price) or 0
    item.note = (form.get("note") or "").strip()[:255]
    item.position = int(parse_float(form.get("position"), item.position) or 0)
    item.is_active = bool(form.get("is_active"))
    await db.commit()
    return redirect("/prices", "Saqlandi", request)


@router.post("/{item_id}/delete")
async def price_delete(item_id: int, request: Request, user: User = Depends(require_manager), db: AsyncSession = Depends(get_db)):
    item = await db.get(PriceItem, item_id)
    if item:
        await db.delete(item)
        await db.commit()
    return redirect("/prices", "O'chirildi", request)
