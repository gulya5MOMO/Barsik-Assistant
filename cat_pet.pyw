import os
os.environ.pop("ALL_PROXY", None)
os.environ.pop("all_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ["NO_PROXY"] = "*"

import sys
import math
import threading
import subprocess
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit
from PyQt6.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath

import pystray
from PIL import Image, ImageDraw

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATE_FILE = os.path.join(BASE_DIR, "cat_state.txt")
COMMAND_FILE = os.path.join(BASE_DIR, "cat_command.txt")
VOICE_FILE = os.path.join(BASE_DIR, "voice_state.txt")
MOUTH_FILE = os.path.join(BASE_DIR, "mouth_state.txt")

PARENT_PID = None
if len(sys.argv) > 1:
    try:
        PARENT_PID = int(sys.argv[1])
    except Exception:
        pass


def get_voice_state() -> bool:
    try:
        if os.path.exists(VOICE_FILE):
            with open(VOICE_FILE, "r", encoding="utf-8") as f:
                return f.read().strip() == "1"
    except Exception:
        pass
    return True


def set_voice_state(enabled: bool):
    try:
        with open(VOICE_FILE, "w", encoding="utf-8") as f:
            f.write("1" if enabled else "0")
    except Exception:
        pass


def get_mouth_state() -> bool:
    try:
        if os.path.exists(MOUTH_FILE):
            with open(MOUTH_FILE, "r", encoding="utf-8") as f:
                return f.read().strip() == "1"
    except Exception:
        pass
    return True


def set_mouth_state(enabled: bool):
    try:
        with open(MOUTH_FILE, "w", encoding="utf-8") as f:
            f.write("1" if enabled else "0")
    except Exception:
        pass


def make_tray_image():
    ico_path = os.path.join(BASE_DIR, "cat.ico")
    if os.path.exists(ico_path):
        try:
            img = Image.open(ico_path).convert("RGBA")
            img = img.resize((64, 64), Image.LANCZOS)
            return img
        except Exception:
            pass

    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 8, 58, 58), fill=(20, 20, 25, 255))
    d.polygon([(12, 20), (6, 2), (24, 14)], fill=(20, 20, 25, 255))
    d.polygon([(52, 20), (58, 2), (40, 14)], fill=(20, 20, 25, 255))
    d.ellipse((18, 26, 28, 38), fill=(255, 220, 100, 255))
    d.ellipse((36, 26, 46, 38), fill=(255, 220, 100, 255))
    d.ellipse((21, 30, 25, 36), fill=(10, 10, 10, 255))
    d.ellipse((39, 30, 43, 36), fill=(10, 10, 10, 255))
    return img


class DesktopCat(QWidget):
    show_signal = pyqtSignal()
    quit_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.W = 220
        self.H = 240
        self.resize(self.W, self.H)

        self.tick = 0
        self.blink = False
        self.state = "idle"
        self.mouth_open = False
        self.paw_phase = 0
        self.voice_on = get_voice_state()
        self.mouth_on = get_mouth_state()

        self.input_box = QLineEdit(self)
        self.input_box.setPlaceholderText("Команда... Enter")
        self.input_box.setGeometry(10, 5, self.W - 20, 30)
        self.input_box.setStyleSheet("""
            QLineEdit {
                background: #1e1e1e;
                color: #ffffff;
                border: 2px solid #2d7d46;
                border-radius: 6px;
                padding: 4px 8px;
                font-family: Segoe UI;
                font-size: 10pt;
            }
        """)
        self.input_box.returnPressed.connect(self.send_command)
        self.input_box.show()
        self.input_box.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(50)

        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.do_blink)
        self.blink_timer.start(3000)

        self.state_timer = QTimer()
        self.state_timer.timeout.connect(self.read_state)
        self.state_timer.start(300)

        self.position_near_clock()
        self.old_pos = None

        self.show_signal.connect(self._show_from_tray)
        self.quit_signal.connect(self._quit_app)

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        QApplication.quit()

    def read_state(self):
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    s = f.read().strip()
                if s and s != self.state:
                    self.state = s
                    self.update()
        except Exception:
            pass
        self.voice_on = get_voice_state()
        self.mouth_on = get_mouth_state()

    def send_command(self):
        text = self.input_box.text().strip()
        if text:
            try:
                with open(COMMAND_FILE, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception:
                pass
        self.input_box.clear()
        self.input_box.clearFocus()

    def animate(self):
        self.tick += 1
        self.paw_phase = (self.paw_phase + 1) % 20
        # Рот двигается только если:
        # 1) сейчас состояние talking (ассистент говорит)
        # 2) тумблер "рот" включён
        if self.state == "talking" and self.mouth_on:
            self.mouth_open = (self.tick % 6) < 3
        else:
            self.mouth_open = False
        self.update()

    def do_blink(self):
        if self.state == "happy":
            return
        self.blink = True
        self.update()
        QTimer.singleShot(150, self.end_blink)

    def end_blink(self):
        self.blink = False
        self.update()

    def position_near_clock(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - self.W - 20
        y = screen.height() - self.H - 10
        self.move(x, y)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        black = QColor(20, 20, 25)
        eye_color = QColor(255, 220, 100)
        nose_color = QColor(255, 130, 150)
        pink_inner = QColor(90, 40, 55)

        oy = 40
        cx = self.W // 2
        state = self.state

        tail_speed = 8
        if state in ("thinking", "talking"):
            tail_speed = 4
        elif state == "error":
            tail_speed = 30

        tail_angle = math.sin(self.tick / tail_speed) * 25
        if state == "error":
            tail_angle = -30
        elif state == "happy":
            tail_angle = 40

        tail_pen = QPen(black, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(tail_pen)
        tail_base = QPointF(cx + 30, 130 + oy)
        angle_rad = math.radians(tail_angle - 40)
        tail_len = 55
        tail_end = QPointF(
            tail_base.x() + math.cos(angle_rad) * tail_len,
            tail_base.y() + math.sin(angle_rad) * tail_len
        )
        mid = QPointF(
            tail_base.x() + math.cos(angle_rad) * tail_len * 0.5,
            tail_base.y() + math.sin(angle_rad) * tail_len * 0.5 - 10
        )
        path = QPainterPath(tail_base)
        path.quadTo(mid, tail_end)
        p.drawPath(path)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(black))
        p.drawEllipse(cx - 42, 75 + oy, 84, 70)

        paw_offset = 0
        if state == "working":
            paw_offset = int(math.sin(self.paw_phase / 2) * 4)

        p.drawEllipse(cx - 30, 130 + oy + paw_offset, 22, 16)
        p.drawEllipse(cx + 8, 130 + oy - paw_offset, 22, 16)

        head_y = 20 + oy
        if state == "thinking":
            head_y = 24 + oy
        elif state == "error":
            head_y = 28 + oy

        p.drawEllipse(cx - 45, head_y, 90, 80)

        ear_tilt = 0
        if state == "error":
            ear_tilt = -10
        elif state == "thinking":
            ear_tilt = 5

        left_ear = QPainterPath()
        left_ear.moveTo(cx - 40, head_y + 15)
        left_ear.lineTo(cx - 55 + ear_tilt, head_y - 25)
        left_ear.lineTo(cx - 20, head_y + 2)
        left_ear.closeSubpath()
        p.setBrush(QBrush(black))
        p.drawPath(left_ear)

        right_ear = QPainterPath()
        right_ear.moveTo(cx + 40, head_y + 15)
        right_ear.lineTo(cx + 55 - ear_tilt, head_y - 25)
        right_ear.lineTo(cx + 20, head_y + 2)
        right_ear.closeSubpath()
        p.drawPath(right_ear)

        p.setBrush(QBrush(pink_inner))
        li = QPainterPath()
        li.moveTo(cx - 38, head_y + 12)
        li.lineTo(cx - 47 + ear_tilt, head_y - 14)
        li.lineTo(cx - 26, head_y + 4)
        li.closeSubpath()
        p.drawPath(li)

        ri = QPainterPath()
        ri.moveTo(cx + 38, head_y + 12)
        ri.lineTo(cx + 47 - ear_tilt, head_y - 14)
        ri.lineTo(cx + 26, head_y + 4)
        ri.closeSubpath()
        p.drawPath(ri)

        eye_y = head_y + 38

        if state == "happy":
            p.setPen(QPen(eye_color, 3))
            p.drawArc(cx - 30, eye_y - 5, 18, 14, 0, 180 * 16)
            p.drawArc(cx + 12, eye_y - 5, 18, 14, 0, 180 * 16)
        elif state == "error":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(eye_color))
            p.drawEllipse(cx - 30, eye_y - 8, 18, 14)
            p.drawEllipse(cx + 12, eye_y - 8, 18, 14)
            p.setBrush(QBrush(QColor(10, 10, 10)))
            p.drawEllipse(cx - 24, eye_y - 2, 6, 8)
            p.drawEllipse(cx + 18, eye_y - 2, 6, 8)
        elif state == "thinking":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(eye_color))
            p.drawEllipse(cx - 32, eye_y - 16, 22, 26)
            p.drawEllipse(cx + 10, eye_y - 16, 22, 26)
            p.setBrush(QBrush(QColor(10, 10, 10)))
            p.drawEllipse(cx - 25, eye_y - 8, 8, 18)
            p.drawEllipse(cx + 17, eye_y - 8, 8, 18)
        elif self.blink:
            p.setPen(QPen(eye_color, 3))
            p.drawLine(cx - 28, eye_y, cx - 12, eye_y)
            p.drawLine(cx + 12, eye_y, cx + 28, eye_y)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(eye_color))
            if state == "working":
                p.drawEllipse(cx - 28, eye_y - 8, 16, 16)
                p.drawEllipse(cx + 12, eye_y - 8, 16, 16)
            else:
                p.drawEllipse(cx - 30, eye_y - 12, 18, 22)
                p.drawEllipse(cx + 12, eye_y - 12, 18, 22)
            p.setBrush(QBrush(QColor(10, 10, 10)))
            p.drawEllipse(cx - 24, eye_y - 6, 6, 14)
            p.drawEllipse(cx + 18, eye_y - 6, 6, 14)

        nose = QPainterPath()
        nose.moveTo(cx, head_y + 60)
        nose.lineTo(cx - 6, head_y + 54)
        nose.lineTo(cx + 6, head_y + 54)
        nose.closeSubpath()
        p.setBrush(QBrush(nose_color))
        p.drawPath(nose)

        p.setPen(QPen(black, 2))
        # Рот: открывается только если тумблер "рот" ВКЛ
        if state == "talking" and self.mouth_open and self.mouth_on:
            p.setBrush(QBrush(QColor(60, 20, 30)))
            p.drawEllipse(cx - 10, head_y + 62, 20, 14)
        elif state == "happy":
            p.drawArc(cx - 12, head_y + 58, 24, 16, 0, -180 * 16)
        else:
            p.drawLine(cx, head_y + 60, cx, head_y + 66)
            p.drawLine(cx, head_y + 66, cx - 8, head_y + 70)
            p.drawLine(cx, head_y + 66, cx + 8, head_y + 70)

        p.setPen(QPen(QColor(180, 180, 180), 1))
        p.drawLine(cx - 20, head_y + 62, cx - 55, head_y + 58)
        p.drawLine(cx - 20, head_y + 65, cx - 55, head_y + 66)
        p.drawLine(cx - 20, head_y + 68, cx - 55, head_y + 74)
        p.drawLine(cx + 20, head_y + 62, cx + 55, head_y + 58)
        p.drawLine(cx + 20, head_y + 65, cx + 55, head_y + 66)
        p.drawLine(cx + 20, head_y + 68, cx + 55, head_y + 74)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() > 38:
                self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None

    def contextMenuEvent(self, event):
        event.ignore()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


def run_tray(cat):
    def on_show(icon, item):
        cat.show_signal.emit()

    def on_hide(icon, item):
        cat.hide()

    def on_toggle_voice(icon, item):
        current = get_voice_state()
        set_voice_state(not current)
        cat.voice_on = not current
        try:
            cmd = "голос выкл" if current else "голос вкл"
            with open(COMMAND_FILE, "w", encoding="utf-8") as f:
                f.write(cmd)
        except Exception:
            pass
        try:
            icon.update_menu()
        except Exception:
            pass

    def on_toggle_mouth(icon, item):
        current = get_mouth_state()
        set_mouth_state(not current)
        cat.mouth_on = not current
        try:
            icon.update_menu()
        except Exception:
            pass

    def voice_label(item):
        return "🔊 Голос: ВКЛ" if get_voice_state() else "🔇 Голос: ВЫКЛ"

    def mouth_label(item):
        return "👄 Рот: ВКЛ" if get_mouth_state() else "👄 Рот: ВЫКЛ"

    def on_quit(icon, item):
        icon.stop()
        try:
            if PARENT_PID:
                subprocess.run(f"taskkill /F /PID {PARENT_PID}", shell=True,
                               capture_output=True)
        except Exception:
            pass
        cat.quit_signal.emit()

    menu = pystray.Menu(
        pystray.MenuItem("Показать кота", on_show, default=True),
        pystray.MenuItem("Спрятать", on_hide),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(voice_label, on_toggle_voice),
        pystray.MenuItem(mouth_label, on_toggle_mouth),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Выход (закрыть всё)", on_quit),
    )
    icon = pystray.Icon("BarsikCat", make_tray_image(), "Барсик", menu)
    icon.run()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    cat = DesktopCat()
    cat.show()
    t = threading.Thread(target=run_tray, args=(cat,), daemon=True)
    t.start()
    sys.exit(app.exec())