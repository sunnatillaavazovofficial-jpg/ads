# MONOOS — yangi dizayn bosmaxona shablonida (artwork)

Bosmaxona (Swiss Parenterals) yuborgan artwork shablonlariga yangi MONOOS dizayni joylandi.
**Shablon o'zgarmagan:** faqat dizayn almashtirildi.

| Mahsulot | Tayyor fayl (4 sahifa, vektor PDF) |
|---|---|
| Cefoperazone + Sulbactam Bio | [`cefoperazone/ART-WORK_Cefoperazone_Sulbactam_Bio_yangi-dizayn.pdf`](cefoperazone/ART-WORK_Cefoperazone_Sulbactam_Bio_yangi-dizayn.pdf) |
| Ampicillin + Sulbactam Bio | [`ampicillin/ART-WORK_Ampicillin_Sulbactam_Bio_yangi-dizayn.pdf`](ampicillin/ART-WORK_Ampicillin_Sulbactam_Bio_yangi-dizayn.pdf) |

Har bir PDF asl shablon bilan bir xil tuzilgan (sahifa o'lchamlari ham aynan bir xil):

| Sahifa | Nima |
|---|---|
| 1 | Karobka razvyortkasi: **yangi dizayn** |
| 2 | Flakon etiketkasi (haqiqiy o'lcham + kattalashtirilgan): **yangi dizayn** |
| 3–4 | Yo'riqnoma (rus va o'zbek tilida): **asl shablondan o'zgarishsiz** |

## Nima o'zgardi, nima o'zgarmadi

**Yangi dizaynda chizildi:**
- Ingliz tilidagi old panel va rus tilidagi old panel;
- yuqori qopqoq;
- etiketkaning o'rta (dizayn) qismi.

Matnlar shablondagidek, faqat yangi uslubda: MONOOS logosi, to'lqinlar, rangli dori nomi, doza plashkasi.

**Shablondagidek qoldi (asl vektor obyektlar, tegilmagan):**
- kesish va bukish chiziqlari, karobka o'lchamlari;
- o'rtadagi yon panellar: tarkib, saqlash, ishlab chiqaruvchi, Mfg. Lic. No., shtrix-kod, S logotipi;
- pastki qopqoq va raqamli identifikatsiya joyi (GTIN / B NO / MFG / EXP / SRNO);
- barcha qizil zonalar: Internal Artwork code, Lic. no. Space, Non-UV/Varnish zone;
- etiketkaning chap (tarkib) va o'ng (Batch / Mfg / Exp, ishlab chiqaruvchi) qismlari;
- yo'riqnoma sahifalari.

Tekshiruv: o'zgarmagan qismlar asl PDF ustiga 600 dpi da qo'yib solishtirildi, siljish 0 mm.
Yo'riqnoma sahifalari asl bilan piksellarigacha bir xil.

## O'lchamlar (shablondan)

| | Cefoperazone | Ampicillin |
|---|---|---|
| Karobka | 35 × 35 × 65 mm | 35 × 35 × 60 mm |
| Flakon etiketkasi | 80 × 30 mm | 60 × 28 mm |

Old panellarning kesiladigan chetlarida va yuqori qopqoq yonlarida 3 mm vylet (bleed) bor.

## Papka ichida

- `ART-WORK_..._yangi-dizayn.pdf` — bosmaxonaga yuboriladigan yakuniy fayl;
- `1-karobka.svg`, `2-etiketka.svg` — CorelDRAW'da tahrirlash uchun (o'lchami pt'da, aniq).
  Qatlamlar: `YANGI-DIZAYN-FON`, `YANGI-DIZAYN-LOGO`, `YANGI-DIZAYN-MATN`, `SHABLON`;
- `1-karobka.png`, `2-etiketka.png` — 300 dpi, tez ko'rish uchun.

## E'tibor bering

1. **Logo.** Shablonda MONOOS'ning eski belgisi bor edi (to'q sariq va ko'k shakl).
   Yangi dizayndagi yoyli MONOOS logosi qo'yildi. Eski logo qolishi kerak bo'lsa, almashtirib beraman.
2. **Ranglar.** Cefoperazone shabloni 3 ta Pantone (355 C, 2011 C, 534 C) + qora bilan bosilardi.
   Yangi dizaynda gradientlar bor, shuning uchun u **CMYK** da bosiladi. Rang belgisi CMYK ga
   almashtirildi (Ampicillin shablonida avvaldan CMYK edi). Bosmaxona bilan tasdiqlang.
3. **Matnlar** shablondagidek. Ruscha savdo nomi shablon va yo'riqnomadagidek **"Цефаперазон"**
   ("а" bilan) yozilgan, xalqaro nomi esa "Цефоперазон". Ro'yxatdan o'tgan nom shu ekanini tekshiring.
4. Ampicillin etiketkasida shablonda "АМПИЦИЛЛИН ИСУЛЬБАКТАМ ДЛЯИНЪЕКЦИЙ" (probelsiz) yozilgan edi.
   Yangi etiketkada probellar bilan yozildi: "АМПИЦИЛЛИН И СУЛЬБАКТАМ ДЛЯ ИНЪЕКЦИЙ ПО 1,5 г".
5. Ampicillin yuqori qopqog'ida shablondagidek faqat dori nomi bor, unga logo qo'shildi.

## Qayta yaratish

Skriptlar: [`../monoos-karobka-skript/`](../monoos-karobka-skript/), fayl `template_box.py`.
Asl artwork PDF kerak bo'ladi:

```bash
ART_NAME=ART-WORK_Cefoperazone_Sulbactam_Bio_yangi-dizayn.pdf python3 template_box.py fonts ../monoos-shablon-artwork/cefoperazone cefoperazone Art-work_Cefoperazone_Sulbactam_Bio.pdf
```

```bash
ART_NAME=ART-WORK_Ampicillin_Sulbactam_Bio_yangi-dizayn.pdf python3 template_box.py fonts ../monoos-shablon-artwork/ampicillin ampicillin ART-WORK_AMPICILLIN_SULBACTAM_BIO.pdf
```
