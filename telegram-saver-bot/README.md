# Telegram Saver Bot

Bu bot Telegram'dagi **bir martalik (view-once)** rasm, video va ovozli xabarlarni, shuningdek
**o'chirilgan** va **tahrirlangan** xabarlarni saqlab qoladi. Bot faqat bitta egaga
(`OWNER_ID`) xizmat qiladi. Boshqa odamlar undan foydalana olmaydi.

Bot shaxsiy chatlaringizni **Telegram Business → Chatbotlar** funksiyasi orqali ko'radi.

> ⚠️ **Talab:** akkauntingizda **Telegram Premium** bo'lishi kerak. Chatbot ulash faqat Business
> funksiyasida bor, Business esa Premium bilan keladi.

---

## Nima qiladi

| Holat | Natija |
|---|---|
| 🔥 Bir martalik rasm/video/ovoz/dumaloq video kelsa | Uni **ochmasdan turib** istalgan xabar bilan **reply** qiling (masalan `.`). Bot mediani sizga yuboradi va reply xabaringizni chatdan o'chiradi |
| 🗑 Suhbatdosh xabarni o'chirsa | O'chirilgan matn yoki media sizga keladi |
| ✏️ Suhbatdosh xabarni tahrirlasa | Eski va yangi matn sizga keladi |
| Oddiy rasm yoki videoga reply qilsangiz | Uni ham saqlab beradi |

Xabarlar serverdagi SQLite bazasida `KEEP_DAYS` kun (standart 30 kun) saqlanadi, keyin o'zi tozalanadi.

---

## 1. Botni BotFather'da sozlash (bir marta)

1. [@BotFather](https://t.me/BotFather) → `/mybots` → botingizni tanlang
2. **Bot Settings → Business Mode → Turn on** ✅ (shuni yoqmasangiz bot ishlamaydi)

## 2. Serverga o'rnatish

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

---

## Sozlamalar (`.env`)

| O'zgaruvchi | Standart | Tavsif |
|---|---|---|
| `BOT_TOKEN` | — | BotFather bergan token (majburiy) |
| `OWNER_ID` | — | Sizning Telegram ID raqamingiz (majburiy) |
| `KEEP_DAYS` | `30` | Xabarlar bazada necha kun saqlanadi |
| `TZ_OFFSET` | `5` | Vaqt zonasi, UTC+N (Toshkent = 5) |
| `DELETE_TRIGGER_REPLY` | `1` | Reply xabaringizni avtomatik o'chirish (`1`/`0`) |
| `DB_PATH` | `data/messages.db` | Baza fayli joyi |

## Cheklovlar

- Bot faqat **ulangandan keyin** kelgan xabarlarni ko'radi. Undan oldin o'chirilgan xabarlarni tiklay olmaydi.
- Bir martalik mediani **ochishdan oldin** reply qilish kerak. Ochilgandan keyin Telegram uni o'chirib yuboradi.
- Telegram Bot API orqali 20 MB dan katta faylni yuklab bo'lmaydi.
- Faqat shaxsiy chatlar ishlaydi. Guruh va kanallar Business orqali ulanmaydi.

## Xavfsizlik

- `.env` faylini hech qachon GitHub'ga yuklamang. U `.gitignore`ga qo'shilgan.
- Token kimgadir ko'rinib qolgan bo'lsa: @BotFather → `/mybots` → bot → **API Token → Revoke**,
  yangi tokenni `.env`ga yozing va botni qayta ishga tushiring.
