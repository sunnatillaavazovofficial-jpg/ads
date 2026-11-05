"""
AI Rasm — skrinshotni ChatGPT (OpenAI rasm modeli) orqali real rasmga aylantiradi.

Ish tartibi:
  1. Skrinshot olinadi (Ctrl+Alt+S yoki kamera tugmasi) yoki rasm fayli ochiladi.
  2. Tahrirlash oynasi ochiladi: ustiga chizish, strelka, belgi va yozuv qo'shish mumkin.
  3. Nima qilish kerakligi yoziladi yoki tayyor shablon tanlanadi.
  4. "Real rasm qilish" — natija oynada chiqadi va "Hujjatlar/AI Rasm" papkasiga saqlanadi.

Dizayn AI Yordamchi bilan bir xil. by Sunnatilla Designer — https://sunnatilla-designer.uz/
"""

import base64
import datetime
import json
import math
import os
import sys
import time

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
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox,
                               QColorDialog, QComboBox, QDialog, QFileDialog,
                               QFrame, QGraphicsDropShadowEffect, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPlainTextEdit, QProgressBar, QPushButton,
                               QScrollArea, QSizeGrip, QSlider,
                               QSystemTrayIcon, QToolButton, QVBoxLayout,
                               QWidget)

APP_NAME = "AI Rasm"
ORG_NAME = "AI Yordamchi"          # sozlamalar AI Yordamchi bilan yonma-yon saqlanadi
API_EDIT = "https://api.openai.com/v1/images/edits"
API_CHAT = "https://api.openai.com/v1/chat/completions"
CHAT_MODEL = "gpt-4o-mini"
# "Avto" tanlansa — shu tartibda sinab ko'riladi (qaysi biri hisobingizda ishlasa)
IMAGE_MODELS = ["gpt-image-2", "gpt-image-1.5", "gpt-image-1"]
AUTHOR = "Sunnatilla Designer"
AUTHOR_URL = "https://sunnatilla-designer.uz/"
HOTKEY_TEXT = "Ctrl+Alt+S"

# ---------------------------------------------------------------------------
# Ranglar (AI Yordamchi bilan bir xil)
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
COLORS = [("Asl rang", C_ACCENT), ("Ko'k", "#2563EB"), ("Binafsha", "#7C3AED"),
          ("Yashil", "#16A34A"), ("Qizil", "#DC2626"), ("Apelsin", "#EA580C"),
          ("Pushti", "#DB2777")]
PEN_COLORS = ["#EF4444", "#F59E0B", "#22C55E", "#3B82F6", "#111827", "#FFFFFF"]

# ---------------------------------------------------------------------------
# Ikonkalar — qalin, to'q uslubda
# ---------------------------------------------------------------------------
ICONS = {
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
    "trash": '<path d="M2.8 6h18.4" stroke-width="3"/>'
             '<path d="M8 6V4.2C8 3 9 2 10.2 2h3.6C15 2 16 3 16 4.2V6" stroke-width="2.6"/>'
             '<path fill="{c}" stroke-width="1.6" d="M5 8h14l-1 12.2A2 2 0 0 1 16 22H8a2 2 0 0 '
             '1-2-1.8z"/>',
    "sparkle": '<path d="M11 2.5l2.1 5.6 5.6 2.1-5.6 2.1L11 17.9l-2.1-5.6-5.6-2.1 5.6-2.1z" '
               'fill="{c}" stroke-width="1.2"/><path d="M19 14.5l.9 2.3 2.3.9-2.3.9-.9 2.3-.9-2.3'
               '-2.3-.9 2.3-.9z" fill="{c}" stroke-width="1"/>',
    "save": '<path d="M12 3v11.5" stroke-width="3"/><path d="m7 10 5 5 5-5" stroke-width="3"/>'
            '<path d="M4 17v2.5A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5V17" stroke-width="3"/>',
    "copy": '<path d="M4.5 15.5c-1.4 0-2.5-1.1-2.5-2.5V4.5C2 3.1 3.1 2 4.5 2H13c1.4 0 2.5 1.1 2.5 2.5"'
            ' stroke-width="2.8"/>'
            '<rect width="14" height="14" x="8" y="8" rx="2.6" fill="{c}" stroke-width="2"/>',
    "folder": '<path fill="{c}" d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 '
              '3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" stroke-width="2"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" stroke-width="2.7"/>'
           '<circle cx="12" cy="12" r="3.3" fill="{c}" stroke="none"/>',
    "close": '<path d="M18 6 6 18" stroke-width="3.6"/><path d="m6 6 12 12" stroke-width="3.6"/>',
    "grip": '<circle cx="8" cy="5" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="5" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="8" cy="12" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="12" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="8" cy="19" r="2" fill="{c}" stroke="none"/>'
            '<circle cx="16" cy="19" r="2" fill="{c}" stroke="none"/>',
    "pin": '<path d="M12 16.5v5.5" stroke-width="3"/>'
           '<path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 '
           '1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 '
           '0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" stroke-width="2.6"/>',
    "pin_on": '<path d="M12 16.5v5.5" stroke-width="3"/>'
              '<path fill="{c}" d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 '
              '0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 '
              '0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" stroke-width="2.6"/>',
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
    "dot1": '<circle cx="12" cy="12" r="2.4" fill="{c}" stroke="none"/>',
    "dot2": '<circle cx="12" cy="12" r="4.2" fill="{c}" stroke="none"/>',
    "dot3": '<circle cx="12" cy="12" r="6.4" fill="{c}" stroke="none"/>',
}


def svg_pixmap(name, color=C_ICON, size=22, stroke=2.5, bg=C_BG) -> QPixmap:
    body = ICONS[name].replace("{c}", color).replace("{bg}", bg)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
           f'stroke-linejoin="round">{body}</svg>')
    k = 3
    pm = QPixmap(size * k, size * k)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(p)
    p.end()
    pm.setDevicePixelRatio(k)
    return pm


def svg_icon(name, color=C_ICON, size=22, stroke=2.5, bg=C_BG) -> QIcon:
    return QIcon(svg_pixmap(name, color, size, stroke, bg))


def app_icon(size: int = 256) -> QPixmap:
    """Dastur ikonkasi: gradientli kvadrat ichida skrinshot ramkasi va uchqun."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#F97316"))
    g.setColorAt(1, QColor("#DB2777"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
    corners = ICONS["camera"].replace('<circle cx="12" cy="12" r="3.8" fill="{c}" stroke="none"/>', "")
    star = '<path d="M12 5.2l1.7 4.9 4.9 1.7-4.9 1.7L12 18.4l-1.7-4.9-4.9-1.7 4.9-1.7z" fill="{c}"/>'
    body = (corners + star).replace("{c}", "#FFFFFF")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" '
           f'stroke-linejoin="round">{body}</svg>')
    m = size * 0.17
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(m, m, size - 2 * m, size - 2 * m))
    p.end()
    return pm


def accent_text(color: str) -> str:
    c = QColor(color)
    lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
    return "#111827" if lum > 170 else "#FFFFFF"


def shadow(widget, blur=36, dy=10, alpha=38):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(eff)


def set_autostart(on: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                         winreg.KEY_SET_VALUE)
    try:
        if on:
            cmd = (f'"{sys.executable}"' if getattr(sys, "frozen", False)
                   else f'"{sys.executable}" "{os.path.abspath(__file__)}"')
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


# ---------------------------------------------------------------------------
# Tayyor shablonlar (sarlavha o'zbekcha, ko'rsatma rasm modeli uchun inglizcha)
# ---------------------------------------------------------------------------
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
    ("Sifatni oshirish", "Tiniqlik, ranglar va detallarni yaxshilaydi",
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


# ---------------------------------------------------------------------------
# Sozlamalar va saqlash joyi
# ---------------------------------------------------------------------------
def config_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    os.makedirs(base, exist_ok=True)
    return base


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def load_config() -> dict:
    cfg = {"api_key": "", "image_model": "auto", "rx": None, "ry": None, "pinned": True,
           "size": "O'rta", "auto_hide": True, "color": C_ACCENT, "line_opacity": 55,
           "autostart": False, "out_size": "Avto", "quality": "Avto"}
    try:
        with open(config_path(), encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if not cfg.get("api_key"):
        # AI Yordamchi'dagi kalitdan foydalanamiz (qayta kiritish shart emas)
        other = os.path.join(os.path.dirname(config_dir()), "AI Yordamchi", "config.json")
        try:
            with open(other, encoding="utf-8") as f:
                cfg["api_key"] = json.load(f).get("api_key", "")
        except Exception:
            pass
    if not cfg.get("api_key"):
        cfg["api_key"] = os.environ.get("OPENAI_API_KEY", "")
    if cfg.get("size") not in SCALES:
        cfg["size"] = "O'rta"
    if not QColor(str(cfg.get("color"))).isValid():
        cfg["color"] = C_ACCENT
    if cfg.get("out_size") not in SIZES:
        cfg["out_size"] = "Avto"
    if cfg.get("quality") not in QUALITIES:
        cfg["quality"] = "Avto"
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


def output_dir() -> str:
    docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation) or \
        os.path.join(os.path.expanduser("~"), "Documents")
    path = os.path.join(docs, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def open_output_dir():
    QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir()))


def image_to_png(img: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


# ---------------------------------------------------------------------------
# OpenAI so'rovi (alohida oqimda)
# ---------------------------------------------------------------------------
class ImageWorker(QThread):
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
                API_CHAT,
                headers={"Authorization": f"Bearer {self.cfg['api_key']}"},
                json={"model": CHAT_MODEL, "temperature": 0,
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


# ---------------------------------------------------------------------------
# Global tugma (Windows): Ctrl+Alt+S — istalgan joydan skrinshot
# ---------------------------------------------------------------------------
class GlobalHotkey(QAbstractNativeEventFilter):
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
            mods = 0x0002 | 0x0001 | 0x4000          # CONTROL | ALT | NOREPEAT
            self.ok = bool(self.user32.RegisterHotKey(None, self.HK_ID, mods, 0x53))  # 'S'
        except Exception:
            self.ok = False

    def nativeEventFilter(self, event_type, message):
        try:
            if self.ok and bytes(event_type) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                import ctypes.wintypes
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == 0x0312 and msg.wParam == self.HK_ID:   # WM_HOTKEY
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
        if not r.isEmpty():
            dpr = self.pm.devicePixelRatio()
            src = QRect(int(r.x() * dpr), int(r.y() * dpr), int(r.width() * dpr),
                        int(r.height() * dpr))
            p.drawPixmap(r, self.pm, src)
            p.setPen(QPen(QColor("#FFFFFF"), 2))
            p.drawRect(r.adjusted(0, 0, -1, -1))
            p.setPen(QColor("#FFFFFF"))
            p.drawText(r.left(), max(16, r.top() - 8), f"{int(r.width() * dpr)} × {int(r.height() * dpr)}")
        # yo'riqnoma
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
        src = QRect(int(r.x() * dpr), int(r.y() * dpr), int(r.width() * dpr), int(r.height() * dpr))
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
    pen = QPen(it["c"], it["w"], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
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
# Umumiy "kartochka" oyna (oq, yumaloq burchakli — AI Yordamchi uslubida)
# ---------------------------------------------------------------------------
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
        close = small_btn("close", "Yopish", s)
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
        scr = (QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen())
        g = scr.availableGeometry()
        w, h = min(w, int(g.width() * 0.94)), min(h, int(g.height() * 0.92))
        self.resize(w, h)
        self.move(g.center().x() - w // 2, g.center().y() - h // 2)


def small_btn(icon, tip, s, color=C_ICON):
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


# ---------------------------------------------------------------------------
# Tahrirlash oynasi
# ---------------------------------------------------------------------------
class EditorWindow(CardWindow):
    TOOLS = [("pen", "Qalam"), ("marker", "Marker"), ("arrow", "Strelka"),
             ("rect", "To'rtburchak"), ("ellipse", "Doira"), ("text", "Matn yozish")]

    def __init__(self, ctrl, image: QImage):
        super().__init__(ctrl, "Rasmni tahrirlash", "image")
        s = self.s
        self.worker = None
        self.template_idx = None

        row = QHBoxLayout()
        row.setSpacing(int(14 * s))
        self.body.addLayout(row, 1)

        # ---- chap: asboblar + rasm ----
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
        for col in PEN_COLORS:
            b = QPushButton()
            b.setCheckable(True)
            d = int(22 * s)
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
            b = small_btn(ic, tip, s)
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

        # ---- o'ng: shablonlar + ko'rsatma ----
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
        cw = int(min(max(iw, 640), 1100) + 340 * s + 90)
        chh = int(min(max(ih, 460), 760) + 150)
        self.fit_on_screen(cw, chh)

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

    def _update_info(self):
        n = len(self.canvas.items)
        self.info.setText(f"{self.canvas.img.width()} × {self.canvas.img.height()} px"
                          + (f"  ·  {n} ta belgi — ular ko'rsatma sifatida yuboriladi" if n else
                             "  ·  Ustiga chizib yoki yozib, nima qilishni ko'rsatishingiz mumkin"))

    def _chip(self, k):
        if self.template_idx == k:
            self.template_idx = None
        else:
            self.template_idx = k
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
            self.ctrl.open_settings(self)
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
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out = output_dir()
        res_path = os.path.join(out, f"{stamp}_natija.png")
        try:
            self._flat.save(os.path.join(out, f"{stamp}_asl.png"))
            with open(res_path, "wb") as f:
                f.write(png)
            with open(os.path.join(out, "tarix.md"), "a", encoding="utf-8") as f:
                f.write(f"## {stamp}\n\n- Shablon: {self._tpl_title or '—'}\n"
                        f"- Ko'rsatma: {self.prompt.toPlainText().strip() or '—'}\n"
                        f"- Model: {model}\n- Natija: {os.path.basename(res_path)}\n\n")
            self.status.setText("Tayyor ✓  Natija \"Hujjatlar/AI Rasm\" papkasiga saqlandi.")
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Tayyor ✓  (saqlab bo'lmadi: {e})")
        self.ctrl.show_result(result, self._flat, res_path)

    def closeEvent(self, e):
        if self.worker is not None and self.worker.isRunning():
            self.worker.done.disconnect()
            self.worker.failed.disconnect()
            self.worker.progress.disconnect()
            self.ctrl.keep_worker(self.worker)
        self.ctrl.forget(self)
        super().closeEvent(e)


# ---------------------------------------------------------------------------
# Natija oynasi
# ---------------------------------------------------------------------------
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
        super().__init__(ctrl, "Natija", "sparkle")
        s = self.s
        self.result, self.original, self.path = result, original, path
        self.view = ImageView(result)
        self.view.setObjectName("canvas")
        self.view.setAttribute(Qt.WA_StyledBackground, True)
        self.body.addWidget(self.view, 1)

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
                               ("save", "Saqlash…", self._save_as),
                               ("folder", "Papka", open_output_dir),
                               ("pen", "Yana tahrirlash", self._edit)]:
            b = QPushButton("  " + text)
            b.setIcon(svg_icon(icon, C_ICON, int(18 * s)))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            row.addWidget(b)
        self.body.addLayout(row)
        self.fit_on_screen(int(min(max(result.width(), 700), 1200) + 80),
                           int(min(max(result.height(), 500), 860) + 150))

    def _toggle(self, on):
        self.view.set_image(self.original if on else self.result)
        self.cmp.setText("  Natijani ko'rish" if on else "  Aslini ko'rish")

    def _copy(self):
        QGuiApplication.clipboard().setImage(self.result)
        self.msg.setText("Nusxalandi ✓")

    def _save_as(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Saqlash", os.path.basename(self.path),
                                            "PNG (*.png);;JPEG (*.jpg)")
        if fn:
            self.msg.setText("Saqlandi ✓" if self.result.save(fn) else "Saqlab bo'lmadi")

    def _edit(self):
        self.ctrl.open_editor(self.result)

    def closeEvent(self, e):
        self.ctrl.forget(self)
        super().closeEvent(e)


# ---------------------------------------------------------------------------
# Sozlamalar oynasi
# ---------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, parent, cfg, s):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Sozlamalar")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(int(480 * s))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, int(16 * s))
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
        lay.addWidget(section("OpenAI API kalit"))
        self.key = QLineEdit(cfg.get("api_key", ""))
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setPlaceholderText("sk-...")
        lay.addWidget(self.key)
        link = QLabel('<a href="https://platform.openai.com/api-keys" '
                      'style="color:#6366F1;text-decoration:none;">API kalitni olish →</a>')
        link.setOpenExternalLinks(True)
        link.setObjectName("muted")
        lay.addWidget(link)
        mrow = QHBoxLayout()
        mrow.addWidget(QLabel("Rasm modeli:"))
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.addItems(["auto"] + IMAGE_MODELS)
        self.model.setCurrentText(cfg.get("image_model", "auto"))
        self.model.setToolTip("auto — hisobingizda ishlaydigan eng yangi modelni o'zi tanlaydi")
        mrow.addWidget(self.model, 1)
        lay.addLayout(mrow)

        lay.addSpacing(int(8 * s))
        lay.addWidget(section("O'lcham"))
        seg = QHBoxLayout()
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

        lay.addSpacing(int(8 * s))
        lay.addWidget(section("Rang (chet chizig'i va tugmalar)"))
        crow = QHBoxLayout()
        crow.setSpacing(int(8 * s))
        self.color = cfg.get("color", C_ACCENT)
        self.color_group = QButtonGroup(self)
        d = int(28 * s)
        known = False
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

        lay.addSpacing(int(8 * s))
        lay.addWidget(section("Yashirinish va orqa fon"))
        self.auto_hide = QCheckBox("  Kursor chiqqach chetga kirib ketsin (shaffof chiziq bo'lib tursin)")
        self.auto_hide.setChecked(cfg.get("auto_hide", True))
        lay.addWidget(self.auto_hide)
        orow = QHBoxLayout()
        orow.addWidget(QLabel("Chiziq ko'rinishi:"))
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(15, 100)
        self.opacity.setValue(int(cfg.get("line_opacity", 55)))
        orow.addWidget(self.opacity, 1)
        self.op_lbl = QLabel(f"{self.opacity.value()}%")
        self.opacity.valueChanged.connect(lambda v: self.op_lbl.setText(f"{v}%"))
        orow.addWidget(self.op_lbl)
        lay.addLayout(orow)
        self.autostart = QCheckBox("  Kompyuter yonganda o'zi ishga tushsin")
        self.autostart.setChecked(cfg.get("autostart", False))
        self.autostart.setEnabled(sys.platform == "win32")
        lay.addWidget(self.autostart)
        hk = QLabel(f"Istalgan joydan skrinshot: {HOTKEY_TEXT}")
        hk.setObjectName("muted")
        lay.addWidget(hk)

        lay.addSpacing(int(8 * s))
        lay.addWidget(section("Rasmlar saqlanadigan joy"))
        frow = QHBoxLayout()
        path = QLabel(output_dir())
        path.setObjectName("muted")
        path.setWordWrap(True)
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        frow.addWidget(path, 1)
        fbtn = QPushButton("  Papkani ochish")
        fbtn.setIcon(svg_icon("folder", C_ICON, int(18 * s)))
        fbtn.setCursor(Qt.PointingHandCursor)
        fbtn.clicked.connect(open_output_dir)
        frow.addWidget(fbtn)
        lay.addLayout(frow)
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

        avail = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(max(self.minimumWidth(), inner.sizeHint().width() + 20),
                    min(inner.sizeHint().height() + int(80 * s), int(avail.height() * 0.9)))

    def _swatch(self, col, tip, d):
        b = QPushButton()
        b.setCheckable(True)
        b.setFixedSize(d, d)
        b.setToolTip(tip)
        b.setCursor(Qt.PointingHandCursor)
        b.setProperty("color", col)
        self._style_swatch(b, col, d)
        b.clicked.connect(lambda _=False, btn=b: setattr(self, "color", btn.property("color")))
        self.color_group.addButton(b)
        return b

    @staticmethod
    def _style_swatch(b, col, d):
        b.setStyleSheet(f"QPushButton {{ background: {col}; border: 3px solid #FFFFFF; "
                        f"border-radius: {d // 2}px; padding: 0; min-width: {d - 6}px; "
                        f"max-width: {d - 6}px; min-height: {d - 6}px; max-height: {d - 6}px; }}"
                        f"QPushButton:checked {{ border: 3px solid #C7CBD4; }}")

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Rang tanlang")
        if c.isValid():
            self.color = c.name()
            self.custom_sw.setProperty("color", self.color)
            self._style_swatch(self.custom_sw, self.color, self.custom_sw.width())
            self.custom_sw.setVisible(True)
            self.custom_sw.setChecked(True)

    def values(self):
        b = self.size_group.checkedButton()
        return {"api_key": self.key.text().strip(),
                "image_model": self.model.currentText().strip() or "auto",
                "size": b.text() if b else "O'rta", "color": self.color,
                "auto_hide": self.auto_hide.isChecked(), "line_opacity": self.opacity.value(),
                "autostart": self.autostart.isChecked()}


# ---------------------------------------------------------------------------
# Ekrandagi ikonkalar paneli (AI Yordamchi bilan bir xil uslub)
# ---------------------------------------------------------------------------
class HoverBubble(QWidget):
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
        for _ in range(3):
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
        self.icon_name, self.label, self.shortcut = icon_name, label, shortcut
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
        name = "pin_on" if (self.icon_name == "pin" and self.isChecked()) else self.icon_name
        self.setIcon(svg_icon(name, C_ICON_ACTIVE if on else C_ICON, self.isz,
                              bg=C_HOVER if on else C_BG))

    def enterEvent(self, e):
        self.refresh()
        self.hovered.emit(self)
        super().enterEvent(e)

    def leaveEvent(self, e):
        QTimer.singleShot(0, self.refresh)
        self.unhovered.emit(self)
        super().leaveEvent(e)


class GripHandle(QLabel):
    def __init__(self, win, s):
        super().__init__()
        self.win = win
        self.setFixedSize(int(24 * s), int(28 * s))
        self.setAlignment(Qt.AlignCenter)
        self.setPixmap(svg_pixmap("grip", "#6B7080", int(18 * s)))
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


class EdgeLine(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(APP_NAME)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
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


class RailWindow(QWidget):
    MARGIN = 18
    EDGE_GAP = 6

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.cfg = ctrl.cfg
        self.s = s = SCALES.get(self.cfg.get("size"), 1.0)
        self.accent = self.cfg.get("color", C_ACCENT)
        self.auto_hide = self.cfg.get("auto_hide", True)
        self.collapsed = False
        self.anim = None
        self.drag_off = None
        self._out_since = None
        self.busy = False            # skrinshot olinayotganda yashirinmasin

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(app_icon()))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apply_flags(self.cfg.get("pinned", True))

        self.bubble = HoverBubble(s)
        self.rail = self._build_rail()
        self.line = EdgeLine(self)
        self.line.hide()
        self.rail_pos = self._initial_pos()
        self.layout_children()

        self.watch = QTimer(self)
        self.watch.setInterval(200)
        self.watch.timeout.connect(self._tick)
        self.watch.start()

    # ---------- qurilish ----------
    def _hook(self, b):
        b.hovered.connect(lambda x: self.show_bubble_text(x, x.label, x.shortcut))
        b.unhovered.connect(lambda x: self.bubble.hide())

    def _sep(self):
        f = QFrame()
        f.setObjectName("sep")
        f.setFixedHeight(1)
        return f

    def _build_rail(self):
        s = self.s
        rail = QFrame(self)
        rail.setObjectName("rail")
        shadow(rail)
        pad = int(7 * s)
        rl = QVBoxLayout(rail)
        rl.setContentsMargins(pad, int(6 * s), pad, int(8 * s))
        rl.setSpacing(int(4 * s))
        top = QHBoxLayout()
        top.setSpacing(0)
        top.addWidget(GripHandle(self, s))
        x = RailButton("close", "Yopish (dasturdan chiqish)", s)
        x.setObjectName("xbtn")
        x.setFixedSize(int(22 * s), int(28 * s))
        x.isz = int(15 * s)
        x.setIconSize(QSize(x.isz, x.isz))
        x.refresh()
        x.clicked.connect(self.ctrl.quit)
        self._hook(x)
        top.addWidget(x)
        rl.addLayout(top)

        self.pin_btn = RailButton("pin", "Hamma oynalar ustida qadash", s, checkable=True)
        self.pin_btn.setChecked(self.cfg.get("pinned", True))
        self.pin_btn.clicked.connect(self.toggle_pin)
        self._hook(self.pin_btn)
        rl.addWidget(self.pin_btn)
        rl.addSpacing(int(2 * s))
        rl.addWidget(self._sep())
        rl.addSpacing(int(2 * s))
        for icon, label, sc, fn in [("camera", "Skrinshot olish", HOTKEY_TEXT, self.ctrl.start_capture),
                                    ("image", "Rasm faylini ochish", "", self.ctrl.open_file),
                                    ("folder", "Natijalar papkasi", "", open_output_dir)]:
            b = RailButton(icon, label, s, sc)
            b.clicked.connect(fn)
            self._hook(b)
            rl.addWidget(b)
        rl.addSpacing(int(2 * s))
        rl.addWidget(self._sep())
        rl.addSpacing(int(2 * s))
        b = RailButton("settings", "Sozlamalar", s)
        b.clicked.connect(lambda: self.ctrl.open_settings(self))
        self._hook(b)
        rl.addWidget(b)
        rail.setFixedWidth(int(46 * s) + 2 * pad)
        rail.setFixedHeight(rail.sizeHint().height())
        return rail

    # ---------- joylashuv ----------
    def apply_flags(self, pinned):
        flags = Qt.Window | Qt.FramelessWindowHint
        if pinned:
            flags |= Qt.WindowStaysOnTopHint
        vis = self.isVisible()
        self.setWindowFlags(flags)
        if vis:
            self.show()

    @staticmethod
    def _screen_for(point):
        scr = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
        return scr.availableGeometry()

    def _initial_pos(self):
        rx, ry = self.cfg.get("rx"), self.cfg.get("ry")
        size = self.rail.size()
        if rx is not None and ry is not None:
            r = QRect(QPoint(int(rx), int(ry)), size)
            if QGuiApplication.screenAt(r.center()) is not None:
                return self._clamp(r.topLeft())
        g = QGuiApplication.primaryScreen().availableGeometry()
        return self._clamp(QPoint(g.right() - size.width() - 12,
                                  g.top() + (g.height() - size.height()) // 2))

    def _clamp(self, pos):
        size = self.rail.size()
        g = self._screen_for(QRect(pos, size).center())
        x = max(g.left(), min(pos.x(), g.right() + 1 - size.width()))
        y = max(g.top(), min(pos.y(), g.bottom() + 1 - size.height()))
        if self.auto_hide:
            x = (g.left() + self.EDGE_GAP if x + size.width() // 2 < g.center().x()
                 else g.right() + 1 - size.width() - self.EDGE_GAP)
        return QPoint(x, y)

    def edge_side(self):
        r = QRect(self.rail_pos, self.rail.size())
        g = self._screen_for(r.center())
        return "left" if r.center().x() < g.center().x() else "right"

    def layout_children(self):
        m = self.MARGIN
        win = QRect(self.rail_pos, self.rail.size()).adjusted(-m, -m, m, m)
        self.setFixedSize(win.size())
        self.move(win.topLeft())
        self.rail.move(m, m)

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
        self.layout_children()
        self.cfg["rx"], self.cfg["ry"] = self.rail_pos.x(), self.rail_pos.y()
        save_config(self.cfg)

    def show_bubble_text(self, widget, text, shortcut):
        if self.drag_off is not None or self.collapsed:
            return
        self.bubble.prepare(text, shortcut)
        rail_tl = self.rail.mapToGlobal(QPoint(0, 0))
        wy = widget.mapToGlobal(QPoint(0, 0)).y()
        anchor = QRect(rail_tl.x(), wy, self.rail.width(), widget.height())
        g = self._screen_for(anchor.center())
        bw = self.bubble.width()
        right = anchor.center().x() < g.center().x()
        if right and anchor.right() + bw > g.right():
            right = False
        elif not right and anchor.left() - bw < g.left():
            right = True
        x = anchor.right() - 4 if right else anchor.left() - bw + 4
        self.bubble.move(x, anchor.center().y() - self.bubble.height() // 2 + 2)
        self.bubble.show()
        self.bubble.raise_()

    # ---------- chetga kirib ketish ----------
    def _tick(self):
        if (not self.auto_hide or self.collapsed or self.busy or self.drag_off is not None
                or (self.anim is not None and self.anim.state() == QParallelAnimationGroup.Running)
                or QApplication.activeModalWidget() is not None
                or QApplication.activePopupWidget() is not None
                or not self.isVisible()):
            self._out_since = None
            return
        if self.frameGeometry().adjusted(-4, -4, 4, 4).contains(QCursor.pos()):
            self._out_since = None
            return
        self.bubble.hide()
        now = time.monotonic()
        if self._out_since is None:
            self._out_since = now
        elif now - self._out_since >= 0.5:
            self._out_since = None
            self.collapse()

    def _offscreen_x(self):
        g = self._screen_for(QRect(self.rail_pos, self.rail.size()).center())
        if self.edge_side() == "left":
            return g.left() - self.rail.width() - self.MARGIN - 4
        return g.right() + 1 - self.MARGIN + 4

    def _run_anim(self, end_pos, a, b, on_done=None):
        if self.anim is not None:
            self.anim.stop()
        grp = QParallelAnimationGroup(self)
        pa = QPropertyAnimation(self, b"pos")
        pa.setDuration(230)
        pa.setEasingCurve(QEasingCurve.OutCubic)
        pa.setEndValue(end_pos)
        grp.addAnimation(pa)
        oa = QPropertyAnimation(self, b"windowOpacity")
        oa.setDuration(230)
        oa.setStartValue(a)
        oa.setEndValue(b)
        grp.addAnimation(oa)
        if on_done:
            grp.finished.connect(on_done)
        self.anim = grp
        grp.start()

    def collapse(self):
        if self.collapsed:
            return
        self.bubble.hide()
        self.collapsed = True
        self._run_anim(QPoint(self._offscreen_x(), self.y()), 1.0, 0.0, self._show_line)

    def _show_line(self):
        if not self.collapsed:
            return
        self.rail.hide()
        r = QRect(self.rail_pos, self.rail.size())
        g = self._screen_for(r.center())
        hit_w = max(10, int(12 * self.s))
        lh = max(90, int(r.height() * 0.6))
        self.setFixedSize(hit_w, lh)
        self.move(g.left() if self.edge_side() == "left" else g.right() + 1 - hit_w,
                  r.center().y() - lh // 2)
        self.line.setGeometry(0, 0, hit_w, lh)
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
            QTimer.singleShot(0, lambda: (self.showNormal(), self.expand()))
        elif e.type() == QEvent.ActivationChange and self.isActiveWindow() and self.collapsed:
            QTimer.singleShot(0, self.expand)
        super().changeEvent(e)

    def toggle_pin(self):
        pinned = self.pin_btn.isChecked()
        self.cfg["pinned"] = pinned
        save_config(self.cfg)
        self.apply_flags(pinned)
        self.layout_children()
        self.pin_btn.refresh()

    def bring_front(self):
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


# ---------------------------------------------------------------------------
# Uslub
# ---------------------------------------------------------------------------
ARROW_PATH = ""


def ensure_arrow_image():
    global ARROW_PATH
    path = os.path.join(config_dir(), "arrow.png")
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


def make_style(s: float, accent: str) -> str:
    on_accent = accent_text(accent)
    hover = QColor(accent).darker(125).name()

    def px(v):
        return f"{max(1, round(v * s))}px"
    return f"""
* {{ font-family: "Segoe UI", "Inter", Arial; font-size: {px(14)}; color: {C_TEXT}; }}
#rail, #card {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: {px(22)}; }}
#sep {{ background: {C_BORDER}; margin: 0 {px(8)}; }}
#vsep {{ background: {C_BORDER}; margin: 0 {px(4)}; }}
RailButton, QToolButton {{ border: none; border-radius: {px(13)}; background: transparent; }}
RailButton:hover, QToolButton#small:hover, QToolButton#tool:hover {{ background: {C_HOVER}; }}
RailButton:checked, QToolButton#tool:checked {{ background: {C_HOVER}; }}
QToolButton#tool {{ border-radius: {px(10)}; }}
RailButton#xbtn {{ border-radius: {px(8)}; }}
RailButton#xbtn:hover {{ background: #FDE8E8; }}
#toolbar {{ background: #F6F7FA; border: 1px solid {C_BORDER}; border-radius: {px(14)}; }}
#canvas {{ background: #F1F3F7; border-radius: {px(14)}; }}
#title {{ font-size: {px(16)}; font-weight: 700; }}
#section {{ font-size: {px(12)}; font-weight: 700; color: {C_MUTED}; text-transform: uppercase; }}
#muted {{ color: {C_MUTED}; font-size: {px(12)}; }}
#credit {{ font-size: {px(13)}; }}
#side, #settingsBody, QScrollArea {{ background: #FFFFFF; }}
QPlainTextEdit {{ background: #F6F7FA; border: 1px solid {C_BORDER}; border-radius: {px(14)};
    padding: {px(8)} {px(10)}; selection-background-color: #C7D2FE; }}
QPlainTextEdit:focus {{ border: 1px solid #9CA3AF; background: #FFFFFF; }}
QPushButton {{ border: 1px solid {C_BORDER}; border-radius: {px(12)}; padding: {px(8)} {px(14)};
    background: #FFFFFF; font-weight: 600; }}
QPushButton:hover {{ background: {C_HOVER}; }}
QPushButton:checked {{ background: {C_HOVER}; }}
QPushButton#primary {{ background: {accent}; color: {on_accent}; border: none; font-size: {px(15)}; }}
QPushButton#primary:hover {{ background: {hover}; }}
QPushButton#primary:disabled {{ background: #9CA3AF; }}
QPushButton#seg {{ padding: {px(7)} {px(10)}; }}
QPushButton#seg:checked, QPushButton#chip:checked {{ background: {accent}; color: {on_accent};
    border: 1px solid {accent}; }}
QPushButton#chip {{ padding: {px(7)} {px(8)}; font-weight: 600; font-size: {px(13)}; }}
QComboBox {{ border: 1px solid {C_BORDER}; border-radius: {px(10)}; padding: {px(5)} {px(10)};
    background: #FFFFFF; min-width: {px(110)}; }}
QComboBox::drop-down {{ border: none; width: {px(26)}; subcontrol-origin: padding;
    subcontrol-position: center right; }}
QComboBox::down-arrow {{ image: url("{ARROW_PATH}"); width: {px(12)}; height: {px(12)}; }}
QComboBox QAbstractItemView {{ border: 1px solid {C_BORDER}; selection-background-color: {C_HOVER};
    selection-color: {C_TEXT}; background: white; outline: 0; }}
QLineEdit {{ border: 1px solid {C_BORDER}; border-radius: {px(10)}; padding: {px(8)} {px(10)}; }}
QLineEdit:focus {{ border: 1px solid #9CA3AF; }}
QCheckBox {{ padding: {px(4)} 0; spacing: {px(8)}; }}
QDialog {{ background: #FFFFFF; }}
QProgressBar {{ background: {C_HOVER}; border: none; border-radius: {px(3)}; }}
QProgressBar::chunk {{ background: {accent}; border-radius: {px(3)}; }}
#bubble {{ background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: {px(16)}; }}
#bubbleText {{ font-size: {px(15)}; font-weight: 500; }}
#keycap {{ background: #FFFFFF; border: 1px solid #DADDE5; border-bottom: 2px solid #D0D4DD;
    border-radius: {px(7)}; padding: {px(2)} {px(8)}; font-family: Consolas, "Courier New";
    font-size: {px(13)}; color: #6B7084; }}
QToolTip {{ background: white; color: {C_TEXT}; border: 1px solid {C_BORDER}; padding: 4px 8px; }}
QScrollBar:vertical {{ width: {px(8)}; background: transparent; }}
QScrollBar::handle:vertical {{ background: #D5D8E0; border-radius: {px(4)}; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


# ---------------------------------------------------------------------------
# Boshqaruvchi
# ---------------------------------------------------------------------------
class Controller:
    def __init__(self, app):
        self.app = app
        self.cfg = load_config()
        self.rail = None
        self.windows = []
        self.workers = []
        self.capturing = False
        ensure_arrow_image()

        self.tray = QSystemTrayIcon(QIcon(app_icon()))
        self.tray.setToolTip(f"{APP_NAME} — skrinshot: {HOTKEY_TEXT}")
        menu = QMenu()
        menu.addAction("Skrinshot olish", self.start_capture)
        menu.addAction("Rasm faylini ochish", self.open_file)
        menu.addAction("Natijalar papkasi", open_output_dir)
        menu.addAction("Sozlamalar", lambda: self.open_settings(self.rail))
        menu.addSeparator()
        menu.addAction("Chiqish", self.quit)
        self._menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.rail.bring_front() if r == QSystemTrayIcon.Trigger and self.rail else None)
        self.tray.show()

        self.hotkey = GlobalHotkey(self.start_capture)
        app.installNativeEventFilter(self.hotkey)
        self.rebuild()

    def rebuild(self):
        old = self.rail
        self.app.setStyleSheet(make_style(SCALES.get(self.cfg.get("size"), 1.0),
                                          self.cfg.get("color", C_ACCENT)))
        self.rail = RailWindow(self)
        self.rail.show()
        if old is not None:
            old.dispose()

    # ---- skrinshot ----
    def start_capture(self):
        if self.capturing:
            return
        self.capturing = True
        self.rail.busy = True
        self.rail.bubble.hide()
        self.rail.hide()
        QTimer.singleShot(280, self._grab)

    def _grab(self):
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        pm = screen.grabWindow(0)
        self.overlay = CaptureOverlay(screen, pm)
        self.overlay.captured.connect(self._captured)
        self.overlay.cancelled.connect(self._capture_done)
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()
        self.overlay.setFocus()

    def _capture_done(self):
        self.capturing = False
        self.overlay = None
        self.rail.busy = False
        self.rail.show()

    def _captured(self, img):
        self._capture_done()
        self.open_editor(img)

    def open_file(self):
        fn, _ = QFileDialog.getOpenFileName(None, "Rasmni tanlang", "",
                                            "Rasmlar (*.png *.jpg *.jpeg *.webp *.bmp)")
        if fn:
            img = QImage(fn)
            if not img.isNull():
                self.open_editor(img)

    # ---- oynalar ----
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
        worker.finished.connect(lambda: self.workers.remove(worker) if worker in self.workers else None)

    def open_settings(self, parent=None):
        if self.rail:
            self.rail.bubble.hide()
        dlg = SettingsDialog(parent, self.cfg, SCALES.get(self.cfg.get("size"), 1.0))
        if dlg.exec():
            v = dlg.values()
            need = any(v[k] != self.cfg.get(k) for k in ("size", "color", "auto_hide"))
            if v["autostart"] != self.cfg.get("autostart"):
                try:
                    set_autostart(v["autostart"])
                except Exception:  # noqa: BLE001
                    v["autostart"] = self.cfg.get("autostart", False)
            self.cfg.update(v)
            save_config(self.cfg)
            if self.rail:
                self.rail.line.update()
            if need:
                QTimer.singleShot(0, self.rebuild)

    def quit(self):
        if self.rail is not None:
            self.cfg["rx"], self.cfg["ry"] = self.rail.rail_pos.x(), self.rail.rail_pos.y()
        save_config(self.cfg)
        self.hotkey.unregister()
        self.tray.hide()
        QApplication.quit()


def main():
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setQuitOnLastWindowClosed(False)
    app._ctrl = Controller(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
