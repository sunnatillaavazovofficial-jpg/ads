import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import config
from .db import Base, db_session, engine
from .routes import accounting, admin, auth, telegram, works
from .security import LoginRequired
from .services import notify
from .services.settings import bootstrap
from .tg.bot import bot
from .tg.manager import tg_manager
from .web import redirect, render

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("telethon").setLevel(logging.WARNING)
log = logging.getLogger("dizaynhub")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with db_session() as db:
        bootstrap(db)
    notify.set_loop(asyncio.get_running_loop())
    await tg_manager.start()
    await bot.start()
    log.info("%s ishga tushdi: http://%s:%s", config.SITE_NAME, config.HOST, config.PORT)
    yield
    await bot.stop()
    await tg_manager.stop()


app = FastAPI(title=config.SITE_NAME, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def origin_check(request: Request, call_next):
    """Boshqa saytdan yuborilgan POST so'rovlarni rad etadi (CSRF himoyasi)."""
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and origin != "null":
            allowed = {request.headers.get("host", ""), request.headers.get("x-forwarded-host", "")}
            if config.PUBLIC_URL:
                allowed.add(urlparse(config.PUBLIC_URL).netloc)
            if urlparse(origin).netloc not in allowed:
                return PlainTextResponse("Ruxsat etilmagan so'rov (origin)", status_code=403)
    return await call_next(request)


app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, session_cookie="dh_session",
                   max_age=60 * 60 * 24 * 30, same_site="lax", https_only=config.COOKIE_SECURE)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

for r in (auth.router, works.router, accounting.router, admin.router, telegram.router):
    app.include_router(r)


@app.exception_handler(LoginRequired)
async def _login_required(request: Request, exc: LoginRequired):
    if request.headers.get("x-requested-with") == "fetch":
        return JSONResponse({"error": "login"}, status_code=401)
    nxt = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    return redirect(f"/login?next={quote(nxt)}")


@app.exception_handler(HTTPException)
async def _http_error(request: Request, exc: HTTPException):
    if request.headers.get("x-requested-with") == "fetch":
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    titles = {403: "Ruxsat yo'q", 404: "Topilmadi"}
    return render(request, "error.html", status_code=exc.status_code,
                  title=titles.get(exc.status_code, "Xatolik"), message=exc.detail)


@app.get("/healthz")
def healthz():
    return {"ok": True}
