# AI Yordamchi

Ekran chetiga yopishib turadigan kichik yordamchi (Windows, `.exe`). ChatGPT (OpenAI API) yordamida ishlaydi.

## Nimalar qiladi

| Ikonka | Vazifa | Tugma |
|---|---|---|
| 文A | **Tarjima**: O'zbekcha (lotin), Türkçe, English, Русский | `Ctrl+1` |
| A✓ | **Grammatika**: xatolarni topadi, matnni ma'noli qilib to'g'rilaydi va xatolarni tushuntiradi | `Ctrl+2` |
| UZ | **O'zbekcha yangi lotin**: kirill yoki boshqa tildagi matnni yangi lotinda yozadi | `Ctrl+3` |
| TR | **Türkçe**: turk tilida to'g'ri yozib beradi | `Ctrl+4` |
| 🔍 | **Inglizcha nima deb izlash**: narsa yoki xususiyatini tasvirlasangiz, inglizcha nomini va qidiruv so'zlarini beradi (Google tugmasi bilan) | `Ctrl+5` |

- Faqat ikonkalar ko'rinadi, **yozuv faqat kursor ikonka ustiga borganda** chiqadi.
- 📌 **Qadash**: oyna hamma dasturlar ustida turadi (o'chirib qo'yish mumkin).
- Tepadagi **⋮⋮ tutqich** bilan sudrab, ekranning **chap** yoki **o'ng** tomoniga qo'ying: chapga qo'ysangiz ikonkalar chapda, o'ngga qo'ysangiz o'ngda turadi.
- Barcha yozishmalar **Hujjatlar\AI Yordamchi\YYYY-MM-DD.md** fayllarida saqlanadi (📁 tugmasi papkani ochadi).
- `Ctrl+Enter` yuborish, `Esc` panelni yopish. Trey (soat yonidagi) ikonkasidan ham boshqarsa bo'ladi.

## .exe ni olish

**1-usul (eng oson):** to'g'ridan-to'g'ri yuklab oling — https://github.com/sunnatillaavazovofficial-jpg/ads/releases/latest/download/AI-Yordamchi.exe (GitHub akkaunti shart emas). Har bir yangi build avtomatik **Releases** bo'limiga joylanadi.

**2-usul: o'z kompyuteringizda.** Windows'da Python 3.10+ o'rnating, so'ng shu papkada `build.bat` ni ikki marta bosib ishga tushiring (Python o'rnatishda "Add python.exe to PATH" belgisini qo'ying). Natija: `dist\AI-Yordamchi.exe`.

## Birinchi ishga tushirish

⚙ **Sozlamalar** tugmasini bosib OpenAI API kalitini kiriting (https://platform.openai.com/api-keys). Model standart holatda `gpt-4o-mini` (arzon va tez); xohlasangiz boshqasini tanlang.
