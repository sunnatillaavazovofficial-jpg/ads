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

**1-usul: GitHub Actions.** `ai-yordamchi/` papkasi o'zgarib push qilinganda **Actions → Build AI Yordamchi (Windows exe)** avtomatik ishlaydi. Tugagach, sahifa pastidagi **Artifacts** bo'limidan `AI-Yordamchi-exe` ni yuklab oling.

**2-usul: o'z kompyuteringizda.** Windows'da Python 3.10+ o'rnating, so'ng shu papkada `build.bat` ni ishga tushiring. Natija: `dist\AI-Yordamchi.exe`.

## Birinchi ishga tushirish

⚙ **Sozlamalar** tugmasini bosib OpenAI API kalitini kiriting (https://platform.openai.com/api-keys). Model standart holatda `gpt-4o-mini` (arzon va tez); xohlasangiz boshqasini tanlang.
