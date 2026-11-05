#!/usr/bin/env python3
"""BIG LIFE banner generator (CorelDRAW uchun SVG).

Har bir o'lcham uchun alohida SVG yaratadi. O'lchamlar santimetrda,
SVG ichida millimetrda (1 birlik = 1 mm) - CorelDRAW import qilganda
real o'lchamda ochiladi.

Ishga tushirish:  python3 generate.py
"""
import os

# (eni_cm, bo'yi_cm, nomi)
SIZES = [
    (750, 240, "750x240_kocha_1ta"),
    (600, 240, "600x240_kocha_3ta"),
    (400, 200, "400x200_kocha_2ta"),
    (400, 100, "400x100_proxod_2ta"),
    (450, 120, "450x120_proxod_4ta"),
    (520, 150, "520x150_naves"),
    (395, 150, "395x150_naves"),
    (675, 266, "675x266"),
    (675, 200, "675x200"),
    (160, 90, "asosiy_16x9"),
]

BROWN = "#4a2414"
BEIGE_LINE = "#cbb497"
PHONES = ["+998 95 092 55 50", "+998 94 411 11 11"]
ADDR1 = ["Toshkent, Abu Saxiy Center,", "1-qavat, C-22"]
ADDR2 = ["Abu Saxiy, 3-blok,", "5-qator, 2-do'kon"]

# ---------- Logo belgisi (170 x 117 birlik) ----------
MARK_W, MARK_H = 170, 117
MARK = (
    "M0,34 L50,28 C82,24 102,14 118,0 L170,0 C148,32 116,50 72,50 L0,50 Z "
    "M0,62 L92,62 C124,62 142,86 136,117 L100,117 C104,94 94,80 72,80 L8,80 Z"
)

# ---------- "BIG LIFE" harflari (balandligi 100) ----------
GLYPHS = {
    "B": (92, "M0,0 H66 C80,0 88,10 88,24 C88,36 83,44 76,48 C86,52 92,62 92,75 "
              "C92,91 82,100 66,100 H0 Z M22,18 V40 H60 C64,40 66,36 66,29 "
              "C66,22 64,18 60,18 Z M22,58 V82 H62 C67,82 70,78 70,70 "
              "C70,62 67,58 62,58 Z"),
    "I": (22, "M0,0 H22 V100 H0 Z"),
    "G": (92, "M20,0 H90 V20 H26 C23,20 22,21 22,24 V76 C22,79 23,80 26,80 H70 "
              "V64 H46 V46 H92 V80 C92,92 84,100 72,100 H20 C8,100 0,92 0,80 "
              "V20 C0,8 8,0 20,0 Z"),
    "L": (80, "M0,0 H22 V80 H80 V100 H0 Z"),
    "F": (82, "M0,0 H82 V20 H22 V40 H72 V60 H22 V100 H0 Z"),
    "E": (84, "M0,0 H84 V20 H22 V40 H74 V60 H22 V80 H84 V100 H0 Z"),
}
GAP, SPACE, XSCALE = 12, 44, 1.12


def wordmark(text):
    """'BIG LIFE' ni path sifatida qaytaradi (shrift kerak emas)."""
    parts, x = [], 0.0
    for ch in text:
        if ch == " ":
            x += SPACE - GAP
            continue
        w, d = GLYPHS[ch]
        parts.append(f'<path transform="translate({x:.2f},0) scale({XSCALE},1)" d="{d}"/>')
        x += w * XSCALE + GAP
    return "\n".join(parts), x - GAP


PHONE_ICON = ("M-4.6,-7.2 C-5.4,-8 -6.6,-8 -7.3,-7.3 L-8.6,-6 C-10,-4.6 -9.4,-0.6 -4.9,3.9 "
              "C-0.4,8.4 3.6,9 5,7.6 L6.3,6.3 C7,5.6 7,4.4 6.2,3.6 L4.4,1.8 "
              "C3.6,1 2.4,1.1 1.7,1.8 L0.9,2.6 C-0.6,1.9 -2.6,-0.1 -3.3,-1.6 "
              "L-2.5,-2.4 C-1.8,-3.1 -1.8,-4.3 -2.6,-5.1 Z")
PIN_ICON = ("M0,9 C-4,4 -7,0.5 -7,-3 C-7,-7 -3.9,-10 0,-10 C3.9,-10 7,-7 7,-3 "
            "C7,0.5 4,4 0,9 Z M0,-6 C-1.7,-6 -3,-4.7 -3,-3 C-3,-1.3 -1.7,0 0,0 "
            "C1.7,0 3,-1.3 3,-3 C3,-4.7 1.7,-6 0,-6 Z")


def build(wcm, hcm, name):
    W, H = wcm * 10.0, hcm * 10.0  # mm
    o = []
    a = o.append
    a(f'<?xml version="1.0" encoding="UTF-8"?>')
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:g}mm" height="{H:g}mm" '
      f'viewBox="0 0 {W:g} {H:g}">')
    a(f'<title>BIG LIFE banner {wcm}x{hcm} sm</title>')
    a('<defs>'
      '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
      '<stop offset="0" stop-color="#f3ebe0"/><stop offset="1" stop-color="#e7d9c6"/>'
      '</linearGradient>'
      '<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0" stop-color="#e9dcca"/><stop offset="1" stop-color="#dccbb4"/>'
      '</linearGradient>'
      '</defs>')

    # 1. Fon
    a('<g id="FON">')
    a(f'<rect width="{W:g}" height="{H:g}" fill="url(#bg)"/>')
    # yorug'lik/soya chiziqlari
    for k, (x0, op) in enumerate([(0.18, 0.35), (0.42, 0.25), (0.70, 0.30)]):
        x = W * x0
        a(f'<path d="M{x:.1f},0 L{x+0.28*H:.1f},0 L{x+0.28*H-0.55*H:.1f},{H:g} '
          f'L{x-0.55*H:.1f},{H:g} Z" fill="#ffffff" opacity="{op}"/>')
    # devor (pastki zinapoya)
    a(f'<path d="M0,{0.60*H:.1f} L{0.30*W:.1f},{0.66*H:.1f} L{0.62*W:.1f},{0.72*H:.1f} '
      f'L{W:g},{0.70*H:.1f} L{W:g},{H:g} L0,{H:g} Z" fill="url(#wall)"/>')
    a(f'<path d="M0,{0.60*H:.1f} L{0.30*W:.1f},{0.66*H:.1f} L{0.62*W:.1f},{0.72*H:.1f} '
      f'L{W:g},{0.70*H:.1f}" fill="none" stroke="#f7f1e8" stroke-width="{0.006*H:.2f}"/>')
    a('</g>')

    # odam joylari
    slot_w = min(0.29 * W, 0.56 * H)
    margin = 0.015 * W
    left = (margin, 0.0, slot_w, H)
    right = (W - margin - slot_w, 0.0, slot_w, H)
    cx = W / 2

    # Logo o'lchamlari
    wm, wm_w = wordmark("BIG LIFE")
    center_w = right[0] - (left[0] + slot_w)
    logo_w = min(1.1 * H, 0.75 * center_w)
    s = logo_w / wm_w                  # wordmark masshtabi (100 birlik balandlik)
    wm_h = 100 * s
    mark_s = (0.30 * logo_w) / MARK_W
    mark_h = MARK_H * mark_s
    tag_fs = 0.30 * wm_h
    block_h = mark_h + 0.25 * wm_h + wm_h + 0.45 * wm_h + tag_fs
    pw = W - 0.056 * W
    fs = min(0.042 * H, (pw / 3) / 25)
    ph = fs * 4.2
    contact_top = H - ph - 0.045 * H
    y_top = max(0.06 * H, (contact_top - block_h) / 2 - 0.02 * H)
    mark_x = cx - MARK_W * mark_s / 2 + 0.05 * logo_w
    wy = y_top + mark_h + 0.25 * wm_h
    ty = wy + wm_h + 0.45 * wm_h + tag_fs * 0.8

    # 2. Dekor chiziqlar (logo belgisidan ilhomlangan)
    sw = 0.006 * H
    x0 = cx - 0.30 * logo_w
    x1 = max(right[0] + 0.02 * H, cx + 0.62 * logo_w)
    yA = ty + 0.06 * H
    yB = yA + 0.055 * H
    top = 0.18 * H
    r = (yB - yA) / 2
    a(f'<g id="DEKOR_CHIZIQLAR" fill="none" stroke="{BEIGE_LINE}" stroke-width="{sw:.2f}" '
      f'stroke-linecap="round">')
    a(f'<path d="M{W:g},{top:.1f} L{x1+0.2*H:.1f},{top:.1f} '
      f'C{x1+0.08*H:.1f},{top:.1f} {x1+0.05*H:.1f},{yA-0.18*H:.1f} {x1-0.02*H:.1f},{yA-0.09*H:.1f} '
      f'C{x1-0.08*H:.1f},{yA-0.02*H:.1f} {x1-0.2*H:.1f},{yA:.1f} {x1-0.3*H:.1f},{yA:.1f} '
      f'L{x0+r:.1f},{yA:.1f} A{r:.1f},{r:.1f} 0 0 0 {x0+r:.1f},{yB:.1f} '
      f'L{x1-0.25*H:.1f},{yB:.1f} '
      f'C{x1-0.12*H:.1f},{yB:.1f} {x1-0.06*H:.1f},{yB+0.04*H:.1f} {x1-0.02*H:.1f},{min(yB+0.13*H, contact_top):.1f}"/>')
    a(f'<path d="M{W:g},{top+0.06*H:.1f} L{x1+0.25*H:.1f},{top+0.06*H:.1f} '
      f'C{x1+0.15*H:.1f},{top+0.06*H:.1f} {x1+0.12*H:.1f},{yA-0.16*H:.1f} {x1+0.05*H:.1f},{yA-0.07*H:.1f}"/>')
    a('</g>')

    # 3. Odam rasmlari uchun joy (PowerClip)
    a('<g id="ODAM_RASMLARI">')
    for nm, (x, y, w, h) in (("CHAP_MODEL", left), ("ONG_MODEL", right)):
        lfs = 0.035 * H
        a(f'<g id="{nm}">')
        a(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#d9c8b2" '
          f'fill-opacity="0.35" stroke="#a88d6c" stroke-width="{0.003*H:.2f}" '
          f'stroke-dasharray="{0.02*H:.1f},{0.012*H:.1f}"/>')
        a(f'<text x="{x+w/2:.1f}" y="{0.42*H:.1f}" text-anchor="middle" '
          f'font-family="Arial" font-size="{lfs:.1f}" fill="#a88d6c">MODEL RASMI</text>')
        a(f'<text x="{x+w/2:.1f}" y="{0.42*H+lfs*1.3:.1f}" text-anchor="middle" '
          f'font-family="Arial" font-size="{lfs*0.7:.1f}" fill="#a88d6c">(PowerClip ichiga)</text>')
        a('</g>')
    a('</g>')

    # 4. Logo
    a(f'<g id="LOGO" fill="{BROWN}">')
    a(f'<path id="LOGO_BELGI" transform="translate({mark_x:.2f},{y_top:.2f}) scale({mark_s:.4f})" d="{MARK}"/>')
    a(f'<g id="BIG_LIFE" transform="translate({cx-logo_w/2:.2f},{wy:.2f}) scale({s:.4f})">{wm}</g>')
    ls = max(0.0, (logo_w - 14 * 0.66 * tag_fs) / 13)
    a(f'<text id="ALWAYS_FORWARD" x="{cx+ls/2:.1f}" y="{ty:.1f}" text-anchor="middle" '
      f'font-family="Arial" font-size="{tag_fs:.1f}" letter-spacing="{ls:.1f}">ALWAYS FORWARD</text>')
    a('</g>')

    # 5. Kontakt paneli
    px = 0.028 * W
    py = contact_top
    a('<g id="KONTAKT_PANEL">')
    a(f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" rx="{ph*0.22:.1f}" '
      f'fill="#f5efe6" fill-opacity="0.93"/>')
    col_w = pw / 3
    icon_r = fs * 1.15
    cols = [(PHONE_ICON, PHONES, "bold"), (PIN_ICON, ADDR1, "normal"), (PIN_ICON, ADDR2, "normal")]
    for i, (icon, lines, weight) in enumerate(cols):
        cx0 = px + col_w * i
        # matn kengligini taxminan hisoblab, ikonka+matnni markazlaymiz
        tw = max(len(t) for t in lines) * fs * 0.54
        gw = icon_r * 2 + 0.6 * icon_r + tw
        ix = cx0 + (col_w - gw) / 2 + icon_r
        iy = py + ph / 2
        a(f'<circle cx="{ix:.1f}" cy="{iy:.1f}" r="{icon_r:.1f}" fill="{BROWN}"/>')
        a(f'<path transform="translate({ix:.1f},{iy:.1f}) scale({icon_r/14:.4f})" '
          f'd="{icon}" fill="#ffffff" fill-rule="evenodd"/>')
        tx = ix + icon_r * 1.6
        for j, t in enumerate(lines):
            yy = iy - fs * 0.25 + j * fs * 1.25
            a(f'<text x="{tx:.1f}" y="{yy:.1f}" font-family="Arial" font-weight="{weight}" '
              f'font-size="{fs:.1f}" fill="{BROWN}">{t}</text>')
        if i:
            a(f'<line x1="{cx0:.1f}" y1="{py+ph*0.2:.1f}" x2="{cx0:.1f}" y2="{py+ph*0.8:.1f}" '
              f'stroke="#b89a78" stroke-width="{0.003*H:.2f}"/>')
    a('</g>')
    a('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "svg")
    os.makedirs(out, exist_ok=True)
    for w, h, n in SIZES:
        path = os.path.join(out, f"big-life_{n}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build(w, h, n))
        print(path)
