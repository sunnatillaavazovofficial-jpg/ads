# AI Yordamchi

Ekranda hamma dasturlar ustida turadigan kichik yordamchi (Windows, `.exe`). ChatGPT (OpenAI API) yordamida ishlaydi.

**Yuklab olish:** https://github.com/sunnatillaavazovofficial-jpg/ads/releases/latest/download/AI-Yordamchi.exe (GitHub akkaunti shart emas)

## Funksiyalar

| Ikonka | Vazifa | Tugma |
|---|---|---|
| 文A | **Tarjima**: o'zbekcha (yangi alifbo / lotin / kirill), English, Русский | `Ctrl+1` |
| A✓ | **Grammatika**: xatolarni topadi, matnni ma'noli qilib to'g'rilaydi va xatolarni tushuntiradi | `Ctrl+2` |
| Öz | **Yangi alifbo**: avval xatolarni to'g'rilaydi, keyin yangi o'zbek lotin alifbosida yozadi (Oʻ→Ö, Gʻ→Ğ, Sh→Ş, Ch→Ç) | `Ctrl+3` |
| Ўз | **Kirill**: avval xatolarni to'g'rilaydi, keyin o'zbek kirill yozuvida yozadi | `Ctrl+4` |
| 🔍 | **Inglizcha nima deb izlash**: narsa yoki xususiyatini tasvirlasangiz, inglizcha nomini va qidiruv so'zlarini beradi (Google tugmasi bilan) | `Ctrl+5` |

Qaysi funksiyalar panelda ko'rinishini **⚙ Sozlamalar** ichida belgilaysiz.

## Boshqaruv

- Ekranda faqat ikonkalar turadi. **Yozuv faqat kursor ikonka ustiga borganda** chiqadi.
- Eng tepada **⋮⋮ tutqich** joylashgan: sudrab, oynani ekranning istalgan joyiga qo'yasiz va u **o'sha joyda qotib turadi**. Yonidagi **✕** dasturni yopadi.
- 📌 **Qadash** tugmasi tepada turadi: oynani hamma dasturlar ustida ushlab turadi.
- **⚙ Sozlamalar** ichida:
  - API kalit va model;
  - **o'lcham**: Kichik / O'rta / Katta / Juda katta;
  - funksiyalarni yoqish/o'chirish;
  - **yozishmalar papkasi** (Hujjatlar\AI Yordamchi): har kun uchun alohida `.md` fayl;
  - **by Sunnatilla Designer** yozuvi: bosilsa https://sunnatilla-designer.uz/ sayti ochiladi.
- `Ctrl+Enter` yuboradi, `Esc` panelni yopadi.

## O'zingiz yig'moqchi bo'lsangiz

Windows'da Python 3.10+ o'rnating ("Add python.exe to PATH" belgisini qo'ying), so'ng shu papkadagi `build.bat` ni ikki marta bosing. Natija: `dist\AI-Yordamchi.exe`.

---
by [Sunnatilla Designer](https://sunnatilla-designer.uz/)
