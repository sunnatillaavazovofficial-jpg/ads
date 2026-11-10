"""DizaynHub — ishga tushirish: python run.py"""
import uvicorn

from app import config

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
        log_level="info",
    )
