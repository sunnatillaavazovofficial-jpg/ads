#!/usr/bin/env python3
"""MONOOS karobka dizaynini (Cefoperazone / Ampicillin + Sulbactam) vektor (SVG) qilib chizadi.

Har bir detal alohida: logo, fon, matn, shtrix-kod, panellar, flakon etiketkasi
va qutining to'liq razvyortkasi (kesish/bukish chiziqlari bilan).

Matnlar shrift konturlariga (curves) aylantirilgan, shuning uchun CorelDRAW /
Illustrator'da shrift o'rnatilmagan bo'lsa ham to'g'ri ochiladi.

Ishlatish:  python3 build_box.py <shriftlar_papkasi> <chiqish_papkasi> [mahsulot]
            mahsulot: cefoperazone (standart) yoki ampicillin — pastdagi PRODUCTS ga qarang.
Shriftlar (Google Fonts, bepul): RobotoCondensed[wght].ttf, Roboto[wdth,wght].ttf,
Montserrat[wght].ttf
"""
import os
import sys

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONT_DIR = sys.argv[1] if len(sys.argv) > 1 else "fonts"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out"
PRODUCT = sys.argv[3] if len(sys.argv) > 3 else "cefoperazone"

# ---------------------------------------------------------------- o'lchamlar
# Quti (mm): old panel eni W, chuqurligi D (yon panel eni), balandligi H.
W, D, H = 60, 36, 80
BLEED = 3            # mm, vylet
TUCK = 15            # mm, qopqoq tilchasi
DUST = 20            # mm, yon qanotchalar (pylnik) balandligi
GLUE = 14            # mm, yelim qanoti
# Panel ichki koordinatalari 0.1 mm birlikda (old panel 600 x 800).
U = 0.1

# ---------------------------------------------------------------- mahsulotlar
_SIDE_COMMON = [
    ("Dosage:", ["As directed by the physician."]),
    ("Storage:", ["Store below 25°C", "in a dry place, away from light.",
                  "Keep out of reach of children."]),
    (None, ["Reconstituted solution is stable for", "7 days at 2°C-8°C or 24 hours",
            "at 8°C-25°C."]),
]
_MANUF = ["*SWISS PARENTERALS LTD.", "402, 412-414, Kerala Industrial",
          "Estate, G.I.D.C., Nr. Bavla,", "Dist.: Ahmedabad-382 220,", "Gujarat, India."]

# Har bir mahsulot: matnlar, asosiy ranglar va fon ranglarini almashtirish jadvali (remap).
# Fon ranglari Cefoperazone (ko'k-yashil) varianti asosida yozilgan; remap ularni
# boshqa mahsulot ranglariga o'tkazadi.
PRODUCTS = {
    "cefoperazone": dict(
        title1="CEFOPERAZONE", title1_w=(440, 352, 340),      # old panel, yon panel 2, qopqoq
        title2="SULBACTAM", title2_w=(356, 284, 272),
        sub="Cefoperazone and Sulbactam", sub_w=366,
        dose="1000 mg + 500 mg", pill_w=374, dose_cap=27,
        side=[("Composition:", ["Each vial contains:", "Cefoperazone Sodium USP",
                                "equivalent to Cefoperazone 1000 mg", "Sulbactam Sodium USP",
                                "equivalent to Sulbactam 500 mg"])] + _SIDE_COMMON +
             [("Manufactured by:", _MANUF)],
        lic="Mfg. Lic. No.:",
        c_title1="#1A3D91", c_title2="#2C8C3D", c_badge="#2E8B3E", c_sub="#1A3D91",
        c_ml="#1A3D91", c_body="#1E2D5C", c_side="#22307A", c_side_accent="#22307A",
        c_logo_text="#1A3D91", c_logo_swoosh="#1A3D91",
        logo_arc1=[(0, "#EE7F1A"), (1, "#F39A26")],
        logo_arc2=[(0, "#F6A92A"), (0.6, "#FAC046"), (1, "#F7B233")],
        pill=[(0, "#173C8E"), (0.55, "#1D5AA8"), (1, "#3FA24A")],
        remap={},
    ),
    "ampicillin": dict(
        title1="AMPICILLIN", title1_w=(355, 284, 274),
        title2="SULBACTAM", title2_w=(356, 284, 272),
        sub="Ampicillin and Sulbactam", sub_w=334,
        dose="1.5 g (1000 mg + 500 mg)", pill_w=404, dose_cap=22.5,
        side=[("Composition:", ["Each vial contains:", "Ampicillin Sodium USP",
                                "equivalent to Ampicillin 1000 mg", "Sulbactam Sodium USP",
                                "equivalent to Sulbactam 500 mg"])] + _SIDE_COMMON +
             [("~Manufactured by:", _MANUF)],
        lic="Mfg. Lic. No. :",
        c_title1="#561C8E", c_title2="#13809A", c_badge="#5A1690", c_sub="#2B2068",
        c_ml="#3A1A7A", c_body="#23224A", c_side="#3E3B5C", c_side_accent="#4E2385",
        c_logo_text="#1A1B5E", c_logo_swoosh="#2B1B6E",
        logo_arc1=[(0, "#5E1E98"), (1, "#8A49BE")],
        logo_arc2=[(0, "#7C3FB4"), (0.55, "#2F86B0"), (1, "#38C4D4")],
        pill=[(0, "#3E1489"), (0.55, "#3A2E92"), (1, "#17A6BB")],
        remap={
            # to'q ko'k -> to'q binafsha
            "#0E2C6F": "#381A72", "#153B8E": "#45218A", "#1A50AC": "#5428A0", "#1F63C2": "#6633B2",
            "#173F96": "#4A2390", "#1F74D0": "#6C38B6",
            # ko'k lenta -> binafsha
            "#1E6ACB": "#5A2CA8", "#2A86DD": "#7A44C4", "#69B6F0": "#A57BE0",
            # och ko'k chiziq -> lavanda
            "#5AA8E8": "#8E5CCF", "#8CC8F2": "#B591E6", "#C4E3F9": "#D9C6F4",
            "#3D8FDD": "#7A44C4", "#9FD0F4": "#C6A9EE", "#7DBDEF": "#B08AE6",
            # burchak / och fon
            "#A9D5F5": "#CDB6F0", "#E1F0FC": "#EEE6FA", "#F4F9FE": "#F8F5FD", "#D5EAFA": "#E9DEF8",
            # yashil -> moviy (teal)
            "#3FA94E": "#22B3CC", "#23994A": "#138FA6", "#1A7F3E": "#0D6F86",
            "#B8DC5C": "#8EE0EE", "#7DBE3E": "#4CC6DC", "#8DC63F": "#5CCDE0",
            # pastki och lenta -> och moviy
            "#D2E9FA": "#D8F2F7", "#8EC6F2": "#7FD3E3", "#3C8EDD": "#1FA8C4",
            # oltiburchaklar
            "#D6EAFA": "#E3D8F6", "#E4F1FC": "#EEE7FA", "#E2F0FC": "#ECE4F9", "#C3DEF4": "#D3C2F0",
            "#DCEDFB": "#E6DCF8", "#E6F2FC": "#EEE7FA", "#BBD9F3": "#CDBBEE",
            "#D3E8FA": "#CFDDF7", "#C9E2F8": "#C5D6F5", "#E1EFFC": "#E0E8FA",
            "#B4D5F1": "#B5C9EE", "#A9CFEF": "#AFC3EC", "#9CC8EC": "#A2B7E8",
        },
    ),
}
TH = PRODUCTS[PRODUCT]


def C(c):
    """Fon rangini tanlangan mahsulot ranglariga o'tkazadi."""
    return TH["remap"].get(c.upper(), c) if isinstance(c, str) else c


TITLE1, TITLE2, BADGE, SUBC = TH["c_title1"], TH["c_title2"], TH["c_badge"], TH["c_sub"]
MLC, TEXT, SIDE_TEXT, SIDE_ACCENT = TH["c_ml"], TH["c_body"], TH["c_side"], TH["c_side_accent"]
LOGO_TEXT, LOGO_SWOOSH = TH["c_logo_text"], TH["c_logo_swoosh"]
NAVY_DARK = C("#0E2C6F")
G_DARK = C("#23994A")
G_LIME = C("#8DC63F")


def n(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ---------------------------------------------------------------- shriftlar
class Font:
    def __init__(self, file, **axes):
        path = os.path.join(FONT_DIR, file)
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
        self.hb.set_variations(axes)
        self.tt = TTFont(path)
        self.gs = self.tt.getGlyphSet(location=axes)
        self.upem = self.tt["head"].unitsPerEm
        self.order = self.tt.getGlyphOrder()
        self.cap = self.tt["OS/2"].sCapHeight / self.upem

    def shape(self, s):
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True})
        return list(zip(buf.glyph_infos, buf.glyph_positions))

    def width(self, s, size, tracking=0.0):
        g = self.shape(s)
        return (sum(p.x_advance for _, p in g) / self.upem + tracking * (len(g) - 1)) * size

    def outline(self, s, x, y, size, sx=1.0, tracking=0.0):
        k = size / self.upem
        pen = SVGPathPen(self.gs, ntos=n)
        cx = 0.0
        for info, pos in self.shape(s):
            name = self.order[info.codepoint]
            ox = x + (cx + pos.x_offset) * k * sx
            oy = y - pos.y_offset * k
            self.gs[name].draw(TransformPen(pen, (k * sx, 0, 0, -k, ox, oy)))
            cx += pos.x_advance + tracking * self.upem
        return pen.getCommands()


F_TITLE = Font("RobotoCondensed[wght].ttf", wght=800)
F_COND_B = Font("RobotoCondensed[wght].ttf", wght=700)
F_COND = Font("RobotoCondensed[wght].ttf", wght=400)
F_REG = Font("Roboto[wdth,wght].ttf", wght=400, wdth=100)
F_MED = Font("Roboto[wdth,wght].ttf", wght=500, wdth=100)
F_SEMI = Font("Roboto[wdth,wght].ttf", wght=600, wdth=100)
F_LOGO = Font("Montserrat[wght].ttf", wght=700)
F_SUB = Font("Roboto[wdth,wght].ttf", wght=460, wdth=90)
F_BODY = Font("Roboto[wdth,wght].ttf", wght=400, wdth=90)


def text(font, s, x, y, size, fill, anchor="start", width=None, maxwidth=None,
         sx=1.0, tracking=0.0, cap=None):
    """Matnni kontur (path) qilib qaytaradi. cap - bosh harf balandligi."""
    if cap is not None:
        size = cap / font.cap
    nat = font.width(s, size, tracking)
    if width is not None:
        sx = width / nat
    elif maxwidth is not None and nat * sx > maxwidth:
        sx = maxwidth / nat
    w = nat * sx
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    d = font.outline(s, x, y, size, sx, tracking)
    return f'<path fill="{fill}" d="{d}"/>'


def fit_cap(font, s, maxw, cap_max):
    """Matn maxw ga sig'adigan eng katta bosh harf balandligi (cap_max dan oshmaydi)."""
    w = font.width(s, cap_max / font.cap)
    return cap_max if w <= maxw else cap_max * maxw / w


def group(gid, body, extra=""):
    return f'<g id="{gid}"{extra}>\n{body}\n</g>'


def P(*pts):
    return " ".join(f"{n(x)},{n(y)}" for x, y in pts)


def hexagon(cx, cy, r):
    import math
    pts = [(cx + r * math.cos(math.radians(90 + 60 * i)),
            cy + r * math.sin(math.radians(90 + 60 * i))) for i in range(6)]
    return "M" + " L".join(f"{n(x)},{n(y)}" for x, y in pts) + " Z"


class Art:
    """SVG bo'lagi: defs (gradientlar) + qatlamlar."""

    def __init__(self, prefix):
        self.p = prefix
        self.defs = []

    def lin(self, name, x1, y1, x2, y2, stops):
        gid = f"{self.p}-{name}"
        st = "".join(f'<stop offset="{o}" stop-color="{c}"' +
                     (f' stop-opacity="{a}"' if a != 1 else "") + "/>"
                     for o, c, a in [(s[0], C(s[1])) + tuple(s[2:3]) + (1,) * (len(s) < 3)
                                     for s in stops])
        self.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                         f'x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}">{st}</linearGradient>')
        return f"url(#{gid})"


# ================================================================ LOGO
# Logo o'z koordinatalarida: "MONOOS" eni 555, bosh harf balandligi 65.
LOGO_W, LOGO_H = 600, 200


def logo_body(a, color_text=None, swoosh=None):
    color_text = color_text or LOGO_TEXT
    swoosh = swoosh or LOGO_SWOOSH
    g_or = a.lin("logo-or", 0, 110, 380, 0, TH["logo_arc1"])
    g_ye = a.lin("logo-ye", 200, 0, 590, 140, TH["logo_arc2"])
    arc = (
        f'<path fill="{g_or}" d="M10,112 C80,58 160,30 240,18 C300,9 360,8 400,14 '
        f'L420,64 C280,58 140,76 10,112 Z"/>\n'
        f'<path fill="{g_ye}" d="M190,26 C300,-4 450,-6 525,44 C558,66 578,100 590,142 '
        f'C530,104 455,79 385,68 C315,57 245,46 190,26 Z"/>\n'
        f'<path fill="{swoosh}" d="M244,80 C380,75 505,98 574,141 '
        f'C490,117 380,101 244,90 Z"/>'
    )
    word = text(F_LOGO, "MONOOS", 2, 196, 0, color_text, cap=66, width=556, tracking=0.03)
    return group(f"{a.p}-logo-yoy", arc) + "\n" + group(f"{a.p}-logo-yozuv", word)


# ================================================================ OLD PANEL
def vial_icon(x, y, h, stroke="#FFFFFF", sw=3.2):
    """Oddiy flakon ikonkasi (kontur). x,y - chap-yuqori, h - balandlik."""
    s = h / 66.0

    def T(px, py):
        return f"{n(x + px * s)},{n(y + py * s)}"
    outline = (f"M{T(4,0)} L{T(23,0)} L{T(23,8)} L{T(4,8)} Z "
               f"M{T(8,8)} L{T(8,14)} C{T(8,17)} {T(1,18)} {T(1,24)} L{T(1,62)} "
               f"C{T(1,65)} {T(3,66)} {T(6,66)} L{T(21,66)} C{T(24,66)} {T(26,65)} {T(26,62)} "
               f"L{T(26,24)} C{T(26,18)} {T(19,17)} {T(19,14)} L{T(19,8)}")
    ticks = f"M{T(6,36)} L{T(12,36)} M{T(6,44)} L{T(10,44)} M{T(6,52)} L{T(12,52)}"
    return (f'<path fill="none" stroke="{stroke}" stroke-width="{n(sw)}" stroke-linejoin="round" '
            f'd="{outline}"/>\n'
            f'<path fill="none" stroke="{stroke}" stroke-width="{n(sw * 0.8)}" stroke-linecap="round" '
            f'd="{ticks}"/>')


# --- to'lqin lentalar geometriyasi (silliq Hermite egri chiziqlari)
BX0, BX1, BY0, BY1 = -40, 640, -40, 840   # vylet bilan chegara


def _unit(v):
    import math
    ln = math.hypot(*v)
    return (v[0] / ln, v[1] / ln)


def hcurve(S, K, E, tS, tK, tE, k=0.4):
    """S -> K -> E nuqtalaridan o'tuvchi ikki bo'lakli kubik egri."""
    import math
    tS, tK, tE = _unit(tS), _unit(tK), _unit(tE)
    d1, d2 = math.dist(S, K) * k, math.dist(K, E) * k
    return [(S, (S[0] + tS[0] * d1, S[1] + tS[1] * d1), (K[0] - tK[0] * d1, K[1] - tK[1] * d1), K),
            (K, (K[0] + tK[0] * d2, K[1] + tK[1] * d2), (E[0] - tE[0] * d2, E[1] - tE[1] * d2), E)]


def _perim(p):
    x, y = p
    if abs(y - BY0) < 1e-6:
        return x - BX0
    if abs(x - BX1) < 1e-6:
        return (BX1 - BX0) + (y - BY0)
    if abs(y - BY1) < 1e-6:
        return (BX1 - BX0) + (BY1 - BY0) + (BX1 - x)
    return 2 * (BX1 - BX0) + (BY1 - BY0) + (BY1 - y)


_CORNERS = [(0, (BX0, BY0)), (BX1 - BX0, (BX1, BY0)),
            ((BX1 - BX0) + (BY1 - BY0), (BX1, BY1)), (2 * (BX1 - BX0) + (BY1 - BY0), (BX0, BY1))]


def _on_edge(p):
    x, y = p
    return min(abs(x - BX0), abs(x - BX1), abs(y - BY0), abs(y - BY1)) < 1e-6


def _walk(p, q):
    if not (_on_edge(p) and _on_edge(q)):
        return []          # uchli (ichkarida tugaydigan) lenta
    sp, sq = _perim(p), _perim(q)
    return [c for s, c in sorted(_CORNERS, key=lambda t: -t[0]) if sq < s < sp]


def ribbon(ca, cb):
    """Ikki egri chiziq orasidagi lenta (yopiq kontur)."""
    d = [f"M{P(ca[0][0])}"] + [f"C{P(s[1], s[2], s[3])}" for s in ca]
    d += [f"L{P(c)}" for c in _walk(ca[-1][3], cb[-1][3])] + [f"L{P(cb[-1][3])}"]
    d += [f"C{P(s[2], s[1], s[0])}" for s in reversed(cb)]
    d += [f"L{P(c)}" for c in _walk(cb[0][0], ca[0][0])] + ["Z"]
    return " ".join(d)


def spline(pts, k=0.38):
    """Nuqtalardan o'tuvchi silliq (Catmull-Rom) kubik egri."""
    import math
    T = []
    for i in range(len(pts)):
        if i == 0:
            d = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        elif i == len(pts) - 1:
            d = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
        else:
            d = (pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1])
        T.append(_unit(d))
    segs = []
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        ln = math.dist(p, q) * k
        segs.append((p, (p[0] + T[i][0] * ln, p[1] + T[i][1] * ln),
                     (q[0] - T[i + 1][0] * ln, q[1] - T[i + 1][1] * ln), q))
    return segs


def shift(pts, dx, dy):
    out = []
    for x, y in pts:
        if y == BY0:
            out.append((x + dx, y))          # yuqori chegarada qoladi
        elif x == BX0:
            out.append((x, y + dy))          # chap chegarada qoladi
        else:
            out.append((x + dx, y + dy))
    return out


_C0 = [(496, -40), (480, 200), (462, 380), (446, 462), (400, 512), (300, 542), (120, 553), (-40, 556)]
_TAPER = (408, 652)
WAVE = {
    "c0": spline(_C0),
    "c1": spline(shift(_C0, 11, 12)),
    "c2": spline(shift(_C0, 22, 26)),
    "c3": spline([(545, -40), (530, 200), (504, 390), (472, 464), (432, 530), (370, 572), (250, 598),
                  (80, 610), (-40, 612)]),
    "c4": spline([(614, -40), (598, 120), (570, 250), (540, 330), (510, 402), (484, 462), (454, 530),
                  (424, 600), (408, 652), (405, 730), (415, 840)]),
    "g0": spline([(640, 190), (590, 280), (550, 350), (520, 402), (488, 464), (458, 530), (430, 596),
                  _TAPER]),
    "g1": spline([(640, 236), (606, 300), (576, 352), (550, 404), (514, 470), (482, 536), (452, 600),
                  _TAPER]),
    "g2": spline([(640, 268), (616, 316), (592, 362), (568, 408), (532, 474), (498, 540), (464, 604),
                  _TAPER]),
    "c9": spline([(640, 330), (600, 404), (562, 470), (520, 540), (478, 604), (440, 660), (420, 722),
                  (418, 840)]),
    "c10": spline([(640, 430), (602, 500), (566, 568), (536, 630), (506, 690), (482, 760), (472, 840)]),
}


def front_background(a):
    """Old panel foni: to'lqin lentalar, oltiburchaklar. 600x800 (+40 vylet)."""
    w = WAVE
    out = ['<rect x="-40" y="-40" width="680" height="880" fill="#FFFFFF"/>']
    pale = a.lin("pale", 560, 0, 330, 260, [(0, "#D5EAFA"), (1, "#FFFFFF", 0)])
    out.append(f'<path fill="{pale}" d="M330,-40 H520 V500 C470,330 380,140 330,-40 Z"/>')
    hx = []
    for cx, cy, r, f, o in [(452, 96, 30, "#D6EAFA", 0.9), (420, 160, 20, "none", 1),
                            (470, 214, 24, "#E4F1FC", 1), (440, 40, 18, "none", 1),
                            (585, 300, 22, "#E2F0FC", 1)]:
        hx.append(f'<path d="{hexagon(cx, cy, r)}" fill="{C(f)}" fill-opacity="{o}" '
                  f'stroke="{C("#C3DEF4")}" stroke-width="2"/>')
    out.append(group(f"{a.p}-hex-yuqori", "\n".join(hx)))


    g_lb = a.lin("lb", 0, 560, 500, 0, [(0, "#5AA8E8"), (0.5, "#8CC8F2"), (1, "#C4E3F9")])
    g_b1 = a.lin("b1", 0, 600, 540, 0, [(0, "#1E6ACB"), (0.55, "#2A86DD"), (1, "#69B6F0")])
    g_nv = a.lin("nv", 120, 760, 600, 0, [(0, NAVY_DARK), (0.5, "#153B8E"), (0.8, "#1A50AC"),
                                           (1, "#1F63C2")])
    g_cr = a.lin("cr", 640, -40, 520, 640, [(0, "#A9D5F5"), (0.5, "#E1F0FC"), (1, "#F4F9FE")])
    g_gd = a.lin("gd", 640, 190, 408, 652, [(0, "#3FA94E"), (0.5, G_DARK), (1, "#1A7F3E")])
    g_gl = a.lin("gl", 640, 236, 408, 652, [(0, "#B8DC5C"), (1, "#7DBE3E")])
    g_rb = a.lin("rb", 640, 330, 440, 840, [(0, "#D2E9FA"), (0.45, "#8EC6F2"), (1, "#3C8EDD")])
    bands = [("och-fon", "c4", "c10", g_cr), ("och-kok-lenta", "c0", "c1", g_lb),
             ("kok-lenta", "c2", "c3", g_b1), ("toq-kok-lenta", "c3", "c4", g_nv),
             ("och-kok-past", "c9", "c10", g_rb),
             ("yashil-lenta", "g0", "g1", g_gd), ("och-yashil-lenta", "g1", "g2", g_gl)]
    lent = [f'<path id="{a.p}-{name}" fill="{fill}" d="{ribbon(w[ca], w[cb])}"/>'
            for name, ca, cb, fill in bands]
    out.append(group(f"{a.p}-lentalar", "\n".join(lent)))
    # pastki o'ng burchak: oltiburchaklar va molekula
    hx = []
    for cx, cy, r, f, o in [(560, 612, 26, "#D3E8FA", 0.95), (606, 660, 22, "none", 1),
                            (568, 714, 32, "#C9E2F8", 0.9), (620, 760, 20, "#E1EFFC", 1),
                            (530, 778, 18, "none", 1), (614, 566, 16, "#E6F2FC", 1)]:
        hx.append(f'<path d="{hexagon(cx, cy, r)}" fill="{C(f)}" fill-opacity="{o}" '
                  f'stroke="{C("#B4D5F1")}" stroke-width="2"/>')
    pts = [(532, 572), (560, 612), (606, 660), (568, 714), (530, 778)]
    hx.append(f'<path fill="none" stroke="{C("#A9CFEF")}" stroke-width="2" d="M' +
              " L".join(f"{x},{y}" for x, y in pts) + '"/>')
    for x, y in pts + [(640, 700)]:
        hx.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{C("#9CC8EC")}"/>')
    out.append(group(f"{a.p}-hex-pastki", "\n".join(hx)))
    return "\n".join(out)


def front_text(a, bottom=True):
    t = []
    t.append(group(f"{a.p}-nomi-1", text(F_TITLE, TH["title1"], 44, 218, 0, TITLE1,
                                          cap=57, width=TH["title1_w"][0], tracking=-0.005)))
    t.append(group(f"{a.p}-nomi-2", text(F_TITLE, TH["title2"], 44, 286, 0, TITLE2,
                                          cap=55, width=TH["title2_w"][0], tracking=-0.005)))
    bio = (f'<rect x="410" y="232" width="76" height="54" rx="9" fill="{BADGE}"/>\n' +
           text(F_COND_B, "BIO", 448, 277, 0, "#FFFFFF", anchor="middle", cap=36, sx=0.95))
    t.append(group(f"{a.p}-bio", bio))
    t.append(group(f"{a.p}-xalqaro-nomi", text(F_SUB, TH["sub"], 45, 337, 0,
                                                SUBC, cap=24, width=TH["sub_w"])))
    pw = TH["pill_w"]
    pill_g = a.lin("pill", 42, 0, 42 + pw, 0, TH["pill"])
    pill = (f'<rect x="42" y="358" width="{pw}" height="47" rx="10" fill="{pill_g}"/>\n' +
            text(F_MED, TH["dose"], 42 + pw / 2, 396, 0, "#FFFFFF", anchor="middle",
                 cap=TH["dose_cap"]))
    t.append(group(f"{a.p}-dozasi", pill))
    lines = ["Powder for solution for injection", "For IM / IV use", "Prescription only medicine"]
    body = "\n".join(text(F_BODY, s, 45, 464 + 37 * i, 0, TEXT, cap=20.5) for i, s in enumerate(lines))
    t.append(group(f"{a.p}-tavsif", body))
    if bottom:
        b = [vial_icon(44, 670, 66),
             text(F_MED, "1 vial", 92, 731, 0, "#FFFFFF", cap=22),
             '<rect x="176.5" y="686" width="3" height="56" fill="#FFFFFF"/>',
             '<rect x="196" y="691" width="110" height="50" rx="9" fill="#FFFFFF"/>',
             text(F_SEMI, "20 ml", 251, 731, 0, MLC, anchor="middle", cap=23)]
        t.append(group(f"{a.p}-hajmi", "\n".join(b)))
    return "\n".join(t)


def front_logo(a, x=44, y=30, w=200):
    s = w / LOGO_W
    return group(f"{a.p}-logo", logo_body(a), f' transform="translate({n(x)},{n(y)}) scale({n(s)})"')


def front_panel(prefix):
    a = Art(prefix)
    layers = {
        "fon": front_background(a),
        "logo": front_logo(a),
        "matn": front_text(a),
    }
    return a, layers


# ================================================================ YON PANEL (tarkib)
EAN_L = ["0001101", "0011001", "0010011", "0111101", "0100011",
         "0110001", "0101111", "0111011", "0110111", "0001011"]
EAN_G = ["0100111", "0110011", "0011011", "0100001", "0011101",
         "0111001", "0000101", "0010001", "0001001", "0010111"]
EAN_R = ["1110010", "1100110", "1101100", "1000010", "1011100",
         "1001110", "1010000", "1000100", "1001000", "1110100"]
EAN_PARITY = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
              "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]


def ean13_check(d12):
    s = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(d12))
    return str((10 - s % 10) % 10)


def ean13(code, x, y, module, bar_h, color="#000000", digit_font=None):
    """EAN-13 shtrix-kod: x - chap jim zona boshlanishi, y - chiziqlar tepasi."""
    assert len(code) == 13 and code[-1] == ean13_check(code[:12]), "EAN-13 nazorat raqami xato"
    first, left, right = code[0], code[1:7], code[7:]
    bits = "101"
    for d, p in zip(left, EAN_PARITY[int(first)]):
        bits += (EAN_L if p == "L" else EAN_G)[int(d)]
    bits += "01010"
    for d in right:
        bits += EAN_R[int(d)]
    bits += "101"
    guard = set(range(0, 3)) | set(range(45, 50)) | set(range(92, 95))
    x0 = x + 11 * module
    rects = []
    i = 0
    while i < len(bits):
        if bits[i] == "1":
            j = i
            while j < len(bits) and bits[j] == "1" and ((j in guard) == (i in guard)):
                j += 1
            h = bar_h + (5 * module if i in guard else 0)
            rects.append(f'<rect x="{n(x0 + i * module)}" y="{n(y)}" width="{n((j - i) * module)}" '
                         f'height="{n(h)}"/>')
            i = j
        else:
            i += 1
    out = [f'<g fill="{color}">'] + rects + ["</g>"]
    f = digit_font or F_REG
    cap = 7.2 * module
    by = y + bar_h + 8.5 * module
    out.append(text(f, first, x0 - 2 * module, by, 0, color, anchor="end", cap=cap))
    for k, d in enumerate(left):
        out.append(text(f, d, x0 + (3 + 7 * k + 3.5) * module, by, 0, color, anchor="middle", cap=cap))
    for k, d in enumerate(right):
        out.append(text(f, d, x0 + (50 + 7 * k + 3.5) * module, by, 0, color, anchor="middle", cap=cap))
    return "\n".join(out)


BARCODE = "8904180253442"
SIDE_BLOCKS = TH["side"]


def side_info_panel(prefix):
    a = Art(prefix)
    fon = '<rect x="0" y="0" width="360" height="800" fill="#FFFFFF"/>'
    x, y = 26, 62
    lh, cap = 23.4, 13.6
    maxw = 360 - x - 20
    t = []
    for k, (head, lines) in enumerate(SIDE_BLOCKS):
        blk = []
        if head and head.startswith("~"):      # oddiy (qalin emas) sarlavha
            blk.append(text(F_COND, head[1:], x, y, 0, SIDE_TEXT, cap=cap, maxwidth=maxw))
            y += lh
        elif head:
            blk.append(text(F_COND_B, head, x, y, 0, SIDE_ACCENT, cap=cap + 0.6, maxwidth=maxw))
            y += lh
        for s in lines:
            if s.startswith("*"):
                blk.append(text(F_COND_B, s[1:], x, y, 0, SIDE_ACCENT, cap=cap, maxwidth=maxw))
            else:
                blk.append(text(F_COND, s, x, y, 0, SIDE_TEXT, cap=cap, maxwidth=maxw))
            y += lh
        y += lh * 0.55
        t.append(group(f"{prefix}-blok-{k + 1}", "\n".join(blk)))
    y += 2
    lic = (f'<rect x="{x - 2}" y="{n(y)}" width="300" height="40" rx="6" fill="none" '
           f'stroke="{SIDE_TEXT}" stroke-width="1.6"/>\n' +
           text(F_COND, TH["lic"], x + 10, y + 26.5, 0, SIDE_TEXT, cap=cap))
    t.append(group(f"{prefix}-litsenziya", lic))
    bc_y = y + 56
    module = 2.8
    bar_h = 800 - 34 - bc_y - 5 * module
    bc = ean13(BARCODE, 10, bc_y, module, bar_h - 10 * module, color="#000000", digit_font=F_COND)
    t.append(group(f"{prefix}-shtrix-kod", bc))
    return a, {"fon": fon, "matn": "\n".join(t)}


# ================================================================ YON PANEL 2 (brend)
def side_brand_panel(prefix):
    """36x80 mm yon panel, matn pastdan yuqoriga o'qiladi."""
    a = Art(prefix)
    # aylantirilgan koordinatalar: eni 800 (quti balandligi bo'ylab), bo'yi 360
    fon = []
    fon.append('<rect x="-40" y="-40" width="880" height="440" fill="#FFFFFF"/>')
    main = a.lin("main", 0, 360, 800, 0, [(0, NAVY_DARK), (0.5, "#173F96"), (1, "#1F74D0")])
    lb = a.lin("lb", 0, 300, 800, 0, [(0, "#3D8FDD"), (1, "#9FD0F4")])
    fon.append(f'<path fill="{G_DARK}" d="M-40,262 C200,262 480,258 840,232 L840,242 '
               f'C480,268 200,272 -40,272 Z"/>')
    fon.append(f'<path fill="{G_LIME}" d="M-40,274 C200,274 480,270 840,246 L840,252 '
               f'C480,276 200,280 -40,280 Z"/>')
    fon.append(f'<path fill="{lb}" d="M-40,284 C200,284 480,280 840,256 L840,266 '
               f'C480,290 200,294 -40,294 Z"/>')
    fon.append(f'<path fill="{main}" d="M-40,300 C200,300 480,296 840,272 L840,400 L-40,400 Z"/>')
    for cx, cy, r, f in [(742, 46, 24, "#DCEDFB"), (782, 84, 18, "none"), (706, 92, 16, "#E6F2FC")]:
        fon.append(f'<path d="{hexagon(cx, cy, r)}" fill="{C(f)}" stroke="{C("#BBD9F3")}" stroke-width="2"/>')
    logo = group(f"{prefix}-logo", logo_body(a), ' transform="translate(40,30) scale(0.3)"')
    t = []
    t.append(text(F_TITLE, TH["title1"], 40, 160, 0, TITLE1, cap=46, width=TH["title1_w"][1]))
    t.append(text(F_TITLE, TH["title2"], 40, 222, 0, TITLE2, cap=44, width=TH["title2_w"][1]))
    t.append(f'<rect x="334" y="178" width="60" height="44" rx="7" fill="{BADGE}"/>')
    t.append(text(F_COND_B, "BIO", 364, 214, 0, "#FFFFFF", anchor="middle", cap=29))
    pill_g = a.lin("pill", 430, 0, 740, 0, TH["pill"])
    t.append(f'<rect x="430" y="122" width="300" height="40" rx="9" fill="{pill_g}"/>')
    t.append(text(F_MED, TH["dose"], 580, 154, 0, "#FFFFFF", anchor="middle",
                  cap=fit_cap(F_MED, TH["dose"], 280, 22)))
    t.append(text(F_REG, TH["sub"], 430, 196, 0, SUBC, cap=17, width=300))
    t.append(text(F_REG, "Powder for solution for injection", 430, 226, 0, TEXT, cap=15.5))
    t.append(text(F_MED, "For IM / IV use  ·  Prescription only medicine", 40, 344, 0,
                  "#FFFFFF", cap=17))
    t.append(vial_icon(632, 304, 46, sw=2.6))
    t.append(text(F_MED, "1 vial", 664, 345, 0, "#FFFFFF", cap=16))
    t.append('<rect x="718" y="314" width="2.4" height="38" fill="#FFFFFF"/>')
    t.append(text(F_SEMI, "20 ml", 790, 345, 0, "#FFFFFF", anchor="end", cap=17))
    rot = ' transform="translate(0,800) rotate(-90)"'
    return a, {"fon": group(f"{prefix}-fon-r", "\n".join(fon), rot),
               "logo": group(f"{prefix}-logo-r", logo, rot),
               "matn": group(f"{prefix}-matn-r", "\n".join(t), rot)}


# ================================================================ QOPQOQLAR
def top_lid(prefix):
    """Yuqori qopqoq 600 x 360 (old panel tomoni pastda)."""
    a = Art(prefix)
    fon = ['<rect x="0" y="0" width="600" height="360" fill="#FFFFFF"/>']
    main = a.lin("main", 0, 360, 600, 0, [(0, NAVY_DARK), (0.5, "#173F96"), (1, "#1F74D0")])
    fon.append(f'<path fill="{main}" d="M0,318 C200,316 420,300 600,250 L600,360 L0,360 Z"/>')
    fon.append(f'<path fill="{G_DARK}" d="M0,300 C200,298 420,282 600,232 L600,242 '
               f'C420,292 200,308 0,309 Z"/>')
    for cx, cy, r, f in [(520, 70, 30, "#DCEDFB"), (565, 120, 24, "none"), (488, 130, 20, "#E6F2FC")]:
        fon.append(f'<path d="{hexagon(cx, cy, r)}" fill="{C(f)}" stroke="{C("#BBD9F3")}" stroke-width="2"/>')
    logo = group(f"{prefix}-logo", logo_body(a), ' transform="translate(40,32) scale(0.3)"')
    t = [text(F_TITLE, TH["title1"], 40, 160, 0, TITLE1, cap=44, width=TH["title1_w"][2]),
         text(F_TITLE, TH["title2"], 40, 220, 0, TITLE2, cap=42, width=TH["title2_w"][2]),
         f'<rect x="322" y="178" width="58" height="42" rx="7" fill="{BADGE}"/>',
         text(F_COND_B, "BIO", 351, 213, 0, "#FFFFFF", anchor="middle", cap=28),
         text(F_MED, TH["dose"], 40, 270, 0, SUBC, cap=21)]
    return a, {"fon": "\n".join(fon), "logo": logo, "matn": "\n".join(t)}


def bottom_lid(prefix):
    """Pastki qopqoq 600 x 360: seriya / sana maydonlari (bo'sh)."""
    a = Art(prefix)
    fon = '<rect x="0" y="0" width="600" height="360" fill="#FFFFFF"/>'
    t = []
    for i, lab in enumerate(["Batch No.:", "Mfg. Date:", "Exp. Date:"]):
        y = 70 + i * 90
        t.append(text(F_COND_B, lab, 50, y + 38, 0, SIDE_ACCENT, cap=20))
        t.append(f'<rect x="200" y="{y}" width="350" height="56" rx="6" fill="none" '
                 f'stroke="{SIDE_TEXT}" stroke-width="1.8"/>')
    return a, {"fon": fon, "matn": "\n".join(t)}


# ================================================================ FLAKON ETIKETKASI
LABEL_W, LABEL_H = 900, 400   # 90 x 40 mm


def vial_label(prefix):
    a = Art(prefix)
    cx0 = 300  # markaziy (old) qism 300..600, old panel 0.5 masshtabda
    fon = ['<rect x="-40" y="-40" width="980" height="480" fill="#FFFFFF"/>']
    main = a.lin("wing", 0, 400, 900, 0, [(0, NAVY_DARK), (0.5, "#173F96"), (1, "#1F74D0")])
    # chap qanot: pastki navy to'lqin old qismning chap chetiga ulanadi (y~303)
    fon.append(f'<path fill="{main}" d="M-40,330 C80,332 200,318 {cx0 + 2},302 L{cx0 + 2},440 L-40,440 Z"/>')
    fon.append(f'<path fill="{C("#7DBDEF")}" d="M-40,300 C80,302 200,290 {cx0 + 2},274 L{cx0 + 2},295 '
               f'C200,309 80,320 -40,318 Z"/>')
    # o'ng qanot
    fon.append(f'<path fill="{main}" d="M598,440 C700,360 800,334 940,330 L940,440 Z"/>')
    fon.append(f'<path fill="{G_DARK}" d="M598,418 C700,336 800,310 940,306 L940,316 '
               f'C800,320 700,346 610,424 Z"/>')
    fon.append(f'<path fill="{G_LIME}" d="M612,400 C710,322 805,296 940,292 L940,299 '
               f'C805,304 712,330 622,405 Z"/>')
    for cx, cy, r, f in [(840, 60, 24, "#DCEDFB"), (872, 100, 20, "none"), (230, 50, 22, "#E6F2FC"),
                         (262, 84, 16, "none")]:
        fon.append(f'<path d="{hexagon(cx, cy, r)}" fill="{C(f)}" stroke="{C("#BBD9F3")}" stroke-width="2"/>')
    # markaziy qism (old panel dizayni)
    fa = Art(prefix + "-old")
    center_bg = front_background(fa)
    center_txt = front_text(fa)
    center_logo = front_logo(fa)
    a.defs += fa.defs
    clip_id = f"{prefix}-markaz-clip"
    a.defs.append(f'<clipPath id="{clip_id}"><rect x="{cx0}" y="-40" width="300" height="480"/></clipPath>')
    tr = f' transform="translate({cx0},0) scale(0.5)"'
    fon.append(f'<g clip-path="url(#{clip_id})"><g{tr}>{center_bg}</g></g>')
    logo = group(f"{prefix}-logo", center_logo, tr)
    t = [group(f"{prefix}-old-matn", center_txt, tr)]
    # chap qanot: tarkib
    left = []
    yy, lh, cap, x = 46, 15.6, 9.2, 28
    for head, lines in SIDE_BLOCKS[:4]:
        if head:
            left.append(text(F_COND_B, head, x, yy, 0, SIDE_ACCENT, cap=cap + 0.4))
            yy += lh
        for s in lines:
            left.append(text(F_COND, s, x, yy, 0, SIDE_TEXT, cap=cap, maxwidth=250))
            yy += lh
        yy += lh * 0.35
    t.append(group(f"{prefix}-tarkib", "\n".join(left)))
    # o'ng qanot: ishlab chiqaruvchi + seriya
    right = []
    x, yy = 628, 46
    head, lines = SIDE_BLOCKS[4]
    if head.startswith("~"):
        right.append(text(F_COND, head[1:], x, yy, 0, SIDE_TEXT, cap=cap))
    else:
        right.append(text(F_COND_B, head, x, yy, 0, SIDE_ACCENT, cap=cap + 0.4))
    yy += lh
    for s in lines:
        f = F_COND_B if s.startswith("*") else F_COND
        right.append(text(f, s.lstrip("*"), x, yy, 0, SIDE_ACCENT if s.startswith("*") else SIDE_TEXT,
                          cap=cap, maxwidth=250))
        yy += lh
    yy += 10
    for lab in ["Batch No.:", "Mfg. Date:", "Exp. Date:", TH["lic"]]:
        right.append(text(F_COND_B, lab, x, yy + 14, 0, SIDE_ACCENT, cap=cap))
        right.append(f'<path d="M{x + 82},{n(yy + 16)} H{x + 240}" stroke="{SIDE_TEXT}" '
                     f'stroke-width="1" fill="none"/>')
        yy += 26
    t.append(group(f"{prefix}-ishlab-chiqaruvchi", "\n".join(right)))
    return a, {"fon": "\n".join(fon), "logo": logo, "matn": "\n".join(t)}


# ================================================================ SVG yozish
def svg_doc(w_mm, h_mm, vb, body, defs=(), title="", layers_note=""):
    vbx, vby, vbw, vbh = vb
    d = "\n".join(defs)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{n(w_mm)}mm" height="{n(h_mm)}mm" viewBox="{n(vbx)} {n(vby)} {n(vbw)} {n(vbh)}">\n'
            f'<title>{title}</title>\n'
            + (f'<desc>{layers_note}</desc>\n' if layers_note else "")
            + (f"<defs>\n{d}\n</defs>\n" if d else "")
            + body + "\n</svg>\n")


def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("yozildi:", path, f"{len(content) / 1024:.0f} KB")


def panel_file(path, title, a, layers, w_units, h_units, bleed_units=0, keys=("fon", "logo", "matn")):
    b = bleed_units
    body = []
    defs = list(a.defs)
    clip = None
    if b:
        clip = f"{a.p}-bleed-clip"
        defs.append(f'<clipPath id="{clip}"><rect x="{-b}" y="{-b}" width="{w_units + 2 * b}" '
                    f'height="{h_units + 2 * b}"/></clipPath>')
    names = {"fon": "FON", "logo": "LOGO", "matn": "MATN"}
    for k in keys:
        if k in layers:
            body.append(group(f"{names[k]}", layers[k]))
    inner = "\n".join(body)
    if clip:
        inner = f'<g clip-path="url(#{clip})">\n{inner}\n</g>'
    else:
        defs.append(f'<clipPath id="{a.p}-trim-clip"><rect x="0" y="0" width="{w_units}" '
                    f'height="{h_units}"/></clipPath>')
        inner = f'<g clip-path="url(#{a.p}-trim-clip)">\n{inner}\n</g>'
    write(path, svg_doc((w_units + 2 * b) * U, (h_units + 2 * b) * U,
                        (-b, -b, w_units + 2 * b, h_units + 2 * b), inner, defs, title))


def build_parts():
    # 1. Logo
    a = Art("lg")
    body = group("LOGO", logo_body(a))
    write("1-logo/monoos-logo.svg",
          svg_doc(62.4, 22.6, (-12, -14, 624, 226), body, a.defs, "MONOOS logo"))
    a = Art("lgw")
    body = (group("FON-OCHIRISH-MUMKIN",
                  f'<rect x="-30" y="-35" width="660" height="270" fill="{NAVY_DARK}"/>') + "\n" +
            group("LOGO-OQ", logo_body(a, color_text="#FFFFFF", swoosh="#FFFFFF")))
    write("1-logo/monoos-logo-oq.svg",
          svg_doc(66, 27, (-30, -35, 660, 270), body, a.defs, "MONOOS logo (to'q fonda, oq)"))

    # 2-3. Old panel: fon, matn, to'liq
    a, L = front_panel("of")
    panel_file("2-fon/old-panel-fon.svg", "Old panel foni (3 mm vylet bilan)", a, L, 600, 800, 30,
               keys=("fon",))
    a, L = front_panel("om")
    panel_file("3-matn/old-panel-matn-va-logo.svg", "Old panel matni va logo (fonsiz)", a, L, 600, 800,
               keys=("logo", "matn"))
    a, L = front_panel("ot")
    panel_file("4-panellar/1-old-panel.svg", "Old panel (to'liq)", a, L, 600, 800, 30)

    # yon panel
    a, L = side_info_panel("yt")
    panel_file("4-panellar/2-yon-panel-tarkib.svg", "Yon panel - tarkib, saqlash, ishlab chiqaruvchi",
               a, L, 360, 800)
    a, L = side_info_panel("ym")
    panel_file("3-matn/yon-panel-matn.svg", "Yon panel matni (fonsiz)", a, L, 360, 800, keys=("matn",))
    a, L = side_brand_panel("yb")
    panel_file("4-panellar/3-yon-panel-2-brend.svg", "Ikkinchi yon panel - brend", a, L, 360, 800, 30)
    a, L = side_brand_panel("yf")
    panel_file("2-fon/yon-panel-2-fon.svg", "Ikkinchi yon panel foni", a, L, 360, 800, 30, keys=("fon",))
    a, L = top_lid("qy")
    panel_file("4-panellar/4-yuqori-qopqoq.svg", "Yuqori qopqoq", a, L, 600, 360)
    a, L = bottom_lid("qp")
    panel_file("4-panellar/5-pastki-qopqoq.svg", "Pastki qopqoq (seriya/sana maydonlari)", a, L, 600, 360)

    # shtrix-kod
    bc = ean13(BARCODE, 0, 0, 3.3, 229, digit_font=F_COND)
    write("3-matn/shtrix-kod-ean13.svg",
          svg_doc(37.3, 28, (0, -8, 373, 280), group("SHTRIX-KOD", bc), (), f"EAN-13 {BARCODE}"))

    # flakon etiketkasi
    a, L = vial_label("ef")
    panel_file("5-flakon-etiketka/etiketka-fon.svg", "Flakon etiketkasi foni 90x40 mm", a, L,
               LABEL_W, LABEL_H, 30, keys=("fon",))
    a, L = vial_label("et")
    panel_file("5-flakon-etiketka/etiketka-toliq.svg", "Flakon etiketkasi 90x40 mm", a, L,
               LABEL_W, LABEL_H, 30)


# ================================================================ RAZVYORTKA
def build_dieline():
    M = 12  # mm hoshiya
    top = D + TUCK
    ox, oy = M, M + top            # orqa panelning chap-yuqori burchagi
    xs = [0, W, W + D, 2 * W + D, 2 * W + 2 * D, 2 * W + 2 * D + GLUE]
    tw = xs[-1] + 2 * M
    th = top + H + D + TUCK + 2 * M
    defs = []
    art = []

    def place(prefix_art, gid, layers, transform, clip_rect, keys=("fon", "logo", "matn")):
        a = prefix_art
        defs.extend(a.defs)
        cid = f"clip-{gid}"
        x, y, w, h = clip_rect
        defs.append(f'<clipPath id="{cid}"><rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"/></clipPath>')
        out = {}
        for k in keys:
            if k in layers:
                out[k] = (f'<g clip-path="url(#{cid})"><g id="{gid}-{k.upper()}" transform="{transform}">\n'
                          f'{layers[k]}\n</g></g>')
        return out

    B = BLEED
    pieces = []
    # orqa panel (oldi bilan bir xil dizayn) - chap va past cheti kesiladi -> vylet
    a, L = front_panel("orqa")
    pieces.append(place(a, "orqa-panel", L, f"translate({ox},{oy}) scale({U})",
                        (ox - B, oy, W + B, H + B)))
    a, L = side_info_panel("yon1")
    pieces.append(place(a, "yon-panel-1", L, f"translate({ox + xs[1]},{oy}) scale({U})",
                        (ox + xs[1], oy, D, H)))
    a, L = front_panel("old")
    pieces.append(place(a, "old-panel", L, f"translate({ox + xs[2]},{oy}) scale({U})",
                        (ox + xs[2], oy - B, W, H + B)))
    a, L = side_brand_panel("yon2")
    pieces.append(place(a, "yon-panel-2", L, f"translate({ox + xs[3]},{oy}) scale({U})",
                        (ox + xs[3], oy, D, H)))
    a, L = top_lid("qopqoq-yuqori")
    pieces.append(place(a, "qopqoq-yuqori", L, f"translate({ox + W},{oy}) rotate(180) scale({U})",
                        (ox, oy - D, W, D)))
    a, L = bottom_lid("qopqoq-pastki")
    pieces.append(place(a, "qopqoq-pastki", L, f"translate({ox + xs[2]},{oy + H}) scale({U})",
                        (ox + xs[2], oy + H, W, D)))

    layers_xml = []
    for key, name in [("fon", "FON"), ("logo", "LOGO"), ("matn", "MATN")]:
        body = "\n".join(p[key] for p in pieces if key in p)
        layers_xml.append(group(name, body))

    # --- kesish konturi
    x0, y0 = ox, oy
    r = 7      # tilcha burchak radiusi
    ins = 0.5  # tilcha ichkariga
    X = lambda v: x0 + v
    Y = lambda v: y0 + v
    s1a, s1b = xs[1], xs[2]
    s2a, s2b = xs[3], xs[4]
    g0, g1 = xs[4], xs[5]
    dh = DUST
    cut = [
        f"M{n(X(0))},{n(Y(0))}",
        f"V{n(Y(-D))}",
        f"H{n(X(ins))}",
        f"V{n(Y(-D - TUCK + r))}",
        f"A{r},{r} 0 0 1 {n(X(ins + r))},{n(Y(-D - TUCK))}",
        f"H{n(X(W - ins - r))}",
        f"A{r},{r} 0 0 1 {n(X(W - ins))},{n(Y(-D - TUCK + r))}",
        f"V{n(Y(-D))}",
        f"H{n(X(W))}",
        f"V{n(Y(-2))}",
        # yon panel 1 yuqori qanotcha
        f"L{n(X(s1a + 4))},{n(Y(-dh))}",
        f"H{n(X(s1b - 4))}",
        f"L{n(X(s1b))},{n(Y(-2))}",
        f"V{n(Y(0))}",
        f"H{n(X(s2a))}",
        f"V{n(Y(-2))}",
        f"L{n(X(s2a + 4))},{n(Y(-dh))}",
        f"H{n(X(s2b - 4))}",
        f"L{n(X(s2b))},{n(Y(-2))}",
        f"V{n(Y(0))}",
        # yelim qanoti
        f"L{n(X(g1))},{n(Y(5))}",
        f"V{n(Y(H - 5))}",
        f"L{n(X(g0))},{n(Y(H))}",
        # yon panel 2 pastki qanotcha
        f"V{n(Y(H + 2))}",
        f"L{n(X(s2b - 4))},{n(Y(H + dh))}",
        f"H{n(X(s2a + 4))}",
        f"L{n(X(s2a))},{n(Y(H + 2))}",
        # old panel pastki qopqog'i
        f"V{n(Y(H + D))}",
        f"H{n(X(s2a - ins))}",
        f"V{n(Y(H + D + TUCK - r))}",
        f"A{r},{r} 0 0 1 {n(X(s2a - ins - r))},{n(Y(H + D + TUCK))}",
        f"H{n(X(s1b + ins + r))}",
        f"A{r},{r} 0 0 1 {n(X(s1b + ins))},{n(Y(H + D + TUCK - r))}",
        f"V{n(Y(H + D))}",
        f"H{n(X(s1b))}",
        f"V{n(Y(H + 2))}",
        # yon panel 1 pastki qanotcha
        f"L{n(X(s1b - 4))},{n(Y(H + dh))}",
        f"H{n(X(s1a + 4))}",
        f"L{n(X(s1a))},{n(Y(H + 2))}",
        f"V{n(Y(H))}",
        f"H{n(X(0))}",
        "Z",
    ]
    cut_xml = (f'<path d="{" ".join(cut)}" fill="none" stroke="#E30613" stroke-width="0.25" '
               f'stroke-linejoin="round"/>')
    folds = [
        (X(xs[1]), Y(0), X(xs[1]), Y(H)), (X(xs[2]), Y(0), X(xs[2]), Y(H)),
        (X(xs[3]), Y(0), X(xs[3]), Y(H)), (X(xs[4]), Y(0), X(xs[4]), Y(H)),
        (X(0), Y(0), X(W), Y(0)), (X(ins), Y(-D), X(W - ins), Y(-D)),
        (X(s1a), Y(0), X(s1b), Y(0)), (X(s2a), Y(0), X(s2b), Y(0)),
        (X(s1a), Y(H), X(s1b), Y(H)), (X(s2a), Y(H), X(s2b), Y(H)),
        (X(s1b), Y(H), X(s2a), Y(H)), (X(s1b + ins), Y(H + D), X(s2a - ins), Y(H + D)),
    ]
    fold_xml = "\n".join(
        f'<line x1="{n(a)}" y1="{n(b)}" x2="{n(c)}" y2="{n(d)}" stroke="#00A0E3" '
        f'stroke-width="0.25" stroke-dasharray="2 1"/>' for a, b, c, d in folds)

    # tushuntirish yozuvlari (chop etilmaydi)
    nt = []
    lab = lambda s, x, y: text(F_REG, s, x, y, 0, "#6B6B6B", cap=2.1)
    nt.append(lab(f"Quti: {W} x {D} x {H} mm  |  Qizil - kesish, ko'k punktir - bukish  |  "
                  f"Vylet {BLEED} mm  |  Yelim qanoti {GLUE} mm", M, th - 4))
    nt.append(lab("ORQA", X(W / 2) - 4, Y(H) + 6.5))
    nt.append(lab("YELIM", X(g0) + 3, Y(H / 2)))
    note_xml = "\n".join(nt)

    body = "\n".join([
        f'<rect id="QOG-OZ" x="0" y="0" width="{n(tw)}" height="{n(th)}" fill="#FFFFFF"/>',
        *layers_xml,
        group("KESISH-CHIZIG-I", cut_xml),
        group("BUKISH-CHIZIQLARI", fold_xml),
        group("IZOHLAR-CHOP-ETILMAYDI", note_xml),
    ])
    write("6-razvyortka/quti-razvyortka.svg",
          svg_doc(tw, th, (0, 0, tw, th), body, defs,
                  f"Karobka razvyortkasi {W}x{D}x{H} mm",
                  "Qatlamlar: FON, LOGO, MATN, KESISH-CHIZIG-I, BUKISH-CHIZIQLARI, IZOHLAR"))
    return tw, th


if __name__ == "__main__":
    build_parts()
    print("razvyortka:", build_dieline())
