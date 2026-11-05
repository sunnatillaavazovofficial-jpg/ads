# BIG LIFE banner (CorelDRAW uchun)

Namuna dizayn asosida qayta chizilgan vektor banner: bej fon, jigarrang logo,
"ALWAYS FORWARD" yozuvi, dekor chiziqlar va pastki kontakt paneli.

## Fayllar
- `svg/` - har bir o'lcham uchun alohida SVG (real o'lchamda, mm birligida)
- `preview/` - PNG ko'rinishlar
- `generate.py` - matn/o'lchamni o'zgartirib qayta yaratish: `python3 generate.py`

| Fayl | O'lcham (sm) |
|---|---|
| big-life_750x240_kocha_1ta.svg | 750 x 240 |
| big-life_600x240_kocha_3ta.svg | 600 x 240 |
| big-life_400x200_kocha_2ta.svg | 400 x 200 |
| big-life_400x100_proxod_2ta.svg | 400 x 100 |
| big-life_450x120_proxod_4ta.svg | 450 x 120 |
| big-life_520x150_naves.svg | 520 x 150 |
| big-life_395x150_naves.svg | 395 x 150 |
| big-life_675x266.svg | 675 x 266 |
| big-life_675x200.svg | 675 x 200 |
| big-life_asosiy_16x9.svg | 160 x 90 |

## CorelDRAW'da ishlatish
1. **Файл → Импорт** (Ctrl+I) → SVG ni tanlang → Enter (asl o'lchamda joylashadi).
2. Guruhni ochish: **Ctrl+U** (Ungroup).
3. Model rasmlari: rasmni import qiling → **Объект → PowerClip → Поместить во фрейм**
   → `MODEL RASMI` to'rtburchagini tanlang. Keyin to'rtburchak chizig'ini olib tashlang
   (kontur: Нет) va "MODEL RASMI" yozuvlarini o'chiring.
   Rasm fon bilan qo'shilishi uchun kesilgan (PNG, fonsiz) model rasm ishlatish tavsiya.
4. Logo ("BIG LIFE" va belgisi) to'liq vektor (krivoy) - shrift kerak emas.
   Asl logo fayli bo'lsa, `LOGO` guruhini o'shanga almashtiring.
5. Kontakt matnlari va "ALWAYS FORWARD" - Arial shriftida, tahrirlanadigan matn.
   Pechatga berishdan oldin: matnni tanlab **Ctrl+Q** (krivoyga aylantirish).
6. Pechat uchun rang: **Окно → Цвет → CMYK** ga o'tkazing.
