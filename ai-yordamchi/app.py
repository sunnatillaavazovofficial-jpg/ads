"""
AI Yordamchi — ekran chetiga yopishib turadigan, ChatGPT API asosidagi kichik yordamchi.

Imkoniyatlar:
  1. Tarjima          (Ctrl+1)
  2. Grammatika       (Ctrl+2)  – xatolarni topib, matnni ma'noli qilib to'g'rilaydi
  3. O'zbekcha lotin  (Ctrl+3)  – yangi lotin alifbosida yozib beradi
  4. Türkçe           (Ctrl+4)  – turk tilida yozib beradi
  5. Inglizcha qidiruv(Ctrl+5)  – narsa nomi/xususiyatini ingliz tilida nima deb izlashni aytadi

Oyna hamma dasturlar ustida turadi (qadash tugmasi), chap yoki o'ng chetga sudrab
qo'yilsa — ikonkalar ham o'sha tomonga o'tadi. Barcha yozishmalar
"Hujjatlar/AI Yordamchi" papkasida saqlanadi.
"""

import datetime
import json
import os
import re
import sys
import urllib.parse

import requests
from PySide6.QtCore import (QByteArray, QEasingCurve, QPoint, QPropertyAnimation,
                            QRect, QRectF, QSize, QStandardPaths, Qt, QThread, QTimer,
                            QUrl, Signal)
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QGuiApplication,
                           QIcon, QKeySequence, QPainter, QPixmap, QShortcut)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFrame,
                               QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QPlainTextEdit, QPushButton,
                               QSystemTrayIcon, QToolButton, QVBoxLayout,
                               QWidget)

APP_NAME = "AI Yordamchi"
API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

# ---------------------------------------------------------------------------
# Ranglar
# ---------------------------------------------------------------------------
C_BG = "#FFFFFF"
C_BORDER = "#E6E8EE"
C_ICON = "#7C8193"
C_ICON_ACTIVE = "#111827"
C_HOVER = "#EEF0F5"
C_ACCENT = "#4F46E5"
C_TEXT = "#111827"
C_MUTED = "#8A8FA3"

# ---------------------------------------------------------------------------
# Ikonkalar (SVG, lucide uslubida)
# ---------------------------------------------------------------------------
ICONS = {
    "translate": '<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/>'
                 '<path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>',
    "grammar": '<path d="m6 16 6-12 6 12"/><path d="M8 12h8"/><path d="m16 20 2 2 4-4"/>',
    "uz": '<rect x="2" y="4.5" width="20" height="15" rx="4"/>'
          '<text x="12" y="16.2" font-size="10" font-weight="800" text-anchor="middle" '
          'font-family="Arial" fill="{c}" stroke="none">UZ</text>',
    "tr": '<rect x="2" y="4.5" width="20" height="15" rx="4"/>'
          '<text x="12" y="16.2" font-size="10" font-weight="800" text-anchor="middle" '
          'font-family="Arial" fill="{c}" stroke="none">TR</text>',
    "search": '<circle cx="10.5" cy="10.5" r="7"/><path d="m21 21-5.5-5.5"/>'
              '<path d="M7.5 10.5h6"/><path d="M10.5 7.5v6"/>',
    "pin": '<path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 '
           '15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 '
           '0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/>',
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
    "close": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "power": '<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.77.04"/>',
    "grip": '<circle cx="9" cy="5" r="1" fill="{c}"/><circle cx="15" cy="5" r="1" fill="{c}"/>'
            '<circle cx="9" cy="12" r="1" fill="{c}"/><circle cx="15" cy="12" r="1" fill="{c}"/>'
            '<circle cx="9" cy="19" r="1" fill="{c}"/><circle cx="15" cy="19" r="1" fill="{c}"/>',
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


def svg_icon(name: str, color: str = C_ICON, size: int = 22, stroke: float = 1.8) -> QIcon:
    body = ICONS[name].replace("{c}", color)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
           f'stroke-linejoin="round">{body}</svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    scale = 3
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    renderer.render(p)
    p.end()
    pm.setDevicePixelRatio(scale)
    return QIcon(pm)


def app_icon(size: int = 256) -> QPixmap:
    """Dastur ikonkasi: gradientli kvadrat ichida uchqun."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    from PySide6.QtGui import QLinearGradient
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
# Rejimlar va promptlar
# ---------------------------------------------------------------------------
LANGS = {
    "O'zbekcha (lotin)": "Uzbek, written in the modern Uzbek Latin alphabet (o‘, g‘, sh, ch, ng, ’)",
    "Türkçe": "Turkish (Türkiye Türkçesi)",
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
                  "naturally and meaningfully. Keep the ORIGINAL language and meaning. If the "
                  "text is Uzbek, use the modern Uzbek Latin alphabet (o‘, g‘, sh, ch, ’).\n"
                  "Answer strictly in this format:\n"
                  "✅ To‘g‘rilangan matn:\n<corrected text>\n\n"
                  "📝 Xatolar:\n- <short explanation in Uzbek Latin of each fix>\n"
                  "If there are no errors, say so under 'Xatolar'.",
    },
    {
        "key": "uzbek", "icon": "uz", "title": "O'zbekcha (yangi lotin)", "shortcut": "3",
        "placeholder": "Kirill, rus yoki boshqa tildagi matn — yangi lotinda yozib beraman…",
        "prompt": "Rewrite the user's text in correct literary Uzbek using the official modern "
                  "Uzbek LATIN alphabet (with o‘, g‘, sh, ch, ng and the tutuq belgisi ’). If "
                  "the text is in Cyrillic Uzbek, transliterate it accurately; if it is in "
                  "another language, translate it into Uzbek. Fix any grammar or spelling "
                  "mistakes. Output ONLY the resulting Uzbek text.",
    },
    {
        "key": "turkish", "icon": "tr", "title": "Türkçe yozish", "shortcut": "4",
        "placeholder": "Matnni yozing — turk tilida to'g'ri yozib beraman…",
        "prompt": "Write the user's text in correct, natural Turkish (Türkiye Türkçesi) with "
                  "proper Turkish characters (ç, ğ, ı, İ, ö, ş, ü). Translate it if it is in "
                  "another language and fix all grammar and spelling mistakes. "
                  "Output ONLY the Turkish text.",
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
    cfg = {"api_key": "", "model": DEFAULT_MODEL, "side": "right", "y": None,
           "pinned": True, "lang": "O'zbekcha (lotin)"}
    try:
        with open(config_path(), encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if not cfg.get("api_key"):
        cfg["api_key"] = os.environ.get("OPENAI_API_KEY", "")
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
    """Kursor ikonka ustiga borganda chiqadigan yozuv (rasmdagidek: nom + tugmalar)."""

    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 14)
        self.card = QFrame()
        self.card.setObjectName("bubble")
        shadow(self.card, 24, 6, 45)
        outer.addWidget(self.card)
        lay = QHBoxLayout(self.card)
        lay.setContentsMargins(16, 8, 10, 8)
        lay.setSpacing(6)
        self.label = QLabel()
        self.label.setObjectName("bubbleText")
        lay.addWidget(self.label)
        lay.addSpacing(14)
        self.keys = []
        for _ in range(2):
            k = QLabel()
            k.setObjectName("keycap")
            k.setAlignment(Qt.AlignCenter)
            lay.addWidget(k)
            self.keys.append(k)

    def show_for(self, text, shortcut, anchor_rect, side):
        self.label.setText(text)
        parts = shortcut.split("+") if shortcut else []
        for i, k in enumerate(self.keys):
            k.setVisible(i < len(parts))
            if i < len(parts):
                k.setText(parts[i])
        self.adjustSize()
        y = anchor_rect.center().y() - self.height() // 2 + 2
        if side == "left":
            x = anchor_rect.right() + 2
        else:
            x = anchor_rect.left() - self.width() - 2
        self.move(x, y)
        self.show()
        self.raise_()


class RailButton(QToolButton):
    hovered = Signal(object)
    unhovered = Signal(object)

    def __init__(self, icon_name, label, shortcut="", checkable=False):
        super().__init__()
        self.icon_name, self.label, self.shortcut = icon_name, label, shortcut
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 46)
        self.setIconSize(QSize(22, 22))
        self.setFocusPolicy(Qt.NoFocus)
        self.toggled.connect(self.refresh)
        self.refresh()

    def refresh(self, *_):
        on = self.isChecked() or self.underMouse()
        color = C_ACCENT if (self.isChecked() and self.icon_name == "pin") else \
            (C_ICON_ACTIVE if on else C_ICON)
        self.setIcon(svg_icon(self.icon_name, color))

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

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setFixedSize(46, 22)
        self.setAlignment(Qt.AlignCenter)
        self.setPixmap(svg_icon("grip", "#B5B9C6", 18).pixmap(QSize(18, 18)))
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.win.start_drag(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        self.win.drag_to(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        self.win.end_drag()

    def enterEvent(self, e):
        self.win.show_bubble_text(self, "Sudrab chapga / o'ngga qo'ying", "")

    def leaveEvent(self, e):
        self.win.bubble.hide()


class SettingsDialog(QDialog):
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Sozlamalar")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(8)
        t = QLabel("Sozlamalar")
        t.setObjectName("title")
        lay.addWidget(t)
        lay.addSpacing(6)
        lay.addWidget(QLabel("OpenAI API kalit:"))
        self.key = QLineEdit(cfg.get("api_key", ""))
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("sk-...")
        lay.addWidget(self.key)
        link = QLabel('<a href="https://platform.openai.com/api-keys">API kalitni olish →</a>')
        link.setOpenExternalLinks(True)
        link.setObjectName("muted")
        lay.addWidget(link)
        lay.addSpacing(6)
        lay.addWidget(QLabel("Model:"))
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.addItems(["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"])
        self.model.setCurrentText(cfg.get("model", DEFAULT_MODEL))
        lay.addWidget(self.model)
        lay.addSpacing(6)
        info = QLabel(f"Yozishmalar saqlanadigan papka:\n{history_dir()}")
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addSpacing(10)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("Bekor qilish")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Saqlash")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

    def values(self):
        return self.key.text().strip(), self.model.currentText().strip() or DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Asosiy oyna
# ---------------------------------------------------------------------------
class MainWindow(QWidget):
    MARGIN = 16        # soya uchun bo'sh joy
    EDGE_GAP = 6       # ekran chetidan masofa
    PANEL_W = 400
    PANEL_H = 540

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.side = self.cfg.get("side", "right")
        self.mode = None
        self.worker = None
        self.drag_offset = None
        self.anim = None

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(app_icon()))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apply_flags(self.cfg.get("pinned", True))

        self.bubble = HoverBubble()

        # --- ikonkalar paneli (rail) ---
        self.rail = QFrame()
        self.rail.setObjectName("rail")
        shadow(self.rail)
        rl = QVBoxLayout(self.rail)
        rl.setContentsMargins(7, 6, 7, 9)
        rl.setSpacing(4)
        rl.addWidget(GripHandle(self), 0, Qt.AlignHCenter)

        self.mode_buttons = {}
        for m in MODES:
            b = RailButton(m["icon"], m["title"], f"Ctrl+{m['shortcut']}", checkable=True)
            b.clicked.connect(lambda _=False, k=m["key"]: self.toggle_mode(k))
            self._hook_hover(b)
            rl.addWidget(b)
            self.mode_buttons[m["key"]] = b

        sep = QFrame()
        sep.setObjectName("sep")
        sep.setFixedHeight(1)
        rl.addSpacing(4)
        rl.addWidget(sep)
        rl.addSpacing(4)

        self.pin_btn = RailButton("pin", "Ustida qadash", "", checkable=True)
        self.pin_btn.setChecked(self.cfg.get("pinned", True))
        self.pin_btn.clicked.connect(self.toggle_pin)
        self._hook_hover(self.pin_btn)
        rl.addWidget(self.pin_btn)

        b = RailButton("folder", "Yozishmalar papkasi")
        b.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(history_dir())))
        self._hook_hover(b)
        rl.addWidget(b)

        b = RailButton("settings", "Sozlamalar (API kalit)")
        b.clicked.connect(self.open_settings)
        self._hook_hover(b)
        rl.addWidget(b)

        b = RailButton("power", "Chiqish")
        b.clicked.connect(self.quit_app)
        self._hook_hover(b)
        rl.addWidget(b)

        self.rail.setFixedWidth(60)
        self.rail.adjustSize()

        # --- ish paneli ---
        self.panel = self._build_panel()
        self.panel.hide()

        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        self.layout_.setSpacing(10)
        self.layout_.setAlignment(Qt.AlignTop)

        # --- klaviatura tugmalari ---
        for m in MODES:
            QShortcut(QKeySequence(f"Ctrl+{m['shortcut']}"), self,
                      activated=lambda k=m["key"]: self.open_mode(k))
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.send)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.send)
        QShortcut(QKeySequence("Escape"), self, activated=self.close_panel)

        self._setup_tray()
        self.relayout()
        y = self.cfg.get("y")
        self.reposition(y=y)

    # ---------------- qurilish ----------------
    def _hook_hover(self, btn):
        btn.hovered.connect(lambda b: self.show_bubble_text(b, b.label, b.shortcut))
        btn.unhovered.connect(lambda b: self.bubble.hide())

    def _build_panel(self):
        p = QFrame()
        p.setObjectName("panel")
        p.setFixedSize(self.PANEL_W, self.PANEL_H)
        shadow(p)
        lay = QVBoxLayout(p)
        lay.setContentsMargins(18, 14, 14, 16)
        lay.setSpacing(10)

        head = QHBoxLayout()
        self.p_icon = QLabel()
        head.addWidget(self.p_icon)
        self.p_title = QLabel()
        self.p_title.setObjectName("title")
        head.addWidget(self.p_title)
        head.addStretch()
        self.lang_box = QComboBox()
        self.lang_box.addItems(list(LANGS))
        self.lang_box.setCurrentText(self.cfg.get("lang", "O'zbekcha (lotin)"))
        self.lang_box.currentTextChanged.connect(self._lang_changed)
        head.addWidget(self.lang_box)
        close = self._small_btn("close", "Yopish (Esc)")
        close.clicked.connect(self.close_panel)
        head.addWidget(close)
        lay.addLayout(head)

        self.input = QPlainTextEdit()
        self.input.setObjectName("input")
        lay.addWidget(self.input, 1)

        row = QHBoxLayout()
        row.setSpacing(4)
        paste = self._small_btn("paste", "Buferdan qo'yish")
        paste.clicked.connect(self.paste_clipboard)
        row.addWidget(paste)
        clear = self._small_btn("trash", "Tozalash")
        clear.clicked.connect(lambda: (self.input.clear(), self.output.clear(),
                                       self.status.setText("")))
        row.addWidget(clear)
        row.addStretch()
        hint = QLabel("Ctrl+Enter")
        hint.setObjectName("muted")
        row.addWidget(hint)
        self.send_btn = QPushButton("  Yuborish")
        self.send_btn.setObjectName("primary")
        self.send_btn.setIcon(svg_icon("send", "#FFFFFF", 16))
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
        b = QToolButton()
        b.setObjectName("small")
        b.setIcon(svg_icon(icon, C_ICON, 18))
        b.setIconSize(QSize(18, 18))
        b.setFixedSize(32, 32)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        return b

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(QIcon(app_icon()), self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        menu.addAction("Ko'rsatish", self.bring_front)
        menu.addAction("Yozishmalar papkasi",
                       lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(history_dir())))
        menu.addAction("Sozlamalar", self.open_settings)
        menu.addSeparator()
        menu.addAction("Chiqish", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.bring_front() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    # ---------------- joylashuv ----------------
    def apply_flags(self, pinned):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if pinned:
            flags |= Qt.WindowStaysOnTopHint
        visible = self.isVisible()
        self.setWindowFlags(flags)
        if visible:
            self.show()

    def relayout(self):
        """Ikonkalar ekran qaysi chetida bo'lsa — o'sha tomonda turadi."""
        while self.layout_.count():
            self.layout_.takeAt(0)
        order = [self.rail, self.panel] if self.side == "left" else [self.panel, self.rail]
        for w in order:
            self.layout_.addWidget(w, 0, Qt.AlignTop)
        panel_on = self.mode is not None
        w = self.rail.width() + 2 * self.MARGIN
        h = self.rail.sizeHint().height() + 2 * self.MARGIN
        if panel_on:
            w += self.PANEL_W + self.layout_.spacing()
            h = max(h, self.PANEL_H + 2 * self.MARGIN)
        self.setFixedSize(w, h)

    def screen_geo(self):
        scr = QGuiApplication.screenAt(self.frameGeometry().center()) or \
            QGuiApplication.primaryScreen()
        return scr.availableGeometry()

    def target_pos(self, y=None):
        g = self.screen_geo()
        if y is None:
            y = self.y()
        y = max(g.top() - self.MARGIN, min(y, g.bottom() - self.height() + self.MARGIN))
        if self.side == "left":
            x = g.left() - self.MARGIN + self.EDGE_GAP
        else:
            x = g.right() + 1 - self.width() + self.MARGIN - self.EDGE_GAP
        return QPoint(x, y)

    def reposition(self, y=None, animate=False):
        if y is None and not self.isVisible():
            g = QGuiApplication.primaryScreen().availableGeometry()
            y = g.top() + (g.height() - self.height()) // 3
        pos = self.target_pos(y)
        if animate:
            self.anim = QPropertyAnimation(self, b"pos", self)
            self.anim.setDuration(220)
            self.anim.setEasingCurve(QEasingCurve.OutCubic)
            self.anim.setEndValue(pos)
            self.anim.start()
        else:
            self.move(pos)

    def start_drag(self, gpos):
        self.bubble.hide()
        self.drag_offset = gpos - self.pos()

    def drag_to(self, gpos):
        if self.drag_offset is not None:
            self.move(gpos - self.drag_offset)

    def end_drag(self):
        if self.drag_offset is None:
            return
        self.drag_offset = None
        g = self.screen_geo()
        rail_center = self.rail.mapToGlobal(self.rail.rect().center()).x()
        new_side = "left" if rail_center < g.center().x() else "right"
        if new_side != self.side:
            self.side = new_side
            self.relayout()
        self.reposition(animate=True)
        self.cfg["side"] = self.side
        self.cfg["y"] = self.target_pos().y()
        save_config(self.cfg)

    def show_bubble_text(self, widget, text, shortcut):
        if self.drag_offset is not None:
            return
        top_left = widget.mapToGlobal(QPoint(0, 0))
        rail_tl = self.rail.mapToGlobal(QPoint(0, 0))
        anchor = QRect(rail_tl.x(), top_left.y(), self.rail.width(), widget.height())
        self.bubble.show_for(text, shortcut, anchor, self.side)

    # ---------------- harakatlar ----------------
    def toggle_mode(self, key):
        if self.mode == key:
            self.close_panel()
        else:
            self.open_mode(key)

    def open_mode(self, key):
        m = MODE_BY_KEY[key]
        was_open = self.mode is not None
        self.mode = key
        for k, b in self.mode_buttons.items():
            b.blockSignals(True)
            b.setChecked(k == key)
            b.blockSignals(False)
            b.refresh()
        self.p_title.setText(m["title"])
        self.p_icon.setPixmap(svg_icon(m["icon"], C_ACCENT, 20).pixmap(QSize(20, 20)))
        self.input.setPlaceholderText(m["placeholder"])
        self.lang_box.setVisible(key == "translate")
        self.google_btn.setVisible(key == "search")
        if not was_open:
            y = self.y()
            self.panel.show()
            self.relayout()
            self.reposition(y)
        self.bring_front()
        self.input.setFocus()

    def close_panel(self):
        if self.mode is None:
            return
        self.mode = None
        for b in self.mode_buttons.values():
            b.blockSignals(True)
            b.setChecked(False)
            b.blockSignals(False)
            b.refresh()
        self.panel.hide()
        y = self.y()
        self.relayout()
        self.reposition(y)

    def toggle_pin(self):
        pinned = self.pin_btn.isChecked()
        self.cfg["pinned"] = pinned
        save_config(self.cfg)
        self.apply_flags(pinned)
        self.pin_btn.refresh()
        self.status.setText("Hamma oynalar ustida turadi." if pinned
                            else "Qadash o'chirildi.")

    def _lang_changed(self, text):
        self.cfg["lang"] = text
        save_config(self.cfg)

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
        dlg = SettingsDialog(self, self.cfg)
        if dlg.exec():
            self.cfg["api_key"], self.cfg["model"] = dlg.values()
            save_config(self.cfg)
            if self.mode:
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
            if not self.cfg.get("api_key"):
                return
        m = MODE_BY_KEY[self.mode]
        lang = self.lang_box.currentText()
        system = m["prompt"].format(lang=LANGS[lang])
        self._req = (m["title"], lang if self.mode == "translate" else "", text)
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
        self.output.setPlainText(answer)
        self._reset_send()
        try:
            save_history(*self._req, answer)
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

    def quit_app(self):
        self.cfg["side"] = self.side
        self.cfg["y"] = self.y()
        save_config(self.cfg)
        self.tray.hide()
        QApplication.quit()


STYLE = f"""
* {{ font-family: "Segoe UI", "Inter", Arial; font-size: 14px; color: {C_TEXT}; }}
#rail {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: 22px; }}
#sep {{ background: {C_BORDER}; margin: 0 8px; }}
RailButton, QToolButton {{ border: none; border-radius: 13px; background: transparent; }}
RailButton:hover, QToolButton#small:hover {{ background: {C_HOVER}; }}
RailButton:checked {{ background: {C_HOVER}; }}
#panel {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: 22px; }}
#title {{ font-size: 16px; font-weight: 600; }}
#muted {{ color: {C_MUTED}; font-size: 12px; }}
QPlainTextEdit {{ background: #F6F7FA; border: 1px solid {C_BORDER}; border-radius: 14px;
    padding: 8px 10px; font-size: 14px; selection-background-color: #C7D2FE; }}
QPlainTextEdit:focus {{ border: 1px solid #A5B4FC; background: #FFFFFF; }}
#output {{ background: #FAFAFC; }}
QPushButton {{ border: 1px solid {C_BORDER}; border-radius: 12px; padding: 8px 16px;
    background: #FFFFFF; font-weight: 600; }}
QPushButton:hover {{ background: {C_HOVER}; }}
QPushButton#primary {{ background: {C_ACCENT}; color: white; border: none; }}
QPushButton#primary:hover {{ background: #4338CA; }}
QPushButton#primary:disabled {{ background: #A5B4FC; }}
QComboBox {{ border: 1px solid {C_BORDER}; border-radius: 10px; padding: 5px 10px;
    background: #FFFFFF; min-width: 120px; }}
QComboBox QAbstractItemView {{ border: 1px solid {C_BORDER}; selection-background-color: {C_HOVER};
    selection-color: {C_TEXT}; background: white; outline: 0; }}
QLineEdit {{ border: 1px solid {C_BORDER}; border-radius: 10px; padding: 8px 10px; }}
QLineEdit:focus {{ border: 1px solid #A5B4FC; }}
QDialog {{ background: #FFFFFF; }}
#bubble {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: 16px; }}
#bubbleText {{ font-size: 15px; font-weight: 500; color: {C_TEXT}; }}
#keycap {{ background: #FFFFFF; border: 1px solid #DADDE5; border-bottom: 2px solid #D0D4DD;
    border-radius: 7px; padding: 2px 8px; min-width: 14px; font-family: Consolas, "Courier New";
    font-size: 13px; color: #6B7084; }}
QToolTip {{ background: white; color: {C_TEXT}; border: 1px solid {C_BORDER}; padding: 4px 8px; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ background: #D5D8E0; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


def main():
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
