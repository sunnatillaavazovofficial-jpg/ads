"""
AI Yordamchi — ekranda turadigan, ChatGPT (OpenAI API) asosidagi yordamchi.

Matn funksiyalari (Sozlamalarda yoqib/o'chirsa bo'ladi):
  1. Tarjima                 (Ctrl+1)
  2. Grammatikani to'g'rilash(Ctrl+2)
  3. Yangi alifbo (Ö Ğ Ş Ç)  (Ctrl+3)
  4. Kirill                  (Ctrl+4)
  5. Inglizcha qidiruv       (Ctrl+5)

Skrinshot va rasm:
  - PrintScreen yoki Win+Shift+S — oddiy skrinshot: nusxalanadi, tanlangan papkaga saqlanadi
    va "Sifatini oshiraymi?" deb so'raladi (2x kattalashtirish + tiniqlashtirish).
  - AI rasm — skrinshot ustiga chizib/yozib, shablon yoki ko'rsatma bilan real rasmga aylantirish.

Ochilganda bir marta ko'rinadi, keyin ekran chetiga kirib shaffof chiziq bo'lib turadi.
Taskbarda ko'rinmaydi (trey ikonkasi bor), kompyuter yonganda o'zi ishga tushadi.

by Sunnatilla Designer — https://sunnatilla-designer.uz/
"""

import base64
import datetime
import json
import math
import os
import re
import sys
import time
import urllib.parse

import requests
from PySide6.QtCore import (QAbstractNativeEventFilter, QBuffer, QByteArray,
                            QEasingCurve, QEvent, QIODevice,
                            QParallelAnimationGroup, QPoint, QPointF,
                            QPropertyAnimation, QRect, QRectF, QSize,
                            QStandardPaths, Qt, QThread, QTimer, QUrl, Signal)
from PySide6.QtGui import (QColor, QCursor, QDesktopServices, QFont,
                           QGuiApplication, QIcon, QImage, QKeySequence,
                           QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF, QShortcut)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox,
                               QColorDialog, QComboBox, QDialog, QFileDialog,
                               QFrame, QGraphicsDropShadowEffect, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPlainTextEdit, QProgressBar, QPushButton,
                               QScrollArea, QSizeGrip, QSlider,
                               QSystemTrayIcon, QToolButton, QVBoxLayout,
                               QWidget)

APP_NAME = "AI Yordamchi"
API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"
AUTHOR = "Sunnatilla Designer"
AUTHOR_URL = "https://sunnatilla-designer.uz/"

# ---------------------------------------------------------------------------
# Ranglar
# ---------------------------------------------------------------------------
C_BG = "#FFFFFF"
C_BORDER = "#E6E8EE"
C_ICON = "#16181D"
C_ICON_ACTIVE = "#000000"
C_HOVER = "#EEF0F5"
C_ACCENT = "#111827"
C_TEXT = "#111827"
C_MUTED = "#8A8FA3"

SCALES = {"Kichik": 0.8, "O'rta": 1.0, "Katta": 1.2, "Juda katta": 1.4}

# Asosiy rang (chet chizig'i va tugmalar). Birinchisi — asl (eski) rang.
COLORS = [("Asl rang", C_ACCENT), ("Ko'k", "#2563EB"), ("Binafsha", "#7C3AED"),
          ("Yashil", "#16A34A"), ("Qizil", "#DC2626"), ("Apelsin", "#EA580C"),
          ("Pushti", "#DB2777")]


def accent_text(color: str) -> str:
    """Rang ustidagi yozuv uchun oq yoki qora."""
    c = QColor(color)
    lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
    return "#111827" if lum > 170 else "#FFFFFF"


SNIP_KEY = r"Control Panel\Keyboard"
SNIP_VALUE = "PrintScreenKeyForSnippingEnabled"


def windows_snip_key(cfg: dict, block: bool) -> None:
    """Windows'ning o'z skrinshot vositasini (Snipping Tool) PrintScreen tugmasidan uzish
    yoki avvalgi holatiga qaytarish. Faqat joriy foydalanuvchi uchun, admin kerak emas."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SNIP_KEY) as k:
            try:
                cur = winreg.QueryValueEx(k, SNIP_VALUE)[0]
            except FileNotFoundError:
                cur = None
            if block:
                if cur != 0:
                    cfg["snip_prev"] = cur          # avvalgi qiymatni eslab qolamiz
                    save_config(cfg)
                winreg.SetValueEx(k, SNIP_VALUE, 0, winreg.REG_DWORD, 0)
            elif "snip_prev" in cfg:
                prev = cfg.pop("snip_prev")
                save_config(cfg)
                if prev is None:
                    try:
                        winreg.DeleteValue(k, SNIP_VALUE)
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(k, SNIP_VALUE, 0, winreg.REG_DWORD, int(prev))
    except Exception:
        pass


def set_autostart(on: bool) -> None:
    """Windows yonganda dasturni avtomatik ishga tushirish."""
    if sys.platform != "win32":
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                         winreg.KEY_SET_VALUE)
    try:
        if on:
            if getattr(sys, "frozen", False):
                cmd = f'"{sys.executable}" --autostart'
            else:
                cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}" --autostart'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)

# ---------------------------------------------------------------------------
# Ikonkalar — qalin, to'q uslubda (lupa rasmidagidek)
# {c} — ikonka rangi, {bg} — fon rangi
# ---------------------------------------------------------------------------
ICONS = {
    # Tarjima (to'q shakl)
    "translate": '<path fill="{c}" stroke="{c}" stroke-width="0.7" stroke-linejoin="round" '
                 'd="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99'
                 'h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 '
                 '2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 '
                 '22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>',
    # Grammatika: "A" va belgi (to'q shakl)
    "grammar": '<path fill="{c}" stroke="{c}" stroke-width="0.8" stroke-linejoin="round" '
               'd="M12.45 16h2.09L9.43 3H7.57L2.46 16h2.09l1.12-3h5.64l1.14 3zm-6.02-5L8.5 5.48 '
               '10.57 11H6.43zm15.16.59l-8.09 8.09L9.83 16l-1.41 1.41 5.09 5.09L23 13l-1.41-1.41z"/>',
    "newalpha": '<rect x="1" y="3.5" width="22" height="17" rx="5" fill="{c}" stroke="none"/>'
                '<text x="12" y="16.7" font-size="11.5" font-weight="900" text-anchor="middle" '
                'font-family="Arial" fill="{bg}" stroke="none">Öz</text>',
    "cyrillic": '<rect x="1" y="3.5" width="22" height="17" rx="5" fill="{c}" stroke="none"/>'
                '<text x="12" y="16.7" font-size="11.5" font-weight="900" text-anchor="middle" '
                'font-family="Arial" fill="{bg}" stroke="none">Ўз</text>',
    # Lupa — siz yuborgan rasmdagidek
    "search": '<circle cx="9.8" cy="9.8" r="7" stroke-width="3.3"/>'
              '<path d="M15.6 15.6 20.6 20.6" stroke-width="5"/>'
              '<path d="M6.3 9.6a3.5 3.5 0 0 1 3.3-3.3" stroke-width="2" stroke-linecap="butt"/>',
    "pin": '<path d="M12 16.5v5.5" stroke-width="3"/>'
           '<path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 '
           '1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 '
           '0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" stroke-width="2.6"/>',
    "pin_on": '<path d="M12 16.5v5.5" stroke-width="3"/>'
              '<path fill="{c}" d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 '
              '0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 '
              '0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" stroke-width="2.6"/>',
    "folder": '<path fill="{c}" d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 '
              '3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" stroke-width="2"/>',
    # Sozlamalar: to'q tishli g'ildirak
    "settings": '<path fill="{c}" stroke-width="1.6" d="M19.4 15a1.65 1.65 0 0 0 .33 '
                '1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 '
                '0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 '
                '0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 '
                '1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 '
                '0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 '
                '1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 '
                '1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 '
                '1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
                '<circle cx="12" cy="12" r="3.2" fill="{bg}" stroke="none"/>',
    "close": '<path d="M18 6 6 18" stroke-width="3.6"/><path d="m6 6 12 12" stroke-width="3.6"/>',
    "grip": '<circle cx="8" cy="5" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="5" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="8" cy="12" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="12" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="8" cy="19" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="19" r="2" fill="{c}" stroke="none"/>',
    "copy": '<path d="M4.5 15.5c-1.4 0-2.5-1.1-2.5-2.5V4.5C2 3.1 3.1 2 4.5 2H13c1.4 0 2.5 1.1 2.5 2.5"'
            ' stroke-width="2.8"/>'
            '<rect width="14" height="14" x="8" y="8" rx="2.6" fill="{c}" stroke-width="2"/>',
    "paste": '<path d="M16 4h1.5A2.5 2.5 0 0 1 20 6.5v13a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 '
             '19.5v-13A2.5 2.5 0 0 1 6.5 4H8" stroke-width="2.8"/>'
             '<rect width="9" height="5" x="7.5" y="1.5" rx="1.5" fill="{c}" stroke-width="1.6"/>',
    "send": '<path fill="{c}" stroke-width="2" d="M21.5 2.5 2.8 9.4l7.6 4.2 4.2 7.6z"/>'
            '<path d="M21.5 2.5 10.4 13.6" stroke="{bg}" stroke-width="1.8"/>',
    "trash": '<path d="M2.8 6h18.4" stroke-width="3"/>'
             '<path d="M8 6V4.2C8 3 9 2 10.2 2h3.6C15 2 16 3 16 4.2V6" stroke-width="2.6"/>'
             '<path fill="{c}" stroke-width="1.6" d="M5 8h14l-1 12.2A2 2 0 0 1 16 22H8a2 2 0 0 '
             '1-2-1.8z"/>',
    "globe": '<circle cx="12" cy="12" r="9.6" stroke-width="2.8"/><path d="M2.6 12h18.8" '
             'stroke-width="2.4"/><path d="M12 2.4a15 15 0 0 1 3.8 9.6 15 15 0 0 1-3.8 9.6 15 15 '
             '0 0 1-3.8-9.6A15 15 0 0 1 12 2.4z" stroke-width="2.4"/>',
    "logo": '<path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9z" '
            'fill="{c}"/><path d="M19 15l.8 1.9 1.9.8-1.9.8L19 20.4l-.8-1.9-1.9-.8 1.9-.8z" '
            'fill="{c}"/>',
    "camera": '<path d="M3 8V5.5A2.5 2.5 0 0 1 5.5 3H8M16 3h2.5A2.5 2.5 0 0 1 21 5.5V8M21 16v2.5'
              'a2.5 2.5 0 0 1-2.5 2.5H16M8 21H5.5A2.5 2.5 0 0 1 3 18.5V16" stroke-width="2.9"/>'
              '<circle cx="12" cy="12" r="3.8" fill="{c}" stroke="none"/>',
    "image": '<rect x="2.5" y="3.5" width="19" height="17" rx="3" stroke-width="2.7"/>'
             '<circle cx="8.6" cy="9" r="2.1" fill="{c}" stroke="none"/>'
             '<path d="M4.2 19.3 9.6 13.2l3.6 4 2.6-2.7 4.4 4.8z" fill="{c}" stroke="none"/>',
    "pen": '<path fill="{c}" stroke-width="1.4" d="M16.5 3.2a2.4 2.4 0 0 1 3.4 0l.9.9a2.4 2.4 0 0 '
           '1 0 3.4L9 19.3l-5 1.4 1.4-5z"/>',
    "marker": '<path fill="{c}" stroke-width="1.4" d="m9 11 6.5-6.5a2.1 2.1 0 0 1 3 0l1 1a2.1 2.1 0 '
              '0 1 0 3L13 15z"/><path d="m9 11-2.6 2.6 4 4L13 15" stroke-width="2.4"/>'
              '<path d="M6.4 17.6 4 20h5" stroke-width="2.4"/>',
    "arrow": '<path d="M5 19 18 6" stroke-width="3.2"/><path d="M9 5.5h9.5V15" stroke-width="3.2"/>',
    "rect": '<rect x="3.5" y="5" width="17" height="14" rx="2.5" stroke-width="3"/>',
    "ellipse": '<ellipse cx="12" cy="12" rx="9" ry="7.5" stroke-width="3"/>',
    "text": '<path d="M5 7V4.5h14V7M12 4.5v15M8.8 19.5h6.4" stroke-width="3.2"/>',
    "undo": '<path d="M9 14 4 9l5-5" stroke-width="3"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" '
            'stroke-width="3"/>',
    "redo": '<path d="m15 14 5-5-5-5" stroke-width="3"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13" '
            'stroke-width="3"/>',
    "sparkle": '<path d="M11 2.5l2.1 5.6 5.6 2.1-5.6 2.1L11 17.9l-2.1-5.6-5.6-2.1 5.6-2.1z" '
               'fill="{c}" stroke-width="1.2"/><path d="M19 14.5l.9 2.3 2.3.9-2.3.9-.9 2.3-.9-2.3'
               '-2.3-.9 2.3-.9z" fill="{c}" stroke-width="1"/>',
    "save": '<path d="M12 3v11.5" stroke-width="3"/><path d="m7 10 5 5 5-5" stroke-width="3"/>'
            '<path d="M4 17v2.5A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5V17" stroke-width="3"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" stroke-width="2.7"/>'
           '<circle cx="12" cy="12" r="3.3" fill="{c}" stroke="none"/>',
    "dot1": '<circle cx="12" cy="12" r="2.4" fill="{c}" stroke="none"/>',
    "dot2": '<circle cx="12" cy="12" r="4.2" fill="{c}" stroke="none"/>',
    "dot3": '<circle cx="12" cy="12" r="6.4" fill="{c}" stroke="none"/>',
}


def svg_pixmap(name: str, color: str = C_ICON, size: int = 22, stroke: float = 2.5,
               bg: str = C_BG) -> QPixmap:
    body = ICONS[name].replace("{c}", color).replace("{bg}", bg)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
           f'stroke-linejoin="round">{body}</svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    k = 3
    pm = QPixmap(size * k, size * k)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    renderer.render(p)
    p.end()
    pm.setDevicePixelRatio(k)
    return pm


def svg_icon(name, color=C_ICON, size=22, stroke=2.5, bg=C_BG) -> QIcon:
    return QIcon(svg_pixmap(name, color, size, stroke, bg))


def app_icon(size: int = 256) -> QPixmap:
    """Dastur ikonkasi: gradientli kvadrat ichida uchqun."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#6366F1"))
    g.setColorAt(1, QColor("#8B5CF6"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
    body = ICONS["logo"].replace("{c}", "#FFFFFF")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="#FFFFFF" stroke-width="1" stroke-linejoin="round">{body}</svg>')
    m = size * 0.16
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(m, m, size - 2 * m, size - 2 * m))
    p.end()
    return pm


# ---------------------------------------------------------------------------
# Yangi o'zbek lotin alifbosi: Oʻ→Ö, Gʻ→Ğ, Sh→Ş, Ch→Ç (ng o'zgarmaydi)
# ---------------------------------------------------------------------------
_APOS = "ʻ‘'`’"
_WORD = re.compile(r"[A-Za-zÖöĞğŞşÇç" + _APOS + r"]+")
_FOREIGN = re.compile(r"[wW]|[cC](?![hH])|[tTpP][hH]")


def to_new_alphabet(text: str) -> str:
    """Eski lotin yozuvidagi qolgan harflarni yangi alifboga o'giradi (kafolat uchun)."""
    def word(m):
        w = m.group(0)
        w = re.sub(r"([OoGg])[" + _APOS + "]",
                   lambda x: {"O": "Ö", "o": "ö", "G": "Ğ", "g": "ğ"}[x.group(1)], w)
        if not _FOREIGN.search(w):  # inglizcha so'zlarga tegmaymiz
            w = re.sub(r"S[Hh]", "Ş", w).replace("sh", "ş")
            w = re.sub(r"C[Hh]", "Ç", w).replace("ch", "ç")
        return w

    out = []
    for token in re.split(r"(\s+)", text):
        if "://" in token or "@" in token or token.startswith("www."):
            out.append(token)
        else:
            out.append(_WORD.sub(word, token))
    return "".join(out)


# ---------------------------------------------------------------------------
# Funksiyalar va promptlar
# ---------------------------------------------------------------------------
NEW_ALPHA_RULES = (
    "The NEW Uzbek Latin alphabet (2026 law) has 28 letters: A B D E F G H I J K L M N O P Q R "
    "S T U V X Y Z Ö Ğ Ş Ç plus the apostrophe ’ (tutuq belgisi). Mapping from the old Latin "
    "alphabet: oʻ→ö, gʻ→ğ, sh→ş, ch→ç (capitals Ö, Ğ, Ş, Ç). 'ng' is written as n+g. "
    "From Cyrillic: ў→ö, ғ→ğ, ш→ş, ч→ç, қ→q, ҳ→h, х→x, ъ→’, ц→s/ts, "
    "е→ye at word start / after vowels, ё→yo, ю→yu, я→ya."
)

LANGS = {
    "O'zbekcha (yangi alifbo)": "Uzbek written in the NEW Uzbek Latin alphabet. " + NEW_ALPHA_RULES,
    "O'zbekcha (lotin)": "Uzbek, written in the current Uzbek Latin alphabet (oʻ, gʻ, sh, ch, ’)",
    "Ўзбекча (кирилл)": "Uzbek, written in the Uzbek Cyrillic alphabet (ў, қ, ғ, ҳ)",
    "English": "English",
    "Русский": "Russian",
}

MODES = [
    {
        "key": "translate", "icon": "translate", "title": "Tarjima", "shortcut": "1",
        "placeholder": "Tarjima qilinadigan matnni yozing yoki qo'ying…",
        "prompt": "You are a professional translator. Translate the user's text into {lang}. "
                  "Preserve the meaning, tone and formatting. If the text is already in the "
                  "target language, translate it into English instead. "
                  "Output ONLY the translation, nothing else.",
    },
    {
        "key": "grammar", "icon": "grammar", "title": "Grammatikani to'g'rilash", "shortcut": "2",
        "placeholder": "Xatoli matnni yozing — to'g'rilab, ma'noli qilib beraman…",
        "prompt": "You are an expert editor. Find and fix ALL grammar, spelling, punctuation and "
                  "word-choice errors in the user's text and rewrite it so it reads clearly, "
                  "naturally and meaningfully. Keep the ORIGINAL language, alphabet and meaning. "
                  "If the text is Uzbek Latin, use oʻ, gʻ and ’ correctly. "
                  "Output ONLY the corrected text — no explanations, no list of errors.",
    },
    {
        "key": "newalpha", "icon": "newalpha", "title": "Yangi alifbo (Ö Ğ Ş Ç)", "shortcut": "3",
        "placeholder": "Matnni yozing (lotin, kirill yoki boshqa tilda) — xatolarini to'g'rilab, "
                       "yangi alifboda yozib beraman…",
        "prompt": "You are an expert Uzbek editor. First fix ALL grammar, spelling and "
                  "punctuation errors so the text is clear and meaningful, then write the result "
                  "in literary Uzbek using the NEW Uzbek Latin alphabet. " + NEW_ALPHA_RULES +
                  " If the text is in old Latin or Cyrillic Uzbek, convert it; if it is in "
                  "another language, translate it into Uzbek. Never use oʻ, gʻ, sh or ch. "
                  "Output ONLY the resulting text.",
    },
    {
        "key": "cyrillic", "icon": "cyrillic", "title": "Kirillda yozish", "shortcut": "4",
        "placeholder": "Matnni yozing — xatolarini to'g'rilab, o'zbek kirill yozuvida "
                       "yozib beraman…",
        "prompt": "You are an expert Uzbek editor. First fix ALL grammar, spelling and "
                  "punctuation errors so the text is clear and meaningful, then write the result "
                  "in literary Uzbek using the Uzbek CYRILLIC alphabet (а б в г д е ё ж з и й к "
                  "л м н о п р с т у ф х ц ч ш ъ ь э ю я ў қ ғ ҳ). Transliterate from old or new "
                  "Latin (oʻ/ö→ў, gʻ/ğ→ғ, sh/ş→ш, ch/ç→ч, q→қ, h→ҳ, x→х, ’→ъ, ye→е, yo→ё, "
                  "yu→ю, ya→я); if the text is in another language, translate it into Uzbek. "
                  "Output ONLY the resulting Cyrillic text.",
    },
    {
        "key": "search", "icon": "search", "title": "Inglizcha nima deb izlash", "shortcut": "5",
        "placeholder": "Narsani yoki xususiyatini tasvirlang, masalan: \"telefonni stolga "
                       "qotiradigan egiluvchan ushlagich\"…",
        "prompt": "The user describes an object, product, spare part, tool, material, software "
                  "feature or property (usually in Uzbek or Russian) and may not know its name. "
                  "Identify exactly what it is and output ONLY its most precise ENGLISH name / "
                  "search term (usually 1-5 words) on a single line — nothing else, no "
                  "explanation, no alternatives, no label.",
    },
]
MODE_BY_KEY = {m["key"]: m for m in MODES}

# Menyudagi rasm asboblari (Sozlamalarda yoqib/o'chirsa bo'ladi)
EXTRA_TOOLS = [
    {"key": "shot", "icon": "camera", "title": "Skrinshot olish", "shortcut": "PrtSc"},
    {"key": "aiimage", "icon": "sparkle", "title": "AI rasm (skrinshot → real rasm)",
     "shortcut": ""},
]
TOOL_KEYS = [m["key"] for m in MODES] + [t["key"] for t in EXTRA_TOOLS]

PLAIN_RULE = ("\n\nIMPORTANT: answer in plain text only. Never use emojis, markdown (**, #, `), "
              "bullet points, quotation marks around the answer, headings, labels like "
              "'Translation:' or any comments. Output only the result itself.")

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3]")
_LABEL_WORDS = (r"(english name|search term|translation|tarjima|to[‘'ʻ`]?g[‘'ʻ`]?rilangan "
                r"matn|natija|javob|result|answer|corrected text)")
_LABEL = re.compile(r"^" + _LABEL_WORDS + r"\s*:\s*", re.I)
_LABEL_ONLY = re.compile(_LABEL_WORDS + r"\s*:?", re.I)
# javob oxiriga qo'shilgan izoh bo'limlari (kerak emas)
_TAIL = re.compile(r"^(xatolar|errors|izoh|izohlar|tushuntirish|explanation|notes?|changes|"
                   r"o[‘'ʻ`]?zgarishlar|изменения|ошибки)\s*:?\s*$", re.I)


def clean_output(text: str, single_line: bool = False) -> str:
    """Javobdan emoji, markdown belgilarini va keraksiz yorliqlarni olib tashlaydi."""
    t = _EMOJI.sub("", text)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t, flags=re.S)
    t = re.sub(r"__(.+?)__", r"\1", t, flags=re.S)
    t = re.sub(r"^[ \t]{0,3}#{1,6}[ \t]*", "", t, flags=re.M)
    t = t.replace("`", "")
    lines = [ln.strip() for ln in t.strip().splitlines()]
    for i, ln in enumerate(lines):
        if i > 0 and _TAIL.match(ln):
            lines = lines[:i]                          # "Xatolar:" va undan keyingisi kerak emas
            break
    while lines and (not lines[0] or _LABEL_ONLY.fullmatch(lines[0])):
        lines.pop(0)                                   # faqat yorliqdan iborat qator
    if lines:
        lines[0] = _LABEL.sub("", lines[0])
    if single_line:
        lines = [ln for ln in lines if ln][:1]
    t = "\n".join(lines).strip()
    if len(t) >= 2 and (t[0], t[-1]) in {('"', '"'), ("«", "»"), ("“", "”")}:
        t = t[1:-1].strip()
    return t


# ---------------------------------------------------------------------------
# Sozlamalar va tarix
# ---------------------------------------------------------------------------
def config_path() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "config.json")


def load_config() -> dict:
    cfg = {"api_key": "", "model": DEFAULT_MODEL, "rx": None, "ry": None,
           "pinned": True, "lang": "O'zbekcha (lotin)", "size": "O'rta",
           "modes": list(TOOL_KEYS), "auto_hide": True, "color": C_ACCENT,
           "line_opacity": 55, "autostart": True, "image_model": "auto", "save_dir": "",
           "hook_keys": True, "shot_autosave": True, "shot_ask": True,
           "out_size": "Avto", "quality": "Avto"}
    try:
        with open(config_path(), encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if not cfg.get("api_key"):
        cfg["api_key"] = os.environ.get("OPENAI_API_KEY", "")
    if cfg.get("lang") not in LANGS:
        cfg["lang"] = "O'zbekcha (lotin)"
    if cfg.get("size") not in SCALES:
        cfg["size"] = "O'rta"
    if not cfg.get("v3"):
        # yangi versiyaga o'tish: rasm asboblari va avto-ishga tushish yoqiladi
        cfg["modes"] = list(dict.fromkeys(list(cfg.get("modes", [])) +
                                          [t["key"] for t in EXTRA_TOOLS]))
        cfg["autostart"] = True
        cfg["v3"] = True
    cfg["modes"] = [k for k in cfg.get("modes", []) if k in TOOL_KEYS]
    if cfg.get("out_size") not in SIZES:
        cfg["out_size"] = "Avto"
    if cfg.get("quality") not in QUALITIES:
        cfg["quality"] = "Avto"
    if not QColor(str(cfg.get("color"))).isValid():
        cfg["color"] = C_ACCENT
    try:
        cfg["line_opacity"] = max(15, min(100, int(cfg.get("line_opacity", 55))))
    except (TypeError, ValueError):
        cfg["line_opacity"] = 55
    return cfg


def save_config(cfg: dict) -> None:
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def history_dir() -> str:
    docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) or \
        os.path.join(os.path.expanduser("~"), "Documents")
    path = os.path.join(docs, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def open_history_dir():
    QDesktopServices.openUrl(QUrl.fromLocalFile(history_dir()))


def save_history(mode_title: str, extra: str, text: str, answer: str) -> None:
    now = datetime.datetime.now()
    path = os.path.join(history_dir(), now.strftime("%Y-%m-%d") + ".md")
    head = f"## {now:%H:%M:%S} — {mode_title}" + (f" → {extra}" if extra else "")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{head}\n\n**Siz:**\n\n{text.strip()}\n\n**Javob:**\n\n{answer.strip()}\n\n---\n\n")


# ---------------------------------------------------------------------------
# API so'rovi alohida oqimda
# ---------------------------------------------------------------------------
class Worker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, api_key, model, system, text):
        super().__init__()
        self.api_key, self.model, self.system, self.text = api_key, model, system, text

    def run(self):
        try:
            r = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={"model": self.model, "temperature": 0.2,
                      "messages": [{"role": "system", "content": self.system},
                                   {"role": "user", "content": self.text}]},
                timeout=90,
            )
            if r.status_code != 200:
                try:
                    msg = r.json()["error"]["message"]
                except Exception:
                    msg = r.text[:300]
                self.failed.emit(f"Xato {r.status_code}: {msg}")
                return
            self.done.emit(r.json()["choices"][0]["message"]["content"].strip())
        except requests.exceptions.ConnectionError:
            self.failed.emit("Internetga ulanib bo'lmadi.")
        except requests.exceptions.Timeout:
            self.failed.emit("Server javob bermadi (vaqt tugadi).")
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Xato: {e}")


# ---------------------------------------------------------------------------
# UI elementlari
# ---------------------------------------------------------------------------
def shadow(widget, blur=36, dy=10, alpha=38):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(eff)


class HoverBubble(QWidget):
    """Kursor ikonka ustiga borgandagina chiqadigan yozuv (nom + tugmalar)."""

    def __init__(self, s):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 14)
        card = QFrame()
        card.setObjectName("bubble")
        shadow(card, 24, 6, 45)
        outer.addWidget(card)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(int(16 * s), int(8 * s), int(10 * s), int(8 * s))
        lay.setSpacing(int(6 * s))
        self.label = QLabel()
        self.label.setObjectName("bubbleText")
        lay.addWidget(self.label)
        lay.addSpacing(int(14 * s))
        self.keys = []
        for _ in range(2):
            k = QLabel()
            k.setObjectName("keycap")
            k.setAlignment(Qt.AlignCenter)
            lay.addWidget(k)
            self.keys.append(k)

    def prepare(self, text, shortcut):
        self.label.setText(text)
        parts = shortcut.split("+") if shortcut else []
        for i, k in enumerate(self.keys):
            k.setVisible(i < len(parts))
            if i < len(parts):
                k.setText(parts[i])
        self.adjustSize()


class RailButton(QToolButton):
    hovered = Signal(object)
    unhovered = Signal(object)

    def __init__(self, icon_name, label, s, shortcut="", checkable=False):
        super().__init__()
        self.icon_name, self.label, self.shortcut, self.s = icon_name, label, shortcut, s
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(int(46 * s), int(46 * s))
        self.isz = int(24 * s)
        self.setIconSize(QSize(self.isz, self.isz))
        self.setFocusPolicy(Qt.NoFocus)
        self.toggled.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        on = self.isChecked() or self.underMouse()
        name = self.icon_name
        if name == "pin" and self.isChecked():
            name = "pin_on"
        color = C_ICON_ACTIVE if on else C_ICON
        bg = C_HOVER if on else C_BG
        self.setIcon(svg_icon(name, color, self.isz, bg=bg))

    def enterEvent(self, e):
        self.refresh()
        self.hovered.emit(self)
        super().enterEvent(e)

    def leaveEvent(self, e):
        QTimer.singleShot(0, self.refresh)
        self.unhovered.emit(self)
        super().leaveEvent(e)


class GripHandle(QLabel):
    """Sudrab olib yurish uchun tutqich."""

    def __init__(self, win, s):
        super().__init__()
        self.win = win
        self.setFixedSize(int(24 * s), int(28 * s))
        self.setAlignment(Qt.AlignCenter)
        isz = int(18 * s)
        self.setPixmap(svg_pixmap("grip", "#6B7080", isz))
        self.setCursor(Qt.SizeAllCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.win.start_drag(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        self.win.drag_to(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        self.win.end_drag()

    def enterEvent(self, e):
        self.win.show_bubble_text(self, "Sudrab joyini o'zgartiring", "")

    def leaveEvent(self, e):
        self.win.bubble.hide()


class SettingsDialog(QDialog):
    def __init__(self, parent, cfg, s):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Sozlamalar")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(int(480 * s))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, int(16 * s))
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("settingsBody")
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(int(24 * s), int(20 * s), int(24 * s), int(8 * s))
        lay.setSpacing(int(8 * s))

        t = QLabel("Sozlamalar")
        t.setObjectName("title")
        lay.addWidget(t)
        lay.addSpacing(int(4 * s))

        # API
        lay.addWidget(self._section("OpenAI API kalit"))
        self.key = QLineEdit(cfg.get("api_key", ""))
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("sk-...")
        lay.addWidget(self.key)
        link = QLabel('<a href="https://platform.openai.com/api-keys" '
                      'style="color:#6366F1;text-decoration:none;">API kalitni olish →</a>')
        link.setOpenExternalLinks(True)
        link.setObjectName("muted")
        lay.addWidget(link)
        row = QHBoxLayout()
        row.addWidget(QLabel("Model:"))
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.addItems(["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"])
        self.model.setCurrentText(cfg.get("model", DEFAULT_MODEL))
        row.addWidget(self.model, 1)
        lay.addLayout(row)

        # O'lcham
        lay.addSpacing(int(8 * s))
        lay.addWidget(self._section("O'lcham"))
        seg = QHBoxLayout()
        seg.setSpacing(int(6 * s))
        self.size_group = QButtonGroup(self)
        for name in SCALES:
            b = QPushButton(name)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(name == cfg.get("size", "O'rta"))
            self.size_group.addButton(b)
            seg.addWidget(b)
        lay.addLayout(seg)

        # Rang
        lay.addSpacing(int(8 * s))
        lay.addWidget(self._section("Rang (chet chizig'i va tugmalar)"))
        crow = QHBoxLayout()
        crow.setSpacing(int(8 * s))
        self.color = cfg.get("color", C_ACCENT)
        self.color_group = QButtonGroup(self)
        known = False
        d = int(28 * s)
        for name, col in COLORS:
            sw = self._swatch(col, name, d)
            if col.lower() == self.color.lower():
                sw.setChecked(True)
                known = True
            crow.addWidget(sw)
        self.custom_sw = self._swatch(self.color if not known else "#FFFFFF", "Boshqa rang", d)
        self.custom_sw.setVisible(not known)
        self.custom_sw.setChecked(not known)
        crow.addWidget(self.custom_sw)
        more = QPushButton("Boshqa…")
        more.setCursor(Qt.PointingHandCursor)
        more.clicked.connect(self._pick_color)
        crow.addWidget(more)
        crow.addStretch()
        lay.addLayout(crow)

        # Avtomatik yashirish
        lay.addSpacing(int(8 * s))
        lay.addWidget(self._section("Yashirinish va orqa fon"))
        self.auto_hide = QCheckBox("  Kursor chiqqach chetga kirib ketsin (shaffof chiziq "
                                   "bo'lib tursin)")
        self.auto_hide.setChecked(cfg.get("auto_hide", True))
        self.auto_hide.setCursor(Qt.PointingHandCursor)
        lay.addWidget(self.auto_hide)
        orow = QHBoxLayout()
        orow.addWidget(QLabel("Chiziq ko'rinishi:"))
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(15, 100)
        self.opacity.setValue(int(cfg.get("line_opacity", 55)))
        orow.addWidget(self.opacity, 1)
        self.opacity_lbl = QLabel(f"{self.opacity.value()}%")
        self.opacity_lbl.setMinimumWidth(int(40 * s))
        self.opacity.valueChanged.connect(lambda v: self.opacity_lbl.setText(f"{v}%"))
        orow.addWidget(self.opacity_lbl)
        lay.addLayout(orow)
        self.autostart = QCheckBox("  Kompyuter yonganda o'zi ishga tushsin")
        self.autostart.setChecked(cfg.get("autostart", False))
        self.autostart.setCursor(Qt.PointingHandCursor)
        self.autostart.setEnabled(sys.platform == "win32")
        lay.addWidget(self.autostart)

        # Funksiyalar
        lay.addSpacing(int(8 * s))
        lay.addWidget(self._section("Funksiyalar (panelda ko'rinadiganlari)"))
        self.mode_checks = {}
        isz = int(20 * s)
        for m in MODES:
            c = QCheckBox(f"  {m['title']}   ·   Ctrl+{m['shortcut']}")
            c.setIcon(svg_icon(m["icon"], C_ICON, isz))
            c.setIconSize(QSize(isz, isz))
            c.setChecked(m["key"] in cfg.get("modes", []))
            c.setCursor(Qt.PointingHandCursor)
            lay.addWidget(c)
            self.mode_checks[m["key"]] = c
        for t in EXTRA_TOOLS:
            c = QCheckBox(f"  {t['title']}" + (f"   ·   {t['shortcut']}" if t["shortcut"] else ""))
            c.setIcon(svg_icon(t["icon"], C_ICON, isz))
            c.setIconSize(QSize(isz, isz))
            c.setChecked(t["key"] in cfg.get("modes", []))
            c.setCursor(Qt.PointingHandCursor)
            lay.addWidget(c)
            self.mode_checks[t["key"]] = c

        # Skrinshot va AI rasm
        lay.addSpacing(int(8 * s))
        lay.addWidget(self._section("Skrinshot va AI rasm"))
        self.hook_keys = QCheckBox("  PrintScreen va Win+Shift+S — shu dastur (Windows'ning "
                                   "o'z vositasi bloklanadi)")
        self.hook_keys.setChecked(cfg.get("hook_keys", True))
        self.hook_keys.setEnabled(sys.platform == "win32")
        lay.addWidget(self.hook_keys)
        self.shot_autosave = QCheckBox("  Skrinshotni papkaga avtomatik saqlash")
        self.shot_autosave.setChecked(cfg.get("shot_autosave", True))
        lay.addWidget(self.shot_autosave)
        self.shot_ask = QCheckBox("  Skrinshotdan keyin so'rasin: sifatini oshirish / AI rasm")
        self.shot_ask.setChecked(cfg.get("shot_ask", True))
        lay.addWidget(self.shot_ask)
        for c in (self.hook_keys, self.shot_autosave, self.shot_ask):
            c.setCursor(Qt.PointingHandCursor)
        irow = QHBoxLayout()
        irow.addWidget(QLabel("AI rasm modeli:"))
        self.image_model = QComboBox()
        self.image_model.setEditable(True)
        self.image_model.addItems(["auto"] + IMAGE_MODELS)
        self.image_model.setCurrentText(cfg.get("image_model", "auto"))
        self.image_model.setToolTip("auto — hisobingizda ishlaydigan eng yangi modelni o'zi tanlaydi")
        irow.addWidget(self.image_model, 1)
        lay.addLayout(irow)
        lay.addWidget(QLabel("Rasmlar saqlanadigan papka (ichida: Skrinshotlar, Yuqori sifat, "
                             "AI rasmlar):"))
        drow = QHBoxLayout()
        self.save_dir = cfg.get("save_dir") or ""
        self.save_lbl = QLabel(self.save_dir or images_dir(cfg))
        self.save_lbl.setObjectName("muted")
        self.save_lbl.setWordWrap(True)
        self.save_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        drow.addWidget(self.save_lbl, 1)
        pick = QPushButton("  Tanlash…")
        pick.setIcon(svg_icon("folder", C_ICON, int(18 * s)))
        pick.setCursor(Qt.PointingHandCursor)
        pick.clicked.connect(self._pick_dir)
        drow.addWidget(pick)
        opn = QPushButton("Ochish")
        opn.setCursor(Qt.PointingHandCursor)
        opn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(self.save_dir or images_dir(cfg))))
        drow.addWidget(opn)
        lay.addLayout(drow)

        # Yozishmalar papkasi
        lay.addSpacing(int(8 * s))
        lay.addWidget(self._section("Yozishmalar saqlanadigan joy"))
        frow = QHBoxLayout()
        path = QLabel(history_dir())
        path.setObjectName("muted")
        path.setWordWrap(True)
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        frow.addWidget(path, 1)
        fbtn = QPushButton("  Papkani ochish")
        fbtn.setIcon(svg_icon("folder", C_ICON, int(18 * s)))
        fbtn.setCursor(Qt.PointingHandCursor)
        fbtn.clicked.connect(open_history_dir)
        frow.addWidget(fbtn)
        lay.addLayout(frow)

        # Pastki qator: muallif + tugmalar (har doim ko'rinib turadi)
        lay.addStretch()
        bottom = QHBoxLayout()
        bottom.setContentsMargins(int(24 * s), int(10 * s), int(24 * s), 0)
        credit = QLabel(f'<a href="{AUTHOR_URL}" style="color:{C_MUTED};text-decoration:none;">'
                        f'by <b style="color:{C_TEXT};">{AUTHOR}</b></a>')
        credit.setObjectName("credit")
        credit.setOpenExternalLinks(True)
        credit.setCursor(Qt.PointingHandCursor)
        credit.setToolTip(AUTHOR_URL)
        bottom.addWidget(credit)
        bottom.addStretch()
        cancel = QPushButton("Bekor qilish")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Saqlash")
        ok.setObjectName("primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        bottom.addWidget(cancel)
        bottom.addWidget(ok)
        outer.addLayout(bottom)

        # ekranga sig'adigan balandlik
        avail = (parent.screen() if parent else QGuiApplication.primaryScreen()).availableGeometry()
        want = inner.sizeHint().height() + int(80 * s)
        self.resize(max(self.minimumWidth(), inner.sizeHint().width() + 20),
                    min(want, int(avail.height() * 0.9)))

    @staticmethod
    def _section(text):
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def _swatch(self, col, tip, d):
        b = QPushButton()
        b.setCheckable(True)
        b.setFixedSize(d, d)
        b.setToolTip(tip)
        b.setCursor(Qt.PointingHandCursor)
        b.setProperty("color", col)
        self._style_swatch(b, col, d)
        b.clicked.connect(lambda _=False, btn=b: self._swatch_clicked(btn))
        self.color_group.addButton(b)
        return b

    @staticmethod
    def _style_swatch(b, col, d):
        b.setStyleSheet(
            f"QPushButton {{ background: {col}; border: 3px solid #FFFFFF; "
            f"border-radius: {d // 2}px; padding: 0; min-width: {d - 6}px; max-width: {d - 6}px; "
            f"min-height: {d - 6}px; max-height: {d - 6}px; }}"
            f"QPushButton:checked {{ border: 3px solid #C7CBD4; }}"
            f"QPushButton:hover {{ border: 3px solid #E3E6EC; }}")

    def _swatch_clicked(self, btn):
        self.color = btn.property("color")

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Rang tanlang")
        if c.isValid():
            self.color = c.name()
            self.custom_sw.setProperty("color", self.color)
            self._style_swatch(self.custom_sw, self.color, self.custom_sw.width())
            self.custom_sw.setVisible(True)
            self.custom_sw.setChecked(True)

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Rasmlar saqlanadigan papkani tanlang",
                                             self.save_lbl.text())
        if d:
            self.save_dir = d
            self.save_lbl.setText(d)

    def values(self):
        size = self.size_group.checkedButton().text() if self.size_group.checkedButton() \
            else "O'rta"
        modes = [k for k, c in self.mode_checks.items() if c.isChecked()]
        return {"api_key": self.key.text().strip(),
                "model": self.model.currentText().strip() or DEFAULT_MODEL,
                "size": size, "modes": modes, "color": self.color,
                "auto_hide": self.auto_hide.isChecked(),
                "line_opacity": self.opacity.value(),
                "autostart": self.autostart.isChecked(),
                "hook_keys": self.hook_keys.isChecked(),
                "shot_autosave": self.shot_autosave.isChecked(),
                "shot_ask": self.shot_ask.isChecked(),
                "image_model": self.image_model.currentText().strip() or "auto",
                "save_dir": self.save_dir}


# ---------------------------------------------------------------------------
# Asosiy oyna
# ---------------------------------------------------------------------------
# ===========================================================================
# SKRINSHOT VA AI RASM
# ===========================================================================
# "auto" tanlansa — shu tartibda sinab ko'riladi (qaysi biri hisobingizda ishlasa)
IMAGE_MODELS = ["gpt-image-2", "gpt-image-1.5", "gpt-image-1"]
API_EDIT = "https://api.openai.com/v1/images/edits"
PEN_COLORS = ["#EF4444", "#F59E0B", "#22C55E", "#3B82F6", "#111827", "#FFFFFF"]

TEMPLATES = [
    ("Real foto", "Ekrandagi tasvirni haqiqiy fotosuratga aylantiradi",
     "Transform this image (a screenshot, render, drawing or mockup) into a photorealistic "
     "photograph taken with a professional camera: natural lighting, real materials and "
     "textures, realistic shadows and reflections. Keep the same composition, layout, "
     "perspective, objects and colors."),
    ("Interyer", "Xona dizaynini real interyer fotosuratiga aylantiradi",
     "Turn this into a photorealistic interior photograph like in an architecture magazine: "
     "soft natural daylight, realistic furniture, fabrics, wood, stone and glass materials, "
     "accurate proportions. Keep the same room layout, furniture placement and color scheme."),
    ("Eksteryer", "Bino yoki hovlini real fotosuratga aylantiradi",
     "Turn this into a photorealistic architectural exterior photograph: realistic facade "
     "materials, real sky and daylight, natural landscaping and surroundings. Keep the same "
     "building shape, proportions, colors and camera angle."),
    ("Mahsulot", "Professional studiya mahsulot fotosurati",
     "Create a professional studio product photograph of the object in this image: clean "
     "background, softbox lighting, realistic reflections and shadows, e-commerce quality. "
     "Keep the product's exact shape, colors, logos and details."),
    ("Chizmadan real", "Qo'lda chizilgan rasm yoki eskizni realga aylantiradi",
     "This is a sketch or drawing. Create a realistic photograph of what it depicts, faithful "
     "to the shapes, proportions, positions and colors of the drawing."),
    ("Portret", "Odamni tabiiy, real fotosurat ko'rinishiga keltiradi",
     "Make the person in this image look like a real high-quality photograph: natural skin "
     "texture, realistic hair and lighting. Keep the same identity, face, pose, clothing and "
     "background composition."),
    ("Reklama", "Reklama banneri uchun sifatli, jozibali rasm",
     "Turn this into a polished, high-end advertising image: vibrant but natural colors, "
     "professional commercial lighting, crisp details. Keep all text readable and the layout "
     "the same."),
    ("Fon almashtirish", "Asosiy obyektni saqlab, fonni real fonga almashtiradi",
     "Keep the main subject exactly as it is and replace the background with a realistic, "
     "fitting, high-quality photographic environment with matching lighting and shadows."),
    ("Sifatni oshirish", "Tiniqlik, ranglar va detallarni yaxshilaydi (AI)",
     "Enhance this image: increase sharpness and fine detail, remove noise, blur and "
     "compression artifacts, improve lighting and colors. Keep everything else identical."),
    ("3D render", "Fotorealistik 3D render ko'rinishi",
     "Turn this into a high-quality photorealistic 3D render with physically based materials, "
     "global illumination and realistic depth of field. Keep the same composition."),
    ("Kechki ko'rinish", "Shu joyni kechki/tungi yoritishda ko'rsatadi",
     "Show the same scene in the evening at dusk with realistic warm artificial lighting, "
     "glowing windows and lamps, photorealistic. Keep the same composition and objects."),
    ("Ortiqchani o'chirish", "Belgilangan narsalarni olib tashlaydi",
     "Remove the objects that are circled, crossed out or pointed at by the drawn marks, and "
     "fill those areas naturally so it looks like they were never there. Keep everything else "
     "unchanged."),
]

MARKS_RULE = ("The colored strokes, arrows, boxes, circles and handwritten text drawn on top of "
              "the image are the user's annotations and instructions, not part of the scene. "
              "Follow them (they point at areas to change or say what to do) and make sure no "
              "annotation marks or annotation text appear in the final image.")

SIZES = {"Avto": "auto", "Kvadrat (1:1)": "1024x1024", "Yotiq (3:2)": "1536x1024",
         "Tik (2:3)": "1024x1536"}
QUALITIES = {"Avto": "auto", "Past (tez)": "low", "O'rta": "medium", "Yuqori": "high"}


def default_images_dir() -> str:
    pics = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or \
        os.path.join(os.path.expanduser("~"), "Pictures")
    return os.path.join(pics, APP_NAME)


def images_dir(cfg: dict) -> str:
    """Rasmlar saqlanadigan papka (Sozlamalarda tanlanadi)."""
    for d in (cfg.get("save_dir") or "", default_images_dir()):
        if not d:
            continue
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except OSError:
            continue
    return os.path.expanduser("~")


def open_images_dir(cfg: dict):
    QDesktopServices.openUrl(QUrl.fromLocalFile(images_dir(cfg)))


# tanlangan papka ichidagi alohida papkalar
SUBDIRS = {"shot": "Skrinshotlar", "hq": "Yuqori sifat", "ai": "AI rasmlar"}
PICKER_SECONDS = 120          # oxirgi skrinshotlar oynasi shu vaqt ichida ishlaydi
PICKER_MAX = 10


def images_subdir(cfg: dict, kind: str) -> str:
    root = images_dir(cfg)
    path = os.path.join(root, SUBDIRS[kind])
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except OSError:
        return root


def send_ctrl_v():
    """Faol oynaga Ctrl+V yuboradi (Windows)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        for vk in (0x10, 0xA0, 0xA1, 0x12):          # Shift/Alt bosilib qolgan bo'lsa — qo'yib yuboramiz
            if u.GetAsyncKeyState(vk) & 0x8000:
                u.keybd_event(vk, 0, 2, 0)
        u.keybd_event(0x11, 0, 0, 0)
        u.keybd_event(0x56, 0, 0, 0)
        u.keybd_event(0x56, 0, 2, 0)
        u.keybd_event(0x11, 0, 2, 0)
    except Exception:
        pass


def stamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def unique_path(folder: str, name: str, ext: str = ".png") -> str:
    """Bir xil nomli fayl bor bo'lsa — _2, _3 ... qo'shadi (ustiga yozilmasin)."""
    path = os.path.join(folder, name + ext)
    n = 2
    while os.path.exists(path):
        path = os.path.join(folder, f"{name}_{n}{ext}")
        n += 1
    return path


def image_to_png(img: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


class ImageWorker(QThread):
    """Rasmni OpenAI rasm modeliga yuborib, real rasm oladi."""
    done = Signal(bytes, str, str)     # natija PNG, model, yakuniy prompt
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, cfg, png, template_prompt, user_text, has_marks):
        super().__init__()
        self.cfg, self.png = dict(cfg), png
        self.template_prompt, self.user_text, self.has_marks = template_prompt, user_text, has_marks

    def _translate(self, text):
        try:
            r = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {self.cfg['api_key']}"},
                json={"model": self.cfg.get("model", DEFAULT_MODEL), "temperature": 0,
                      "messages": [{"role": "system", "content":
                                    "Translate the user's image-editing instruction into clear, "
                                    "precise English. Output only the translation, plain text."},
                                   {"role": "user", "content": text}]},
                timeout=40)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip() or text
        except Exception:
            pass
        return text

    @staticmethod
    def _model_problem(status, msg):
        m = msg.lower()
        return status in (403, 404) or ("model" in m and any(
            k in m for k in ("not found", "does not exist", "invalid", "unsupported",
                             "not supported", "access", "verif")))

    def run(self):
        try:
            parts = []
            if self.template_prompt:
                parts.append(self.template_prompt)
            if self.user_text.strip():
                self.progress.emit("Ko'rsatma tayyorlanmoqda…")
                parts.append("User's instructions: " + self._translate(self.user_text.strip()))
            if not parts:
                parts.append(TEMPLATES[0][2])
            if self.has_marks:
                parts.append(MARKS_RULE)
            prompt = "\n\n".join(parts)
            chosen = self.cfg.get("image_model", "auto")
            models = IMAGE_MODELS if chosen in ("", "auto") else [chosen]
            size = SIZES.get(self.cfg.get("out_size"), "auto")
            quality = QUALITIES.get(self.cfg.get("quality"), "auto")
            last = "Noma'lum xato"
            for i, model in enumerate(models):
                self.progress.emit("Rasm yaratilmoqda… (30–120 soniya)")
                data = {"model": model, "prompt": prompt, "n": "1", "size": size}
                if quality != "auto":
                    data["quality"] = quality
                r = requests.post(API_EDIT,
                                  headers={"Authorization": f"Bearer {self.cfg['api_key']}"},
                                  data=data,
                                  files={"image": ("image.png", self.png, "image/png")},
                                  timeout=300)
                if r.status_code == 200:
                    item = r.json()["data"][0]
                    if item.get("b64_json"):
                        out = base64.b64decode(item["b64_json"])
                    else:
                        out = requests.get(item["url"], timeout=120).content
                    self.done.emit(out, model, prompt)
                    return
                try:
                    msg = r.json()["error"]["message"]
                except Exception:
                    msg = r.text[:300]
                last = f"Xato {r.status_code}: {msg}"
                if i < len(models) - 1 and self._model_problem(r.status_code, msg):
                    continue
                break
            self.failed.emit(last)
        except requests.exceptions.ConnectionError:
            self.failed.emit("Internetga ulanib bo'lmadi.")
        except requests.exceptions.Timeout:
            self.failed.emit("Server javob bermadi (vaqt tugadi). Qayta urinib ko'ring.")
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Xato: {e}")


def enhance_png(png: bytes):
    """Skrinshot sifatini oshirish: 2 barobar kattalashtirish + tiniqlashtirish (bepul, tez)."""
    try:
        import io
        from PIL import Image, ImageEnhance, ImageFilter
        im = Image.open(io.BytesIO(png))
        im.load()
        im = im.convert("RGB")
        w, h = im.size
        f = 2.0 if max(w, h) <= 2400 else (1.5 if max(w, h) <= 3600 else 1.0)
        if f > 1:
            im = im.resize((round(w * f), round(h * f)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=120, threshold=2))
        im = ImageEnhance.Contrast(im).enhance(1.04)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return buf.getvalue(), im.size[0], im.size[1]
    except ImportError:
        img = QImage.fromData(png)
        f = 2 if max(img.width(), img.height()) <= 2400 else 1
        img = img.scaled(img.width() * f, img.height() * f, Qt.KeepAspectRatio,
                         Qt.SmoothTransformation)
        return image_to_png(img), img.width(), img.height()


class EnhanceWorker(QThread):
    done = Signal(bytes, int, int)
    failed = Signal(str)

    def __init__(self, png):
        super().__init__()
        self.png = png

    def run(self):
        try:
            self.done.emit(*enhance_png(self.png))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Sifatni oshirib bo'lmadi: {e}")


# ---------------------------------------------------------------------------
# PrintScreen va Win+Shift+S ni ushlash (Windows)
# ---------------------------------------------------------------------------
class KeyboardHook:
    """PrintScreen yoki Win+Shift+S — skrinshot; Ctrl+V+S yoki Ctrl+Shift+V — oxirgi
    skrinshotlar oynasi (faqat oxirgi skrinshotdan keyin 2 daqiqa ichida)."""
    VK_SNAPSHOT, VK_S, VK_V = 0x2C, 0x53, 0x56
    WIN_KEYS, SHIFT_KEYS, CTRL_KEYS = (0x5B, 0x5C), (0x10, 0xA0, 0xA1), (0x11, 0xA2, 0xA3)

    def __init__(self, callback, picker_cb=None, picker_active=None):
        self.callback = callback
        self.picker_cb = picker_cb
        self.picker_active = picker_active or (lambda: False)
        self.router = None            # oxirgi skrinshotlar oynasi ochiq bo'lsa — tugmalar unga
        self.hook = None
        self.down = set()
        self.snap_down = False
        self.eaten = set()
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes
            self.ct = ctypes
            self.user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            class KBD(ctypes.Structure):
                _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                            ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                            ("dwExtraInfo", ctypes.c_size_t)]
            self.KBD = KBD
            LRESULT = ctypes.c_ssize_t
            HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
            self.user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE,
                                                      wintypes.DWORD]
            self.user32.SetWindowsHookExW.restype = wintypes.HHOOK
            self.user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM,
                                                   wintypes.LPARAM]
            self.user32.CallNextHookEx.restype = LRESULT
            self.user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE
            self.proc = HOOKPROC(self._proc)          # havolani saqlab qo'yamiz (GC o'chirmasin)
            self.hook = self.user32.SetWindowsHookExW(13, self.proc,                # WH_KEYBOARD_LL
                                                      kernel32.GetModuleHandleW(None), 0)
        except Exception:
            self.hook = None

    @property
    def ok(self):
        return bool(self.hook)

    def _fire(self):
        QTimer.singleShot(0, self.callback)

    def _mask_start_menu(self):
        # Win tugmasi qo'yib yuborilganda Start menyusi ochilib ketmasligi uchun
        try:
            self.user32.keybd_event(0xE8, 0, 0, 0)
            self.user32.keybd_event(0xE8, 0, 2, 0)
        except Exception:
            pass

    def _proc(self, ncode, wparam, lparam):
        try:
            if ncode == 0:
                kb = self.ct.cast(lparam, self.ct.POINTER(self.KBD)).contents
                vk, injected = kb.vkCode, kb.flags & 0x10
                is_down = wparam in (0x100, 0x104)
                is_up = wparam in (0x101, 0x105)
                if not injected:
                    if is_down:
                        self.down.add(vk)
                    elif is_up:
                        self.down.discard(vk)
                    if is_up and vk in self.eaten:
                        self.eaten.discard(vk)
                        return 1
                    if self.router is not None and is_down and self.router(vk):
                        self.eaten.add(vk)
                        return 1
                    ctrl = any(k in self.down for k in self.CTRL_KEYS)
                    shift = any(k in self.down for k in self.SHIFT_KEYS)
                    if is_down and ctrl and self.picker_cb and self.picker_active() and (
                            (vk == self.VK_V and shift) or
                            (vk == self.VK_S and self.VK_V in self.down)):
                        self.eaten.add(vk)
                        QTimer.singleShot(0, self.picker_cb)
                        return 1
                    if vk == self.VK_SNAPSHOT:
                        if is_down and not self.snap_down:
                            self.snap_down = True
                            self._fire()
                        elif is_up:
                            if not self.snap_down:
                                self._fire()
                            self.snap_down = False
                        return 1
                    if vk == self.VK_S and is_down and shift and any(
                            k in self.down for k in self.WIN_KEYS):
                        self.eaten.add(vk)
                        self._mask_start_menu()
                        self._fire()
                        return 1
        except Exception:
            pass
        return self.user32.CallNextHookEx(self.hook, ncode, wparam, lparam)

    def unhook(self):
        if self.hook:
            try:
                self.user32.UnhookWindowsHookEx(self.hook)
            except Exception:
                pass
            self.hook = None


class GlobalHotkey(QAbstractNativeEventFilter):
    """Zaxira tugma: Ctrl+Alt+S (Windows)."""
    HK_ID = 0xA51

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.ok = False
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.user32 = ctypes.windll.user32
            self.ok = bool(self.user32.RegisterHotKey(None, self.HK_ID, 0x0002 | 0x0001 | 0x4000,
                                                      0x53))
        except Exception:
            self.ok = False

    def nativeEventFilter(self, event_type, message):
        try:
            if self.ok and bytes(event_type) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                import ctypes.wintypes
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == 0x0312 and msg.wParam == self.HK_ID:
                    QTimer.singleShot(0, self.callback)
                    return True, 0
        except Exception:
            pass
        return False, 0

    def unregister(self):
        if self.ok:
            try:
                self.user32.UnregisterHotKey(None, self.HK_ID)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Skrinshot: ekranda joy belgilash
# ---------------------------------------------------------------------------
class CaptureOverlay(QWidget):
    captured = Signal(QImage)
    cancelled = Signal()

    def __init__(self, screen, pixmap):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.pm = pixmap
        self.start = None
        self.end = None
        self.setCursor(Qt.CrossCursor)
        self.setGeometry(screen.geometry())
        self.setFocusPolicy(Qt.StrongFocus)

    def sel_rect(self):
        if self.start is None or self.end is None:
            return QRect()
        return QRect(self.start, self.end).normalized()

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.pm)
        p.fillRect(self.rect(), QColor(10, 12, 20, 110))
        r = self.sel_rect()
        dpr = self.pm.devicePixelRatio()
        if not r.isEmpty():
            src = QRect(int(r.x() * dpr), int(r.y() * dpr), int(r.width() * dpr),
                        int(r.height() * dpr))
            p.drawPixmap(r, self.pm, src)
            p.setPen(QPen(QColor("#FFFFFF"), 2))
            p.drawRect(r.adjusted(0, 0, -1, -1))
            p.drawText(r.left(), max(16, r.top() - 8),
                       f"{int(r.width() * dpr)} × {int(r.height() * dpr)}")
        hint = "Joyni belgilang  ·  Enter — butun ekran  ·  Esc — bekor qilish"
        f = QFont("Segoe UI")
        f.setPixelSize(15)
        f.setBold(True)
        p.setFont(f)
        w = p.fontMetrics().horizontalAdvance(hint) + 36
        box = QRectF((self.width() - w) / 2, 24, w, 40)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawRoundedRect(box, 20, 20)
        p.setPen(QColor(C_TEXT))
        p.drawText(box, Qt.AlignCenter, hint)
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.start = self.end = e.position().toPoint()
            self.update()
        elif e.button() == Qt.RightButton:
            self._cancel()

    def mouseMoveEvent(self, e):
        if self.start is not None:
            self.end = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self.start is None:
            return
        r = self.sel_rect()
        if r.width() < 8 or r.height() < 8:
            self.start = self.end = None
            self.update()
            return
        self._finish(r)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._cancel()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._finish(self.rect())

    def _finish(self, r):
        dpr = self.pm.devicePixelRatio()
        src = QRect(int(r.x() * dpr), int(r.y() * dpr), int(r.width() * dpr),
                    int(r.height() * dpr))
        img = self.pm.copy(src).toImage()
        img.setDevicePixelRatio(1.0)
        self.hide()
        self.captured.emit(img)
        self.close()
        self.deleteLater()

    def _cancel(self):
        self.hide()
        self.cancelled.emit()
        self.close()
        self.deleteLater()


# ---------------------------------------------------------------------------
# Chizish maydoni
# ---------------------------------------------------------------------------
def draw_item(p: QPainter, it: dict):
    t = it["t"]
    if t == "text":
        f = QFont("Segoe UI")
        f.setBold(True)
        f.setPixelSize(max(6, int(it["size"])))
        path = QPainterPath()
        path.addText(it["p"], f, it["s"])
        outline = QColor("#000000") if QColor(it["c"]).lightness() > 200 else QColor("#FFFFFF")
        p.setPen(QPen(outline, max(2.0, it["size"] / 7), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(it["c"])
        p.drawPath(path)
        return
    p.setPen(QPen(it["c"], it["w"], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if t == "pen":
        pts = it["pts"]
        path = QPainterPath(pts[0])
        for q in pts[1:]:
            path.lineTo(q)
        if len(pts) == 1:
            path.lineTo(pts[0] + QPointF(0.01, 0.01))
        p.drawPath(path)
    elif t == "rect":
        p.drawRoundedRect(QRectF(it["a"], it["b"]).normalized(), it["w"], it["w"])
    elif t == "ellipse":
        p.drawEllipse(QRectF(it["a"], it["b"]).normalized())
    elif t == "arrow":
        a, b = it["a"], it["b"]
        ang = math.atan2(b.y() - a.y(), b.x() - a.x())
        head = max(12.0, it["w"] * 4.2)
        base = QPointF(b.x() - head * 0.8 * math.cos(ang), b.y() - head * 0.8 * math.sin(ang))
        p.drawLine(a, base)
        left = QPointF(b.x() - head * math.cos(ang - 0.45), b.y() - head * math.sin(ang - 0.45))
        right = QPointF(b.x() - head * math.cos(ang + 0.45), b.y() - head * math.sin(ang + 0.45))
        p.setPen(QPen(it["c"], max(1.0, it["w"] * 0.6), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(it["c"])
        p.drawPolygon(QPolygonF([b, left, right]))


class Canvas(QWidget):
    changed = Signal()
    UI_WIDTHS = [3, 6, 11]
    UI_FONTS = [16, 22, 32]

    def __init__(self, image: QImage):
        super().__init__()
        self.img = image.convertToFormat(QImage.Format_ARGB32)
        self.items, self.redo_stack = [], []
        self.cur = None
        self.tool = "pen"
        self.color = QColor(PEN_COLORS[0])
        self.size_idx = 1
        self.edit = None
        self.setMinimumSize(320, 240)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_image(self, img: QImage):
        self.img = img.convertToFormat(QImage.Format_ARGB32)
        self.items, self.redo_stack, self.cur = [], [], None
        self.changed.emit()
        self.update()

    def geom(self):
        pad = 12
        iw, ih = max(1, self.img.width()), max(1, self.img.height())
        sc = min((self.width() - 2 * pad) / iw, (self.height() - 2 * pad) / ih, 2.0)
        sc = max(sc, 0.01)
        return sc, QPointF((self.width() - iw * sc) / 2, (self.height() - ih * sc) / 2)

    def to_img(self, pos):
        sc, o = self.geom()
        return QPointF((pos.x() - o.x()) / sc, (pos.y() - o.y()) / sc)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        sc, o = self.geom()
        p.translate(o)
        p.scale(sc, sc)
        p.drawImage(0, 0, self.img)
        for it in self.items + ([self.cur] if self.cur else []):
            draw_item(p, it)
        p.end()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self._commit_text()
        pos = e.position()
        pt = self.to_img(pos)
        sc, _ = self.geom()
        if self.tool == "text":
            self._start_text(pos, pt, sc)
            return
        w = self.UI_WIDTHS[self.size_idx] / sc
        c = QColor(self.color)
        if self.tool == "pen":
            self.cur = {"t": "pen", "pts": [pt], "c": c, "w": w}
        elif self.tool == "marker":
            c.setAlpha(105)
            self.cur = {"t": "pen", "pts": [pt], "c": c, "w": w * 3.2}
        else:
            self.cur = {"t": self.tool, "a": pt, "b": pt, "c": c, "w": w}
        self.update()

    def mouseMoveEvent(self, e):
        if self.cur is None:
            return
        pt = self.to_img(e.position())
        if self.cur["t"] == "pen":
            self.cur["pts"].append(pt)
        else:
            self.cur["b"] = pt
        self.update()

    def mouseReleaseEvent(self, e):
        if self.cur is None:
            return
        it, self.cur = self.cur, None
        if it["t"] in ("rect", "ellipse", "arrow"):
            d = it["b"] - it["a"]
            if abs(d.x()) + abs(d.y()) < 3:
                self.update()
                return
        self._push(it)

    def _push(self, it):
        self.items.append(it)
        self.redo_stack.clear()
        self.changed.emit()
        self.update()

    def _start_text(self, pos, pt, sc):
        ui_px = self.UI_FONTS[self.size_idx]
        ed = QLineEdit(self)
        ed.setObjectName("canvasText")
        ed.setPlaceholderText("Yozing va Enter bosing…")
        ed.setStyleSheet(f"QLineEdit#canvasText {{ background: rgba(255,255,255,235); "
                         f"border: 2px solid {self.color.name()}; border-radius: 8px; "
                         f"padding: 2px 6px; font-size: {ui_px}px; font-weight: 700; "
                         f"color: {self.color.name() if self.color.lightness() < 230 else '#111827'}; }}")
        ed.setMinimumWidth(220)
        ed.adjustSize()
        ed.move(int(pos.x()), int(pos.y() - ed.height() / 2))
        ed.show()
        ed.setFocus()
        ed.returnPressed.connect(self._commit_text)
        self.edit = (ed, pt, ui_px / sc, QColor(self.color))

    def _commit_text(self):
        if not self.edit:
            return
        ed, pt, size_img, color = self.edit
        self.edit = None
        txt = ed.text().strip()
        ed.hide()
        ed.deleteLater()
        if txt:
            self._push({"t": "text", "p": QPointF(pt.x(), pt.y() + size_img * 0.38),
                        "s": txt, "c": color, "size": size_img})

    def undo(self):
        self._commit_text()
        if self.items:
            self.redo_stack.append(self.items.pop())
            self.changed.emit()
            self.update()

    def redo(self):
        if self.redo_stack:
            self.items.append(self.redo_stack.pop())
            self.changed.emit()
            self.update()

    def clear_marks(self):
        self._commit_text()
        if self.items:
            self.redo_stack = list(reversed(self.items))
            self.items = []
            self.changed.emit()
            self.update()

    def has_marks(self):
        return bool(self.items)

    def render_flat(self) -> QImage:
        self._commit_text()
        out = self.img.copy()
        p = QPainter(out)
        p.setRenderHint(QPainter.Antialiasing)
        for it in self.items:
            draw_item(p, it)
        p.end()
        return out


# ---------------------------------------------------------------------------
# Umumiy "kartochka" oyna (oq, yumaloq burchakli)
# ---------------------------------------------------------------------------
def card_btn(icon, tip, s, color=C_ICON):
    b = QToolButton()
    b.setObjectName("small")
    isz = int(18 * s)
    b.setIcon(svg_icon(icon, color, isz))
    b.setIconSize(QSize(isz, isz))
    b.setFixedSize(int(34 * s), int(34 * s))
    b.setCursor(Qt.PointingHandCursor)
    b.setToolTip(tip)
    return b


def section(text):
    lbl = QLabel(text)
    lbl.setObjectName("section")
    return lbl


class CardWindow(QWidget):
    def __init__(self, ctrl, title, icon):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.ctrl = ctrl
        self.s = s = SCALES.get(ctrl.cfg.get("size"), 1.0)
        self.accent = ctrl.cfg.get("color", C_ACCENT)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(f"{title} — {APP_NAME}")
        self.setWindowIcon(QIcon(app_icon()))
        self._drag = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        self.card = QFrame()
        self.card.setObjectName("card")
        shadow(self.card, 40, 12, 45)
        outer.addWidget(self.card)
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(int(18 * s), int(12 * s), int(14 * s), int(8 * s))
        lay.setSpacing(int(10 * s))

        self.header = QWidget()
        self.header.setCursor(Qt.SizeAllCursor)
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setPixmap(svg_pixmap(icon, self.accent, int(22 * s)))
        hl.addWidget(ic)
        hl.addSpacing(int(4 * s))
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("title")
        hl.addWidget(self.title_lbl)
        hl.addStretch()
        self.header_extra = QHBoxLayout()
        hl.addLayout(self.header_extra)
        close = card_btn("close", "Yopish", s)
        close.clicked.connect(self.close)
        hl.addWidget(close)
        self.header.installEventFilter(self)
        lay.addWidget(self.header)

        self.body = QVBoxLayout()
        self.body.setSpacing(int(10 * s))
        lay.addLayout(self.body, 1)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()
        grip_row.addWidget(QSizeGrip(self.card), 0, Qt.AlignBottom | Qt.AlignRight)
        lay.addLayout(grip_row)

    def eventFilter(self, obj, e):
        if obj is self.header:
            if e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
                self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if e.type() == QEvent.MouseMove and self._drag is not None:
                if self.isMaximized():
                    self.showNormal()
                self.move(e.globalPosition().toPoint() - self._drag)
                return True
            if e.type() == QEvent.MouseButtonRelease:
                self._drag = None
                return True
            if e.type() == QEvent.MouseButtonDblClick:
                self.showNormal() if self.isMaximized() else self.showMaximized()
                return True
        return super().eventFilter(obj, e)

    def fit_on_screen(self, w, h):
        scr = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        w, h = min(w, int(g.width() * 0.94)), min(h, int(g.height() * 0.92))
        self.resize(w, h)
        self.move(g.center().x() - w // 2, g.center().y() - h // 2)

    def closeEvent(self, e):
        self.ctrl.forget(self)
        super().closeEvent(e)


# ---------------------------------------------------------------------------
# AI rasm: tahrirlash oynasi
# ---------------------------------------------------------------------------
class EditorWindow(CardWindow):
    TOOLS = [("pen", "Qalam"), ("marker", "Marker"), ("arrow", "Strelka"),
             ("rect", "To'rtburchak"), ("ellipse", "Doira"), ("text", "Matn yozish")]

    def __init__(self, ctrl, image: QImage):
        super().__init__(ctrl, "AI rasm — tahrirlash", "image")
        s = self.s
        self.worker = None
        self.template_idx = None
        openf = card_btn("folder", "Boshqa rasm faylini ochish", s)
        openf.clicked.connect(self._open_other)
        self.header_extra.addWidget(openf)

        row = QHBoxLayout()
        row.setSpacing(int(14 * s))
        self.body.addLayout(row, 1)

        left = QVBoxLayout()
        left.setSpacing(int(8 * s))
        row.addLayout(left, 1)
        tb_frame = QFrame()
        tb_frame.setObjectName("toolbar")
        tb = QHBoxLayout(tb_frame)
        tb.setContentsMargins(int(6 * s), int(4 * s), int(6 * s), int(4 * s))
        tb.setSpacing(int(2 * s))
        self.tool_group = QButtonGroup(self)
        self.tool_btns = {}
        for key, tip in self.TOOLS:
            b = self._tool_btn(key, tip)
            b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            self.tool_group.addButton(b)
            tb.addWidget(b)
            self.tool_btns[key] = b
        tb.addWidget(self._vsep())
        self.color_group = QButtonGroup(self)
        d = int(22 * s)
        for col in PEN_COLORS:
            b = QPushButton()
            b.setCheckable(True)
            b.setFixedSize(d, d)
            b.setCursor(Qt.PointingHandCursor)
            ring = "#C7CBD4" if col.upper() == "#FFFFFF" else "#FFFFFF"
            b.setStyleSheet(f"QPushButton {{ background: {col}; border: 2px solid {ring}; "
                            f"border-radius: {d // 2}px; padding: 0; min-width: {d - 4}px; "
                            f"max-width: {d - 4}px; min-height: {d - 4}px; max-height: {d - 4}px; }}"
                            f"QPushButton:checked {{ border: 3px solid #9CA3AF; }}")
            b.clicked.connect(lambda _=False, c=col: self.set_color(c))
            self.color_group.addButton(b)
            b.setChecked(col == PEN_COLORS[0])
            tb.addWidget(b)
        tb.addWidget(self._vsep())
        self.size_group = QButtonGroup(self)
        for i, ic in enumerate(["dot1", "dot2", "dot3"]):
            b = self._tool_btn(ic, ["Ingichka", "O'rta", "Qalin"][i])
            b.clicked.connect(lambda _=False, k=i: self.set_size(k))
            self.size_group.addButton(b)
            b.setChecked(i == 1)
            tb.addWidget(b)
        tb.addWidget(self._vsep())
        for ic, tip, fn in [("undo", "Orqaga (Ctrl+Z)", self._undo),
                            ("redo", "Oldinga (Ctrl+Y)", self._redo),
                            ("trash", "Chizilganlarni tozalash", self._clear)]:
            b = card_btn(ic, tip, s)
            b.clicked.connect(fn)
            tb.addWidget(b)
        tb.addStretch()
        left.addWidget(tb_frame)

        self.canvas = Canvas(image)
        self.canvas.setObjectName("canvas")
        self.canvas.setAttribute(Qt.WA_StyledBackground, True)
        left.addWidget(self.canvas, 1)
        self.tool_btns["pen"].setChecked(True)
        self.info = QLabel()
        self.info.setObjectName("muted")
        left.addWidget(self.info)
        self.canvas.changed.connect(self._update_info)
        self._update_info()

        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QFrame.NoFrame)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        side_scroll.setFixedWidth(int(340 * s))
        side = QWidget()
        side.setObjectName("side")
        side_scroll.setWidget(side)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, int(6 * s), 0)
        sl.setSpacing(int(8 * s))
        row.addWidget(side_scroll)

        sl.addWidget(section("Tayyor shablonlar"))
        grid = QGridLayout()
        grid.setSpacing(int(6 * s))
        self.chips = []
        for i, (title, desc, _) in enumerate(TEMPLATES):
            c = QPushButton(title)
            c.setObjectName("chip")
            c.setCheckable(True)
            c.setToolTip(desc)
            c.setCursor(Qt.PointingHandCursor)
            c.clicked.connect(lambda _=False, k=i: self._chip(k))
            grid.addWidget(c, i // 2, i % 2)
            self.chips.append(c)
        sl.addLayout(grid)
        self.tpl_desc = QLabel("Shablon tanlanmasa — \"Real foto\" ishlatiladi.")
        self.tpl_desc.setObjectName("muted")
        self.tpl_desc.setWordWrap(True)
        sl.addWidget(self.tpl_desc)

        sl.addSpacing(int(4 * s))
        sl.addWidget(section("Nima qilish kerak?"))
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("Masalan: shu xonani haqiqiy fotosurat qil, devorlarni oq, "
                                       "polni yog'och qil. O'zbekcha yozsangiz bo'ladi.")
        self.prompt.setMinimumHeight(int(110 * s))
        sl.addWidget(self.prompt)

        sl.addSpacing(int(4 * s))
        sl.addWidget(section("Natija"))
        orow = QGridLayout()
        orow.setHorizontalSpacing(int(8 * s))
        orow.addWidget(QLabel("O'lcham:"), 0, 0)
        self.size_box = QComboBox()
        self.size_box.addItems(list(SIZES))
        self.size_box.setCurrentText(ctrl.cfg.get("out_size", "Avto"))
        orow.addWidget(self.size_box, 0, 1)
        orow.addWidget(QLabel("Sifat:"), 1, 0)
        self.quality_box = QComboBox()
        self.quality_box.addItems(list(QUALITIES))
        self.quality_box.setCurrentText(ctrl.cfg.get("quality", "Avto"))
        orow.addWidget(self.quality_box, 1, 1)
        sl.addLayout(orow)
        sl.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(int(6 * s))
        self.progress.hide()
        sl.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        sl.addWidget(self.status)
        self.go = QPushButton("  Real rasm qilish")
        self.go.setObjectName("primary")
        self.go.setIcon(svg_icon("sparkle", accent_text(self.accent), int(18 * s)))
        self.go.setIconSize(QSize(int(18 * s), int(18 * s)))
        self.go.setCursor(Qt.PointingHandCursor)
        self.go.setMinimumHeight(int(44 * s))
        self.go.clicked.connect(self.generate)
        sl.addWidget(self.go)
        hint = QLabel("Ctrl+Enter")
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignCenter)
        sl.addWidget(hint)

        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self._redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self._redo)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.generate)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.generate)

        iw, ih = image.width(), image.height()
        self.fit_on_screen(int(min(max(iw, 640), 1100) + 340 * s + 90),
                           int(min(max(ih, 460), 760) + 150))

    def _tool_btn(self, icon, tip):
        s = self.s
        b = QToolButton()
        b.setObjectName("tool")
        b.setCheckable(True)
        isz = int(20 * s)
        b.setIcon(svg_icon(icon, C_ICON, isz, bg=C_HOVER))
        b.setIconSize(QSize(isz, isz))
        b.setFixedSize(int(36 * s), int(36 * s))
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        return b

    def _vsep(self):
        f = QFrame()
        f.setObjectName("vsep")
        f.setFixedWidth(1)
        f.setFixedHeight(int(24 * self.s))
        return f

    def set_tool(self, k):
        self.canvas._commit_text()
        self.canvas.tool = k
        self.canvas.setCursor(Qt.IBeamCursor if k == "text" else Qt.CrossCursor)

    def set_color(self, c):
        self.canvas.color = QColor(c)

    def set_size(self, k):
        self.canvas.size_idx = k

    def _undo(self):
        self.canvas.undo()

    def _redo(self):
        self.canvas.redo()

    def _clear(self):
        self.canvas.clear_marks()

    def _open_other(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Rasmni tanlang", "",
                                            "Rasmlar (*.png *.jpg *.jpeg *.webp *.bmp)")
        if fn:
            img = QImage(fn)
            if not img.isNull():
                self.canvas.set_image(img)

    def _update_info(self):
        n = len(self.canvas.items)
        self.info.setText(f"{self.canvas.img.width()} × {self.canvas.img.height()} px"
                          + (f"  ·  {n} ta belgi — ular ko'rsatma sifatida yuboriladi" if n else
                             "  ·  Ustiga chizib yoki yozib, nima qilishni ko'rsatishingiz mumkin"))

    def _chip(self, k):
        self.template_idx = None if self.template_idx == k else k
        for i, c in enumerate(self.chips):
            c.setChecked(i == self.template_idx)
        self.tpl_desc.setText(TEMPLATES[k][1] if self.template_idx is not None else
                              "Shablon tanlanmasa — \"Real foto\" ishlatiladi.")

    def generate(self):
        if self.worker is not None and self.worker.isRunning():
            return
        cfg = self.ctrl.cfg
        if not cfg.get("api_key"):
            self.status.setText("API kalit kiritilmagan — Sozlamalarni oching.")
            self.ctrl.open_settings()
            if not cfg.get("api_key"):
                return
        cfg["out_size"] = self.size_box.currentText()
        cfg["quality"] = self.quality_box.currentText()
        save_config(cfg)
        flat = self.canvas.render_flat()
        send = flat
        if max(send.width(), send.height()) > 2048:
            send = send.scaled(2048, 2048, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        tpl = TEMPLATES[self.template_idx][2] if self.template_idx is not None else ""
        self._flat = flat
        self._tpl_title = TEMPLATES[self.template_idx][0] if self.template_idx is not None else ""
        w = self.worker = ImageWorker(cfg, image_to_png(send), tpl,
                                      self.prompt.toPlainText(), self.canvas.has_marks())
        w.progress.connect(self.status.setText)
        w.done.connect(self._done)
        w.failed.connect(self._failed)
        self.go.setEnabled(False)
        self.go.setText("  Yaratilmoqda…")
        self.progress.show()
        self.status.setText("Yuborilmoqda…")
        w.start()

    def _reset(self):
        self.go.setEnabled(True)
        self.go.setText("  Real rasm qilish")
        self.progress.hide()

    def _failed(self, msg):
        self._reset()
        self.status.setText(msg)

    def _done(self, png, model, prompt):
        self._reset()
        result = QImage.fromData(png)
        if result.isNull():
            self.status.setText("Javob rasm emas — qayta urinib ko'ring.")
            return
        out = images_subdir(self.ctrl.cfg, "ai")
        res_path = unique_path(out, f"AI_{stamp()}")
        st = os.path.splitext(os.path.basename(res_path))[0][3:]
        try:
            with open(res_path, "wb") as f:
                f.write(png)
            self._flat.save(os.path.join(out, f"AI_{st}_asl.png"))
            with open(os.path.join(out, "tarix.md"), "a", encoding="utf-8") as f:
                f.write(f"## {st}\n\n- Shablon: {self._tpl_title or '—'}\n"
                        f"- Ko'rsatma: {self.prompt.toPlainText().strip() or '—'}\n"
                        f"- Model: {model}\n- Natija: {os.path.basename(res_path)}\n\n")
            self.status.setText(f"Tayyor ✓  Saqlandi: {res_path}")
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Tayyor ✓  (saqlab bo'lmadi: {e})")
        self.ctrl.show_result(result, self._flat, res_path)

    def closeEvent(self, e):
        if self.worker is not None and self.worker.isRunning():
            for sig in (self.worker.done, self.worker.failed, self.worker.progress):
                try:
                    sig.disconnect()
                except Exception:
                    pass
            self.ctrl.keep_worker(self.worker)
        super().closeEvent(e)


class ImageView(QWidget):
    def __init__(self, img: QImage):
        super().__init__()
        self.img = img
        self.setMinimumSize(300, 220)

    def set_image(self, img):
        self.img = img
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        iw, ih = max(1, self.img.width()), max(1, self.img.height())
        sc = min(self.width() / iw, self.height() / ih, 1.5)
        w, h = iw * sc, ih * sc
        p.drawImage(QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h), self.img)
        p.end()


class ResultWindow(CardWindow):
    def __init__(self, ctrl, result: QImage, original: QImage, path: str):
        super().__init__(ctrl, "AI rasm — natija", "sparkle")
        s = self.s
        self.result, self.original, self.path = result, original, path
        self.view = ImageView(result)
        self.view.setObjectName("canvas")
        self.view.setAttribute(Qt.WA_StyledBackground, True)
        self.body.addWidget(self.view, 1)
        where = QLabel(f"Saqlandi: {path}")
        where.setObjectName("muted")
        where.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.addWidget(where)

        row = QHBoxLayout()
        row.setSpacing(int(8 * s))
        self.cmp = QPushButton("  Aslini ko'rish")
        self.cmp.setIcon(svg_icon("eye", C_ICON, int(18 * s)))
        self.cmp.setCheckable(True)
        self.cmp.setCursor(Qt.PointingHandCursor)
        self.cmp.toggled.connect(self._toggle)
        row.addWidget(self.cmp)
        row.addStretch()
        self.msg = QLabel("")
        self.msg.setObjectName("muted")
        row.addWidget(self.msg)
        for icon, text, fn in [("copy", "Nusxalash", self._copy),
                               ("save", "Boshqa joyga…", self._save_as),
                               ("folder", "Papka", lambda: open_images_dir(self.ctrl.cfg)),
                               ("pen", "Yana tahrirlash", self._edit)]:
            b = QPushButton("  " + text)
            b.setIcon(svg_icon(icon, C_ICON, int(18 * s)))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            row.addWidget(b)
        self.body.addLayout(row)
        self.fit_on_screen(int(min(max(result.width(), 700), 1200) + 80),
                           int(min(max(result.height(), 500), 860) + 170))

    def _toggle(self, on):
        self.view.set_image(self.original if on else self.result)
        self.cmp.setText("  Natijani ko'rish" if on else "  Aslini ko'rish")

    def _copy(self):
        QGuiApplication.clipboard().setImage(self.result)
        self.msg.setText("Nusxalandi ✓")

    def _save_as(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Saqlash", self.path, "PNG (*.png);;JPEG (*.jpg)")
        if fn:
            self.msg.setText("Saqlandi ✓" if self.result.save(fn) else "Saqlab bo'lmadi")

    def _edit(self):
        self.ctrl.open_editor(self.result)


# ---------------------------------------------------------------------------
# Skrinshotdan keyin chiqadigan kichik oyna: "Sifatini oshiraymi?"
# ---------------------------------------------------------------------------
class ShotToast(QWidget):
    def __init__(self, ctrl, img: QImage, path: str, screen_geo: QRect):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.ctrl, self.img, self.path = ctrl, img, path
        self.entry = None
        self.enhanced_path = ""
        self.worker = None
        self.s = s = SCALES.get(ctrl.cfg.get("size"), 1.0)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        card = QFrame()
        card.setObjectName("card")
        shadow(card, 40, 12, 50)
        outer.addWidget(card)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(int(14 * s), int(14 * s), int(14 * s), int(14 * s))
        lay.setSpacing(int(14 * s))

        self.thumb = QLabel()
        tw, th = int(130 * s), int(90 * s)
        self.thumb.setFixedSize(tw, th)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setObjectName("thumb")
        self.thumb.setPixmap(QPixmap.fromImage(img).scaled(tw, th, Qt.KeepAspectRatio,
                                                           Qt.SmoothTransformation))
        lay.addWidget(self.thumb)

        col = QVBoxLayout()
        col.setSpacing(int(4 * s))
        top = QHBoxLayout()
        self.title = QLabel("Skrinshot olindi ✓")
        self.title.setObjectName("title")
        top.addWidget(self.title)
        top.addStretch()
        x = card_btn("close", "Yopish", s)
        x.setFixedSize(int(26 * s), int(26 * s))
        x.clicked.connect(self.close)
        top.addWidget(x)
        col.addLayout(top)
        self.sub = QLabel("Nusxalandi" + (" va saqlandi" if path else "") +
                          f"  ·  {img.width()} × {img.height()} px")
        self.sub.setObjectName("muted")
        col.addWidget(self.sub)
        self.question = QLabel("Sifatini oshiraymi?")
        self.question.setObjectName("question")
        col.addWidget(self.question)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(int(5 * s))
        self.progress.hide()
        col.addWidget(self.progress)
        btns = QHBoxLayout()
        btns.setSpacing(int(6 * s))
        self.b1 = QPushButton("Ha, oshir")
        self.b1.setObjectName("primary")
        self.b2 = QPushButton("  AI rasm")
        self.b2.setIcon(svg_icon("sparkle", C_ICON, int(16 * s)))
        self.b3 = QPushButton("Yo'q")
        for b in (self.b1, self.b2, self.b3):
            b.setCursor(Qt.PointingHandCursor)
            btns.addWidget(b)
        self.b1.clicked.connect(self.enhance)
        self.b2.clicked.connect(self.to_ai)
        self.b3.clicked.connect(self.close)
        col.addLayout(btns)
        lay.addLayout(col)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(15000)

        self.adjustSize()
        self.move(screen_geo.right() - self.width() - 8, screen_geo.bottom() - self.height() - 8)

    def enterEvent(self, e):
        self.timer.stop()

    def leaveEvent(self, e):
        if self.worker is None or not self.worker.isRunning():
            self.timer.start(8000)

    def enhance(self):
        self.timer.stop()
        for b in (self.b1, self.b2, self.b3):
            b.setEnabled(False)
        self.question.setText("Sifat oshirilmoqda…")
        self.progress.show()
        self.worker = EnhanceWorker(image_to_png(self.img))
        self.worker.done.connect(self._enhanced)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _enhanced(self, png, w, h):
        self.progress.hide()
        img = QImage.fromData(png)
        self.img = img
        QGuiApplication.clipboard().setImage(img)
        try:
            self.enhanced_path = unique_path(images_subdir(self.ctrl.cfg, "hq"),
                                             f"Sifatli_{stamp()}")
            with open(self.enhanced_path, "wb") as f:
                f.write(png)
            saved = " va saqlandi"
        except Exception:  # noqa: BLE001
            self.enhanced_path = ""
            saved = ""
        self.thumb.setPixmap(QPixmap.fromImage(img).scaled(self.thumb.size(), Qt.KeepAspectRatio,
                                                           Qt.SmoothTransformation))
        if self.entry is not None:
            self.ctrl.update_shot(self.entry, img, self.enhanced_path)
        self.title.setText("Sifati oshirildi ✓")
        self.sub.setText(f"{w} × {h} px  ·  nusxalandi{saved}")
        self.question.setText("Ctrl+V bilan joylashtiring.")
        self._final_buttons()

    def _failed(self, msg):
        self.progress.hide()
        self.question.setText(msg)
        self._final_buttons()

    def _final_buttons(self):
        for b in (self.b1, self.b2, self.b3):
            b.setEnabled(True)
            try:
                b.clicked.disconnect()
            except Exception:
                pass
        self.b1.setText("Ko'rish")
        self.b1.clicked.connect(self._view)
        self.b1.setVisible(bool(self.enhanced_path or self.path))
        self.b2.clicked.connect(self.to_ai)
        self.b3.setText("Yopish")
        self.b3.clicked.connect(self.close)
        self.timer.start(10000)

    def _view(self):
        p = self.enhanced_path or self.path
        if p:
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))

    def to_ai(self):
        self.ctrl.open_editor(self.img)
        self.close()

    def closeEvent(self, e):
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(5000)
        self.ctrl.forget(self)
        super().closeEvent(e)


# ---------------------------------------------------------------------------
# Oxirgi 10 ta skrinshot oynasi (Ctrl+V+S / Ctrl+Shift+V)
# ---------------------------------------------------------------------------
class ShotTile(QWidget):
    def __init__(self, picker, idx, entry, w, h):
        super().__init__()
        self.picker, self.idx, self.entry = picker, idx, entry
        self.setFixedSize(w, h)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        cur = self.picker.idx == self.idx
        marked = self.idx in self.picker.marked
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.fillPath(path, QColor("#F1F3F7"))
        pm = self.entry["thumb"]
        tw, th = pm.width() / pm.devicePixelRatio(), pm.height() / pm.devicePixelRatio()
        sc = min((r.width() - 10) / tw, (r.height() - 10) / th, 1.0)
        dw, dh = tw * sc, th * sc
        p.save()
        p.setClipPath(path)
        p.drawPixmap(QRectF(r.center().x() - dw / 2, r.center().y() - dh / 2, dw, dh), pm,
                     QRectF(0, 0, pm.width(), pm.height()))
        p.restore()
        accent = QColor(self.picker.accent)
        if cur or marked:
            p.setPen(QPen(accent, 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 12, 12)
        # raqam
        badge = QRectF(r.left() + 6, r.top() + 6, 22, 22)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(17, 24, 39, 200))
        p.drawRoundedRect(badge, 11, 11)
        f = QFont("Segoe UI")
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(badge, Qt.AlignCenter, str((self.idx + 1) % 10))
        if marked:
            ck = QRectF(r.right() - 28, r.top() + 6, 22, 22)
            p.setPen(Qt.NoPen)
            p.setBrush(accent)
            p.drawEllipse(ck)
            p.setPen(QPen(QColor(accent_text(self.picker.accent)), 2.4, Qt.SolidLine, Qt.RoundCap,
                          Qt.RoundJoin))
            p.drawPolyline(QPolygonF([QPointF(ck.left() + 6, ck.center().y()),
                                      QPointF(ck.left() + 10, ck.bottom() - 7),
                                      QPointF(ck.right() - 5, ck.top() + 7)]))
        p.end()

    def enterEvent(self, e):
        self.picker.set_idx(self.idx)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if e.modifiers() & Qt.ControlModifier:
                self.picker.toggle(self.idx)
            else:
                self.picker.paste([self.idx])
        elif e.button() == Qt.RightButton:
            self.picker.toggle(self.idx)


class RecentPicker(QWidget):
    COLS = 5

    def __init__(self, ctrl, shots, no_focus):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if no_focus:
            flags |= Qt.WindowDoesNotAcceptFocus
        super().__init__(None, flags)
        self.ctrl, self.shots = ctrl, list(shots)      # eng yangisi birinchi
        self.idx = 0
        self.marked = set()
        self.done = False
        self.s = s = SCALES.get(ctrl.cfg.get("size"), 1.0)
        self.accent = ctrl.cfg.get("color", C_ACCENT)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        if no_focus:
            self.setAttribute(Qt.WA_ShowWithoutActivating)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        card = QFrame()
        card.setObjectName("card")
        shadow(card, 44, 14, 55)
        outer.addWidget(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(int(18 * s), int(14 * s), int(14 * s), int(14 * s))
        lay.setSpacing(int(10 * s))

        top = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(svg_pixmap("camera", self.accent, int(22 * s)))
        top.addWidget(ic)
        t = QLabel("Oxirgi skrinshotlar")
        t.setObjectName("title")
        top.addWidget(t)
        top.addStretch()
        self.left_lbl = QLabel()
        self.left_lbl.setObjectName("muted")
        top.addWidget(self.left_lbl)
        x = card_btn("close", "Yopish (Esc)", s)
        x.clicked.connect(self.close)
        top.addWidget(x)
        lay.addLayout(top)

        grid = QGridLayout()
        grid.setSpacing(int(8 * s))
        tw, th = int(176 * s), int(118 * s)
        self.tiles = []
        for i, e in enumerate(self.shots):
            tile = ShotTile(self, i, e, tw, th)
            grid.addWidget(tile, i // self.COLS, i % self.COLS)
            self.tiles.append(tile)
        lay.addLayout(grid)

        hint = QLabel("Bosing — shu rasm joylanadi  ·  ← → ↑ ↓ — tanlash  ·  Bo'sh joy / o'ng tugma — "
                      "belgilash  ·  Enter — belgilanganlar (yo'q bo'lsa hammasi)  ·  1–0 — raqam "
                      "bo'yicha  ·  Esc — yopish")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        row = QHBoxLayout()
        row.addStretch()
        self.one_btn = QPushButton("Tanlanganini joylash")
        self.one_btn.clicked.connect(lambda: self.paste([self.idx]))
        self.all_btn = QPushButton("Hammasini joylash  (Enter)")
        self.all_btn.setObjectName("primary")
        self.all_btn.clicked.connect(self.paste_enter)
        for b in (self.one_btn, self.all_btn):
            b.setCursor(Qt.PointingHandCursor)
            row.addWidget(b)
        lay.addLayout(row)

        self.tick = QTimer(self)
        self.tick.timeout.connect(self._update_left)
        self.tick.start(1000)
        self.idle = QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.timeout.connect(self.close)
        self.idle.start(30000)
        self._update_left()
        self._update_buttons()

        self.adjustSize()
        scr = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        self.move(g.center().x() - self.width() // 2, g.center().y() - self.height() // 2)

    def _update_left(self):
        left = max(0, int(PICKER_SECONDS - (time.monotonic() - self.ctrl.last_shot_time)))
        self.left_lbl.setText(f"faol: {left // 60}:{left % 60:02d}  ·  {len(self.shots)} ta")

    def _update_buttons(self):
        n = len(self.marked)
        self.all_btn.setText(f"Belgilangan {n} tasini joylash  (Enter)" if n
                             else "Hammasini joylash  (Enter)")

    def set_idx(self, i):
        if 0 <= i < len(self.shots) and i != self.idx:
            self.idx = i
            for t in self.tiles:
                t.update()

    def move_by(self, d):
        self.idle.start(30000)
        self.set_idx(max(0, min(len(self.shots) - 1, self.idx + d)))

    def toggle(self, i=None):
        self.idle.start(30000)
        i = self.idx if i is None else i
        self.marked.symmetric_difference_update({i})
        self.tiles[i].update()
        self._update_buttons()

    def paste_enter(self):
        if self.marked:
            idxs = sorted(self.marked, reverse=True)          # eskisidan yangisiga
        else:
            idxs = list(range(len(self.shots) - 1, -1, -1))
        self.paste(idxs)

    def paste(self, idxs):
        if self.done:
            return
        self.done = True
        imgs = [self.shots[i]["img"] for i in idxs if 0 <= i < len(self.shots)]
        self.close()
        self.ctrl.paste_images(imgs)

    def handle_key(self, vk):
        """Klaviatura tutqichidan chaqiriladi: True — tugma shu oynaga tegishli."""
        if self.done or not self.isVisible():
            return False
        acts = {0x25: lambda: self.move_by(-1), 0x27: lambda: self.move_by(1),
                0x26: lambda: self.move_by(-self.COLS), 0x28: lambda: self.move_by(self.COLS),
                0x20: self.toggle, 0x0D: self.paste_enter, 0x1B: self.close}
        for d in range(10):
            idx = (d - 1) % 10
            if idx < len(self.shots):
                acts[0x30 + d] = (lambda k=idx: self.paste([k]))
                acts[0x60 + d] = (lambda k=idx: self.paste([k]))
        fn = acts.get(vk)
        if fn is None:
            return False
        QTimer.singleShot(0, fn)
        return True

    def keyPressEvent(self, e):
        k = e.key()
        m = {Qt.Key_Left: 0x25, Qt.Key_Right: 0x27, Qt.Key_Up: 0x26, Qt.Key_Down: 0x28,
             Qt.Key_Space: 0x20, Qt.Key_Return: 0x0D, Qt.Key_Enter: 0x0D, Qt.Key_Escape: 0x1B}
        vk = m.get(k)
        if vk is None and Qt.Key_0 <= k <= Qt.Key_9:
            vk = 0x30 + (k - Qt.Key_0)
        if vk is None or not self.handle_key(vk):
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.ctrl.picker_closed(self)
        super().closeEvent(e)


class EdgeLine(QWidget):
    """Yashiringanda ekran chetida qoladigan shaffof uzun chiziq."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(APP_NAME)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # deyarli ko'rinmas fon — Windows'da sichqonchani "ushlab" turishi uchun
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))
        c = QColor(self.win.accent)
        c.setAlphaF(self.win.cfg.get("line_opacity", 55) / 100.0)
        p.setBrush(c)
        p.setPen(Qt.NoPen)
        lw = max(4, int(6 * self.win.s))
        x = 2 if self.win.edge_side() == "left" else self.width() - lw - 2
        p.drawRoundedRect(QRectF(x, 0, lw, self.height()), lw / 2, lw / 2)
        p.end()

    def enterEvent(self, e):
        self.win.expand()

    def mousePressEvent(self, e):
        self.win.expand()


class MainWindow(QWidget):
    MARGIN = 18        # soya uchun bo'sh joy
    GAP = 10           # panel va ikonkalar orasidagi masofa
    EDGE_GAP = 6       # ekran chetidan masofa (yashirinish yoqilganda)

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.cfg = ctrl.cfg
        self.s = s = SCALES.get(self.cfg.get("size"), 1.0)
        self.mode = None
        self.worker = None
        self.drag_off = None
        self.panel_side = "left"
        self._req = None
        self.accent = self.cfg.get("color", C_ACCENT)
        self.auto_hide = self.cfg.get("auto_hide", True)
        self.collapsed = False
        self.anim = None
        self._out_since = None
        self.busy = False                 # skrinshot olinayotganda yashirinmasin
        self._born = time.monotonic()     # ochilganda bir marta ko'rinib, keyin fonga o'tadi

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(app_icon()))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apply_flags(self.cfg.get("pinned", True))

        self.bubble = HoverBubble(s)
        self.rail = self._build_rail()
        self.panel = self._build_panel()
        self.panel.hide()
        self.line = EdgeLine(self)
        self.line.hide()

        # kursor chiqib ketganini kuzatuvchi taymer
        self.watch = QTimer(self)
        self.watch.setInterval(200)
        self.watch.timeout.connect(self._tick)
        self.watch.start()

        for m in MODES:
            QShortcut(QKeySequence(f"Ctrl+{m['shortcut']}"), self,
                      activated=lambda k=m["key"]: self.open_mode(k))
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.send)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.send)
        QShortcut(QKeySequence("Escape"), self, activated=self.close_panel)

        self.rail_pos = self._initial_rail_pos()
        self.layout_children()

    # ---------------- qurilish ----------------
    def _hook_hover(self, btn):
        btn.hovered.connect(lambda b: self.show_bubble_text(b, b.label, b.shortcut))
        btn.unhovered.connect(lambda b: self.bubble.hide())

    def _sep(self):
        sep = QFrame()
        sep.setObjectName("sep")
        sep.setFixedHeight(1)
        return sep

    def _build_rail(self):
        s = self.s
        rail = QFrame(self)
        rail.setObjectName("rail")
        shadow(rail)
        pad = int(7 * s)
        rl = QVBoxLayout(rail)
        rl.setContentsMargins(pad, int(6 * s), pad, int(8 * s))
        rl.setSpacing(int(4 * s))

        # 1) tutqich + X
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        top.addWidget(GripHandle(self, s))
        x = RailButton("close", "Yopish (dasturdan chiqish)", s)
        x.setFixedSize(int(22 * s), int(28 * s))
        x.isz = int(15 * s)
        x.setIconSize(QSize(x.isz, x.isz))
        x.setObjectName("xbtn")
        x.refresh()
        x.clicked.connect(self.ctrl.quit)
        self._hook_hover(x)
        top.addWidget(x)
        rl.addLayout(top)

        # 2) qadash — tepada
        self.pin_btn = RailButton("pin", "Hamma oynalar ustida qadash", s, checkable=True)
        self.pin_btn.setChecked(self.cfg.get("pinned", True))
        self.pin_btn.clicked.connect(self.toggle_pin)
        self._hook_hover(self.pin_btn)
        rl.addWidget(self.pin_btn)

        # 3) funksiyalar
        self.mode_buttons = {}
        enabled = [m for m in MODES if m["key"] in self.cfg.get("modes", [])]
        if enabled:
            rl.addSpacing(int(2 * s))
            rl.addWidget(self._sep())
            rl.addSpacing(int(2 * s))
        for m in enabled:
            b = RailButton(m["icon"], m["title"], s, f"Ctrl+{m['shortcut']}", checkable=True)
            b.clicked.connect(lambda _=False, k=m["key"]: self.toggle_mode(k))
            self._hook_hover(b)
            rl.addWidget(b)
            self.mode_buttons[m["key"]] = b

        # 4) skrinshot va AI rasm
        tools = [t for t in EXTRA_TOOLS if t["key"] in self.cfg.get("modes", [])]
        if tools:
            rl.addSpacing(int(2 * s))
            rl.addWidget(self._sep())
            rl.addSpacing(int(2 * s))
        for t in tools:
            b = RailButton(t["icon"], t["title"], s, t["shortcut"])
            b.clicked.connect(lambda _=False, k=t["key"]:
                              self.ctrl.start_capture("ai" if k == "aiimage" else "shot"))
            self._hook_hover(b)
            rl.addWidget(b)

        # 5) sozlamalar
        rl.addSpacing(int(2 * s))
        rl.addWidget(self._sep())
        rl.addSpacing(int(2 * s))
        b = RailButton("settings", "Sozlamalar", s)
        b.clicked.connect(self.open_settings)
        self._hook_hover(b)
        rl.addWidget(b)

        rail.setFixedWidth(int(46 * s) + 2 * pad)
        rail.setFixedHeight(rail.sizeHint().height())
        return rail

    def _build_panel(self):
        s = self.s
        p = QFrame(self)
        p.setObjectName("panel")
        p.setFixedSize(int(400 * s), int(520 * s))
        shadow(p)
        lay = QVBoxLayout(p)
        lay.setContentsMargins(int(18 * s), int(14 * s), int(14 * s), int(14 * s))
        lay.setSpacing(int(10 * s))

        head = QHBoxLayout()
        self.p_icon = QLabel()
        head.addWidget(self.p_icon)
        head.addSpacing(int(4 * s))
        self.p_title = QLabel()
        self.p_title.setObjectName("title")
        head.addWidget(self.p_title)
        head.addStretch()
        self.lang_box = QComboBox()
        self.lang_box.addItems(list(LANGS))
        self.lang_box.setCurrentText(self.cfg.get("lang", "O'zbekcha (lotin)"))
        self.lang_box.currentTextChanged.connect(self._lang_changed)
        head.addWidget(self.lang_box)
        close = self._small_btn("close", "Panelni yopish (Esc)")
        close.clicked.connect(self.close_panel)
        head.addWidget(close)
        lay.addLayout(head)

        self.input = QPlainTextEdit()
        self.input.setObjectName("input")
        lay.addWidget(self.input, 1)

        row = QHBoxLayout()
        row.setSpacing(int(4 * s))
        paste = self._small_btn("paste", "Buferdan qo'yish")
        paste.clicked.connect(self.paste_clipboard)
        row.addWidget(paste)
        clear = self._small_btn("trash", "Tozalash")
        clear.clicked.connect(self.clear_all)
        row.addWidget(clear)
        row.addStretch()
        hint = QLabel("Ctrl+Enter")
        hint.setObjectName("muted")
        row.addWidget(hint)
        self.send_btn = QPushButton("  Yuborish")
        self.send_btn.setObjectName("primary")
        self.send_btn.setIcon(svg_icon("send", accent_text(self.accent), int(16 * s), 2.2))
        self.send_btn.setIconSize(QSize(int(16 * s), int(16 * s)))
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.send)
        row.addWidget(self.send_btn)
        lay.addLayout(row)

        self.output = QPlainTextEdit()
        self.output.setObjectName("output")
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Javob shu yerda chiqadi…")
        lay.addWidget(self.output, 1)

        row2 = QHBoxLayout()
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        row2.addWidget(self.status, 1)
        self.google_btn = self._small_btn("globe", "Google'da qidirish")
        self.google_btn.clicked.connect(self.google_search)
        row2.addWidget(self.google_btn)
        copy = self._small_btn("copy", "Javobni nusxalash")
        copy.clicked.connect(self.copy_output)
        row2.addWidget(copy)
        lay.addLayout(row2)
        return p

    def _small_btn(self, icon, tip):
        s = self.s
        b = QToolButton()
        b.setObjectName("small")
        isz = int(18 * s)
        b.setIcon(svg_icon(icon, C_ICON, isz, 2.3))
        b.setIconSize(QSize(isz, isz))
        b.setFixedSize(int(32 * s), int(32 * s))
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        return b

    # ---------------- joylashuv (qo'ygan joyida qotib turadi) ----------------
    def apply_flags(self, pinned):
        # Qt.Tool — taskbarda ko'rinmaydi (trey ikonkasi orqali boshqariladi)
        flags = Qt.FramelessWindowHint | Qt.Tool
        if pinned:
            flags |= Qt.WindowStaysOnTopHint
        visible = self.isVisible()
        self.setWindowFlags(flags)
        if visible:
            self.show()

    @staticmethod
    def _screen_for(point):
        scr = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
        return scr.availableGeometry()

    def _initial_rail_pos(self):
        rx, ry = self.cfg.get("rx"), self.cfg.get("ry")
        size = self.rail.size()
        if rx is not None and ry is not None:
            rect = QRect(QPoint(int(rx), int(ry)), size)
            if QGuiApplication.screenAt(rect.center()) is not None:
                return self._clamp(rect.topLeft())
        g = QGuiApplication.primaryScreen().availableGeometry()
        return QPoint(g.right() - size.width() - 12, g.top() + (g.height() - size.height()) // 3)

    def _clamp(self, pos):
        size = self.rail.size()
        g = self._screen_for(QRect(pos, size).center())
        x = max(g.left(), min(pos.x(), g.right() + 1 - size.width()))
        y = max(g.top(), min(pos.y(), g.bottom() + 1 - size.height()))
        if self.auto_hide:
            # yashirinish yoqilgan bo'lsa — yaqin chetga yopishadi (balandligi erkin)
            if x + size.width() // 2 < g.center().x():
                x = g.left() + self.EDGE_GAP
            else:
                x = g.right() + 1 - size.width() - self.EDGE_GAP
        return QPoint(x, y)

    def edge_side(self):
        rail_g = QRect(self.rail_pos, self.rail.size())
        g = self._screen_for(rail_g.center())
        return "left" if rail_g.center().x() < g.center().x() else "right"

    # ---------------- chetga kirib ketish / chiqib kelish ----------------
    def _tick(self):
        """Kursor dasturdan chiqib ketsa — chetga yashirinadi."""
        busy = (self.worker is not None and self.worker.isRunning())
        if (not self.auto_hide or self.collapsed or self.drag_off is not None
                or busy or self.busy or not self.isVisible()
                or time.monotonic() - self._born < 4.0
                or (self.anim is not None
                            and self.anim.state() == QParallelAnimationGroup.Running)
                or QApplication.activeModalWidget() is not None
                or QApplication.activePopupWidget() is not None):
            self._out_since = None
            return
        inside = self.frameGeometry().adjusted(-4, -4, 4, 4).contains(QCursor.pos())
        if inside:
            self._out_since = None
            return
        self.bubble.hide()
        # panel ochiq va foydalanuvchi hali shu oynada ishlayotgan bo'lsa — kutamiz
        if self.mode is not None and self.isActiveWindow():
            self._out_since = None
            return
        now = time.monotonic()
        if self._out_since is None:
            self._out_since = now
            return
        delay = 0.5 if self.mode is None else 1.0
        if now - self._out_since >= delay:
            self._out_since = None
            self.collapse()

    def _offscreen_x(self):
        """Ikonkalar paneli butunlay ekran chetidan tashqarida bo'ladigan oyna x koordinatasi."""
        g = self._screen_for(QRect(self.rail_pos, self.rail.size()).center())
        rail_off = self.rail.x()  # oyna ichidagi siljish
        if self.edge_side() == "left":
            return g.left() - self.rail.width() - rail_off - 4
        return g.right() + 1 - rail_off + 4

    def _run_anim(self, end_pos, start_op, end_op, on_done=None):
        if self.anim is not None:
            self.anim.stop()
        grp = QParallelAnimationGroup(self)
        a = QPropertyAnimation(self, b"pos")
        a.setDuration(230)
        a.setEasingCurve(QEasingCurve.OutCubic)
        a.setEndValue(end_pos)
        grp.addAnimation(a)
        o = QPropertyAnimation(self, b"windowOpacity")
        o.setDuration(230)
        o.setStartValue(start_op)
        o.setEndValue(end_op)
        grp.addAnimation(o)
        if on_done:
            grp.finished.connect(on_done)
        self.anim = grp
        grp.start()

    def collapse(self):
        if self.collapsed:
            return
        self.bubble.hide()
        if self.mode is not None:     # ish tugadi — panel yopiladi (matn saqlanib qoladi)
            self.close_panel()
        self.collapsed = True
        self._run_anim(QPoint(self._offscreen_x(), self.y()), 1.0, 0.0, self._show_line)

    def _show_line(self):
        if not self.collapsed:
            return
        self.rail.hide()
        rail_g = QRect(self.rail_pos, self.rail.size())
        g = self._screen_for(rail_g.center())
        hit_w = max(10, int(12 * self.s))
        line_h = max(90, int(rail_g.height() * 0.6))
        y = rail_g.center().y() - line_h // 2
        x = g.left() if self.edge_side() == "left" else g.right() + 1 - hit_w
        self.setFixedSize(hit_w, line_h)
        self.move(x, y)
        self.line.setGeometry(0, 0, hit_w, line_h)
        self.line.show()
        self.setWindowOpacity(1.0)

    def expand(self):
        if not self.collapsed:
            return
        self.collapsed = False
        self._out_since = None
        self.line.hide()
        self.rail.show()
        self.layout_children()
        target = self.pos()
        self.move(self._offscreen_x(), target.y())
        self.setWindowOpacity(0.0)
        self._run_anim(target, 0.0, 1.0)

    def changeEvent(self, e):
        if e.type() == QEvent.WindowStateChange and self.isMinimized():
            # taskbardan bosilganda yo'qolib qolmasin
            QTimer.singleShot(0, lambda: (self.showNormal(), self.expand()))
        elif e.type() == QEvent.ActivationChange and self.isActiveWindow() and self.collapsed:
            QTimer.singleShot(0, self.expand)   # taskbardagi ikonkani bosganda
        super().changeEvent(e)

    def layout_children(self):
        """Ikonkalar paneli joyidan qimirlamaydi; ish paneli bo'sh tomonga ochiladi."""
        rail_g = QRect(self.rail_pos, self.rail.size())
        scr = self._screen_for(rail_g.center())
        bbox = QRect(rail_g)
        panel_g = None
        if self.mode is not None:
            pw, ph = self.panel.width(), self.panel.height()
            if self.panel_side == "left":
                px = rail_g.left() - self.GAP - pw
            else:
                px = rail_g.right() + 1 + self.GAP
            py = max(scr.top() + 4, min(rail_g.top(), scr.bottom() - ph - 4))
            panel_g = QRect(px, py, pw, ph)
            bbox = bbox.united(panel_g)
        m = self.MARGIN
        win = bbox.adjusted(-m, -m, m, m)
        self.setFixedSize(win.size())
        self.move(win.topLeft())
        self.rail.move(rail_g.topLeft() - win.topLeft())
        if panel_g is not None:
            self.panel.move(panel_g.topLeft() - win.topLeft())

    def _choose_panel_side(self):
        rail_g = QRect(self.rail_pos, self.rail.size())
        scr = self._screen_for(rail_g.center())
        self.panel_side = "left" if rail_g.center().x() > scr.center().x() else "right"

    def start_drag(self, gpos):
        self.bubble.hide()
        self.drag_off = gpos - self.rail_pos

    def drag_to(self, gpos):
        if self.drag_off is None:
            return
        new = gpos - self.drag_off
        self.move(self.pos() + (new - self.rail_pos))
        self.rail_pos = new

    def end_drag(self):
        if self.drag_off is None:
            return
        self.drag_off = None
        self.rail_pos = self._clamp(self.rail_pos)
        if self.mode is not None:
            self._choose_panel_side()
        self.layout_children()
        self.cfg["rx"], self.cfg["ry"] = self.rail_pos.x(), self.rail_pos.y()
        save_config(self.cfg)

    def show_bubble_text(self, widget, text, shortcut):
        if self.drag_off is not None:
            return
        self.bubble.prepare(text, shortcut)
        rail_tl = self.rail.mapToGlobal(QPoint(0, 0))
        wy = widget.mapToGlobal(QPoint(0, 0)).y()
        anchor = QRect(rail_tl.x(), wy, self.rail.width(), widget.height())
        scr = self._screen_for(anchor.center())
        bw = self.bubble.width()
        fits_right = anchor.right() + bw <= scr.right()
        fits_left = anchor.left() - bw >= scr.left()
        go_right = anchor.center().x() < scr.center().x()
        if self.mode is not None:  # panel ochiq bo'lsa — uning ustiga emas, boshqa tomonga
            go_right = self.panel_side == "left"
        if go_right and not fits_right:
            go_right = False
        elif not go_right and not fits_left:
            go_right = True
        x = anchor.right() - 4 if go_right else anchor.left() - bw + 4
        y = anchor.center().y() - self.bubble.height() // 2 + 2
        self.bubble.move(x, y)
        self.bubble.show()
        self.bubble.raise_()

    # ---------------- harakatlar ----------------
    def _set_checked(self, key):
        for k, b in self.mode_buttons.items():
            b.blockSignals(True)
            b.setChecked(k == key)
            b.blockSignals(False)
            b.refresh()

    def toggle_mode(self, key):
        if self.mode == key:
            self.close_panel()
        else:
            self.open_mode(key)

    def open_mode(self, key):
        if key not in self.mode_buttons:
            return
        if self.collapsed:
            self.expand()
            QTimer.singleShot(260, lambda: self.open_mode(key))
            return
        m = MODE_BY_KEY[key]
        was_open = self.mode is not None
        self.mode = key
        self._set_checked(key)
        isz = int(22 * self.s)
        self.p_icon.setPixmap(svg_pixmap(m["icon"], self.accent, isz))
        self.p_title.setText(m["title"])
        self.input.setPlaceholderText(m["placeholder"])
        self.input.viewport().update()          # eski yozuv qolib ketmasligi uchun
        self.lang_box.setVisible(key == "translate")
        self.google_btn.setVisible(key == "search")
        if not was_open:
            self._choose_panel_side()
            self.panel.show()
            self.layout_children()
        self.panel.update()
        self.bring_front()
        self.input.setFocus()

    def close_panel(self):
        if self.mode is None:
            return
        self.mode = None
        self._set_checked(None)
        self.panel.hide()
        self.layout_children()

    def toggle_pin(self):
        pinned = self.pin_btn.isChecked()
        self.cfg["pinned"] = pinned
        save_config(self.cfg)
        self.apply_flags(pinned)
        self.layout_children()
        self.pin_btn.refresh()
        self.status.setText("Hamma oynalar ustida turadi." if pinned else "Qadash o'chirildi.")

    def _lang_changed(self, text):
        self.cfg["lang"] = text
        save_config(self.cfg)

    def clear_all(self):
        self.input.clear()
        self.output.clear()
        self.status.setText("")

    def paste_clipboard(self):
        txt = QGuiApplication.clipboard().text()
        if txt:
            self.input.setPlainText(txt)
            self.input.setFocus()

    def copy_output(self):
        txt = self.output.toPlainText().strip()
        if txt:
            QGuiApplication.clipboard().setText(txt)
            self.status.setText("Nusxalandi ✓")

    def google_search(self):
        q = self.output.toPlainText().strip() or self.input.toPlainText().strip()
        if q:
            QDesktopServices.openUrl(QUrl("https://www.google.com/search?q=" +
                                          urllib.parse.quote(q)))

    def open_settings(self):
        self.bubble.hide()
        dlg = SettingsDialog(self, self.cfg, self.s)
        if dlg.exec():
            v = dlg.values()
            need_rebuild = any(v[k] != self.cfg.get(k)
                               for k in ("size", "modes", "color", "auto_hide"))
            hook_changed = v["hook_keys"] != self.cfg.get("hook_keys")
            if v["autostart"] != self.cfg.get("autostart"):
                try:
                    set_autostart(v["autostart"])
                except Exception as e:  # noqa: BLE001
                    v["autostart"] = self.cfg.get("autostart", False)
                    self.status.setText(f"Avto-ishga tushirishni sozlab bo'lmadi: {e}")
            self.cfg.update(v)
            save_config(self.cfg)
            self.line.update()
            if hook_changed:
                self.ctrl.update_hook()
            if need_rebuild:
                QTimer.singleShot(0, self.ctrl.rebuild)
            elif self.mode:
                self.status.setText("Sozlamalar saqlandi ✓")

    def send(self):
        if self.mode is None or (self.worker and self.worker.isRunning()):
            return
        text = self.input.toPlainText().strip()
        if not text:
            self.status.setText("Avval matn yozing.")
            return
        if not self.cfg.get("api_key"):
            self.status.setText("API kalit kiritilmagan — Sozlamalarni oching.")
            self.open_settings()
            if not self.cfg.get("api_key") or self.mode is None:
                return
        m = MODE_BY_KEY[self.mode]
        lang = self.lang_box.currentText()
        system = m["prompt"].format(lang=LANGS[lang]) + PLAIN_RULE
        new_alpha = self.mode == "newalpha" or (self.mode == "translate" and "yangi" in lang)
        self._req = (m["title"], lang if self.mode == "translate" else "", text, new_alpha)
        self.send_btn.setEnabled(False)
        self.send_btn.setText("  Kuting…")
        self.status.setText("Javob kutilmoqda…")
        self.output.clear()
        self.worker = Worker(self.cfg["api_key"], self.cfg.get("model", DEFAULT_MODEL),
                             system, text)
        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(self._on_fail)
        self.worker.start()

    def _on_done(self, answer):
        title, extra, text, new_alpha = self._req
        answer = clean_output(answer, single_line=(title == MODE_BY_KEY["search"]["title"]))
        if new_alpha:
            answer = to_new_alphabet(answer)
        self.output.setPlainText(answer)
        self._reset_send()
        try:
            save_history(title, extra, text, answer)
            self.status.setText("Tayyor ✓  Yozishma saqlandi.")
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Tayyor ✓  (saqlab bo'lmadi: {e})")

    def _on_fail(self, msg):
        self._reset_send()
        self.status.setText(msg)

    def _reset_send(self):
        self.send_btn.setEnabled(True)
        self.send_btn.setText("  Yuborish")

    def bring_front(self):
        self._born = time.monotonic()      # bir necha soniya ko'rinib tursin
        self.show()
        self.raise_()
        self.activateWindow()
        if self.collapsed:
            self.expand()

    def dispose(self):
        self.watch.stop()
        if self.anim is not None:
            self.anim.stop()
        self.bubble.close()
        self.bubble.deleteLater()
        self.close()
        self.deleteLater()


ARROW_PATH = ""


def ensure_arrow_image():
    """Ro'yxat (combobox) strelkasi uchun kichik rasm yaratadi."""
    global ARROW_PATH
    d = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "arrow.png")
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           'stroke="#3F4350" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
           '<path d="m6 9 6 6 6-6"/></svg>')
    QSvgRenderer(QByteArray(svg.encode())).render(p)
    p.end()
    pm.save(path)
    ARROW_PATH = path.replace("\\", "/")


def make_style(s: float, accent: str = C_ACCENT) -> str:
    on_accent = accent_text(accent)
    accent_hover = QColor(accent).darker(125).name()

    def px(v):
        return f"{max(1, round(v * s))}px"
    return f"""
* {{ font-family: "Segoe UI", "Inter", Arial; font-size: {px(14)}; color: {C_TEXT}; }}
#rail, #card {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: {px(22)}; }}
#vsep {{ background: {C_BORDER}; margin: 0 {px(4)}; }}
QToolButton#tool {{ border-radius: {px(10)}; }}
QToolButton#tool:hover, QToolButton#tool:checked {{ background: {C_HOVER}; }}
#toolbar {{ background: #F6F7FA; border: 1px solid {C_BORDER}; border-radius: {px(14)}; }}
#canvas, #thumb {{ background: #F1F3F7; border-radius: {px(14)}; }}
#side {{ background: #FFFFFF; }}
#question {{ font-size: {px(15)}; font-weight: 700; }}
QPushButton#chip {{ padding: {px(7)} {px(8)}; font-weight: 600; font-size: {px(13)}; }}
QPushButton#chip:checked {{ background: {accent}; color: {on_accent}; border: 1px solid {accent}; }}
QProgressBar {{ background: {C_HOVER}; border: none; border-radius: {px(3)}; }}
QProgressBar::chunk {{ background: {accent}; border-radius: {px(3)}; }}
#sep {{ background: {C_BORDER}; margin: 0 {px(8)}; }}
RailButton, QToolButton {{ border: none; border-radius: {px(13)}; background: transparent; }}
RailButton:hover, QToolButton#small:hover {{ background: {C_HOVER}; }}
RailButton:checked {{ background: {C_HOVER}; }}
RailButton#xbtn {{ border-radius: {px(8)}; }}
RailButton#xbtn:hover {{ background: #FDE8E8; }}
#panel {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: {px(22)}; }}
#title {{ font-size: {px(16)}; font-weight: 700; }}
#section {{ font-size: {px(12)}; font-weight: 700; color: {C_MUTED}; text-transform: uppercase; }}
#muted {{ color: {C_MUTED}; font-size: {px(12)}; }}
#credit {{ font-size: {px(13)}; }}
QPlainTextEdit {{ background: #F6F7FA; border: 1px solid {C_BORDER}; border-radius: {px(14)};
    padding: {px(8)} {px(10)}; font-size: {px(14)}; selection-background-color: #C7D2FE; }}
QPlainTextEdit:focus {{ border: 1px solid #9CA3AF; background: #FFFFFF; }}
#output {{ background: #FAFAFC; }}
QPushButton {{ border: 1px solid {C_BORDER}; border-radius: {px(12)}; padding: {px(8)} {px(16)};
    background: #FFFFFF; font-weight: 600; }}
QPushButton:hover {{ background: {C_HOVER}; }}
QPushButton#primary {{ background: {accent}; color: {on_accent}; border: none; }}
QPushButton#primary:hover {{ background: {accent_hover}; }}
QPushButton#primary:disabled {{ background: #9CA3AF; }}
QPushButton#seg {{ padding: {px(7)} {px(10)}; font-weight: 600; }}
QPushButton#seg:checked {{ background: {accent}; color: {on_accent}; border: 1px solid {accent}; }}
QComboBox {{ border: 1px solid {C_BORDER}; border-radius: {px(10)}; padding: {px(5)} {px(10)};
    background: #FFFFFF; min-width: {px(120)}; }}
QComboBox::drop-down {{ border: none; width: {px(26)}; subcontrol-origin: padding;
    subcontrol-position: center right; }}
QComboBox::down-arrow {{ image: url("{ARROW_PATH}"); width: {px(12)}; height: {px(12)}; }}
QComboBox QAbstractItemView {{ border: 1px solid {C_BORDER}; selection-background-color: {C_HOVER};
    selection-color: {C_TEXT}; background: white; outline: 0; }}
QLineEdit {{ border: 1px solid {C_BORDER}; border-radius: {px(10)}; padding: {px(8)} {px(10)}; }}
QLineEdit:focus {{ border: 1px solid #9CA3AF; }}
QCheckBox {{ padding: {px(4)} 0; spacing: {px(8)}; }}
QDialog, #settingsBody, QScrollArea {{ background: #FFFFFF; }}
#bubble {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: {px(16)}; }}
#bubbleText {{ font-size: {px(15)}; font-weight: 500; color: {C_TEXT}; }}
#keycap {{ background: #FFFFFF; border: 1px solid #DADDE5; border-bottom: 2px solid #D0D4DD;
    border-radius: {px(7)}; padding: {px(2)} {px(8)}; min-width: {px(14)};
    font-family: Consolas, "Courier New"; font-size: {px(13)}; color: #6B7084; }}
QToolTip {{ background: white; color: {C_TEXT}; border: 1px solid {C_BORDER}; padding: 4px 8px; }}
QScrollBar:vertical {{ width: {px(8)}; background: transparent; }}
QScrollBar::handle:vertical {{ background: #D5D8E0; border-radius: {px(4)}; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


class Controller:
    """Hamma narsani boshqaradi: menyu oynasi, skrinshot, AI rasm oynalari, tugmalar."""

    def __init__(self, app):
        self.app = app
        self.cfg = load_config()
        save_config(self.cfg)
        self.win = None
        self.windows = []          # tahrirlash / natija / skrinshot oynachalari
        self.workers = []
        self.capturing = False
        self.overlay = None
        self.capture_mode = "shot"
        self.shots = []              # oxirgi 10 ta skrinshot (eng yangisi birinchi)
        self.last_shot_time = -1e9
        self.picker = None

        self.tray = QSystemTrayIcon(QIcon(app_icon()))
        self.tray.setToolTip(f"{APP_NAME} — skrinshot: PrintScreen")
        menu = QMenu()
        menu.addAction("Ko'rsatish", lambda: self.win and self.win.bring_front())
        menu.addAction("Skrinshot olish", lambda: self.start_capture("shot"))
        menu.addAction("Oxirgi skrinshotlar", lambda: self.open_picker(from_hook=False))
        menu.addAction("AI rasm (skrinshotdan)", lambda: self.start_capture("ai"))
        menu.addAction("AI rasm (fayldan)", self.open_file)
        menu.addSeparator()
        menu.addAction("Rasmlar papkasi", lambda: open_images_dir(self.cfg))
        menu.addAction("Yozishmalar papkasi", open_history_dir)
        menu.addAction("Sozlamalar", self.open_settings)
        menu.addSeparator()
        menu.addAction("Chiqish", self.quit)
        self._menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.win.bring_front() if r == QSystemTrayIcon.Trigger and self.win
            else None)
        self.tray.show()
        if "--autostart" not in sys.argv:
            self.tray.showMessage(
                APP_NAME, "Ishga tushdi. Menyu ekran chetida — kursorni chetdagi chiziqqa olib "
                "boring. Skrinshot: PrintScreen yoki Win+Shift+S.",
                QSystemTrayIcon.Information, 6000)

        # tugmalar: PrintScreen / Win+Shift+S (+ zaxira Ctrl+Alt+S)
        self.hook = None
        self.update_hook()
        self.hotkey = GlobalHotkey(lambda: self.start_capture("shot"))
        app.installNativeEventFilter(self.hotkey)

        # kompyuter yonganda o'zi ishga tushsin (yo'l o'zgargan bo'lsa ham yangilanadi)
        if self.cfg.get("autostart"):
            try:
                set_autostart(True)
            except Exception:
                pass
        self.rebuild()

    def update_hook(self):
        if self.hook is not None:
            self.hook.unhook()
            self.hook = None
        if self.cfg.get("hook_keys", True):
            self.hook = KeyboardHook(lambda: self.start_capture("shot"),
                                     lambda: self.open_picker(from_hook=True),
                                     self.picker_active)
            windows_snip_key(self.cfg, True)      # Windows vositasi PrintScreen'ni olmasin
        else:
            windows_snip_key(self.cfg, False)     # avvalgi holatiga qaytaramiz

    def rebuild(self):
        old = self.win
        if not ARROW_PATH:
            ensure_arrow_image()
        self.app.setStyleSheet(make_style(SCALES.get(self.cfg.get("size"), 1.0),
                                          self.cfg.get("color", C_ACCENT)))
        self.win = MainWindow(self)
        self.win.show()
        if old is not None:
            old.dispose()

    # ---------------- skrinshot ----------------
    def start_capture(self, mode="shot"):
        if self.capturing:
            return
        self.capturing = True
        self.capture_mode = mode
        for w in list(self.windows):
            if isinstance(w, ShotToast):
                w.close()
        if self.win is not None:
            self.win.busy = True
            self.win.bubble.hide()
            self.win.hide()
        QTimer.singleShot(250, self._grab)

    def _grab(self):
        try:
            screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
            pm = screen.grabWindow(0)
            self.overlay = CaptureOverlay(screen, pm)
            self.overlay.captured.connect(self._captured)
            self.overlay.cancelled.connect(self._capture_done)
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()
            self.overlay.setFocus()
        except Exception:
            self._capture_done()

    def _capture_done(self):
        geo = None
        if self.overlay is not None:
            geo = self.overlay.geometry()
        self.capturing = False
        self.overlay = None
        if self.win is not None:
            self.win.busy = False
            self.win.show()
        return geo

    def _captured(self, img):
        screen_geo = self.overlay.geometry() if self.overlay is not None else None
        self._capture_done()
        if self.capture_mode == "ai":
            self.open_editor(img)
            return
        # oddiy skrinshot: nusxalash (Ctrl+V) + saqlash, keyin so'rash
        QGuiApplication.clipboard().setImage(img)
        path = ""
        if self.cfg.get("shot_autosave", True):
            try:
                path = unique_path(images_subdir(self.cfg, "shot"), f"Skrinshot_{stamp()}")
                if not img.save(path):
                    path = ""
            except Exception:
                path = ""
        entry = self.add_shot(img, path)
        if self.cfg.get("shot_ask", True):
            scr = QGuiApplication.screenAt(screen_geo.center()) if screen_geo else None
            g = (scr or QGuiApplication.primaryScreen()).availableGeometry()
            t = ShotToast(self, img, path, g)
            t.entry = entry
            self.windows.append(t)
            t.show()
            t.raise_()

    # ---------------- oxirgi skrinshotlar ----------------
    def add_shot(self, img, path):
        thumb = QPixmap.fromImage(img.scaled(400, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        entry = {"img": img, "path": path, "thumb": thumb}
        self.shots.insert(0, entry)
        del self.shots[PICKER_MAX:]
        self.last_shot_time = time.monotonic()
        return entry

    def update_shot(self, entry, img, path):
        """Sifati oshirilgan bo'lsa — ro'yxatda yangisi turadi."""
        if entry in self.shots:
            entry["img"] = img
            entry["path"] = path or entry["path"]
            entry["thumb"] = QPixmap.fromImage(img.scaled(400, 260, Qt.KeepAspectRatio,
                                                          Qt.SmoothTransformation))

    def picker_active(self):
        return bool(self.shots) and time.monotonic() - self.last_shot_time < PICKER_SECONDS

    def open_picker(self, from_hook=True):
        if self.capturing or not self.shots:
            return
        if self.picker is not None:
            self.picker.close()
            return
        no_focus = from_hook and self.hook is not None and self.hook.ok
        self.picker = RecentPicker(self, self.shots, no_focus)
        if no_focus:
            self.hook.router = self.picker.handle_key
        self.picker.show()
        self.picker.raise_()
        if not no_focus:
            self.picker.activateWindow()
            self.picker.setFocus()

    def picker_closed(self, picker):
        if self.picker is picker:
            self.picker = None
        if self.hook is not None:
            self.hook.router = None

    def paste_images(self, imgs):
        """Rasmlarni faol oynaga ketma-ket joylaydi (har biri: buferga + Ctrl+V)."""
        imgs = [i for i in imgs if i is not None and not i.isNull()]
        if not imgs:
            return
        cb = QGuiApplication.clipboard()

        def finish():
            if self.shots:                       # Ctrl+V yana oxirgi skrinshotni joylasin
                cb.setImage(self.shots[0]["img"])

        if sys.platform != "win32":
            cb.setImage(imgs[-1])
            return

        def step(i=0):
            if i >= len(imgs):
                QTimer.singleShot(400, finish)
                return
            cb.setImage(imgs[i])
            QTimer.singleShot(120, lambda: (send_ctrl_v(),
                                            QTimer.singleShot(450, lambda: step(i + 1))))
        QTimer.singleShot(180, step)

    def open_file(self):
        fn, _ = QFileDialog.getOpenFileName(None, "Rasmni tanlang", "",
                                            "Rasmlar (*.png *.jpg *.jpeg *.webp *.bmp)")
        if fn:
            img = QImage(fn)
            if not img.isNull():
                self.open_editor(img)

    # ---------------- oynalar ----------------
    def open_editor(self, img: QImage):
        w = EditorWindow(self, img)
        self.windows.append(w)
        w.show()
        w.raise_()
        w.activateWindow()

    def show_result(self, result, original, path):
        w = ResultWindow(self, result, original, path)
        self.windows.append(w)
        w.show()
        w.raise_()
        w.activateWindow()

    def forget(self, w):
        if w in self.windows:
            self.windows.remove(w)

    def keep_worker(self, worker):
        """Oyna yopilsa ham ishlayotgan so'rov tugaguncha saqlab turamiz."""
        self.workers.append(worker)
        worker.finished.connect(lambda: self.workers.remove(worker)
                                if worker in self.workers else None)

    def open_settings(self):
        if self.win is not None:
            if self.win.collapsed:
                self.win.expand()
            self.win.open_settings()

    def quit(self):
        if self.win is not None:
            self.cfg["rx"], self.cfg["ry"] = self.win.rail_pos.x(), self.win.rail_pos.y()
        save_config(self.cfg)
        if self.hook is not None:
            self.hook.unhook()
        if self.picker is not None:
            self.picker.close()
        windows_snip_key(self.cfg, False)         # dastur yopilsa — Windows vositasi qaytadi
        self.hotkey.unregister()
        self.tray.hide()
        QApplication.quit()


def main():
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    # faqat bitta nusxa ishlasin: dastur qayta ochilsa — mavjudini ko'rsatamiz
    name = "AIYordamchi-" + re.sub(r"\W", "", os.environ.get("USERNAME") or
                                   os.environ.get("USER") or "user")
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(400):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(400)
        sock.disconnectFromServer()
        return
    QLocalServer.removeServer(name)
    server = QLocalServer()
    server.listen(name)
    app._server = server
    app._ctrl = ctrl = Controller(app)

    def on_new():
        conn = server.nextPendingConnection()
        if conn is not None:
            conn.disconnected.connect(conn.deleteLater)
        if ctrl.win is not None:
            ctrl.win.bring_front()
    server.newConnection.connect(on_new)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
