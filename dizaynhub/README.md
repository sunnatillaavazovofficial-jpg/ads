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

## Qaysi kompyuterga o'rnatiladi?

**Faqat bitta kompyuterga — server bo'ladigan kompyuterga.** Hamma narsa (dastur,
baza, fayllar, Telegram sessiyalari) o'sha kompyuterda turadi.

- Shu kompyuter **doim yoniq va internetga ulangan** bo'lishi kerak.
  O'chsa, sayt va bot ham to'xtaydi.
- Menejer va dizaynerlar **hech narsa o'rnatmaydi** — o'z telefoni yoki kompyuterida
  brauzerni ochib, domen manzilini yozadi (masalan `https://ish.sizning-domen.uz`).
- Serverni boshqa kompyuterga ko'chirish: dasturni yangi kompyuterga o'rnating va eski
  kompyuterdagi **`data`** papkasini va **`.env`** faylini nusxalab qo'ying.

## Qaysi brauzerlardan kiriladi?

| Brauzer | Holati |
|---|---|
| Google Chrome (kompyuter, Android) | ✅ |
| Yandex Browser (kompyuter, Android, iPhone) | ✅ |
| Safari (Mac, iPhone, iPad) — 15 va yangi versiyalar | ✅ |
| Microsoft Edge, Firefox, Opera | ✅ |

Telefon ekraniga moslashgan (chap menyu ☰ tugmasi orqali ochiladi).
Telegramdagi ovozli xabarlar (.ogg) ayrim Safari versiyalarida o'ynamasligi mumkin —
ular uchun «⬇ Yuklab olish» havolasi bor.

**Domen ulanmasdan oldin** ofisdagi Wi-Fi orqali kirish mumkin: `.env` da `HOST=0.0.0.0`
qiling, server kompyuterida `ipconfig` buyrug'i bilan IP manzilni bilib oling
(masalan `192.168.1.15`) va boshqa qurilmalarda `http://192.168.1.15:8000` ni oching.
Windows «Brandmauer» (Firewall) so'rasa — **Ruxsat berish** ni bosing.
Bu holatda `COOKIE_SECURE=false` bo'lishi kerak, aks holda tizimga kirib bo'lmaydi.

## 1. O'rnatish (Windows)

1. **Python 3.11 yoki yangisini** o'rnating: <https://www.python.org/downloads/>
   — o'rnatishda **«Add python.exe to PATH»** ni albatta belgilang.
2. Dasturni server kompyuteriga yuklab oling: GitHub'da repozitoriyni oching →
   **Code → Download ZIP** → arxivni oching va ichidagi `dizaynhub` papkasini
   masalan `C:\DizaynHub` ga ko'chiring.
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
   va dasturni qayta ishga tushiring. Endi sayt `https://ish.sizning-domen.uz` da
   Chrome, Safari, Yandex va boshqa brauzerlarda, istalgan joydan ochiladi.
   (`COOKIE_SECURE=true` bo'lganda Wi-Fi orqali `http://192.168...` manzili ishlamaydi —
   hamma domen orqali kirsin.)

## 4b. Statik (oq) IP orqali ulash — Cloudflare'siz

Provayderdan statik IP olgan bo'lsangiz (quyida misol uchun `203.0.113.10` yozilgan —
o'rniga o'z IP'ingizni qo'ying), saytni shu IP orqali ochish mumkin.

> Telegram bot va ulangan akkauntlar uchun port ochish shart emas — ular o'zi Telegramga
> ulanadi. Port faqat saytni brauzerda ochish uchun kerak.

**Avval IP haqiqatan shu kompyuterniki ekanini tekshiring:**

1. Server kompyuterida brauzerda <https://2ip.ru> ni oching — u ko'rsatgan IP sizning
   IP'ingiz bilan bir xil bo'lishi kerak.
2. Router sozlamalarida (odatda `192.168.1.1` yoki `192.168.0.1`) **WAN / Internet IP**
   ham shu bo'lishi kerak. Agar routerda `10.x.x.x`, `100.64…100.127.x.x` yoki
   `192.168.x.x` ko'rsatilsa — provayder «kulrang» IP bergan, port ochib bo'lmaydi.
   Bunda 4-bo'limdagi Cloudflare Tunnel'dan foydalaning.
3. IP **statik** ekanini provayderdan aniqlang (dinamik IP vaqti-vaqti bilan o'zgaradi).

**Sozlash:**

1. `.env` faylida:
   ```
   HOST=0.0.0.0
   PUBLIC_URL=http://203.0.113.10:8000
   COOKIE_SECURE=false
   ```
2. Routerda server kompyuteriga doimiy lokal IP bering (DHCP reservation),
   masalan `192.168.1.15`.
3. Routerda **Port forwarding** (Virtual server): tashqi port `8000` → `192.168.1.15:8000`, TCP.
4. Windows brandmauerida portni oching — PowerShell'ni **administrator** sifatida ochib:
   ```
   New-NetFirewallRule -DisplayName "DizaynHub" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   ```
5. Dasturni qayta ishga tushiring.
6. **Tekshirish:** telefonda Wi-Fi'ni o'chiring (mobil internet bilan) va
   `http://203.0.113.10:8000` ni oching. Yoki <https://2ip.ru/check-port/> saytida
   8000-portni tekshiring — «открыт» chiqishi kerak.

⚠️ Bu usulda aloqa **shifrlanmagan** (http): parollar va Telegram yozishmalari internetda
ochiq ketadi. Sinab ko'rish uchun mayli, doimiy ishlatish uchun domen + HTTPS qiling:

1. Domenning **A yozuvini** IP'ingizga yo'naltiring: `ish.sizning-domen.uz → 203.0.113.10`.
2. Routerda **80 va 443** portlarni server kompyuteriga oching (8000-portni endi yopish mumkin).
3. <https://caddyserver.com/download> dan Windows uchun `caddy.exe` ni yuklab,
   `deploy` papkasiga qo'ying. `deploy\Caddyfile` dagi domenni o'zingiznikiga almashtiring
   va `deploy\caddy.bat` ni ishga tushiring — HTTPS sertifikat avtomatik olinadi.
   `caddy.bat` yorlig'ini ham `shell:startup` ga qo'ying (5-bo'lim).
4. `.env` faylida:
   ```
   HOST=127.0.0.1
   PUBLIC_URL=https://ish.sizning-domen.uz
   COOKIE_SECURE=true
   ```

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
