# Dizayn Nazorat — dizaynerlar ishini nazorat qilish tizimi

Reklama agentligi uchun sayt: menejer yangi ish kiritadi, dizaynerga biriktiradi, ish qaysi bosqichdaligini,
kim qilayotganini, narxini va to'lovini kuzatib boradi. Telegram bot va 10 tagacha (yoki undan ko'p)
Telegram akkauntning saralangan chatlari bitta joyda.

## Imkoniyatlar

**Ishlar**
- Yangi ish: ish nomi, mijoz ismi, telefon yoki Telegram username, manzil/joy, joy o'lchami (eni × bo'yi, m yoki sm),
  izoh, muddat, shoshilinchlik.
- Fayllar: joy rasmi, logo va qo'shimcha fayllar, tayyor dizayn. **Har qanday format** qabul qilinadi
  (rasm, PDF, PSD, AI, CDR, ZIP...), sudrab tashlash mumkin. Barcha fayllarni bitta ZIP qilib yuklab olish.
- Har bir ishga **menejer** va **dizayner** biriktiriladi.
- **Bosqichlar (holat):** Yangi → Dizayn jarayonida → Mijoz tasdig'ida → Tuzatishda → Tasdiqlandi →
  Ishlab chiqarishda → O'rnatishda → Bajarildi (yoki Bekor qilindi).
- **Kanban doska** — kartochkani sudrab boshqa ustunga o'tkazsangiz, holat o'zgaradi.
- Ishni ochish, tahrirlash, o'chirish (dizaynerlar ham qila oladi).
- **Izohlar va tarix** — kim qachon nima qilgani (holat, tayinlash, fayl, to'lov) yozib boriladi.
- **Narx hisoblash:** narxlar ro'yxatidan xizmat/material tanlanadi, «m²» birligida miqdor avtomatik
  joy maydoniga teng bo'ladi; chegirma, avans, qoldiq. Keyin to'lov qo'shib borish mumkin.
- **Bosh sahifa:** faol ishlar, muddati o'tganlar, bosqichlar bo'yicha diagramma, dizaynerlar bandligi,
  oylik moliya (jami/to'langan/qarz), so'nggi harakatlar.
- Qidiruv va filtrlar: holat, dizayner, menejer, «mening ishlarim», muddat bo'yicha saralash.

**Telegram bot**
- Har bir xodim saytdagi **Profil** sahifasidan botni bir bosishda ulaydi.
- Botdan yangi ish kiritish: nom → mijoz → aloqa → o'lcham (`3x6`, `300x150 sm`) → manzil → izoh →
  joy rasmlari → logo/fayllar → narx → dizayner tanlash → saqlash.
- «Mening ishlarim», ish kartochkasi, holatni tugma bilan o'zgartirish, ish fayllarini botdan olish.
- Bildirishnomalar: dizaynerga yangi ish biriktirilganda, holat o'zgarganda, izoh yoki fayl qo'shilganda.

**Telegram akkauntlar (yagona inbox)**
- Bir nechta (masalan 10 ta) shaxsiy/ish Telegram akkauntini ulash (telefon + kod + 2FA parol).
- Har bir akkauntdan **kerakli chatlarni saralash** (shaxsiy, guruh, kanal).
- Barcha saralangan chatlar **bitta oynada**: har bir akkaunt o'z rangi bilan, o'qilmaganlar soni,
  akkaunt bo'yicha filtr, qidiruv.
- Saytdan javob yozish va fayl yuborish, rasm/video/ovozli xabar/fayllarni ko'rish.
- Chatdan bir bosishda **ish yaratish** (mijoz ismi va username avtomatik to'ladi).
- Chatdagi rasm yoki faylni **ishga biriktirish** (📎 tugmasi).
- Ixtiyoriy: yangi yozgan har bir mijozning chatini avtomatik qo'shish.

**Rollar**

| Rol | Imkoniyatlar |
|---|---|
| Administrator | Hammasi + xodimlar, Telegram akkauntlar |
| Menejer | Ishlar, narxlar ro'yxati, Telegram chatlar |
| Dizayner | Ishlarni ko'rish, ochish, tahrirlash, o'chirish, narx hisoblash, fayl yuklash, holat o'zgartirish |

## Serverga o'rnatish (Ubuntu, Docker bilan)

1. Docker o'rnating:

```bash
curl -fsSL https://get.docker.com | sh
```

2. Loyihani yuklab oling va papkaga kiring:

```bash
git clone https://github.com/sunnatillaavazovofficial-jpg/ads.git && cd ads/dizayn-nazorat
```

3. Sozlamalar faylini yarating va to'ldiring (pastdagi «Sozlamalar» bo'limiga qarang):

```bash
cp .env.example .env && nano .env
```

4. Ishga tushiring:

```bash
docker compose up -d --build
```

Sayt serverning o'zida `http://127.0.0.1:8000` da ishlaydi. Tashqaridan domen orqali HTTPS bilan ochish uchun
eng osoni — [Caddy](https://caddyserver.com/docs/install). `/etc/caddy/Caddyfile`:

```
crm.sizning-domen.uz {
    reverse_proxy 127.0.0.1:8000
    request_body {
        max_size 300MB
    }
}
```

So'ng `.env` da `SITE_URL=https://crm.sizning-domen.uz` va `SECURE_COOKIES=true` qilib, qayta ishga tushiring:

```bash
docker compose up -d
```

Nginx ishlatsangiz, `client_max_body_size 300m;` qo'yishni unutmang.

**Birinchi kirish:** `.env` dagi `ADMIN_USERNAME` / `ADMIN_PASSWORD` (standart: `admin` / `admin123`).
Kirgach darhol **Profil** dan parolni o'zgartiring, so'ng **Xodimlar** bo'limida menejer va dizaynerlarni qo'shing.

### Yangilash

```bash
git pull && docker compose up -d --build
```

### Zaxira nusxa

Barcha ma'lumotlar (baza, yuklangan fayllar, Telegram sessiyalari) `dizayn-nazorat/data/` papkasida.
Shu papkani muntazam nusxalab qo'ying. **Bu papkani hech kimga bermang** — unda Telegram akkauntlar sessiyasi bor.

## Sozlamalar (`.env`)

| O'zgaruvchi | Tavsif |
|---|---|
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Birinchi ishga tushishda yaratiladigan administrator |
| `SITE_URL` | Saytning tashqi manzili (bot xabarlaridagi «Saytda ochish» tugmasi uchun) |
| `SECRET_KEY` | Sessiya kaliti; bo'sh qolsa avtomatik yaratiladi |
| `SECURE_COOKIES` | HTTPS orqali ishlasangiz `true` |
| `BOT_TOKEN` | Telegram bot tokeni |
| `TG_API_ID`, `TG_API_HASH` | Telegram akkauntlarni ulash uchun |
| `TG_MARK_READ` | Saytda chat ochilganda Telegramda ham «o'qildi» qo'yilsinmi (`true`/`false`) |
| `MAX_UPLOAD_MB` | Bitta fayl uchun maksimal hajm (standart 300 MB) |
| `TIMEZONE` | Vaqt mintaqasi (standart `Asia/Tashkent`) |

### Telegram botni ulash
1. Telegramda [@BotFather](https://t.me/BotFather) → `/newbot` → nom bering → tokenni oling.
2. `.env` ga `BOT_TOKEN=...` yozing va qayta ishga tushiring.
3. Har bir xodim saytda **Profil → Telegramni ulash** tugmasini bosadi va botda **START** ni bosadi.

> Telegram Bot API cheklovi: bot orqali yuborilgan **20 MB dan katta** fayllarni bot yuklab ololmaydi —
> bunday fayllarni saytdan yuklang (sayt 300 MB gacha qabul qiladi).

### Telegram akkauntlarni ulash
1. [my.telegram.org](https://my.telegram.org) ga telefon raqamingiz bilan kiring → **API development tools** →
   ilova yarating (nomi ixtiyoriy) → `api_id` va `api_hash` ni oling.
2. `.env` ga `TG_API_ID=...` va `TG_API_HASH=...` yozing va qayta ishga tushiring.
3. Saytda **Telegram akkauntlar** → telefon raqam → Telegramga kelgan kod → (agar bo'lsa) 2FA parol.
4. **Chatlarni saralash** tugmasi → kerakli chatlarni belgilang → **Saqlash**. Hammasi **Telegram chatlar**
   bo'limida bitta joyda ko'rinadi.

Eslatmalar:
- Bitta `api_id` bilan barcha 10 ta akkauntni ulash mumkin.
- Tasdiqlash kodini hech kimga yubormang — Telegram boshqa chatga yuborilgan kodni bloklaydi.
- Saytdan spam yoki ommaviy xabar yubormang — Telegram akkauntni cheklashi mumkin.

## Docker'siz ishga tushirish (ixtiyoriy)

Python 3.11+ kerak:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Muhim: har doim **bitta worker** (`--workers 1`) bilan ishga tushiring — bot va Telegram akkauntlar
bitta jarayon ichida ishlaydi.

## Texnik ma'lumot

- Python, FastAPI, SQLAlchemy (SQLite; PostgreSQL kerak bo'lsa `asyncpg` o'rnatib `DATABASE_URL` bering), Jinja2 shablonlar.
- Telegram bot: aiogram 3. Telegram akkauntlar: Telethon.
- Kod tuzilishi: `app/routers/` — sahifalar, `app/bot/` — bot, `app/tg/` — Telegram akkauntlar,
  `app/templates/` — HTML, `app/static/` — CSS/JS.
