# DizaynHub — dizayn ishlarini saqlash va boshqarish sayti

Ichki tizim: menejerlar ish joylaydi (sayt yoki Telegram bot orqali), bosh dizayner
qabul qiladi, dizaynerlar bajaradi. Hisob bo'limi tannarx va narxni hisoblaydi.
Telegram akkauntlaringizni ulab, kerakli chatlarni saytda kuzatib borasiz.

Server — sizning kompyuteringiz. Saytga domen orqali kiriladi.

> Asl talablarning tartiblangan ko'rinishi (Claude uchun prompt): [docs/TZ.md](docs/TZ.md)

---

## Imkoniyatlar

| Bo'lim | Nima qiladi |
|---|---|
| **Ro'yxatdan o'tish** | Kalit + ism + familiya + parol. Kalitga qarab rol beriladi (menejer / dizayner / bosh dizayner / admin). Login — «Ism Familiya». |
| **Yangi ish (shablon)** | 9 ta majburiy maydon: nomi, turi, qisqa ta'rif, o'lchami, rasm, qo'shimcha ma'lumot, logo, maxsus matn, fayllar. Ma'lumot yo'q bo'lsa — «Yo'q» belgisi qo'yilishi shart, aks holda forma saqlanmaydi. |
| **Telegram bot** | Menejer botda «➕ Yangi ish» ni bosadi — bot o'sha 9 ta savolni ketma-ket beradi (rasm/fayllarni to'g'ridan-to'g'ri yuborish mumkin). Bildirishnomalar: yangi ish → bosh dizaynerga («✅ Qabul qilish» tugmasi bilan), qabul qilindi / tayyor → menejerga. |
| **Ish jarayoni** | Yangi → Qabul qilindi (bosh dizayner, dizaynerni biriktiradi) → Jarayonda → Tayyor (tayyor fayl yuklanadi) → Topshirildi. Hammasi hammaga ko'rinadi, har bir ishda tarix va izohlar bor. |
| **Hisob** | Materiallar katalogi (tannarx va sotish narxi). Har bir ishga sarflangan material yoziladi → **tannarx (sebestoimost)**, **umumiy narx**, **foyda**. Hisobot: davr bo'yicha, material sarfi, menejerlar kesimida. Dizaynerlar narxlarni ko'rmaydi. |
| **Telegram chatlar** | 6–7 (yoki ko'proq) akkaunt ulanadi. Har bir akkauntdan faqat kerakli chatlar tanlanadi. Saytda xabarlar, rasmlar, fayllar ko'rinadi, yangi xabarlar avtomatik chiqadi, javob yozish mumkin. Saytda o'qish Telegramda «o'qildi» qilmaydi. Akkauntni menejerga biriktirsangiz, u ham shu chatlarni ko'radi. Ishga mijoz chatini bog'lash mumkin. |
| **Admin** | Foydalanuvchilar (rol, bloklash, parol tiklash), kalitlar, ish turlari. |

---

## 1. O'rnatish (Windows)

1. **Python 3.11 yoki yangisini** o'rnating: <https://www.python.org/downloads/>
   — o'rnatishda **«Add python.exe to PATH»** ni albatta belgilang.
2. Ushbu `dizaynhub` papkasini kompyuterga ko'chiring (masalan `C:\DizaynHub`).
3. `start.bat` ni ikki marta bosing. Birinchi marta kutubxonalar o'rnatiladi (1–2 daqiqa),
   `.env` fayli yaratiladi va sayt ishga tushadi.
4. Brauzerda oching: <http://127.0.0.1:8000>
5. Ro'yxatdan o'tish kalitlari `data\KALITLAR.txt` faylida. **Admin kaliti** bilan o'zingiz
   ro'yxatdan o'ting, keyin menejer va dizaynerlarga ularning kalitini bering.
   Kalitlarni keyinchalik **Sozlamalar** bo'limida o'zgartirasiz.

Linux/macOS: `./start.sh`

## 2. Telegram akkauntlarni ulash uchun API kalit

1. <https://my.telegram.org> ga telefon raqamingiz bilan kiring → **API development tools**.
2. Istalgan nom bilan ilova yarating (App title: `DizaynHub`, Platform: `Desktop`).
3. Chiqqan **api_id** va **api_hash** ni `.env` fayliga yozing (Bloknot bilan oching):
   ```
   TG_API_ID=1234567
   TG_API_HASH=0123456789abcdef0123456789abcdef
   ```
4. Dasturni qayta ishga tushiring (oynani yopib, `start.bat` ni qayta bosing).
5. Saytda **Akkauntlar** → telefon raqam → Telegramga kelgan kod → (2FA bo'lsa parol).
   Shu tarzda 6–7 ta akkauntni ulang.
6. Har bir akkaunt yonidagi **«☑️ Chatlarni tanlash»** → kerakli odamlarni belgilang → Saqlash.
   Tanlangan chatlar **Telegram chatlar** bo'limida ko'rinadi.

> Bitta api_id/api_hash barcha akkauntlar uchun yetarli.

## 3. Telegram bot

1. Telegramda [@BotFather](https://t.me/BotFather) → `/newbot` → nom va username bering.
2. Berilgan tokenni `.env` ga yozing: `BOT_TOKEN=123456:ABC-...`
3. Dasturni qayta ishga tushiring.
4. Har bir xodim saytda **Profil → «Botni ochish va bog'lash»** tugmasini bosadi —
   bot uni taniydi. Menejerlar botda «➕ Yangi ish» orqali ish joylaydi,
   qolganlar bildirishnoma oladi.

## 4. Domenni ulash (Cloudflare Tunnel — bepul, port ochish shart emas)

Uyda statik IP bo'lmasa ham ishlaydi va avtomatik HTTPS beradi.

1. Domeningizni [Cloudflare](https://dash.cloudflare.com) ga qo'shing (domen sotib olingan
   joyda NS serverlarni Cloudflare ko'rsatganlariga almashtirasiz).
2. Cloudflare panelida **Zero Trust → Networks → Tunnels → Create a tunnel** →
   turi **Cloudflared** → nom: `dizaynhub`.
3. **Windows** ni tanlang — ko'rsatilgan buyruqni (`cloudflared.exe service install <TOKEN>`)
   administrator sifatida ochilgan buyruq satrida bajaring. Tunnel Windows xizmati bo'lib
   har doim ishlaydi.
4. **Public hostname** qo'shing: `ish.sizning-domen.uz` → Service: `HTTP` → URL: `localhost:8000`.
5. `.env` faylida:
   ```
   PUBLIC_URL=https://ish.sizning-domen.uz
   COOKIE_SECURE=true
   ```
   va dasturni qayta ishga tushiring. Endi sayt `https://ish.sizning-domen.uz` da ochiladi.

> Muqobil yo'l: routerda 8000-portni ochish + statik IP + Caddy/Nginx (HTTPS uchun).
> Bunda `.env` da `HOST=0.0.0.0` qiling.

## 5. Kompyuter yonganda avtomatik ishga tushirish

- `Win + R` → `shell:startup` → ochilgan papkaga `start.bat` ning **yorlig'ini (shortcut)** qo'ying.
- Windows sozlamalarida kompyuter **uyqu rejimiga o'tmasligini** belgilang
  (Sozlamalar → Tizim → Quvvat → Uyqu: «Hech qachon»).

## 6. Zaxira nusxa (backup)

Barcha ma'lumot **`data`** papkasida: baza, yuklangan fayllar, Telegram sessiyalari.
Vaqti-vaqti bilan shu papkani tashqi diskka yoki bulutga nusxalang.

## Xavfsizlik

- `data\tg_sessions` — ulangan Telegram akkauntlarga to'liq kirish kaliti. Bu papkani
  hech kimga bermang. Akkauntni Telegram → Sozlamalar → Qurilmalar bo'limidan («DizaynHub»)
  istalgan vaqtda uzish mumkin.
- Admin kalitini faqat o'zingiz biling. Xodim ketganda — **Foydalanuvchilar** bo'limida bloklang.
- Parollar shifrlangan (scrypt) holda saqlanadi, fayllar faqat tizimga kirganlarga beriladi.

## Texnik ma'lumot

- Python · FastAPI · SQLite · Telethon (Telegram akkauntlar va bot) · Jinja2.
- Tuzilma: `app/routes` — sahifalar, `app/services` — umumiy mantiq (ish yaratish, holatlar,
  bildirishnomalar), `app/tg` — Telegram (akkauntlar va bot), `app/templates` — HTML.
- `.env` sozlamalari ro'yxati: [.env.example](.env.example).
