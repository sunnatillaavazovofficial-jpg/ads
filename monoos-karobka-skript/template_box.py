#!/usr/bin/env python3
"""Yangi MONOOS dizaynini bosmaxona shabloniga (artwork PDF) joylaydi.

Shablon o'zgarmaydi: kesish/bukish chiziqlari, yon panellar (matn, shtrix-kod, logotip),
qizil majburiy zonalar va yo'riqnoma sahifalari asl holicha qoladi. Faqat ikkala old panel
(inglizcha va ruscha), yuqori qopqoq va flakon etiketkasining old qismi yangi dizaynda chiziladi.

Ishlatish: python3 template_box.py <shriftlar> <chiqish_papkasi> <mahsulot> <shablon.pdf>
"""
import os
import subprocess
import sys
import tempfile

FONTS, OUTDIR, PRODUCT, TPL_PDF = sys.argv[1:5]
sys.argv = [sys.argv[0], FONTS, OUTDIR, PRODUCT]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_box as bb  # noqa: E402
from build_box import n, text, group  # noqa: E402
from tplkit import Template  # noqa: E402
from tpl_geom import CARTON, LABEL, page_rect  # noqa: E402

S01 = 72 / 254          # pt / 0.1 mm
BLEED_PT = 3 * 72 / 25.4

# ---------------------------------------------------------------- shablondagi matnlar
TXT = {
    "cefoperazone": {
        "en": dict(rx="Prescription only medicine", t1="CEFOPERAZONE", t2="SULBACTAM", bio="BIO",
                   sub=["Cefoperazone and Sulbactam"], dose="1000 mg + 500 mg",
                   use=["(For IM / IV use)"], form=["Powder for Injection"], extra=[],
                   vol="20 ml", count=None),
        "ru": dict(rx="Отпускается по рецепту", t1="Цефаперазон", t2="Сульбактам", bio="Био",
                   sub=["Цефоперазон и Сульбактам"], dose="1000 мг + 500 мг",
                   use=["(Для В/М и В/В введения)"], form=["Порошок для инъекций"], extra=[],
                   vol="20 мл", count=None),
        "lid": dict(t1="CEFOPERAZONE", t2="SULBACTAM", bio="BIO",
                    sub=["Cefoperazone and Sulbactam"], dose="1000 mg + 500 mg"),
        "label": dict(rx="Отпускается по рецепту", t1="Цефаперазон", t2="Сульбактам", bio="Био",
                      sub=["Cefoperazone Sulbactam"], dose="1000 мг + 500 мг",
                      use=["(Для В/М и В/В введения)"],
                      form=["Порошок для приготовления", "раствора для инъекций"], extra=[],
                      vol="20 мл", count=None),
    },
    "ampicillin": {
        "en": dict(rx="Prescription only Medicine", t1="AMPICILLIN", t2="SULBACTAM", bio="BIO",
                   sub=["AMPICILLIN AND SULBACTAM", "FOR INJECTION USP"], dose="1.5 gm",
                   use=["(For I.V/I.M only)"], form=["Powder for Injection"], extra=[],
                   vol=None, count="1 Vial"),
        "ru": dict(rx=None, t1="Ампициллин", t2="сульбактам", bio="Био",
                   sub=["АМПИЦИЛЛИН И СУЛЬБАКТАМ", "ДЛЯ ИНЪЕКЦИЙ ПО"], dose="1,5 г",
                   use=["(Только для вв/вм введения)"],
                   form=["Порошок для приготовления", "раствора для инъекции"],
                   extra=["Условия отпуска", "По рецепту врача"], vol=None, count="1 Флакон"),
        "lid": dict(t1="AMPICILLIN", t2="SULBACTAM", bio="BIO", sub=[], dose=None),
        "label": dict(rx=None, t1="AMPICILLIN", t2="SULBACTAM", bio="BIO",
                      sub=["АМПИЦИЛЛИН И СУЛЬБАКТАМ", "ДЛЯ ИНЪЕКЦИЙ ПО"], dose="1,5 г",
                      use=["(Только для вв/вм введения)"],
                      form=["Порошок для приготовления", "раствора для инъекции"], extra=[],
                      vol=None, count="1 Флакон"),
    },
}[PRODUCT]


def narrow_fit(W, H, knee):
    """600x800 to'lqinlarini W x H panelga moslash. knee - burilish (y) joyi."""
    k0, k1 = knee
    return bb.Fit(xs=[(-40, -40), (0, 0), (380, W * 0.663), (460, W * 0.829), (600, W), (640, W + 40)],
                  ys=[(-40, -40), (0, 0), (440, k0), (560, k1), (800, H), (840, H + 40)],
                  w=W, h=H, rs=W / 600 * 1.05)


def fit_width(font, s, cap, maxw, squeeze=1.0):
    nat = font.width(s, cap / font.cap)
    return min(nat * squeeze, maxw)


class Edge:
    """Old paneldagi eng chap to'lqin chizig'i (c0): matn unga tegmasligi uchun chegara."""

    def __init__(self, fit):
        segs = bb.spline(fit.pts(bb.WAVE_PTS["c0"]))
        self.pts = []
        for p0, p1, p2, p3 in segs:
            for i in range(41):
                u = i / 40
                w0, w1, w2, w3 = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3
                self.pts.append((w0 * p0[0] + w1 * p1[0] + w2 * p2[0] + w3 * p3[0],
                                 w0 * p0[1] + w1 * p1[1] + w2 * p2[1] + w3 * p3[1]))
        self.W = fit.w

    def right(self, y_top, y_bot, margin=14):
        xs = [x for x, y in self.pts if y_top - 4 <= y <= y_bot + 6]
        return min(min(xs) - margin if xs else self.W, self.W - 30)

    def bottom(self, x0, x1, margin=16):
        ys = [y for x, y in self.pts if x0 <= x <= x1]
        return min(ys) - margin


def line(font, s, x, y, cap, color, maxw, min_scale=0.86):
    """Bir qator matn: sig'masa avval kichraytiradi, keyin biroz siqadi."""
    nat = font.width(s, cap / font.cap)
    if nat > maxw:
        cap = max(cap * min_scale, cap * maxw / nat)
    return text(font, s, x, y, 0, color, cap=cap, maxwidth=maxw)


def front_text(a, W, H, t, fit, logo_w=150, sizes=None, scale=1.0, gap=1.0):
    """Tor old panel uchun matn va logo. Birliklar 0.1 mm. Qaytaradi: logo, matn, oxirgi y."""
    z = dict(rx=12.5, t1=36, t2=33, sub=16, dose=18, use=14.5, form=14.5)
    z.update(sizes or {})
    z = {kk: v * scale for kk, v in z.items()}
    edge = Edge(fit)
    L = 24
    out = []
    logo = group(f"{a.p}-logo", bb.logo_body(a), f' transform="translate({L},22) scale({n(logo_w / 600)})"')
    y = 22 + logo_w / 600 * 200 + 4

    def R(cap, yy, margin=14):
        return edge.right(yy - cap, yy, margin)

    if t["rx"]:
        y += (10 + z["rx"]) * gap
        out.append(line(bb.F_BODY, t["rx"], L, y, z["rx"], bb.TEXT, R(z["rx"], y) - L))
    y += (12 + z["t1"]) * gap
    out.append(group(f"{a.p}-nomi-1", text(bb.F_TITLE, t["t1"], L, y, 0, bb.TITLE1, cap=z["t1"],
                                           width=fit_width(bb.F_TITLE, t["t1"], z["t1"], R(z["t1"], y, 22) - L, 0.86),
                                           tracking=-0.005)))
    y += (12 + z["t2"]) * gap
    bh = z["t2"] + 6
    bw = bb.F_COND_B.width(t["bio"], (z["t2"] * 0.66) / bb.F_COND_B.cap) + 16
    t2w = fit_width(bb.F_TITLE, t["t2"], z["t2"], R(z["t2"], y, 22) - L - bw - 7, 0.9)
    out.append(group(f"{a.p}-nomi-2", text(bb.F_TITLE, t["t2"], L, y, 0, bb.TITLE2, cap=z["t2"],
                                           width=t2w, tracking=-0.005)))
    bx = L + t2w + 7
    out.append(group(f"{a.p}-bio", f'<rect x="{n(bx)}" y="{n(y - z["t2"] - 3)}" width="{n(bw)}" '
                     f'height="{n(bh)}" rx="5" fill="{bb.BADGE}"/>\n' +
                     text(bb.F_COND_B, t["bio"], bx + bw / 2, y, 0, "#FFFFFF", anchor="middle",
                          cap=z["t2"] * 0.66)))
    y += 8 * gap
    sub = []
    for s in t["sub"]:
        y += (z["sub"] + 9) * gap
        sub.append(line(bb.F_SUB, s, L, y, z["sub"], bb.SUBC, R(z["sub"], y) - L))
    out.append(group(f"{a.p}-xalqaro-nomi", "\n".join(sub)))
    if t.get("dose"):
        y += 12 * gap
        ph = z["dose"] + 16
        tw = bb.F_MED.width(t["dose"], z["dose"] / bb.F_MED.cap)
        pw = min(tw + 34, edge.right(y, y + ph, 10) - L)
        pill_g = a.lin("pill", L, 0, L + pw, 0, bb.TH["pill"])
        out.append(group(f"{a.p}-dozasi",
                         f'<rect x="{L}" y="{n(y)}" width="{n(pw)}" height="{n(ph)}" rx="7" fill="{pill_g}"/>\n' +
                         text(bb.F_MED, t["dose"], L + pw / 2, y + ph / 2 + z["dose"] / 2, 0, "#FFFFFF",
                              anchor="middle", cap=z["dose"], maxwidth=pw - 16)))
        y += ph
    body = []
    first = True
    for key in ("use", "form", "extra"):
        cap = z["use"] if key == "use" else z["form"]
        for s in t[key]:
            y += (cap + (14 if first else 8)) * gap
            first = False
            body.append(line(bb.F_BODY, s, L, y, cap, bb.TEXT, R(cap, y) - L))
        if t[key]:
            y += 4 * gap
    out.append(group(f"{a.p}-tavsif", "\n".join(body)))
    # pastki to'q lenta ichida: flakon ikonkasi + hajm / soni
    bot = [bb.vial_icon(L, H - 92, 52, sw=2.6)]
    if t.get("vol"):
        bot.append(f'<rect x="{L + 34}" y="{n(H - 82)}" width="96" height="40" rx="7" fill="#FFFFFF"/>')
        bot.append(text(bb.F_SEMI, t["vol"], L + 82, H - 53, 0, bb.MLC, anchor="middle", cap=19))
    if t.get("count"):
        bot.append(text(bb.F_MED, t["count"], L + 36, H - 52, 0, "#FFFFFF", cap=17))
    out.append(group(f"{a.p}-hajmi", "\n".join(bot)))
    return logo, "\n".join(out), y, edge.bottom(L, W * 0.57)


def front_text_auto(a, W, H, t, fit, **kw):
    """Matn blokini bo'sh joyga moslaydi: imkon qadar katta, to'lqinlarga tegmasdan."""
    best = None
    for scale in (1.16, 1.12, 1.08, 1.04, 1.0, 0.96, 0.92, 0.88, 0.84, 0.8, 0.76, 0.72, 0.68, 0.64, 0.6):
        trial = bb.Art(a.p + "-x")
        _, _, yend, ylim = front_text(trial, W, H, t, fit, scale=scale, **kw)
        if yend <= ylim:
            best = scale
            break
    best = best or 0.6
    gap = 1.0
    for g2 in (1.5, 1.4, 1.3, 1.2, 1.1, 1.0):
        trial = bb.Art(a.p + "-x")
        _, _, yend, ylim = front_text(trial, W, H, t, fit, scale=best, gap=g2, **kw)
        if yend <= ylim:
            gap = g2
            break
    logo, matn, _, _ = front_text(a, W, H, t, fit, scale=best, gap=gap, **kw)
    return logo, matn


def front_layers(prefix, W, H, t, fit, **kw):
    a = bb.Art(prefix)
    fon = bb.front_background(a, fit)
    logo, matn = front_text_auto(a, W, H, t, fit, **kw)
    return a, {"fon": fon, "logo": logo, "matn": matn}, None


def lid_layers(prefix, W, D, t):
    """Yuqori qopqoq (W x D, 0.1 mm). y=0 - old panelga ulanadigan buklama."""
    a = bb.Art(prefix)
    fon = [f'<rect x="-40" y="0" width="{W + 80}" height="{D}" fill="#FFFFFF"/>']
    main = a.lin("main", 0, D, W, 0, [(0, bb.NAVY_DARK), (0.5, "#173F96"), (1, "#1F74D0")])
    fon.append(f'<path fill="{main}" d="M-40,{D - 34} C{W * 0.3},{D - 36} {W * 0.7},{D - 52} {W + 40},{D - 92} '
               f'L{W + 40},{D} L-40,{D} Z"/>')
    fon.append(f'<path fill="{bb.G_DARK}" d="M-40,{D - 48} C{W * 0.3},{D - 50} {W * 0.7},{D - 66} {W + 40},{D - 106} '
               f'L{W + 40},{D - 99} C{W * 0.7},{D - 59} {W * 0.3},{D - 43} -40,{D - 41} Z"/>')
    fon.append(f'<path fill="{bb.G_LIME}" d="M-40,{D - 58} C{W * 0.3},{D - 60} {W * 0.7},{D - 76} {W + 40},{D - 116} '
               f'L{W + 40},{D - 111} C{W * 0.7},{D - 71} {W * 0.3},{D - 55} -40,{D - 53} Z"/>')
    for cx, cy, r, f in [(W - 50, 46, 20, "#DCEDFB"), (W - 22, 82, 15, "none"), (W - 82, 86, 13, "#E6F2FC")]:
        fon.append(f'<path d="{bb.hexagon(cx, cy, r)}" fill="{bb.C(f)}" stroke="{bb.C("#BBD9F3")}" '
                   f'stroke-width="1.6"/>')
    lw = 140
    logo = group(f"{prefix}-logo", bb.logo_body(a), f' transform="translate(24,22) scale({n(lw / 600)})"')
    m = []
    R = W - 40
    y = 22 + lw / 3 + 18 + 34
    m.append(text(bb.F_TITLE, t["t1"], 24, y, 0, bb.TITLE1, cap=34,
                  width=fit_width(bb.F_TITLE, t["t1"], 34, R - 24, 0.86)))
    y += 44
    bw = bb.F_COND_B.width(t["bio"], 21 / bb.F_COND_B.cap) + 16
    t2w = fit_width(bb.F_TITLE, t["t2"], 32, R - 24 - bw - 8, 0.9)
    m.append(text(bb.F_TITLE, t["t2"], 24, y, 0, bb.TITLE2, cap=32, width=t2w))
    m.append(f'<rect x="{n(24 + t2w + 7)}" y="{y - 35}" width="{n(bw)}" height="38" rx="5" fill="{bb.BADGE}"/>')
    m.append(text(bb.F_COND_B, t["bio"], 24 + t2w + 7 + bw / 2, y, 0, "#FFFFFF", anchor="middle", cap=21))
    for s in t["sub"]:
        y += 30
        m.append(text(bb.F_SUB, s, 24, y, 0, bb.SUBC, cap=15, maxwidth=R - 24))
    if t["dose"]:
        y += 30
        m.append(text(bb.F_MED, t["dose"], 24, y, 0, bb.SUBC, cap=16, maxwidth=R - 24))
    return a, {"fon": "\n".join(fon), "logo": logo, "matn": "\n".join(m)}


def place(a, layers, matrix, clip_page, tag):
    """Qatlamlarni sahifaga joylash: matrix - mahalliy (0.1 mm) -> sahifa (pt)."""
    cid = f"clip-{tag}"
    x0, y0, x1, y1 = clip_page
    defs = a.defs + [f'<clipPath id="{cid}"><rect x="{x0:.4f}" y="{y0:.4f}" width="{x1 - x0:.4f}" '
                     f'height="{y1 - y0:.4f}"/></clipPath>']
    m = " ".join(f"{v:.6f}" for v in matrix)
    out = {}
    for k, v in layers.items():
        out[k] = f'<g clip-path="url(#{cid})"><g id="{tag}-{k.upper()}" transform="matrix({m})">\n{v}\n</g></g>'
    return defs, out


def cmyk_legend(x, y, h):
    s = []
    cols = [("C", "#00AEEF"), ("M", "#EC008C"), ("Y", "#FFF200"), ("K", "#231F20")]
    cx = x
    for ch, col in cols:
        s.append(text(bb.F_REG, ch, cx, y, 0, col, cap=h))
        cx += bb.F_REG.width(ch, h / bb.F_REG.cap) + h * 0.12
    return group("CMYK-BELGI", "\n".join(s))


# ================================================================ 1-sahifa: karobka
def build_carton(svg_in, svg_out):
    g = CARTON[PRODUCT]
    xs, k, ty = g["xs"], g["k"], g["ty"]
    X0A, X1A, X0C, X1C = xs[1], xs[2], xs[3], xs[4]
    Y0, Y1 = g["y0"], g["y1"]
    W = round((X1A - X0A) / S01)
    H = round((Y1 - Y0) / S01)
    D = round((g["lid"] - Y1) / S01)
    t = Template(svg_in)
    assert abs(t.k - k) < 1e-6 and abs(t.ty - ty) < 1e-4, (t.k, t.ty)
    rects = [page_rect(g, X0A, Y0, X1A, Y1), page_rect(g, X0C, Y0, X1C, Y1), page_rect(g, X0A, Y1, X1A, g["lid"])]
    if g["legend"]:
        rects.append(page_rect(g, *g["legend"]))
    t.drop_in(rects)
    fit = narrow_fit(W, H, g["knee"])
    defs, layers = [], {"fon": [], "logo": [], "matn": []}

    def add(res):
        d, ls = res
        defs.extend(d)
        for kk, v in ls.items():
            layers[kk].append(v)

    sc = k * S01
    # A: inglizcha old panel (pastki cheti kesiladi -> vylet)
    a, L, _ = front_layers("old-en", W, H, TXT["en"], fit)
    add(place(a, L, (sc, 0, 0, sc, k * X0A, ty - k * Y1),
              page_rect(g, X0A, Y0 - BLEED_PT, X1A, Y1), "old-en"))
    # C: ruscha old panel (yuqori cheti kesiladi -> vylet)
    a, L, _ = front_layers("old-ru", W, H, TXT["ru"], fit)
    add(place(a, L, (sc, 0, 0, sc, k * X0C, ty - k * Y1),
              page_rect(g, X0C, Y0, X1C, Y1 + BLEED_PT), "old-ru"))
    # yuqori qopqoq (A ga ulangan), 180 gradus aylantirilgan, yon chetlari kesiladi -> vylet
    a, L = lid_layers("qopqoq", W, D, TXT["lid"])
    add(place(a, L, (-sc, 0, 0, -sc, k * X1A, ty - k * Y1),
              page_rect(g, X0A - BLEED_PT, Y1, X1A + BLEED_PT, g["lid"]), "qopqoq"))
    t.add_defs(defs)
    body = "\n".join(group(name, "\n".join(layers[key]))
                     for key, name in [("fon", "YANGI-DIZAYN-FON"), ("logo", "YANGI-DIZAYN-LOGO"),
                                       ("matn", "YANGI-DIZAYN-MATN")])
    t.insert_art(body)
    if g["legend"]:
        lx, ly = k * 40, ty - k * 100
        t.append_art(f'<g transform="translate({lx:.3f},{ly:.3f}) scale({k * S01:.6f})">'
                     f'{cmyk_legend(0, 0, 80)}</g>')
    t.move_strokes_to_top()
    t.write(svg_out)


# ================================================================ 2-sahifa: flakon etiketkasi
def build_label(svg_in, svg_out):
    g = LABEL[PRODUCT]
    k, ty = g["k"], g["ty"]
    t = Template(svg_in)
    assert abs(t.k - k) < 1e-6 and abs(t.ty - ty) < 1e-4, (t.k, t.ty)
    c0, c1 = g["cx"]
    lx0, ly0, lx1, ly1 = g["labels"][0]
    pw_pt = (lx1 - lx0) * (c1 - c0)          # dizayn qismi eni (haqiqiy o'lcham), pt
    ph_pt = ly1 - ly0
    W = 350                                  # virtual eni (karobka old paneli bilan bir xil)
    H = round(W * ph_pt / pw_pt)
    fit = narrow_fit(W, H, (H * 0.56, H * 0.76))
    rects = []
    for (x0, y0, x1, y1) in g["labels"]:
        w = x1 - x0
        rects.append((k * (x0 + w * c0), ty - k * y1, k * (x0 + w * c1), ty - k * y0))
    if g["legend"]:
        x0, y0, x1, y1 = g["legend"]
        rects.append((k * x0, ty - k * y1, k * x1, ty - k * y0))
    t.drop_in(rects)
    defs, layers = [], {"fon": [], "logo": [], "matn": []}
    for i, (x0, y0, x1, y1) in enumerate(g["labels"]):
        w = x1 - x0
        X0 = x0 + w * c0
        sc = k * (w * (c1 - c0)) / W                 # virtual birlik -> sahifa pt
        bleed = BLEED_PT * w / (lx1 - lx0)
        a, L, _ = front_layers(f"etiketka-{i + 1}", W, H, TXT["label"], fit)
        d, ls = place(a, L, (sc, 0, 0, sc, k * X0, ty - k * y1),
                      (k * X0, ty - k * (y1 + bleed), k * (x0 + w * c1), ty - k * (y0 - bleed)),
                      f"etiketka-{i + 1}")
        defs.extend(d)
        for kk, v in ls.items():
            layers[kk].append(v)
    t.add_defs(defs)
    t.insert_art("\n".join(group(name, "\n".join(layers[key]))
                           for key, name in [("fon", "YANGI-DIZAYN-FON"), ("logo", "YANGI-DIZAYN-LOGO"),
                                             ("matn", "YANGI-DIZAYN-MATN")]))
    if g["legend"]:
        t.append_art(f'<g transform="translate({k * 30:.3f},{ty - k * 280:.3f}) scale({k * S01:.6f})">'
                     f'{cmyk_legend(0, 0, 80)}</g>')
    t.move_strokes_to_top()
    t.write(svg_out)


if __name__ == "__main__":
    os.makedirs(OUTDIR, exist_ok=True)
    work = tempfile.mkdtemp()
    p1 = os.path.join(work, "p1.svg")
    subprocess.run(["pdftocairo", "-svg", "-f", "1", "-l", "1", TPL_PDF, p1], check=True)
    build_carton(p1, os.path.join(OUTDIR, "1-karobka.svg"))
    p2 = os.path.join(work, "p2.svg")
    subprocess.run(["pdftocairo", "-svg", "-f", "2", "-l", "2", TPL_PDF, p2], check=True)
    build_label(p2, os.path.join(OUTDIR, "2-etiketka.svg"))

    # yakuniy PDF: 1-2 sahifa yangi, 3-4 (yo'riqnoma) asl shablondan o'zgarishsiz
    import cairosvg
    from pypdf import PdfReader, PdfWriter
    for name in ("1-karobka", "2-etiketka"):
        cairosvg.svg2pdf(url=os.path.join(OUTDIR, name + ".svg"), write_to=os.path.join(work, name + ".pdf"))
        cairosvg.svg2png(url=os.path.join(OUTDIR, name + ".svg"), write_to=os.path.join(OUTDIR, name + ".png"),
                         scale=300 / 72, background_color="white")
    src = PdfReader(TPL_PDF)
    w = PdfWriter()
    for name in ("1-karobka", "2-etiketka"):
        w.add_page(PdfReader(os.path.join(work, name + ".pdf")).pages[0])
    for pg in src.pages[2:]:
        w.add_page(pg)
    final = os.path.join(OUTDIR, os.environ.get("ART_NAME", "artwork.pdf"))
    with open(final, "wb") as fh:
        w.write(fh)
    for i, (a, b) in enumerate(zip(PdfReader(final).pages, src.pages)):
        print("sahifa", i + 1, [round(float(v), 2) for v in a.mediabox[2:]],
              "asl:", [round(float(v), 2) for v in b.mediabox[2:]])
    print("ok", final)
