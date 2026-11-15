import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .auth import Forbidden, LoginRequired, hash_password
from .config import ADMIN_PASSWORD, ADMIN_USERNAME, BASE_DIR, BOT_TOKEN, SECRET_KEY, SECURE_COOKIES
from .db import SessionLocal, init_db
from .models import PriceItem, User
from .routers import auth as auth_router
from .routers import dashboard, files, inbox, jobs, prices, tg_accounts, users
from .tg.manager import manager as tg_manager
from .web import render

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
log = logging.getLogger("app")

DEFAULT_PRICES = [
    ("Banner dizayni", "xizmat", 150000),
    ("Banner pechat (440 g)", "m²", 45000),
    ("Orakal pechat", "m²", 60000),
    ("Kompozit panel", "m²", 250000),
    ("Lightbox (yorug'li quti)", "m²", 900000),
    ("Hajmli harflar", "dona", 120000),
    ("O'rnatish", "xizmat", 200000),
]


async def bootstrap():
    await init_db()
    async with SessionLocal() as db:
        n = (await db.execute(select(func.count(User.id)))).scalar()
        if not n:
            db.add(
                User(
                    username=ADMIN_USERNAME.strip().lower(),
                    full_name="Administrator",
                    password_hash=hash_password(ADMIN_PASSWORD),
                    role="admin",
                )
            )
            log.warning("Admin yaratildi: login=%s (parolni darhol o'zgartiring!)", ADMIN_USERNAME)
        if not (await db.execute(select(func.count(PriceItem.id)))).scalar():
            for i, (name, unit, price) in enumerate(DEFAULT_PRICES):
                db.add(PriceItem(name=name, unit=unit, price=price, position=i))
        await db.commit()


async def _run_bot_forever():
    from .bot.handlers import run_bot

    delay = 5
    while True:
        try:
            await run_bot(BOT_TOKEN)
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Bot to'xtadi, %s soniyadan keyin qayta uriniladi", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap()
    tasks = []
    if BOT_TOKEN:
        tasks.append(asyncio.create_task(_run_bot_forever()))
    else:
        log.info("BOT_TOKEN berilmagan — Telegram bot o'chiq")
    tasks.append(asyncio.create_task(tg_manager.start_all()))
    yield
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await tg_manager.stop_all()


app = FastAPI(title="Dizayn Nazorat", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="dn_session",
    max_age=60 * 60 * 24 * 30,
    same_site="lax",
    https_only=SECURE_COOKIES,
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

for r in (auth_router, dashboard, jobs, files, users, prices, tg_accounts, inbox):
    app.include_router(r.router)


def _wants_json(request: Request) -> bool:
    return request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", "")


@app.exception_handler(LoginRequired)
async def _login_required(request: Request, exc: LoginRequired):
    if _wants_json(request):
        return JSONResponse({"error": "Tizimga kiring"}, status_code=401)
    nxt = request.url.path
    return RedirectResponse(f"/login?next={nxt}" if nxt not in ("/", "/login") else "/login", status_code=303)


@app.exception_handler(Forbidden)
async def _forbidden(request: Request, exc: Forbidden):
    if _wants_json(request):
        return JSONResponse({"error": "Ruxsat yo'q"}, status_code=403)
    return render(request, "error.html", status_code=403, code=403, message="Bu sahifaga ruxsatingiz yo'q.")


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    if _wants_json(request):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    msg = "Sahifa topilmadi." if exc.status_code == 404 else str(exc.detail)
    return render(request, "error.html", status_code=exc.status_code, code=exc.status_code, message=msg)


@app.get("/health")
async def health():
    return {"ok": True}
