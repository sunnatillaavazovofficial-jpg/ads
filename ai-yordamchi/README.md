# AI Yordamchi

Ekranda hamma dasturlar ustida turadigan yordamchi (Windows, `.exe`). ChatGPT (OpenAI API) yordamida ishlaydi. Matn bilan ishlash, skrinshot olish va AI bilan real rasm yasash bitta dasturda jamlangan.

**Yuklab olish:** https://github.com/sunnatillaavazovofficial-jpg/ads/releases/latest/download/AI-Yordamchi.exe (GitHub akkaunti shart emas)

## Matn funksiyalari

| Ikonka | Vazifa | Tugma |
|---|---|---|
| 文A | **Tarjima**: o'zbekcha (yangi alifbo / lotin / kirill), English, Русский | `Ctrl+1` |
| A✓ | **Grammatika**: xatolarni topib, faqat to'g'rilangan matnni beradi | `Ctrl+2` |
| Öz | **Yangi alifbo**: avval xatolarni to'g'rilaydi, keyin yangi o'zbek lotin alifbosida yozadi (Oʻ→Ö, Gʻ→Ğ, Sh→Ş, Ch→Ç) | `Ctrl+3` |
| Ўз | **Kirill**: avval xatolarni to'g'rilaydi, keyin o'zbek kirill yozuvida yozadi | `Ctrl+4` |
| 🔍 | **Inglizcha nima deb izlash**: faqat inglizcha nomini beradi; Google tugmasi bilan darhol izlash mumkin | `Ctrl+5` |

Barcha javoblar **oddiy matn** bo'lib chiqadi: emoji va ortiqcha izohlarsiz.

### Joyida tahrirlash (istalgan dasturda)

Matnni belgilab, tugmani bosasiz va matn **o'sha joyning o'zida** almashadi, panel ochilmaydi:

| Tugma | Natija |
|---|---|
| `Ctrl+Alt+1` | tarjima (Sozlamalarda tanlangan tilga) |
| `Ctrl+Alt+2` | grammatik xatolar to'g'rilanadi |
| `Ctrl+Alt+3` | yangi alifboda (Ö Ğ Ş Ç) yoziladi |
| `Ctrl+Alt+4` | kirillda yoziladi |
| `Ctrl+Alt+5` | inglizcha nomi yozuv kursori yonida ko'rinadi va nusxalanadi (bossangiz, Google'da izlaydi) |

Ishlayotgan paytda yozuv kursori yonida kichik shaffof belgi turadi. Bufer (Ctrl+V) avvalgi holatiga qaytariladi.

## Skrinshot va AI rasm

- **PrintScreen** yoki **Win+Shift+S** bosilganda shu dastur ishlaydi (Windows vositasi o'rniga). Zaxira tugma: `Ctrl+Alt+S`.
- **Oddiy skrinshot:** joyni belgilaysiz. Tepada shaffof ikonkalar bor: ⛶ butun ekran (`Enter`), ✕ bekor qilish (`Esc`). Rasm darhol **nusxalanadi** (`Ctrl+V` bilan joylashtirasiz) va **tanlangan papkaga saqlanadi**. Keyin pastki burchakda yozuvsiz, shaffof oynacha chiqadi: rasm va ikonkalar.
  - **HD** sifatni oshiradi: rasm 2 barobar kattalashtiriladi va tiniqlashtiriladi (bepul, kompyuterda bajariladi), so'ng nusxalanib saqlanadi. Tayyor bo'lgach, rasmda ✓ chiqadi;
  - **✦** AI rasm tahrirlash oynasini ochadi; **👁** ochib ko'rsatadi; **✕** oynachani yopadi.
  - Yozuvlar faqat kursor ikonka ustiga borganda ko'rinadi.
- **Ctrl+V** oxirgi skrinshotni joylaydi.
- **Ctrl+V+S** yoki **Ctrl+Shift+V** **oxirgi 10 ta skrinshot**ni rasm joylanadigan joyning o'zida (yozuv kursori yonida) ko'rsatadi. Fon shaffof, ortiqcha yozuv va tugma yo'q. Bu faqat oxirgi skrinshotdan keyin **2 daqiqa** ishlaydi, keyin o'chadi.
  - rasmni bossangiz yoki uning raqamini (1–0) bossangiz, shu rasm joylanadi;
  - **← → ↑ ↓** bilan tanlaysiz, **bo'sh joy** yoki o'ng tugma bilan belgilaysiz;
  - **Enter** belgilanganlarni, hech narsa belgilanmagan bo'lsa **hammasini** ketma-ket joylaydi;
  - **Esc** oynani yopadi.
- Rasmlar tanlangan papka ichida **alohida papkalarda** saqlanadi: `Skrinshotlar`, `Yuqori sifat`, `AI rasmlar`.
- **AI rasm (✦ tugmasi):** skrinshot olingach, tahrirlash oynasi ochiladi:
  - qalam, marker, strelka, to'rtburchak, doira, **matn yozish**; 6 rang, 3 qalinlik; orqaga/oldinga;
  - chizilgan belgilar AI uchun **ko'rsatma** bo'ladi, natijada esa ko'rinmaydi;
  - nima qilishni o'zbekcha yozasiz yoki **12 ta tayyor shablondan** birini tanlaysiz (Real foto, Interyer, Eksteryer, Mahsulot, Chizmadan real, Portret, Reklama, Fon almashtirish, Sifatni oshirish, 3D render, Kechki ko'rinish, Ortiqchani o'chirish);
  - **Real rasm qilish** (`Ctrl+Enter`) natijani oynada ko'rsatadi va **tanlangan papkaga saqlaydi**.

## Boshqaruv

- Ochilganda menyu **bir marta ko'rinadi, keyin fonga o'tadi**: ekran chetiga kirib, shaffof chiziq bo'lib turadi. Kursor chiziqqa borishi bilan menyu chiqib keladi.
- Ekranda faqat ikonkalar turadi. **Yozuv faqat kursor ikonka ustiga borganda** chiqadi.
- **Taskbarda ko'rinmaydi.** Soat yonidagi trey ikonkasidan boshqariladi.
- **Kompyuter yonganda o'zi ishga tushadi** (Sozlamalarda o'chirsa bo'ladi).
- Tepada **⋮⋮ tutqich** (sudrash) va **✕** (chiqish), uning ostida 📌 qadash.
- **⚙ Sozlamalar:** API kalit va model; o'lcham; rang; yashirinish; avto-ishga tushish; funksiyalarni yoqish/o'chirish; PrintScreen/Win+Shift+S; skrinshotni avto-saqlash; "sifatni oshiraymi" so'rovi; AI rasm modeli; **rasmlar saqlanadigan papka (o'zingiz tanlaysiz)**; yozishmalar papkasi; **by Sunnatilla Designer** havolasi.

## O'zingiz yig'moqchi bo'lsangiz

Windows'da Python 3.10+ o'rnating ("Add python.exe to PATH" belgisini qo'ying), so'ng shu papkadagi `build.bat` ni ikki marta bosing. Natija: `dist\AI-Yordamchi.exe`.

---
by [Sunnatilla Designer](https://sunnatilla-designer.uz/)
