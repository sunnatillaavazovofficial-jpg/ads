# Telegram Saver Bot

Bu bot Telegram'dagi **maxfiy (bir martalik)** rasm, video va ovozli xabarlarni,
**o'chirilgan** va **tahrirlangan** xabarlarni saqlaydi. Chat **tozalab yuborilsa**, butun yozishmani
siz ulagan guruhga tashlaydi. Botdan faqat ruxsat berilgan odamlar foydalanadi. Ruxsatni admin
(`OWNER_ID`) **bot ichida** beradi va oladi. Har bir foydalanuvchi faqat **o'zining** xabarlarini oladi.

Bot shaxsiy chatlaringizni **Telegram Business → Chatbotlar** funksiyasi orqali ko'radi.

> ⚠️ **Talab:** botni ulaydigan har bir akkauntda **Telegram Premium** bo'lishi kerak. Chatbot ulash faqat Business
> funksiyasida bor, Business esa Premium bilan keladi.

---

## Nima qiladi

| Holat | Natija |
|---|---|
| 🔥 Maxfiy (bir martalik) rasm/video/ovoz/dumaloq video kelsa | Uni **ochmasdan turib** istalgan xabar bilan **reply** qiling (masalan `.`). Bot mediani sizga yuboradi va reply xabaringizni chatdan o'chiradi |
| Oddiy rasm yoki videoga reply qilsangiz | Hech narsa qilmaydi |
| 🗑 Suhbatdosh xabarni o'chirsa | O'chirilgan matn yoki media sizga keladi |
| ✏️ Suhbatdosh xabarni tahrirlasa | Eski va yangi matn sizga keladi |
| 🧹 Chat tozalab yuborilsa | Butun yozishma guruhga keladi: sarlavha, to'liq yozishma (HTML fayl, brauzerda ochiladi) va barcha rasm/video/fayllar raqamlari bilan. Guruh ulanmagan bo'lsa, botning o'ziga keladi |

Maxfiy mediani bot shunday ajratadi: Telegram maxfiy mediani botga oddiy xabar sifatida yubormaydi,
uni faqat reply ichida ko'rsatadi. Shuning uchun bot oldin ko'rmagan media maxfiy hisoblanadi.

Xabarlar serverdagi SQLite bazasida `KEEP_DAYS` kun (standart 30 kun) saqlanadi, keyin o'zi tozalanadi.

---

## 1. Botni BotFather'da sozlash (bir marta)

1. [@BotFather](https://t.me/BotFather) → `/mybots` → botingizni tanlang
2. **Bot Settings → Secretary Mode → Turn on** ✅ (oldin «Business Mode» deb atalgan; shuni yoqmasangiz bot ishlamaydi)

## 2. Serverga o'rnatish

### Eng oson yo'l: bitta buyruq (Ubuntu/Debian)

Serverga `root` sifatida kiring va shuni yozing:

```bash
apt update && apt install -y curl && bash <(curl -fsSL https://raw.githubusercontent.com/sunnatillaavazovofficial-jpg/ads/refs/heads/claude/inspiring-shannon-renzbu/telegram-saver-bot/setup.sh)
```

Skript tokenni, sizning ID'ingizni va (ixtiyoriy) qo'shimcha foydalanuvchilar ID'larini so'raydi.
Shu buyruqni qayta ishga tushirsangiz, bot yangilanadi va sozlamalar saqlanib qoladi.

### Qo'lda o'rnatish

Serverga shu papkani ko'chiring (masalan `git clone` bilan), keyin `.env` faylini yarating:

```bash
cd telegram-saver-bot
cp .env.example .env
nano .env
```

`.env` ichida ikki qatorni to'ldiring:

```
BOT_TOKEN=bot_tokeningiz
OWNER_ID=sizning_telegram_id
```

Keyin quyidagi ikki usuldan **bittasini** tanlang.

### A usul: Docker (tavsiya etiladi)

```bash
docker compose up -d --build
```

Loglarni ko'rish:

```bash
docker compose logs -f
```

### B usul: systemd (Ubuntu/Debian, Dockersiz)

```bash
sudo bash install.sh
```

Holat va loglar:

```bash
systemctl status saver-bot
```

```bash
journalctl -u saver-bot -f
```

Ikkala usulda ham server qayta yonganda yoki bot yiqilib qolganda u o'zi qayta ishga tushadi.

## 3. Botni akkauntingizga ulash

1. Botga `/start` yozing
2. Telegram → **Sozlamalar → Telegram Business → Chatbotlar**
3. Botingizning `@username`ini kiriting
4. **Barcha shaxsiy chatlar** (yoki kerakli chatlar) ga ruxsat bering
5. Ruxsatlar ro'yxatida:
   - **Xabarlarni o'qish**: yoqing
   - **Barcha xabarlarni o'chirish**: ixtiyoriy. Yoqsangiz, saqlash uchun yozgan reply xabaringiz chatdan avtomatik o'chadi

Ulangandan keyin bot sizga **"✅ Bot akkauntingizga ulandi!"** deb yozadi.

## 4. Guruhni ulash (tozalangan chatlar uchun)

1. Telegram'da yangi guruh yarating (masalan «Arxiv»)
2. Guruhga botni qo'shing. Bot o'zi ulanadi va guruhga «✅ Guruh ulandi» deb yozadi
   (yoki guruhda `/setgroup` yozing)
3. Uzish: guruhda `/unsetgroup` yozing yoki botni guruhdan chiqaring

Har bir foydalanuvchi o'z guruhini ulaydi. Bir nechta odam bitta guruhni ham ulashi mumkin.
Begona odam botni guruhga qo'shsa, bot o'zi chiqib ketadi.

## 5. Odamlarga ruxsat berish (faqat bot orqali, admin)

Admin botda quyidagi tugmalarni ko'radi:

- **➕ Odam qo'shish**: Telegram kontaktlaringizdan odam tanlaysiz, unga darhol ruxsat beriladi
- **ID raqamni yozib yuborish**: bot «Ruxsat berilsinmi?» deb so'raydi, **✅ Ha** bosasiz
- **👥 Foydalanuvchilar**: ro'yxat (kim ulangan, kimda guruh bor) va **❌** tugmasi bilan ruxsatni olish
- Ruxsatsiz odam botga `/start` yozsa, adminga **✅ Ruxsat berish / ❌ Rad etish** tugmalari bilan so'rov keladi
- Buyruqlar: `/users`, `/add ID`, `/remove ID`

Ruxsat berilgan odam botga `/start` yozadi va 3-bo'limdagidek botni o'z akkauntiga ulaydi.

---

## Sozlamalar (`.env`)

| O'zgaruvchi | Standart | Tavsif |
|---|---|---|
| `BOT_TOKEN` | — | BotFather bergan token (majburiy) |
| `OWNER_ID` | — | Sizning Telegram ID raqamingiz, admin (majburiy) |
| `ALLOWED_IDS` | — | Birinchi ishga tushishda qo'shiladigan odamlar (keyin ruxsatlar bot orqali boshqariladi) |
| `CLEAR_MIN` | `5` | Bir vaqtda shuncha xabar o'chirilsa, «chat tozalandi» deb hisoblanadi |
| `KEEP_DAYS` | `30` | Xabarlar bazada necha kun saqlanadi |
| `TZ_OFFSET` | `5` | Vaqt zonasi, UTC+N (Toshkent = 5) |
| `DELETE_TRIGGER_REPLY` | `1` | Reply xabaringizni avtomatik o'chirish (`1`/`0`) |
| `DB_PATH` | `data/messages.db` | Baza fayli joyi |

## Cheklovlar

- Bot faqat **ulangandan keyin** kelgan xabarlarni ko'radi. Undan oldin o'chirilgan xabarlarni tiklay olmaydi.
- Bir martalik mediani **ochishdan oldin** reply qilish kerak. Ochilgandan keyin Telegram uni o'chirib yuboradi.
- Bot ulanishidan oldin (yoki `KEEP_DAYS` dan oldin) kelgan oddiy media maxfiy deb hisoblanishi mumkin.
- Tozalangan chatdan faqat bot ulangandan keyingi xabarlar tiklanadi.
- Telegram Bot API orqali 20 MB dan katta faylni yuklab bo'lmaydi.
- Faqat shaxsiy chatlar ishlaydi. Guruh va kanallar Business orqali ulanmaydi.

## Xavfsizlik

- `.env` faylini hech qachon GitHub'ga yuklamang. U `.gitignore`ga qo'shilgan.
- Token kimgadir ko'rinib qolgan bo'lsa: @BotFather → `/mybots` → bot → **API Token → Revoke**,
  yangi tokenni `.env`ga yozing va botni qayta ishga tushiring.
