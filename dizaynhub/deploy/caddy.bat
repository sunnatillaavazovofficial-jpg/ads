@echo off
chcp 65001 >nul
cd /d "%~dp0"
title DizaynHub HTTPS (Caddy)
if not exist caddy.exe (
  echo caddy.exe topilmadi. https://caddyserver.com/download dan Windows uchun yuklab,
  echo shu papkaga qo'ying: %~dp0
  pause
  exit /b 1
)
caddy.exe run --config Caddyfile
pause
