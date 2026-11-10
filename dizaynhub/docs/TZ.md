# Texnik topshiriq (Claude uchun prompt)

> Quyidagi matnni to'g'ridan-to'g'ri Claude'ga berish mumkin. U asl talablarning
> tartiblangan, aniqlashtirilgan ko'rinishi.

---

## Vazifa

Menga **dizayn ishlarini saqlab boradigan va boshqaradigan veb-sayt** kerak
(ichki tizim). Sayt bir nechta **menejer** va **dizayner** tomonidan ishlatiladi.
Interfeys tili — o'zbek (lotin).

## Ishga tushirish muhiti

- Server — **mening shaxsiy kompyuterim** (Windows). Alohida hosting yo'q.
- Saytga **domen orqali** kiriladi (masalan, `ish.mening-domenim.uz`), HTTPS bilan.
  Uyda statik IP / port ochish shart bo'lmasligi kerak (masalan, Cloudflare Tunnel).
- O'rnatish va ishga tushirish oddiy bo'lsin: bitta buyruq / `start.bat`.
- Barcha ma'lumotlar (baza, fayllar) bitta papkada saqlansin — zaxira nusxa olish oson bo'lsin.

## Foydalanuvchilar va ro'yxatdan o'tish

- Rollar: **Admin** (men), **Menejer**, **Bosh dizayner**, **Dizayner**.
- Har bir rol uchun **alohida maxfiy kalit** bo'ladi (menejer kaliti, dizayner kaliti va h.k.).
  Kalitlarni admin o'zgartira oladi.
- Ro'yxatdan o'tish formasi: **kalit**, **ism**, **familiya**, **parol**.
  Kalitga qarab foydalanuvchining roli avtomatik aniqlanadi.
- **"Ism Familiya" login sifatida ishlatiladi** (takrorlanmas bo'lishi kerak).
- Admin foydalanuvchilarni bloklashi, rolini o'zgartirishi, parolini tiklashi mumkin.

## Menejer: yangi ish joylash

Menejer yangi ishni **ikki yo'l** bilan joylaydi:
1. Saytda — tayyor **shablon (forma)** orqali;
2. **Telegram bot** orqali — bot savollarni ketma-ket beradi (faqat menejerlar uchun).

Ish maydonlari (tartib aynan shunday):

| # | Maydon | Izoh |
|---|--------|------|
| 1 | Ish nomi | majburiy |
| 2 | Ish turi | ro'yxatdan tanlanadi (banner, logo, vizitka, ...) |
| 3 | Qisqa ta'rif | |
| 4 | Ish o'lchami | eni × bo'yi, o'lchov birligi, soni |
| 5 | Ish rasmi | bir yoki bir nechta rasm |
| 6 | Qo'shimcha ma'lumotlar | |
| 7 | Logo | fayl |
| 8 | Maxsus matn | ishga yoziladigan matn |
| 9 | Fayllar | istalgan formatdagi fayllar (PSD, AI, CDR, PDF, ...) |

**Muhim qoida:** barcha maydonlar **majburiy**. Agar biror narsa yo'q bo'lsa,
menejer **"Yo'q" belgisini qo'yishi shart** — bo'sh qoldirib bo'lmaydi.

## Hisob bo'limi

- **Materiallar katalogi**: material nomi, o'lchov birligi (m², dona, m, ...),
  tannarx (1 birlik) va sotish narxi (1 birlik).
- Har bir ishga **qancha material sarflangani** yoziladi (material × miqdor);
  qo'shimcha xizmatlar (dizayn, montaj, ...) ham qator sifatida qo'shiladi.
- Shundan avtomatik chiqadi: **ishning tannarxi (sebestoimost)**,
  **ishning umumiy narxi** va **foyda**.
- Umumiy hisobot: davr bo'yicha jami tannarx/narx/foyda, qaysi materialdan qancha
  sarflangani, menejerlar kesimida.
- Narxlarni dizaynerlar ko'rmaydi.

## Dizaynerlar ish jarayoni

1. Menejer ish joylaydi → ish **"Yangi"** holatida **bosh dizaynerga** tushadi.
2. **Bosh dizayner ishni qabul qiladi** va dizaynerga (yoki o'ziga) biriktiradi.
3. Dizayner ishni bajaradi, tayyor fayllarni yuklaydi → **"Tayyor"**.
4. Menejer mijozga topshiradi → **"Topshirildi"**.
- Ishlar va ularning holati (kim qabul qildi, kim bajaryapti) **hammaga ko'rinadi**.
- Har bir ishda izohlar va tarix (kim, qachon, nima qildi) bo'ladi.
- Bot orqali bildirishnomalar: yangi ish — bosh dizaynerga (botning o'zida
  "Qabul qilish" tugmasi bilan), qabul qilindi / tayyor — menejerga.

## Telegram chatlarni ulash (ENG MUHIM)

- Saytga **6-7 ta Telegram akkaunt** ulanadi (telefon raqam + kod + 2FA parol orqali).
- Har bir akkauntdagi chatlar ro'yxatidan **faqat keraklilarini tanlab olaman**.
- Tanlangan chatlar saytda ko'rinib turadi: yangi xabarlar, rasmlar, fayllar —
  **kerakli odamning chatini kuzatib boraman**. Kerak bo'lsa javob yozish mumkin.
- Chatni o'qish akkauntda xabarni "o'qilgan" qilmasin.
- Telegram bo'limini admin ko'radi; akkauntni ma'lum menejerga biriktirsam,
  o'sha menejer ham shu akkauntning tanlangan chatlarini ko'radi.
- Ishga mijozning chatini bog'lab qo'yish imkoniyati bo'lsin.

## Texnik talablar

- Python, FastAPI, SQLite (alohida baza serveri shart emas), Telethon (Telegram).
- Fayllar faqat tizimga kirgan foydalanuvchilarga beriladi (ochiq havola yo'q).
- Parollar shifrlangan (hash) holda saqlanadi.
- Telefondan ham qulay ishlashi kerak (mobil moslashuv).
- O'zbek tilida o'rnatish yo'riqnomasi: Python o'rnatish, `.env` sozlash,
  Telegram API ID/HASH olish, BotFather'dan bot ochish, domenni ulash.
