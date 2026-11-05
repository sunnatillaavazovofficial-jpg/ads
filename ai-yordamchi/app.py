"""
AI Yordamchi — ekranda hamma dasturlar ustida turadigan, ChatGPT API asosidagi kichik yordamchi.

Funksiyalar (Sozlamalarda yoqib/o'chirsa bo'ladi):
  1. Tarjima                 (Ctrl+1)
  2. Grammatikani to'g'rilash(Ctrl+2)  – xatolarni topib, matnni ma'noli qilib to'g'rilaydi
  3. Yangi alifbo (Ö Ğ Ş Ç)  (Ctrl+3)  – xatolarni to'g'rilab, yangi o'zbek lotin alifbosida yozadi
  4. Kirill                  (Ctrl+4)  – xatolarni to'g'rilab, o'zbek kirill yozuvida yozadi
  5. Inglizcha qidiruv       (Ctrl+5)  – narsa nomi/xususiyatini ingliz tilida nima deb izlashni aytadi

Oyna qayerga qo'yilsa, o'sha joyda qotib turadi. O'lchamini Sozlamalardan
kichik/katta qilish mumkin. Barcha yozishmalar "Hujjatlar/AI Yordamchi" papkasida saqlanadi.

by Sunnatilla Designer — https://sunnatilla-designer.uz/
"""

import datetime
import json
import os
import re
import sys
import urllib.parse

import requests
from PySide6.QtCore import (QByteArray, QPoint, QRect, QRectF, QSize,
                            QStandardPaths, Qt, QThread, QTimer, QUrl, Signal)
from PySide6.QtGui import (QColor, QDesktopServices, QGuiApplication, QIcon,
                           QKeySequence, QLinearGradient, QPainter, QPixmap,
                           QShortcut)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox,
                               QComboBox, QDialog, QFrame,
                               QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QPlainTextEdit, QPushButton,
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
C_ICON = "#3F4350"
C_ICON_ACTIVE = "#000000"
C_HOVER = "#EEF0F5"
C_ACCENT = "#111827"
C_TEXT = "#111827"
C_MUTED = "#8A8FA3"

SCALES = {"Kichik": 0.8, "O'rta": 1.0, "Katta": 1.2, "Juda katta": 1.4}

# ---------------------------------------------------------------------------
# Ikonkalar — qalin, to'q uslubda (lupa rasmidagidek)
# {c} — ikonka rangi, {bg} — fon rangi
# ---------------------------------------------------------------------------
ICONS = {
    "translate": '<path d="M2.5 5h11M8 2.5V5M5 5c1 4 3.6 7.2 7.2 8.6M11 5c-1 4.2-4 7.6-8 9.2"/>'
                 '<path d="m12.5 21.5 4.5-10 4.5 10M14.2 17.8h5.6"/>',
    "grammar": '<path d="m3.5 17.5 6-14 6 14M5.8 12.6h7.4"/>'
               '<path d="m13.8 19 2.6 2.6L22 16"/>',
    "newalpha": '<rect x="1.5" y="4" width="21" height="16" rx="4.5" fill="{c}" stroke="none"/>'
                '<text x="12" y="16.6" font-size="11" font-weight="bold" text-anchor="middle" '
                'font-family="Arial" fill="{bg}" stroke="none">Öz</text>',
    "cyrillic": '<rect x="1.5" y="4" width="21" height="16" rx="4.5" fill="{c}" stroke="none"/>'
                '<text x="12" y="16.6" font-size="11" font-weight="bold" text-anchor="middle" '
                'font-family="Arial" fill="{bg}" stroke="none">Ўз</text>',
    "search": '<circle cx="10" cy="10" r="7" stroke-width="2.9"/>'
              '<path d="M15.3 15.3 20.6 20.6" stroke-width="4.4"/>'
              '<path d="M6.5 9.8a3.5 3.5 0 0 1 3.3-3.3" stroke-width="1.9" stroke-linecap="butt"/>',
    "pin": '<path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 '
           '15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 '
           '0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/>',
    "pin_on": '<path d="M12 17v5"/><path fill="{c}" d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 '
              '2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l'
              '-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 '
              '0 0 1 1 1z"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 '
              '3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 '
                '1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 '
                '0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 '
                '0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 '
                '1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 '
                '0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 '
                '1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 '
                '1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 '
                '1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "close": '<path d="M18 6 6 18" stroke-width="2.8"/><path d="m6 6 12 12" stroke-width="2.8"/>',
    "grip": '<circle cx="8" cy="5" r="1.7" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="5" r="1.7" fill="{c}" stroke="none"/>'
            '<circle cx="8" cy="12" r="1.7" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="12" r="1.7" fill="{c}" stroke="none"/>'
            '<circle cx="8" cy="19" r="1.7" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="19" r="1.7" fill="{c}" stroke="none"/>',
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4'
            'c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    "paste": '<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14'
             'a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    "trash": '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>'
             '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 '
             '1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "logo": '<path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9z" '
            'fill="{c}"/><path d="M19 15l.8 1.9 1.9.8-1.9.8L19 20.4l-.8-1.9-1.9-.8 1.9-.8z" '
            'fill="{c}"/>',
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
                  "If the text is Uzbek Latin, use oʻ, gʻ and ’ correctly.\n"
                  "Answer strictly in this format:\n"
                  "✅ To‘g‘rilangan matn:\n<corrected text>\n\n"
                  "📝 Xatolar:\n- <short explanation in Uzbek Latin of each fix>\n"
                  "If there are no errors, say so under 'Xatolar'.",
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
                  "Identify exactly what it is and tell the user what to search for in ENGLISH.\n"
                  "Answer strictly in this format:\n"
                  "🔎 English name: <the most precise English name>\n"
                  "📌 Izoh: <1-2 sentences in Uzbek Latin explaining what it is>\n"
                  "🔍 Search queries:\n1. <query>\n2. <query>\n3. <query>\n"
                  "🏷 Alternative names: <comma separated synonyms / technical terms>",
    },
]
MODE_BY_KEY = {m["key"]: m for m in MODES}


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
           "modes": [m["key"] for m in MODES]}
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
    cfg["modes"] = [k for k in cfg.get("modes", []) if k in MODE_BY_KEY]
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
                json={"model": self.model, "temperature": 0.3,
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
        self.setPixmap(svg_pixmap("grip", "#9EA3B0", isz))
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
        self.setMinimumWidth(int(460 * s))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(int(24 * s), int(20 * s), int(24 * s), int(18 * s))
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

        # Pastki qator: muallif + tugmalar
        lay.addSpacing(int(14 * s))
        bottom = QHBoxLayout()
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
        lay.addLayout(bottom)

    @staticmethod
    def _section(text):
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def values(self):
        size = self.size_group.checkedButton().text() if self.size_group.checkedButton() \
            else "O'rta"
        modes = [k for k, c in self.mode_checks.items() if c.isChecked()]
        return {"api_key": self.key.text().strip(),
                "model": self.model.currentText().strip() or DEFAULT_MODEL,
                "size": size, "modes": modes}


# ---------------------------------------------------------------------------
# Asosiy oyna
# ---------------------------------------------------------------------------
class MainWindow(QWidget):
    MARGIN = 18        # soya uchun bo'sh joy
    GAP = 10           # panel va ikonkalar orasidagi masofa

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

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(app_icon()))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apply_flags(self.cfg.get("pinned", True))

        self.bubble = HoverBubble(s)
        self.rail = self._build_rail()
        self.panel = self._build_panel()
        self.panel.hide()

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

        # 4) sozlamalar
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
        self.send_btn.setIcon(svg_icon("send", "#FFFFFF", int(16 * s), 2.2))
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
        return QPoint(x, y)

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
        m = MODE_BY_KEY[key]
        was_open = self.mode is not None
        self.mode = key
        self._set_checked(key)
        isz = int(22 * self.s)
        self.p_icon.setPixmap(svg_pixmap(m["icon"], C_ACCENT, isz))
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
        txt = self.output.toPlainText()
        if self.mode == "grammar" and "✅" in txt:
            m = re.search(r"✅[^\n]*\n(.*?)(\n\s*📝|$)", txt, re.S)
            if m:
                txt = m.group(1).strip()
        if txt:
            QGuiApplication.clipboard().setText(txt)
            self.status.setText("Nusxalandi ✓")

    def google_search(self):
        txt = self.output.toPlainText()
        m = re.search(r"English name:\s*(.+)", txt)
        q = m.group(1).strip() if m else self.input.toPlainText().strip()
        if q:
            QDesktopServices.openUrl(QUrl("https://www.google.com/search?q=" +
                                          urllib.parse.quote(q)))

    def open_settings(self):
        self.bubble.hide()
        dlg = SettingsDialog(self, self.cfg, self.s)
        if dlg.exec():
            v = dlg.values()
            need_rebuild = v["size"] != self.cfg.get("size") or v["modes"] != self.cfg.get("modes")
            self.cfg.update(v)
            save_config(self.cfg)
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
        system = m["prompt"].format(lang=LANGS[lang])
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
        self.show()
        self.raise_()
        self.activateWindow()

    def dispose(self):
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


def make_style(s: float) -> str:
    def px(v):
        return f"{max(1, round(v * s))}px"
    return f"""
* {{ font-family: "Segoe UI", "Inter", Arial; font-size: {px(14)}; color: {C_TEXT}; }}
#rail {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: {px(22)}; }}
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
QPushButton#primary {{ background: {C_ACCENT}; color: white; border: none; }}
QPushButton#primary:hover {{ background: #000000; }}
QPushButton#primary:disabled {{ background: #9CA3AF; }}
QPushButton#seg {{ padding: {px(7)} {px(10)}; font-weight: 600; }}
QPushButton#seg:checked {{ background: {C_ACCENT}; color: white; border: 1px solid {C_ACCENT}; }}
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
QDialog {{ background: #FFFFFF; }}
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
    """Oynani boshqaradi: o'lcham yoki funksiyalar o'zgarsa — qayta quradi."""

    def __init__(self, app):
        self.app = app
        self.cfg = load_config()
        self.win = None
        self.tray = QSystemTrayIcon(QIcon(app_icon()))
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        menu.addAction("Ko'rsatish", lambda: self.win and self.win.bring_front())
        menu.addAction("Yozishmalar papkasi", open_history_dir)
        menu.addAction("Sozlamalar", lambda: self.win and self.win.open_settings())
        menu.addSeparator()
        menu.addAction("Chiqish", self.quit)
        self._menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.win.bring_front() if r == QSystemTrayIcon.Trigger and self.win
            else None)
        self.tray.show()
        self.rebuild()

    def rebuild(self):
        old = self.win
        if not ARROW_PATH:
            ensure_arrow_image()
        self.app.setStyleSheet(make_style(SCALES.get(self.cfg.get("size"), 1.0)))
        self.win = MainWindow(self)
        self.win.show()
        if old is not None:
            old.dispose()

    def quit(self):
        if self.win is not None:
            self.cfg["rx"], self.cfg["ry"] = self.win.rail_pos.x(), self.win.rail_pos.y()
        save_config(self.cfg)
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
    ctrl = Controller(app)  # noqa: F841
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
