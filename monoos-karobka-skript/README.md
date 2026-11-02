# MONOOS karobka generatori

MONOOS dori karobkalarini (razvyortka, panellar, logo, fon, matn, flakon etiketkasi)
vektor qilib yaratadigan skriptlar. Hamma karobkalar bitta shablondan chiqadi, farqi
faqat matn va ranglarda.

| Mahsulot | Papka |
|---|---|
| `cefoperazone` | [`../monoos-cefoperazone-sulbactam-karobka/`](../monoos-cefoperazone-sulbactam-karobka/) |
| `ampicillin` | [`../monoos-ampicillin-sulbactam-karobka/`](../monoos-ampicillin-sulbactam-karobka/) |

## Fayllar

| Fayl | Vazifasi |
|---|---|
| `build_box.py` | Barcha SVG fayllarni yaratadi. Boshida karobka o'lchamlari (`W, D, H`) va `PRODUCTS` jadvali bor |
| `make_pdf.py` | SVG → vektor PDF (aniq mm o'lchamda) |
| `render.js` | SVG → PNG (Node.js + Playwright) |
| `mockup.js` | 3D maket rasmi (Node.js + Playwright) |

## Yangi mahsulot qo'shish

`build_box.py` ichidagi `PRODUCTS` ga yangi yozuv qo'shing: dori nomi (`title1`, `title2`),
xalqaro nomi (`sub`), doza (`dose`), yon panel matnlari (`side`), asosiy ranglar (`c_...`,
`logo_arc1/2`, `pill`) va fon ranglarini almashtirish jadvali (`remap`, ko'k-yashil
Cefoperazone ranglaridan yangi ranglarga).

## Ishga tushirish

Shriftlarni (`RobotoCondensed[wght].ttf`, `Roboto[wdth,wght].ttf`, `Montserrat[wght].ttf`)
github.com/google/fonts dan yuklab, `fonts/` papkasiga qo'ying.

```bash
pip install fonttools uharfbuzz cairosvg
```

```bash
python3 build_box.py fonts ../monoos-ampicillin-sulbactam-karobka ampicillin
```

```bash
python3 make_pdf.py ../monoos-ampicillin-sulbactam-karobka
```

```bash
node render.js ../monoos-ampicillin-sulbactam-karobka --png --dpi=300
```

```bash
node mockup.js ../monoos-ampicillin-sulbactam-karobka ../monoos-ampicillin-sulbactam-karobka/0-korinish/3d-maket.png
```
