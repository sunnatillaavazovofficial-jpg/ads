"""
Dock Panel — Windows taskbar o'rnida turadigan shaffof dok-panel.

  - Ekranning pastki markazida turadi, fonda ishlaydi, kompyuter yonganda o'zi ochiladi.
  - Foydalanilmaganda shaffof; kursor kelganda ikonkalar biroz ko'tariladi
    (kursor qaysi ikonka ustida bo'lsa — o'sha eng ko'p ko'tariladi).
  - Fayl, dastur yoki papkani sichqoncha bilan panelga sudrab qo'shasiz.
  - Papka bosilsa — ichidagilar ochiladi; ulardan narsani sudrab olish yoki
    papkaga sudrab tashlash mumkin.
  - Sozlamalarda alohida "Dock papkasi"ni tanlash mumkin (masalan, Yuklanmalar).

by Sunnatilla Designer — https://sunnatilla-designer.uz/
"""

import json
import math
import os
import re
import shutil
import sys
import threading
import time

from PySide6.QtCore import (QByteArray, QEasingCurve, QEvent, QFileInfo, QMimeData,
                            QObject, QParallelAnimationGroup, QPoint, QPointF,
                            QProcess, QPropertyAnimation, QRect, QRectF, QSize,
                            QStandardPaths, Qt, QTimer, QUrl, Signal)
from PySide6.QtGui import (QColor, QCursor, QDesktopServices, QDrag, QFont,
                           QFontMetrics, QGuiApplication, QIcon,
                           QLinearGradient, QPainter, QPen,
                           QPixmap)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QDialog,
                               QFileDialog, QFileIconProvider, QFrame,
                               QGraphicsDropShadowEffect, QGridLayout,
                               QHBoxLayout, QLabel, QMenu, QPushButton,
                               QScrollArea, QSlider, QSystemTrayIcon,
                               QToolButton, QVBoxLayout, QWidget)

APP_NAME = "Dock Panel"
ORG_NAME = "Sunnatilla Designer"
AUTHOR = "Sunnatilla Designer"
AUTHOR_URL = "https://sunnatilla-designer.uz/"
MIME_INDEX = "application/x-dock-panel-index"

C_TEXT = "#111827"
C_MUTED = "#8A8FA3"
C_BORDER = "#E6E8EE"
C_HOVER = "#EEF0F5"
C_ICON = "#16181D"
C_ACCENT = "#111827"

ICON_SIZES = {"Kichik": 24, "O'rta": 32, "Katta": 48, "Juda katta": 64}
ICON_MIN, ICON_MAX = 20, 96
EDGES = {"bottom": "Pastda", "top": "Tepada", "left": "Chapda", "right": "O'ngda"}
THEMES = ["Avto", "Och", "To'q"]
APP_EXT = {".exe", ".lnk", ".bat", ".cmd", ".url", ".appref-ms"}

# ---------------------------------------------------------------------------
# Kichik ikonkalar (AI Yordamchi uslubida — qalin, to'q)
# ---------------------------------------------------------------------------
ICONS = {
    "folder": '<path fill="{c}" d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 '
              '3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" stroke-width="2"/>',
    "open": '<path d="M14 3h7v7" stroke-width="3"/><path d="M10 14 21 3" stroke-width="3"/>'
            '<path d="M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5" stroke-width="2.8"/>',
    "close": '<path d="M18 6 6 18" stroke-width="3.6"/><path d="m6 6 12 12" stroke-width="3.6"/>',
}


def svg_pixmap(name, color=C_ICON, size=20) -> QPixmap:
    body = ICONS[name].replace("{c}", color)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="2.5" stroke-linecap="round" '
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


def app_icon(size=256) -> QPixmap:
    """Dastur ikonkasi: gradient fonda dok va uchta ikonka."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#0EA5E9"))
    g.setColorAt(1, QColor("#6366F1"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
    u = size / 24
    p.setBrush(QColor(255, 255, 255, 110))
    p.drawRoundedRect(QRectF(3 * u, 14 * u, 18 * u, 6.5 * u), 2.4 * u, 2.4 * u)
    p.setBrush(QColor("#FFFFFF"))
    for i, h in enumerate((5.0, 7.5, 5.0)):
        x = 5 * u + i * 5.2 * u
        p.drawRoundedRect(QRectF(x, 16.5 * u - h * u, 3.8 * u, h * u + 1.6 * u), 1.1 * u, 1.1 * u)
    p.end()
    return pm


def shadow(w, blur=36, dy=10, alpha=40):
    e = QGraphicsDropShadowEffect(w)
    e.setBlurRadius(blur)
    e.setOffset(0, dy)
    e.setColor(QColor(15, 23, 42, alpha))
    w.setGraphicsEffect(e)


# ---------------------------------------------------------------------------
# Sozlamalar
# ---------------------------------------------------------------------------
def std(loc):
    return QStandardPaths.writableLocation(loc) or ""


def config_path() -> str:
    base = std(QStandardPaths.AppConfigLocation)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "config.json")


def default_items():
    items = []
    if sys.platform == "win32":
        win = os.environ.get("SystemRoot", r"C:\Windows")
        items.append(os.path.join(win, "explorer.exe"))
    for loc in (QStandardPaths.DesktopLocation, QStandardPaths.DocumentsLocation,
                QStandardPaths.PicturesLocation):
        items.append(std(loc))
    return [p for p in items if p and os.path.exists(p)]


def load_config() -> dict:
    cfg = {"items": None, "stack_dir": std(QStandardPaths.DownloadLocation), "icon_px": 24,
           "edge": "top", "idle": 70, "theme": "Avto", "hide_taskbar": True, "autostart": True,
           "auto_hide": True}
    try:
        with open(config_path(), encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    if cfg.get("items") is None:
        cfg["items"] = default_items()
    cfg.pop("size", None)                               # eski versiyalardan o'tish
    if not cfg.get("v3"):
        cfg["icon_px"] = 24                             # yangi standart: 24 px, faqat tepada
        cfg["auto_hide"] = True
        cfg["v3"] = True
    cfg["edge"] = "top"
    try:
        cfg["icon_px"] = max(ICON_MIN, min(ICON_MAX, int(cfg.get("icon_px", 52))))
    except (TypeError, ValueError):
        cfg["icon_px"] = 52
    if cfg.get("edge") not in EDGES:
        cfg["edge"] = "bottom"
    if cfg.get("theme") not in THEMES:
        cfg["theme"] = "Avto"
    try:
        cfg["idle"] = max(25, min(100, int(cfg.get("idle", 70))))
    except (TypeError, ValueError):
        cfg["idle"] = 70
    return cfg


def save_config(cfg: dict) -> None:
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


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
# Windows: taskbar'ni avtomatik yashirish, fayl ko'chirish, dasturda ochish
# ---------------------------------------------------------------------------
def _appbar():
    import ctypes
    from ctypes import wintypes

    class APPBARDATA(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                    ("uCallbackMessage", wintypes.UINT), ("uEdge", wintypes.UINT),
                    ("rc", wintypes.RECT), ("lParam", wintypes.LPARAM)]
    abd = APPBARDATA()
    abd.cbSize = ctypes.sizeof(abd)
    abd.hWnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
    shell = ctypes.windll.shell32
    shell.SHAppBarMessage.restype = ctypes.c_size_t
    return shell, abd, ctypes


def taskbar_state():
    """Taskbar holati (1 — avtomatik yashirinadi). Windows bo'lmasa — None."""
    if sys.platform != "win32":
        return None
    try:
        shell, abd, ct = _appbar()
        return int(shell.SHAppBarMessage(4, ct.byref(abd)))           # ABM_GETSTATE
    except Exception:
        return None


def set_taskbar_state(state: int) -> None:
    if sys.platform != "win32" or state is None:
        return
    try:
        shell, abd, ct = _appbar()
        abd.lParam = int(state)
        shell.SHAppBarMessage(10, ct.byref(abd))                      # ABM_SETSTATE
    except Exception:
        pass


def shell_file_op(paths, dest, move=False):
    """Fayllarni papkaga nusxalash/ko'chirish (Windows'da — oddiy Explorer oynasi bilan)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                            ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                            ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                            ("hNameMappings", ctypes.c_void_p),
                            ("lpszProgressTitle", wintypes.LPCWSTR)]
            op = SHFILEOPSTRUCTW()
            op.wFunc = 1 if move else 2                                # FO_MOVE / FO_COPY
            op.pFrom = "\0".join(paths) + "\0\0"
            op.pTo = dest + "\0\0"
            op.fFlags = 0x0040 | 0x0008                                # ALLOWUNDO | RENAMEONCOLLISION
            ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
            return
        except Exception:
            pass
    for p in paths:
        try:
            target = os.path.join(dest, os.path.basename(p.rstrip("/\\")))
            base, ext = os.path.splitext(target)
            n = 2
            while os.path.exists(target):
                target = f"{base} ({n}){ext}"
                n += 1
            if move:
                shutil.move(p, target)
            elif os.path.isdir(p):
                shutil.copytree(p, target)
            else:
                shutil.copy2(p, target)
        except Exception:
            pass


def open_with(app_path, files):
    """Fayllarni shu dasturda ochish (dastur ikonkasi ustiga tashlanganda)."""
    if sys.platform == "win32":
        try:
            import ctypes
            params = " ".join(f'"{f}"' for f in files)
            ctypes.windll.shell32.ShellExecuteW(None, "open", app_path, params, None, 1)
            return
        except Exception:
            pass
    QProcess.startDetached(app_path, list(files))


def open_path(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def windows_theme():
    """Windows tizim mavzusi: (to'qmi, asosiy rang yoki None).
    Asosiy rang — Windows'da "taskbarda asosiy rangni ko'rsatish" yoqilgan bo'lsa."""
    if sys.platform == "win32":
        dark, tint = False, None
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                try:
                    dark = winreg.QueryValueEx(k, "SystemUsesLightTheme")[0] == 0
                except FileNotFoundError:
                    dark = winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
                try:
                    prevalence = winreg.QueryValueEx(k, "ColorPrevalence")[0]
                except FileNotFoundError:
                    prevalence = 0
            if prevalence:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as k:
                    abgr = winreg.QueryValueEx(k, "AccentColor")[0] & 0xFFFFFFFF
                    tint = QColor(abgr & 0xFF, (abgr >> 8) & 0xFF, (abgr >> 16) & 0xFF)
        except Exception:
            pass
        return dark, tint
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark, None
    except Exception:
        return False, None


def effective_theme(cfg):
    t = cfg.get("theme", "Avto")
    if t == "Och":
        return False, None
    if t == "To'q":
        return True, None
    return windows_theme()


# ---------------------------------------------------------------------------
# Panel elementi
# ---------------------------------------------------------------------------
_PROVIDER = None


def file_icon(path, px) -> QPixmap:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = QFileIconProvider()
    icon = _PROVIDER.icon(QFileInfo(path))
    pm = icon.pixmap(QSize(px, px))
    if pm.isNull():
        pm = icon.pixmap(QSize(64, 64))
    return pm


class DockItem:
    def __init__(self, path, px, stack=False):
        self.path = path
        self.stack = stack
        fi = QFileInfo(path)
        self.is_dir = fi.isDir()
        ext = os.path.splitext(path)[1].lower()
        self.kind = "folder" if self.is_dir else ("app" if ext in APP_EXT else "file")
        if self.is_dir:
            self.name = fi.fileName() or path
        elif ext in APP_EXT:
            self.name = fi.completeBaseName()
        else:
            self.name = fi.fileName()
        self.pm = file_icon(path, px)
        self.lift = 0.0


class FileOps(QObject):
    """Fayl amallari tugaganda ochiq papka oynalarini yangilash uchun."""
    finished = Signal(str)

    def run(self, paths, dest, move):
        def work():
            shell_file_op(paths, dest, move)
            self.finished.emit(dest)
        threading.Thread(target=work, daemon=True).start()


# ---------------------------------------------------------------------------
# Dok-panelning o'zi
# ---------------------------------------------------------------------------
class DockView(QWidget):
    """Dok-panel. Ekranning tepasida turadi; kursor chiqqach tepaga kirib ketadi."""

    def __init__(self, ctrl):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.ctrl = ctrl
        self.cfg = ctrl.cfg
        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.B = self.cfg["icon_px"]
        self.hover = None             # kursorning panel bo'ylab koordinatasi
        self.act = 0.0
        self.drop = None              # ("insert", i) yoki ("into", i)
        self.press = None
        self.drag_idx = None
        self.moving = None            # panelni sudrab joyini o'zgartirish
        self.items = []
        self.dark, self.tint = effective_theme(self.cfg)
        self.collapsed = False
        self.slide = None
        self._out_since = None
        self._born = time.monotonic()     # ochilganda bir marta ko'rinib, keyin yashirinadi
        self.anim = QTimer(self)
        self.anim.setInterval(16)
        self.anim.timeout.connect(self._step)
        self.watch = QTimer(self)
        self.watch.setInterval(200)
        self.watch.timeout.connect(self._tick)
        self.watch.start()
        self.rebuild_items()

    # ---------- yo'nalish ----------
    @property
    def edge(self):
        return "top"                      # panel faqat tepada turadi

    @property
    def horizontal(self):
        return self.edge in ("bottom", "top")

    def main(self, pt):
        """Nuqtaning panel bo'ylab koordinatasi."""
        return pt.x() if self.horizontal else pt.y()

    def set_theme(self, dark, tint):
        if (dark, tint) != (self.dark, self.tint):
            self.dark, self.tint = dark, tint
            self.update()

    # ---------- elementlar ----------
    def rebuild_items(self):
        px = int(self.B * 1.4 * max(1.0, self.devicePixelRatioF()))
        pinned = [p for p in self.cfg.get("items", []) if p and os.path.exists(p)]
        self.items = [DockItem(p, px) for p in pinned]
        self.n_pinned = len(self.items)
        sd = self.cfg.get("stack_dir") or ""
        if sd and os.path.isdir(sd):
            self.items.append(DockItem(sd, px, stack=True))
        self.relayout()

    def set_icon_px(self, px):
        px = max(ICON_MIN, min(ICON_MAX, int(px)))
        if px != self.B:
            self.B = self.cfg["icon_px"] = px
            save_config(self.cfg)
            self.rebuild_items()

    def set_edge(self, edge):
        if edge in EDGES:
            self.cfg["edge"] = edge
            save_config(self.cfg)
            self.relayout()

    def save_pinned(self):
        self.cfg["items"] = [it.path for it in self.items[:self.n_pinned]]
        save_config(self.cfg)

    # ---------- o'lchamlar ----------
    def metrics(self):
        B = self.B
        pad = round(B * 0.22)
        gap = round(B * 0.26)
        rise = round(B * 0.30)
        grow = 0.20
        label = max(round(B * 0.60), 40) if self.horizontal else round(B * 0.6) + 170
        sep = gap + 2 if (self.n_pinned and len(self.items) > self.n_pinned) else 0
        grip = 0
        n = max(1, len(self.items))
        length = 2 * (pad + grip) + n * B + (n - 1) * gap + sep   # panel uzunligi
        thick = B + 2 * pad                                   # panel qalinligi
        side = round(B * grow * 0.6) + 10
        space = rise + round(B * grow) + label                # ichkariga — ko'tarilish va nom uchun
        if self.horizontal:
            W, H = length + 2 * side, space + thick + 10
        else:
            W, H = space + thick + 10, length + 2 * side
        return dict(B=B, pad=pad, gap=gap, rise=rise, grow=grow, sep=sep, grip=grip, length=length,
                    thick=thick, side=side, space=space, W=W, H=H)

    def panel_rect(self):
        m = self.metrics()
        e = self.edge
        if e == "bottom":
            return QRectF(m["side"], m["space"], m["length"], m["thick"])
        if e == "top":
            return QRectF(m["side"], 4, m["length"], m["thick"])
        if e == "left":
            return QRectF(10, m["side"], m["thick"], m["length"])
        return QRectF(m["space"], m["side"], m["thick"], m["length"])

    def hover_rect(self):
        m = self.metrics()
        extra = m["rise"] + m["B"] * m["grow"]
        pr = self.panel_rect()
        return {"bottom": pr.adjusted(0, -extra, 0, 0), "top": pr.adjusted(0, 0, 0, extra),
                "left": pr.adjusted(0, 0, extra, 0), "right": pr.adjusted(-extra, 0, 0, 0)}[self.edge]

    def item_c(self, i):
        """i-elementning panel bo'ylab markazi."""
        m = self.metrics()
        c = m["side"] + m["grip"] + m["pad"] + i * (m["B"] + m["gap"]) + m["B"] / 2
        if i >= self.n_pinned:
            c += m["sep"]
        return c

    def icon_rect(self, i, lift):
        m = self.metrics()
        pr = self.panel_rect()
        S = m["B"] * (1 + m["grow"] * lift)
        off = m["rise"] * lift
        c = self.item_c(i)
        e = self.edge
        if e == "bottom":
            return QRectF(c - S / 2, pr.bottom() - m["pad"] - S - off, S, S)
        if e == "top":
            return QRectF(c - S / 2, pr.top() + m["pad"] + off, S, S)
        if e == "left":
            return QRectF(pr.left() + m["pad"] + off, c - S / 2, S, S)
        return QRectF(pr.right() - m["pad"] - S - off, c - S / 2, S, S)

    def relayout(self):
        m = self.metrics()
        self.setFixedSize(m["W"], m["H"])
        self.reposition()
        self.update()

    def home_pos(self):
        g = QGuiApplication.primaryScreen().availableGeometry()
        return QPoint(g.center().x() - self.width() // 2, g.top())

    def reposition(self):
        if self.collapsed:
            self.ctrl.tab.place()
            return
        if self.slide is not None and self.slide.state() == QParallelAnimationGroup.Running:
            return
        g = QGuiApplication.primaryScreen().availableGeometry()
        e = self.edge
        if e == "top":
            self.move(self.home_pos())
            return
        if e == "bottom":
            self.move(g.center().x() - self.width() // 2, g.bottom() - self.height() - 2)
        elif e == "top":
            self.move(g.center().x() - self.width() // 2, g.top() + 2)
        elif e == "left":
            self.move(g.left() + 2, g.center().y() - self.height() // 2)
        else:
            self.move(g.right() - self.width() - 2, g.center().y() - self.height() // 2)

    # ---------- tepaga kirib ketish / chiqib kelish (AI Yordamchi kabi) ----------
    def _tick(self):
        busy = (self.collapsed or not self.cfg.get("auto_hide", True) or not self.isVisible()
                or self.drop is not None or self.drag_idx is not None or self.press is not None
                or self.ctrl.stack is not None
                or (self.slide is not None and self.slide.state() == QParallelAnimationGroup.Running)
                or QApplication.activePopupWidget() is not None
                or QApplication.activeModalWidget() is not None
                or time.monotonic() - self._born < 3.0)
        if busy or self.frameGeometry().adjusted(-6, -6, 6, 6).contains(QCursor.pos()):
            self._out_since = None
            return
        now = time.monotonic()
        if self._out_since is None:
            self._out_since = now
        elif now - self._out_since >= 0.6:
            self._out_since = None
            self.collapse()

    def _slide(self, end_pos, a, b, on_done=None):
        if self.slide is not None:
            self.slide.stop()
        grp = QParallelAnimationGroup(self)
        pa = QPropertyAnimation(self, b"pos")
        pa.setDuration(220)
        pa.setEasingCurve(QEasingCurve.OutCubic)
        pa.setEndValue(end_pos)
        grp.addAnimation(pa)
        oa = QPropertyAnimation(self, b"windowOpacity")
        oa.setDuration(220)
        oa.setStartValue(a)
        oa.setEndValue(b)
        grp.addAnimation(oa)
        if on_done:
            grp.finished.connect(on_done)
        self.slide = grp
        grp.start()

    def collapse(self):
        if self.collapsed:
            return
        self.collapsed = True
        self.hover = None
        hp = self.home_pos()
        self._slide(QPoint(hp.x(), hp.y() - self.height()), 1.0, 0.0, self._hidden)

    def _hidden(self):
        if not self.collapsed:
            return
        self.hide()
        self.setWindowOpacity(1.0)
        self.ctrl.tab.place()
        self.ctrl.tab.show()
        self.ctrl.tab.raise_()

    def expand(self):
        if not self.collapsed:
            return
        self.collapsed = False
        self._out_since = None
        self._born = time.monotonic() - 2.0          # chiqqandan keyin ~1 soniya yashirinmaydi
        self.ctrl.tab.hide()
        hp = self.home_pos()
        self.move(hp.x(), hp.y() - self.height())
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._slide(hp, 0.0, 1.0)

    # ---------- animatsiya ----------
    def _kick(self):
        if not self.anim.isActive():
            self.anim.start()

    def _targets(self):
        m = self.metrics()
        out = []
        for i in range(len(self.items)):
            if self.hover is None or self.moving is not None:
                out.append(0.0)
            else:
                d = (self.hover - self.item_c(i)) / (m["B"] * 0.95)
                out.append(math.exp(-d * d))
        return out

    def _step(self):
        busy = False
        for it, t in zip(self.items, self._targets()):
            it.lift += (t - it.lift) * 0.28
            if abs(t - it.lift) > 0.004:
                busy = True
            else:
                it.lift = t
        ta = 1.0 if (self.hover is not None or self.drop is not None or self.ctrl.stack
                     or self.moving is not None) else 0.0
        self.act += (ta - self.act) * 0.2
        if abs(ta - self.act) > 0.004:
            busy = True
        else:
            self.act = ta
        self.update()
        if not busy:
            self.anim.stop()

    # ---------- chizish ----------
    def paintEvent(self, e):
        m = self.metrics()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        pr = self.panel_rect()
        a = self.act
        dark = self.dark
        if self.tint is not None:
            base = QColor(self.tint)
        else:
            base = QColor(24, 26, 32) if dark else QColor(255, 255, 255)
        base.setAlpha(int(255 * (0.16 + 0.46 * a)))
        rad = m["thick"] * 0.34
        for i, al in enumerate((14, 9, 5)):                     # yumshoq soya
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, int(al * (0.4 + 0.6 * a))))
            p.drawRoundedRect(pr.adjusted(-i, 2 - i, i, 3 + i), rad + i, rad + i)
        p.setBrush(base)
        p.setPen(QPen(QColor(255, 255, 255, int((40 if dark else 70) + 90 * a)), 1))
        p.drawRoundedRect(pr, rad, rad)

        line_col = QColor(255, 255, 255, 110) if dark else QColor(0, 0, 0, 50)
        if m["sep"]:                                             # ajratuvchi chiziq
            c = self.item_c(self.n_pinned) - m["B"] / 2 - m["gap"] / 2 - m["sep"] / 2
            k = m["pad"] * 0.9
            p.setPen(QPen(line_col, 1.5))
            if self.horizontal:
                p.drawLine(QPointF(c, pr.top() + k), QPointF(c, pr.bottom() - k))
            else:
                p.drawLine(QPointF(pr.left() + k, c), QPointF(pr.right() - k, c))

        idle = self.cfg.get("idle", 70) / 100.0
        hovered = None
        for i, it in enumerate(self.items):
            if i == self.drag_idx:
                continue
            r = self.icon_rect(i, it.lift)
            p.setOpacity(idle + (1 - idle) * max(a, it.lift))
            p.drawPixmap(r, it.pm, QRectF(it.pm.rect()))
            p.setOpacity(1.0)
            if self.drop == ("into", i):
                p.setPen(QPen(QColor("#3B82F6"), 2.5))
                p.setBrush(QColor(59, 130, 246, 40))
                p.drawRoundedRect(r.adjusted(-5, -5, 5, 5), 12, 12)
            if it.lift > 0.72 and self.hover is not None and \
                    (hovered is None or it.lift > hovered[1].lift):
                hovered = (r, it)

        if self.drop and self.drop[0] == "insert":              # qo'shiladigan joy
            i = self.drop[1]
            if i < self.n_pinned:
                c = self.item_c(i) - m["B"] / 2 - m["gap"] / 2
            else:
                c = self.item_c(max(0, self.n_pinned - 1)) + m["B"] / 2 + m["gap"] / 2
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#3B82F6"))
            if self.horizontal:
                p.drawRoundedRect(QRectF(c - 2, pr.top() + 6, 4, pr.height() - 12), 2, 2)
            else:
                p.drawRoundedRect(QRectF(pr.left() + 6, c - 2, pr.width() - 12, 4), 2, 2)

        if hovered and self.drag_idx is None and self.drop is None and self.moving is None:
            r, it = hovered                                      # nom — faqat kursor borganda
            f = QFont("Segoe UI")
            f.setPixelSize(max(11, round(m["B"] * 0.25)))
            f.setBold(True)
            p.setFont(f)
            fm = QFontMetrics(f)
            text = fm.elidedText(it.name, Qt.ElideMiddle, 160 if not self.horizontal else 260)
            tw, th = fm.horizontalAdvance(text) + 20, fm.height() + 10
            e = self.edge
            if e == "bottom":
                box = QRectF(r.center().x() - tw / 2, r.top() - th - 6, tw, th)
            elif e == "top":
                box = QRectF(r.center().x() - tw / 2, r.bottom() + 6, tw, th)
            elif e == "left":
                box = QRectF(r.right() + 8, r.center().y() - th / 2, tw, th)
            else:
                box = QRectF(r.left() - tw - 8, r.center().y() - th / 2, tw, th)
            box.moveLeft(max(2, min(box.left(), self.width() - tw - 2)))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(245, 246, 248, 235) if dark else QColor(17, 24, 39, 215))
            p.drawRoundedRect(box, th / 2, th / 2)
            p.setPen(QColor(C_TEXT) if dark else QColor("#FFFFFF"))
            p.drawText(box, Qt.AlignCenter, text)
        p.end()

    # ---------- sichqoncha ----------
    def item_at(self, pos):
        m = self.metrics()
        if not self.hover_rect().contains(QPointF(pos)):
            return None
        for i in range(len(self.items)):
            if abs(self.main(pos) - self.item_c(i)) <= (m["B"] + m["gap"]) / 2:
                return i
        return None

    def _set_hover(self, pos):
        self.hover = self.main(pos) if self.hover_rect().contains(QPointF(pos)) else None
        self._kick()

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self.moving is not None:                              # panelni sudrash
            self.move((e.globalPosition() - self.moving).toPoint())
            return
        self._set_hover(pos)
        if self.press is not None and (e.buttons() & Qt.LeftButton):
            p0, idx = self.press
            if (pos - p0).manhattanLength() > QApplication.startDragDistance():
                self.press = None
                if idx is not None and idx < self.n_pinned:
                    self._drag_item(idx)

    def leaveEvent(self, e):
        if self.moving is None:
            self.hover = None
            self._kick()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.press = (e.position(), self.item_at(e.position()))

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self.moving is not None:                              # eng yaqin chetga yopishadi
            self.moving = None
            self.unsetCursor()
            g = QGuiApplication.primaryScreen().availableGeometry()
            c = e.globalPosition().toPoint()
            dist = {"bottom": g.bottom() - c.y(), "top": c.y() - g.top(),
                    "left": c.x() - g.left(), "right": g.right() - c.x()}
            self.set_edge(min(dist, key=dist.get))
            self.hover = None
            self._kick()
            return
        if self.press is not None:
            _, idx = self.press
            self.press = None
            if idx is not None and idx == self.item_at(e.position()):
                self.activate(idx)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:                  # Ctrl + g'ildirakcha — o'lcham
            step = 4 if e.angleDelta().y() > 0 else -4
            self.set_icon_px(self.B + step)
            e.accept()

    def activate(self, idx):
        it = self.items[idx]
        if it.is_dir:
            r = self.icon_rect(idx, 0)
            tl = self.mapToGlobal(r.topLeft().toPoint())
            self.ctrl.open_stack(it.path, QRect(tl, r.size().toSize()))
        else:
            open_path(it.path)

    def contextMenuEvent(self, e):
        idx = self.item_at(e.pos())
        menu = QMenu(self)
        if idx is not None:
            it = self.items[idx]
            menu.addAction("Ochish", lambda: open_path(it.path))
            if not it.is_dir:
                menu.addAction("Joylashgan papkani ochish",
                               lambda: open_path(os.path.dirname(it.path)))
            if idx < self.n_pinned:
                menu.addAction("Paneldan olib tashlash", lambda: self.remove(idx))
            menu.addSeparator()
        menu.addAction("Fayl yoki dastur qo'shish…", self.ctrl.add_file)
        menu.addAction("Papka qo'shish…", self.ctrl.add_folder)
        size_menu = menu.addMenu("O'lcham")
        for title, px in ICON_SIZES.items():
            a = size_menu.addAction(f"{title}  ({px}px)", lambda v=px: self.set_icon_px(v))
            a.setCheckable(True)
            a.setChecked(px == self.B)
        theme_menu = menu.addMenu("Fon")
        for t in THEMES:
            a = theme_menu.addAction("Avto (Windows mavzusi)" if t == "Avto" else t,
                                     lambda v=t: self.ctrl.set_theme_mode(v))
            a.setCheckable(True)
            a.setChecked(t == self.cfg.get("theme"))
        menu.addAction("Sozlamalar", self.ctrl.open_settings)
        menu.addSeparator()
        menu.addAction("Chiqish", self.ctrl.quit)
        menu.exec(e.globalPos())

    def remove(self, idx):
        if 0 <= idx < self.n_pinned:
            del self.items[idx]
            self.n_pinned -= 1
            self.save_pinned()
            self.relayout()

    def add_paths(self, paths, at=None):
        have = {os.path.normcase(it.path) for it in self.items[:self.n_pinned]}
        new = [p for p in paths if p and os.path.exists(p) and os.path.normcase(p) not in have]
        if not new:
            return
        cur = [it.path for it in self.items[:self.n_pinned]]
        at = len(cur) if at is None else max(0, min(at, len(cur)))
        self.cfg["items"] = cur[:at] + new + cur[at:]
        save_config(self.cfg)
        self.rebuild_items()

    # ---------- panel ichida sudrash (tartib / olib tashlash) ----------
    def _drag_item(self, idx):
        it = self.items[idx]
        md = QMimeData()
        md.setData(MIME_INDEX, str(idx).encode())
        drag = QDrag(self)
        drag.setMimeData(md)
        pm = it.pm.scaled(self.B, self.B, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        drag.setPixmap(pm)
        drag.setHotSpot(QPoint(pm.width() // 2, pm.height() // 2))
        self.drag_idx = idx
        self.update()
        res = drag.exec(Qt.MoveAction)
        self.drag_idx = None
        if res == Qt.IgnoreAction:
            # paneldan ancha uzoqqa tashlansa — olib tashlanadi (faylning o'zi o'chmaydi)
            local = QPointF(self.mapFromGlobal(QCursor.pos()))
            far = self.panel_rect().adjusted(-self.B * 1.2, -self.B * 1.2, self.B * 1.2, self.B * 1.2)
            if not far.contains(local):
                self.remove(idx)
        self.drop = None
        self.update()

    # ---------- tashqaridan sudrab tashlash ----------
    def _drop_target(self, pos, external):
        idx = self.item_at(pos)
        m = self.metrics()
        if external and idx is not None and self.items[idx].kind in ("folder", "app") \
                and abs(self.main(pos) - self.item_c(idx)) < m["B"] * 0.38:
            return ("into", idx)
        i = 0
        while i < self.n_pinned and self.item_c(i) < self.main(pos):
            i += 1
        return ("insert", i)

    def dragEnterEvent(self, e):
        md = e.mimeData()
        if md.hasFormat(MIME_INDEX) or md.hasUrls():
            e.acceptProposedAction()
            self.dragMoveEvent(e)

    def dragMoveEvent(self, e):
        md = e.mimeData()
        external = not md.hasFormat(MIME_INDEX)
        pos = e.position()
        self.drop = self._drop_target(pos, external)
        self.hover = self.main(pos)
        if external and self.drop[0] == "into":
            e.setDropAction(Qt.MoveAction if e.modifiers() & Qt.ShiftModifier else Qt.CopyAction)
            e.accept()
        else:
            e.acceptProposedAction()
        self._kick()

    def dragLeaveEvent(self, e):
        self.drop = None
        self.hover = None
        self._kick()

    def dropEvent(self, e):
        md = e.mimeData()
        target = self._drop_target(e.position(), not md.hasFormat(MIME_INDEX))
        self.drop = None
        self.hover = None
        if md.hasFormat(MIME_INDEX):
            src = int(bytes(md.data(MIME_INDEX)).decode())
            to = target[1] if target[0] == "insert" else src
            paths = [it.path for it in self.items[:self.n_pinned]]
            if 0 <= src < len(paths):
                p = paths.pop(src)
                if to > src:
                    to -= 1
                paths.insert(max(0, min(to, len(paths))), p)
                self.cfg["items"] = paths
                save_config(self.cfg)
                self.rebuild_items()
            e.acceptProposedAction()
            return
        paths = [u.toLocalFile() for u in md.urls() if u.isLocalFile()]
        if not paths:
            return
        if target[0] == "into":
            it = self.items[target[1]]
            if it.is_dir:
                move = bool(e.modifiers() & Qt.ShiftModifier)
                self.ctrl.file_op(paths, it.path, move)
                e.setDropAction(Qt.MoveAction if move else Qt.CopyAction)
            else:
                open_with(it.path, paths)
                e.setDropAction(Qt.CopyAction)
            e.accept()
        else:
            self.add_paths(paths, target[1])
            e.setDropAction(Qt.LinkAction)
            e.accept()
        self._kick()


# ---------------------------------------------------------------------------
# Yashiringanda ekran tepasida qoladigan shaffof chiziq
# ---------------------------------------------------------------------------
class EdgeTab(QWidget):
    def __init__(self, ctrl):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.ctrl = ctrl
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(APP_NAME)

    def place(self):
        dock = self.ctrl.dock
        g = QGuiApplication.primaryScreen().geometry()
        length = dock.metrics()["length"] if dock is not None else 200
        w = max(90, min(260, int(length * 0.5)))
        self.setFixedSize(w, 7)
        self.move(g.center().x() - w // 2, g.top())

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))      # Windows'da sichqonchani "ushlab" turishi uchun
        dock = self.ctrl.dock
        dark = dock.dark if dock is not None else False
        tint = dock.tint if dock is not None else None
        c = QColor(tint) if tint is not None else (QColor(235, 236, 240) if dark else QColor(30, 34, 42))
        c.setAlpha(150)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(0, 1, self.width(), 4), 2, 2)
        p.end()

    def enterEvent(self, e):
        self.ctrl.dock.expand()

    def mousePressEvent(self, e):
        self.ctrl.dock.expand()

    def dragEnterEvent(self, e):
        self.ctrl.dock.expand()                       # fayl sudrab kelinsa ham chiqadi
        e.ignore()


# ---------------------------------------------------------------------------
# Papka oynasi (ichidagilar; sudrab olish va tashlash mumkin)
# ---------------------------------------------------------------------------
class StackCell(QWidget):
    def __init__(self, stack, path, size):
        super().__init__()
        self.stack, self.path = stack, path
        self.name = os.path.basename(path.rstrip("/\\")) or path
        self.pm = file_icon(path, int(size * 1.5))
        self.icon = size
        self.press = None
        self.setFixedSize(int(size * 1.9), int(size * 1.9))
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(self.name)
        self.hover = False

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 120) if not self.stack.dark else QColor(255, 255, 255, 35))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(3, 3, -3, -3), 12, 12)
        s = self.icon
        r = QRectF((self.width() - s) / 2, 8, s, s)
        p.drawPixmap(r, self.pm, QRectF(self.pm.rect()))
        f = QFont("Segoe UI")
        f.setPixelSize(max(10, round(s * 0.22)))
        p.setFont(f)
        fm = QFontMetrics(f)
        txt = fm.elidedText(self.name, Qt.ElideMiddle, self.width() - 8)
        p.setPen(QColor("#F3F4F6") if self.stack.dark else QColor(C_TEXT))
        p.drawText(QRectF(4, r.bottom() + 4, self.width() - 8, fm.height() + 2), Qt.AlignHCenter, txt)
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.press = e.position()

    def mouseMoveEvent(self, e):
        if self.press is not None and (e.position() - self.press).manhattanLength() > \
                QApplication.startDragDistance():
            self.press = None
            md = QMimeData()
            md.setUrls([QUrl.fromLocalFile(self.path)])
            drag = QDrag(self)
            drag.setMimeData(md)
            pm = self.pm.scaled(self.icon, self.icon, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            drag.setPixmap(pm)
            drag.setHotSpot(QPoint(pm.width() // 2, pm.height() // 2))
            self.stack.dragging = True
            drag.exec(Qt.CopyAction | Qt.MoveAction | Qt.LinkAction, Qt.CopyAction)
            self.stack.dragging = False
            QTimer.singleShot(300, self.stack.refresh)

    def mouseReleaseEvent(self, e):
        if self.press is not None and e.button() == Qt.LeftButton:
            self.press = None
            open_path(self.path)
            self.stack.close()


class FolderStack(QWidget):
    COLS = 5
    MAX = 120

    def __init__(self, ctrl, folder, anchor: QRect):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.ctrl, self.folder, self.anchor = ctrl, folder, anchor
        self.dragging = False
        self.dark = ctrl.dock.dark if ctrl.dock is not None else False
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAcceptDrops(True)
        self.size_ = max(40, min(64, ctrl.cfg["icon_px"]))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        self.card = QFrame()
        self.card.setObjectName("glassDark" if self.dark else "glass")
        shadow(self.card, 40, 12, 60)
        outer.addWidget(self.card)
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)
        top = QHBoxLayout()
        name = QLabel(os.path.basename(folder.rstrip("/\\")) or folder)
        name.setObjectName("stackTitleDark" if self.dark else "stackTitle")
        top.addWidget(name)
        top.addStretch()
        for icon, tip, fn in [("open", "Explorer'da ochish", lambda: (open_path(folder), self.close())),
                              ("close", "Yopish (Esc)", self.close)]:
            b = QToolButton()
            b.setObjectName("glassBtn")
            b.setIcon(QIcon(svg_pixmap(icon, "#F3F4F6" if self.dark else C_ICON, 16)))
            b.setIconSize(QSize(16, 16))
            b.setFixedSize(30, 30)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            top.addWidget(b)
        lay.addLayout(top)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setObjectName("stackScroll")
        lay.addWidget(self.scroll)
        self.refresh()

    def entries(self):
        try:
            items = []
            with os.scandir(self.folder) as it:
                for e in it:
                    if e.name.startswith(".") or e.name.lower() in ("desktop.ini", "thumbs.db"):
                        continue
                    try:
                        mt = e.stat().st_mtime
                    except OSError:
                        mt = 0
                    items.append((mt, e.path))
            items.sort(reverse=True)                    # eng yangilari birinchi
            return [p for _, p in items[:self.MAX]]
        except OSError:
            return []

    def refresh(self):
        if not self.isVisible() and self.scroll.widget() is not None:
            return
        body = QWidget()
        body.setObjectName("stackBody")
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)
        paths = self.entries()
        for i, p in enumerate(paths):
            grid.addWidget(StackCell(self, p, self.size_), i // self.COLS, i % self.COLS)
        if not paths:
            empty = QLabel("—")
            empty.setAlignment(Qt.AlignCenter)
            empty.setMinimumSize(int(self.size_ * 3), int(self.size_ * 1.6))
            grid.addWidget(empty, 0, 0)
        self.scroll.setWidget(body)
        cell = int(self.size_ * 1.9) + 2
        cols = max(1, min(self.COLS, len(paths)))
        rows = max(1, math.ceil(len(paths) / self.COLS))
        self.scroll.setFixedSize(cols * cell + (14 if rows > 4 else 0) + 4, min(rows, 4) * cell + 4)
        self.adjustSize()
        self.place()

    def place(self):
        """Panel qaysi chetda bo'lsa — papka oynasi ekran ichkarisi tomonga ochiladi."""
        scr = QGuiApplication.screenAt(self.anchor.center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        a = self.anchor
        edge = self.ctrl.cfg.get("edge", "bottom")
        if edge in ("bottom", "top"):
            x = a.center().x() - self.width() // 2
            y = a.top() - self.height() + 6 if edge == "bottom" else a.bottom() - 6
        else:
            y = a.center().y() - self.height() // 2
            x = a.right() - 6 if edge == "left" else a.left() - self.width() + 6
        x = max(g.left(), min(x, g.right() - self.width()))
        y = max(g.top(), min(y, g.bottom() - self.height()))
        self.move(x, y)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

    def changeEvent(self, e):
        if e.type() == QEvent.ActivationChange and not self.isActiveWindow() and not self.dragging:
            QTimer.singleShot(120, lambda: (not self.isActiveWindow() and not self.dragging
                                            and self.close()))
        super().changeEvent(e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        e.setDropAction(Qt.MoveAction if e.modifiers() & Qt.ShiftModifier else Qt.CopyAction)
        e.accept()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        paths = [p for p in paths if os.path.dirname(p.rstrip("/\\")) != self.folder.rstrip("/\\")]
        if paths:
            move = bool(e.modifiers() & Qt.ShiftModifier)
            self.ctrl.file_op(paths, self.folder, move)
            e.setDropAction(Qt.MoveAction if move else Qt.CopyAction)
            e.accept()

    def closeEvent(self, e):
        self.ctrl.stack_closed(self)
        super().closeEvent(e)


# ---------------------------------------------------------------------------
# Sozlamalar oynasi
# ---------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, cfg):
        super().__init__(None)
        self.setWindowTitle(f"{APP_NAME} — Sozlamalar")
        self.setWindowIcon(QIcon(app_icon()))
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(8)
        t = QLabel("Sozlamalar")
        t.setObjectName("title")
        lay.addWidget(t)

        lay.addWidget(self._section("Dock papkasi (panelning o'ng chetida turadi)"))
        row = QHBoxLayout()
        self.stack_dir = cfg.get("stack_dir") or ""
        self.dir_lbl = QLabel(self.stack_dir or "—")
        self.dir_lbl.setObjectName("muted")
        self.dir_lbl.setWordWrap(True)
        row.addWidget(self.dir_lbl, 1)
        pick = QPushButton("Tanlash…")
        pick.clicked.connect(self._pick)
        row.addWidget(pick)
        clear = QPushButton("Olib tashlash")
        clear.clicked.connect(lambda: (setattr(self, "stack_dir", ""), self.dir_lbl.setText("—")))
        row.addWidget(clear)
        lay.addLayout(row)

        lay.addSpacing(6)
        lay.addWidget(self._section("Ikonkalar o'lchami (panel ustida Ctrl + g'ildirakcha)"))
        srow = QHBoxLayout()
        self.icon_px = QSlider(Qt.Horizontal)
        self.icon_px.setRange(ICON_MIN, ICON_MAX)
        self.icon_px.setSingleStep(2)
        self.icon_px.setValue(int(cfg.get("icon_px", 52)))
        srow.addWidget(self.icon_px, 1)
        self.px_lbl = QLabel(f"{self.icon_px.value()} px")
        self.px_lbl.setMinimumWidth(52)
        self.icon_px.valueChanged.connect(lambda v: self.px_lbl.setText(f"{v} px"))
        srow.addWidget(self.px_lbl)
        lay.addLayout(srow)
        prow = QHBoxLayout()
        for title, px in ICON_SIZES.items():
            b = QPushButton(title)
            b.setObjectName("seg")
            b.clicked.connect(lambda _=False, v=px: self.icon_px.setValue(v))
            prow.addWidget(b)
        lay.addLayout(prow)

        lay.addSpacing(6)
        lay.addWidget(self._section("Ko'rinish"))
        trow = QHBoxLayout()
        trow.addWidget(QLabel("Fon:"))
        self.theme_group = QButtonGroup(self)
        for name in THEMES:
            b = QPushButton("Avto (Windows)" if name == "Avto" else name)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setProperty("key", name)
            b.setChecked(name == cfg.get("theme"))
            self.theme_group.addButton(b)
            trow.addWidget(b)
        trow.addStretch()
        lay.addLayout(trow)
        orow = QHBoxLayout()
        orow.addWidget(QLabel("Foydalanilmaganda ko'rinishi:"))
        self.idle = QSlider(Qt.Horizontal)
        self.idle.setRange(25, 100)
        self.idle.setValue(int(cfg.get("idle", 70)))
        orow.addWidget(self.idle, 1)
        self.idle_lbl = QLabel(f"{self.idle.value()}%")
        self.idle.valueChanged.connect(lambda v: self.idle_lbl.setText(f"{v}%"))
        orow.addWidget(self.idle_lbl)
        lay.addLayout(orow)

        lay.addSpacing(6)
        lay.addWidget(self._section("Windows"))
        self.auto_hide = QCheckBox("  Kursor chiqqach tepaga kirib ketsin (shaffof chiziq bo'lib tursin)")
        self.auto_hide.setChecked(cfg.get("auto_hide", True))
        lay.addWidget(self.auto_hide)
        self.hide_tb = QCheckBox("  Windows taskbar'ini yashirish")
        self.hide_tb.setChecked(cfg.get("hide_taskbar", True))
        self.hide_tb.setEnabled(sys.platform == "win32")
        lay.addWidget(self.hide_tb)
        self.autostart = QCheckBox("  Kompyuter yonganda o'zi ishga tushsin")
        self.autostart.setChecked(cfg.get("autostart", True))
        self.autostart.setEnabled(sys.platform == "win32")
        lay.addWidget(self.autostart)

        lay.addSpacing(14)
        bottom = QHBoxLayout()
        credit = QLabel(f'<a href="{AUTHOR_URL}" style="color:{C_MUTED};text-decoration:none;">'
                        f'by <b style="color:{C_TEXT};">{AUTHOR}</b></a>')
        credit.setOpenExternalLinks(True)
        credit.setCursor(Qt.PointingHandCursor)
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

    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, "Dock papkasini tanlang", self.stack_dir)
        if d:
            self.stack_dir = d
            self.dir_lbl.setText(d)

    def values(self):
        t = self.theme_group.checkedButton()
        return {"stack_dir": self.stack_dir, "icon_px": self.icon_px.value(),
                "edge": "top", "auto_hide": self.auto_hide.isChecked(),
                "theme": t.property("key") if t else "Avto", "idle": self.idle.value(),
                "hide_taskbar": self.hide_tb.isChecked(), "autostart": self.autostart.isChecked()}


STYLE = f"""
* {{ font-family: "Segoe UI", "Inter", Arial; font-size: 14px; color: {C_TEXT}; }}
QDialog {{ background: #FFFFFF; }}
#title {{ font-size: 16px; font-weight: 700; }}
#section {{ font-size: 12px; font-weight: 700; color: {C_MUTED}; text-transform: uppercase; }}
#muted {{ color: {C_MUTED}; font-size: 12px; }}
QPushButton {{ border: 1px solid {C_BORDER}; border-radius: 12px; padding: 8px 14px;
    background: #FFFFFF; font-weight: 600; }}
QPushButton:hover {{ background: {C_HOVER}; }}
QPushButton#primary {{ background: {C_ACCENT}; color: white; border: none; }}
QPushButton#seg:checked {{ background: {C_ACCENT}; color: white; border: 1px solid {C_ACCENT}; }}
QCheckBox {{ padding: 4px 0; }}
#glass {{ background: rgba(255,255,255,200); border: 1px solid rgba(255,255,255,170);
    border-radius: 22px; }}
#glassDark {{ background: rgba(22,24,30,205); border: 1px solid rgba(255,255,255,40);
    border-radius: 22px; }}
#stackTitle {{ font-size: 13px; font-weight: 700; color: {C_TEXT}; }}
#stackTitleDark {{ font-size: 13px; font-weight: 700; color: #F3F4F6; }}
#stackScroll, #stackBody {{ background: transparent; }}
QToolButton#glassBtn {{ background: rgba(255,255,255,150); border: none; border-radius: 15px; }}
QToolButton#glassBtn:hover {{ background: rgba(255,255,255,235); }}
QMenu {{ background: #FFFFFF; border: 1px solid {C_BORDER}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {C_HOVER}; color: {C_TEXT}; }}
QToolTip {{ background: white; color: {C_TEXT}; border: 1px solid {C_BORDER}; padding: 4px 8px; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ background: rgba(120,125,140,120); border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


# ---------------------------------------------------------------------------
# Boshqaruvchi
# ---------------------------------------------------------------------------
class Controller:
    def __init__(self, app):
        self.app = app
        self.cfg = load_config()
        save_config(self.cfg)
        self.stack = None
        self.dock = None
        self.tab = None
        self.ops = FileOps()
        self.ops.finished.connect(self._op_done)

        self.tray = QSystemTrayIcon(QIcon(app_icon()))
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        menu.addAction("Fayl yoki dastur qo'shish…", self.add_file)
        menu.addAction("Papka qo'shish…", self.add_folder)
        menu.addAction("Sozlamalar", self.open_settings)
        menu.addSeparator()
        menu.addAction("Chiqish", self.quit)
        self._menu = menu
        self.tray.setContextMenu(menu)
        self.tray.show()

        self.apply_windows()
        self.tab = EdgeTab(self)
        self.dock = DockView(self)
        self.dock.show()
        scr = QGuiApplication.primaryScreen()
        scr.availableGeometryChanged.connect(lambda _g: self.dock.reposition())
        QTimer.singleShot(1500, self.dock.reposition)      # taskbar yashirilgach joyini to'g'rilaymiz

        # Windows mavzusi (och/to'q, asosiy rang) o'zgarsa — panel rangi ham o'zgaradi
        self.theme_timer = QTimer()
        self.theme_timer.timeout.connect(self.refresh_theme)
        self.theme_timer.start(3000)
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _s: self.refresh_theme())
        except Exception:
            pass

    def refresh_theme(self):
        dark, tint = effective_theme(self.cfg)
        if self.dock is not None:
            self.dock.set_theme(dark, tint)
            self.tab.update()

    def set_theme_mode(self, mode):
        self.cfg["theme"] = mode
        save_config(self.cfg)
        self.refresh_theme()

    def apply_windows(self):
        if self.cfg.get("autostart"):
            try:
                set_autostart(True)
            except Exception:
                pass
        if self.cfg.get("hide_taskbar"):
            cur = taskbar_state()
            if cur is not None:
                if "tb_prev" not in self.cfg:
                    self.cfg["tb_prev"] = cur              # avvalgi holatni eslab qolamiz
                    save_config(self.cfg)
                set_taskbar_state(1)                      # ABS_AUTOHIDE
        else:
            self.restore_taskbar()

    def restore_taskbar(self):
        if "tb_prev" in self.cfg:
            set_taskbar_state(self.cfg.pop("tb_prev"))
            save_config(self.cfg)

    # ---- papka oynasi ----
    def open_stack(self, folder, anchor):
        if self.stack is not None:
            same = self.stack.folder == folder
            self.stack.close()
            if same:
                return
        self.stack = FolderStack(self, folder, anchor)
        self.stack.show()
        self.stack.raise_()
        self.stack.activateWindow()
        self.dock._kick()

    def stack_closed(self, st):
        if self.stack is st:
            self.stack = None
        self.dock._kick()

    def file_op(self, paths, dest, move):
        self.ops.run(paths, dest, move)

    def _op_done(self, dest):
        if self.stack is not None and os.path.normcase(self.stack.folder) == os.path.normcase(dest):
            self.stack.refresh()

    # ---- qo'shish ----
    def add_file(self):
        files, _ = QFileDialog.getOpenFileNames(None, "Panelga qo'shish")
        if files:
            self.dock.add_paths(files)

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(None, "Panelga papka qo'shish")
        if d:
            self.dock.add_paths([d])

    def open_settings(self):
        dlg = SettingsDialog(self.cfg)
        if dlg.exec():
            v = dlg.values()
            if v["autostart"] != self.cfg.get("autostart"):
                try:
                    set_autostart(v["autostart"])
                except Exception:
                    v["autostart"] = self.cfg.get("autostart")
            tb_changed = v["hide_taskbar"] != self.cfg.get("hide_taskbar")
            self.cfg.update(v)
            save_config(self.cfg)
            if tb_changed:
                self.apply_windows()
            self.dock.B = self.cfg["icon_px"]
            if not self.cfg.get("auto_hide", True):
                self.dock.expand()
            self.dock.rebuild_items()
            self.refresh_theme()
            QTimer.singleShot(1200, self.dock.reposition)

    def quit(self):
        if self.stack is not None:
            self.stack.close()
        self.tab.hide()
        self.restore_taskbar()            # dastur yopilsa — Windows taskbar avvalgi holatiga qaytadi
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
    app.setWindowIcon(QIcon(app_icon()))
    app.setStyleSheet(STYLE)

    # faqat bitta nusxa
    name = "DockPanel-" + re.sub(r"\W", "", os.environ.get("USERNAME") or
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
        if ctrl.dock.collapsed:
            ctrl.dock.expand()
        ctrl.dock._born = time.monotonic()
        ctrl.dock.show()
        ctrl.dock.raise_()
    server.newConnection.connect(on_new)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
