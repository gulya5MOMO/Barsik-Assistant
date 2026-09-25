import os
os.environ.pop("ALL_PROXY", None)
os.environ.pop("all_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ["NO_PROXY"] = "*"

import subprocess
import time
import re
import sys
import glob
import shutil
import ctypes
import wave
import io
import urllib.parse
import webbrowser
import threading
import requests
import mss
import pytesseract
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FTimeout
import pyautogui
import pygetwindow as gw
import pygame
import pyttsx3
from ddgs import DDGS

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUNTIME_DIR = os.path.join(BASE_DIR, "runtime")
OLLAMA_DIR = os.path.join(RUNTIME_DIR, "ollama")
OLLAMA_EXE = os.path.join(OLLAMA_DIR, "ollama.exe")
MODELS_DIR = os.path.join(RUNTIME_DIR, "models")
TESSERACT_EXE = os.path.join(RUNTIME_DIR, "tesseract", "tesseract.exe")

STATE_FILE = os.path.join(BASE_DIR, "cat_state.txt")
COMMAND_FILE = os.path.join(BASE_DIR, "cat_command.txt")
VOICE_FILE = os.path.join(BASE_DIR, "voice_state.txt")

if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
else:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

OLLAMA_PROCESS = None


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


if not os.path.exists(VOICE_FILE):
    set_voice_state(True)


def start_ollama():
    global OLLAMA_PROCESS
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        if r.status_code == 200:
            return True
    except Exception:
        pass

    if not os.path.exists(OLLAMA_EXE):
        return False

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = MODELS_DIR
    env["OLLAMA_HOST"] = "127.0.0.1:11434"
    env["NO_PROXY"] = "*"

    try:
        OLLAMA_PROCESS = subprocess.Popen(
            [OLLAMA_EXE, "serve"],
            env=env,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=OLLAMA_DIR,
        )
    except Exception:
        return False

    for _ in range(30):
        time.sleep(1)
        try:
            r = requests.get("http://127.0.0.1:11434/api/tags", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
    return False


start_ollama()

import ollama

LLM_MODEL = "qwen2.5:3b"
FAST_OPTS = {"temperature": 0.3, "num_predict": 150, "num_ctx": 1024}
SEARCH_TIMEOUT = 6

VOICE_ENABLED = get_voice_state()
VOICE_ID = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_RU-RU_IRINA_11.0"
VOICE_RATE = 200
VOICE_PITCH = 1.6

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

CAT_PERSONA = (
    "Ты — чёрный кот-ассистент Барсик. Умеешь управлять ПК. "
    "Милый, дерзкий, иногда вставляешь «мяу». "
    "Отвечай по-русски, коротко (1-3 предложения). "
    "ЗАПРЕЩЕНО: эмодзи, смайлики, иероглифы."
)

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
]

KNOWN_APPS = {
    "блокнот": "notepad.exe", "notepad": "notepad.exe",
    "вордпад": "write.exe", "wordpad": "write.exe",
    "заметки": "ms-stickynotes:", "стикеры": "ms-stickynotes:",
    "калькулятор": "calc.exe", "calc": "calc.exe",
    "проводник": "explorer.exe", "explorer": "explorer.exe",
    "консоль": "cmd.exe", "cmd": "cmd.exe", "терминал": "cmd.exe",
    "powershell": "powershell.exe",
    "диспетчер задач": "taskmgr.exe", "taskmgr": "taskmgr.exe",
    "диспетчер устройств": "devmgmt.msc",
    "службы": "services.msc",
    "реестр": "regedit.exe", "regedit": "regedit.exe",
    "планировщик": "taskschd.msc",
    "монитор ресурсов": "resmon.exe",
    "сведения о системе": "msinfo32.exe",
    "управление компьютером": "compmgmt.msc",
    "просмотр событий": "eventvwr.msc",
    "управление дисками": "diskmgmt.msc",
    "восстановление системы": "rstrui.exe",
    "очистка диска": "cleanmgr.exe",
    "настройка системы": "msconfig.exe",
    "монитор стабильности": "perfmon.exe",
    "редактор политик": "gpedit.msc",
    "брандмауэр": "wf.msc", "firewall": "wf.msc",
    "свойства системы": "sysdm.cpl",
    "программы и компоненты": "appwiz.cpl",
    "звук": "mmsys.cpl", "звуки": "mmsys.cpl",
    "экран": "desk.cpl", "дисплей": "desk.cpl",
    "мышь": "main.cpl",
    "дата и время": "timedate.cpl",
    "регион": "intl.cpl", "языки": "intl.cpl",
    "питание": "powercfg.cpl",
    "шрифты": "control fonts",
    "панель управления": "control.exe",
    "настройки": "ms-settings:", "параметры": "ms-settings:",
    "паинт": "mspaint.exe", "paint": "mspaint.exe", "пейнт": "mspaint.exe",
    "фото": "ms-photos:", "фотографии": "ms-photos:",
    "ножницы": "snippingtool.exe", "snipping tool": "snippingtool.exe",
    "photoshop": "photoshop.exe", "фотошоп": "photoshop.exe",
    "gimp": "gimp-2.10.exe",
    "paint.net": "paintdotnet.exe",
    "inkscape": "inkscape.exe",
    "krita": "krita.exe",
    "blender": "blender.exe", "блендер": "blender.exe",
    "3d max": "3dsmax.exe",
    "maya": "maya.exe",
    "figma": "figma.exe",
    "canva": "canva.exe",
    "проигрыватель": "wmplayer.exe",
    "vlc": "vlc.exe", "влс": "vlc.exe",
    "mpc": "mpc-hc64.exe",
    "kmplayer": "kmplayer.exe",
    "potplayer": "potplayer.exe",
    "фильмы": "ms-filmstv:", "movies": "ms-filmstv:",
    "obs": "obs64.exe", "обс": "obs64.exe",
    "bandicam": "bdcam.exe",
    "camtasia": "camtasia.exe",
    "movavi": "movavi.exe",
    "da vinci": "resolve.exe",
    "premiere": "adobe premiere pro.exe",
    "after effects": "afterfx.exe",
    "vegas": "vegas190.exe",
    "spotify": "spotify.exe", "спотифай": "spotify.exe",
    "itunes": "itunes.exe",
    "aimp": "aimp.exe",
    "foobar": "foobar2000.exe",
    "audacity": "audacity.exe",
    "fl studio": "fl64.exe",
    "ableton": "ableton live 11.exe",
    "chrome": "chrome.exe", "хром": "chrome.exe", "браузер": "chrome.exe",
    "edge": "msedge.exe", "эдж": "msedge.exe",
    "firefox": "firefox.exe", "файрфокс": "firefox.exe",
    "opera": "opera.exe", "опера": "opera.exe",
    "brave": "brave.exe",
    "vivaldi": "vivaldi.exe",
    "yandex": "browser.exe", "яндекс браузер": "browser.exe",
    "word": "winword.exe", "ворд": "winword.exe",
    "excel": "excel.exe", "эксель": "excel.exe",
    "powerpoint": "powerpnt.exe", "поверпоинт": "powerpnt.exe",
    "outlook": "outlook.exe", "аутлук": "outlook.exe",
    "access": "msaccess.exe",
    "teams": "teams.exe", "тимс": "teams.exe",
    "visio": "visio.exe",
    "libreoffice": "soffice.exe",
    "почта": "outlookmail:",
    "календарь": "outlookcal:",
    "карты": "bingmaps:",
    "погода": "bingweather:",
    "магазин": "ms-windows-store:",
    "xbox": "xbox:",
    "telegram": "telegram.exe", "телеграм": "telegram.exe",
    "тг": "telegram.exe",
    "whatsapp": "whatsapp.exe", "ватсап": "whatsapp.exe",
    "discord": "discord://", "дискорд": "discord://", "дс": "discord://",
    "skype": "skype.exe", "скайп": "skype.exe",
    "zoom": "zoom.exe", "зум": "zoom.exe",
    "slack": "slack.exe",
    "viber": "viber.exe",
    "vk": "vk.exe", "вк": "vk.exe",
    "vscode": "code", "вс код": "code", "vs code": "code",
    "visual studio": "devenv.exe",
    "pycharm": "pycharm64.exe", "пайчарм": "pycharm64.exe",
    "intellij": "idea64.exe",
    "android studio": "studio64.exe",
    "sublime": "sublime_text.exe",
    "notepad++": "notepad++.exe",
    "git": "git-bash.exe",
    "github desktop": "githubdesktop.exe",
    "docker": "docker desktop.exe",
    "postman": "postman.exe",
    "wireshark": "wireshark.exe",
    "filezilla": "filezilla.exe",
    "putty": "putty.exe",
    "unity": "unity.exe", "юнити": "unity.exe",
    "unreal": "unrealengine.exe",
    "steam": "steam://open/main", "стим": "steam://open/main",
    "epic": "com.epicgames.launcher://",
    "origin": "origin://",
    "uplay": "uplay://",
    "battle.net": "battlenet://",
    "gog": "goggalaxy://",
    "roblox": "roblox://", "роблокс": "roblox://",
    "minecraft": "minecraft://", "майнкрафт": "minecraft://",
    "defender": "windowsdefender:",
    "касперский": "avp.exe",
    "avast": "avastui.exe",
    "eset": "egui.exe",
    "norton": "nortonsecurity.exe",
    "malwarebytes": "mbam.exe",
    "7zip": "7zfm.exe", "7 zip": "7zfm.exe",
    "winrar": "winrar.exe", "винрар": "winrar.exe",
    "ccleaner": "ccleaner64.exe",
    "revo uninstaller": "revouninstaller.exe",
    "cpu-z": "cpuz.exe",
    "gpu-z": "gpuz.exe",
    "hwinfo": "hwinfo64.exe",
    "msi afterburner": "msiafterburner.exe",
    "fraps": "fraps.exe",
    "geforce experience": "nvidia geforce experience.exe",
    "nvidia control panel": "nvcplui.exe",
    "яндекс диск": "yandexdisk.exe",
    "google drive": "googledrivefs.exe",
    "dropbox": "dropbox.exe",
    "onedrive": "onedrive.exe",
    "cortana": "ms-cortana:",
    "новости": "msnnews:",
}

STEAM_GAMES = {
    "cs": "730", "cs2": "730", "кс": "730", "кс2": "730",
    "dota": "570", "dota2": "570", "дота": "570",
    "pubg": "578080", "gta": "271590", "гта": "271590",
    "rust": "252490", "раст": "252490", "terraria": "105600",
}

SPECIAL_FOLDERS = {
    "изображения": "pictures", "картинки": "pictures", "фото": "pictures",
    "документы": "personal", "видео": "videos", "музыка": "music",
    "загрузки": "downloads", "скачанное": "downloads",
    "рабочий стол": "desktop", "desktop": "desktop",
}

MATH_WORDS = {
    "плюс": "+", "минус": "-", "умножить на": "*", "умножить": "*",
    "разделить на": "/", "разделить": "/", "делить на": "/", "делить": "/",
}


def set_cat_state(state: str):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(state)
    except Exception:
        pass


def find_chrome():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None


def normalize(text: str) -> str:
    fixes = [
        (r"\bотрой\b", "открой"), (r"\bокрой\b", "открой"),
        (r"\bотктой\b", "открой"), (r"\bаткрой\b", "открой"),
        (r"\bнайдти\b", "найди"), (r"\bнати\b", "найди"),
        (r"\bнайти\b", "найди"), (r"\bпоискать\b", "найди"),
        (r"\bпоиск\b", "найди"), (r"\bпаищи\b", "поищи"),
        (r"\bнапиш\b", "напиши"),
        (r"\bдиспечер\b", "диспетчер"), (r"\bустрйств\b", "устройств"),
        (r"\bриблкс\b", "роблокс"), (r"\bдс\b", "дискорд"),
        (r"\bдск\b", "дискорд"), (r"\bдис\b", "дискорд"),
        (r"\bкс\b", "кс2"), (r"\bдотка\b", "дота"), (r"\bтг\b", "телеграм"),
        (r"\bсоздать\b", "создай"), (r"\bудалить\b", "удали"),
        (r"\bпереименовать\b", "переименуй"),
        (r"\bудалит\b", "удали"), (r"\bстереть\b", "сотри"),
    ]
    out = text
    for pat, repl in fixes:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out


def clean_output(text: str) -> str:
    text = re.sub(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u3000-\u303f]+', '', text)
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
    text = re.sub(r'[\U00002600-\U000027BF]', '', text)
    text = re.sub(r'[\U0001F000-\U0001F2FF]', '', text)
    text = re.sub(r'[\u2600-\u26FF\u2700-\u27BF]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_math(text: str) -> str:
    s = text.lower()
    for word, sym in MATH_WORDS.items():
        s = s.replace(word, sym)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^0-9+\-*/().]", "", s)
    return s


def safe_eval(expr: str):
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expr):
            return None
        result = eval(expr, {"__builtins__": {}}, {})
        if isinstance(result, float) and result.is_integer():
            return int(result)
        return result
    except Exception:
        return None


def speak(text: str):
    # Всегда читаем актуальное состояние из файла
    if not get_voice_state():
        return
    if not text:
        return
    text = clean_output(text)
    if not text:
        return
    set_cat_state("talking")
    try:
        raw = os.path.join(BASE_DIR, "tts_raw.wav")
        out = os.path.join(BASE_DIR, "tts_out.wav")
        for p in (raw, out):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        engine = pyttsx3.init()
        engine.setProperty("voice", VOICE_ID)
        engine.setProperty("rate", VOICE_RATE)
        engine.save_to_file(text, raw)
        engine.runAndWait()
        engine.stop()

        for _ in range(50):
            if os.path.exists(raw) and os.path.getsize(raw) > 1000:
                break
            time.sleep(0.1)
        else:
            set_cat_state("idle")
            return

        with wave.open(raw, "rb") as w:
            params = w.getparams()
            frames = w.readframes(w.getnframes())

        with wave.open(out, "wb") as w:
            w.setnchannels(params.nchannels)
            w.setsampwidth(params.sampwidth)
            w.setframerate(int(params.framerate * VOICE_PITCH))
            w.writeframes(frames)

        pygame.mixer.init()
        pygame.mixer.music.load(out)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()
    except Exception:
        pass
    finally:
        set_cat_state("idle")


SendInput = ctypes.windll.user32.SendInput


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong), ("ki", KEYBDINPUT),
        ("padding", ctypes.c_ubyte * 8),
    ]


def send_unicode_char(char: str):
    code = ord(char)
    inputs = (INPUT * 2)()
    inputs[0].type = 1
    inputs[0].ki.wScan = code
    inputs[0].ki.dwFlags = 0x0004
    inputs[1].type = 1
    inputs[1].ki.wScan = code
    inputs[1].ki.dwFlags = 0x0004 | 0x0002
    SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def type_text(text: str):
    set_cat_state("working")
    try:
        is_ascii = all(ord(c) < 128 for c in text)
        if not is_ascii:
            try:
                import pyperclip
                pyperclip.copy(text)
                time.sleep(0.2)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.2)
                set_cat_state("idle")
                return
            except Exception:
                pass

        for c in text:
            send_unicode_char(c)
            time.sleep(0.02)
    except Exception:
        pass
    finally:
        set_cat_state("idle")


def wait_for_window(title_substrings, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            for title in title_substrings:
                wins = gw.getWindowsWithTitle(title)
                for w in wins:
                    if w.width > 100 and w.height > 100:
                        return w
        except Exception:
            pass
        time.sleep(0.3)
    return None


def focus_window(w, retries=3):
    for i in range(retries):
        try:
            if w.isMinimized:
                w.restore()
                time.sleep(0.4)
            w.activate()
            time.sleep(0.5)
            cx = w.left + w.width // 2
            cy = w.top + w.height // 2
            pyautogui.click(cx, cy)
            time.sleep(0.3)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def focus_and_click(substring: str, timeout: float = 6.0) -> bool:
    w = wait_for_window([substring, "Блокнот", "Notepad",
                         "Calculator", "Калькулятор"], timeout)
    if w:
        return focus_window(w)
    return False


def search_start_menu(name: str):
    name_low = name.lower()
    patterns = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\**\*.lnk"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\**\*.lnk"),
    ]
    for p in patterns:
        try:
            for lnk in glob.glob(p, recursive=True):
                base = os.path.splitext(os.path.basename(lnk))[0].lower()
                if name_low == base or name_low in base:
                    return lnk
        except Exception:
            pass
    return None


def search_in_folders(name: str, max_depth: int = 3):
    name_low = name.lower()
    bases = [
        r"C:\Program Files", r"C:\Program Files (x86)",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        os.path.expandvars(r"%LOCALAPPDATA%"),
        r"C:\Games",
    ]

    def scan(folder, depth):
        if depth > max_depth:
            return None
        try:
            entries = os.listdir(folder)
        except Exception:
            return None
        for e in entries:
            if e.lower().endswith(".exe") and name_low in e.lower():
                full = os.path.join(folder, e)
                low = e.lower()
                if any(x in low for x in ["unins", "update", "helper", "crash", "setup"]):
                    continue
                return full
        for e in entries:
            full = os.path.join(folder, e)
            if os.path.isdir(full):
                if name_low in e.lower() or len(name_low) < 4:
                    r = scan(full, depth + 1)
                    if r:
                        return r
        return None

    for b in bases:
        if not os.path.exists(b):
            continue
        r = scan(b, 0)
        if r:
            return r
    return None


def find_discord():
    update = os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe")
    if os.path.exists(update):
        return ("update", update)
    matches = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Discord\app-*\Discord.exe"))
    if matches:
        return ("exe", sorted(matches)[-1])
    return None


def pc_open(program: str):
    n = program.lower().strip().strip('"').strip("'")
    set_cat_state("working")

    if n in ("notepad.exe", "блокнот", "notepad", "блакнот"):
        subprocess.run("taskkill /F /IM notepad.exe", shell=True, capture_output=True)
        time.sleep(0.8)
        notes_path = os.path.join(BASE_DIR, "cat_notes.txt")
        try:
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass
        subprocess.Popen(["notepad.exe", notes_path])
        w = wait_for_window(["cat_notes", "Блокнот", "Notepad"], timeout=8.0)
        if w:
            focus_window(w)
        time.sleep(0.5)
        return True, "cat_notes"

    if n in KNOWN_APPS:
        target = KNOWN_APPS[n]
        try:
            if "://" in target or target.endswith(":"):
                os.startfile(target)
            else:
                subprocess.Popen(f'start "" {target}', shell=True)
            return True, None
        except Exception:
            return False, None

    if n in STEAM_GAMES:
        try:
            os.startfile(f"steam://run/{STEAM_GAMES[n]}")
            return True, None
        except Exception:
            return False, None

    if "discord" in n or "дискорд" in n:
        d = find_discord()
        if d:
            kind, path = d
            try:
                if kind == "update":
                    subprocess.Popen([path, "--processStart", "Discord.exe"])
                else:
                    os.startfile(path)
                return True, None
            except Exception:
                return False, None

    lnk = search_start_menu(n)
    if lnk:
        try:
            os.startfile(lnk)
            return True, None
        except Exception:
            return False, None

    exe = search_in_folders(n)
    if exe:
        try:
            subprocess.Popen([exe])
            return True, None
        except Exception:
            return False, None

    return False, None


def pc_open_folder(name: str) -> bool:
    n = name.lower().strip()
    if n in SPECIAL_FOLDERS:
        target = SPECIAL_FOLDERS[n]
        if target.startswith("C:"):
            if os.path.exists(target):
                subprocess.Popen(f'explorer "{target}"')
                return True
        else:
            subprocess.Popen(f"explorer shell:{target}")
            return True
    home = os.path.expanduser("~")
    for c in [os.path.join(home, "Desktop", name), os.path.join(home, "Desktop", n)]:
        if os.path.exists(c) and os.path.isdir(c):
            subprocess.Popen(f'explorer "{c}"')
            return True
    return False


def _clean_name(name: str) -> str:
    n = name.strip().strip('"').strip("'").strip()
    n = re.sub(r"\s+на\s+(рабочем\s+столе|пк|компьютере|десктопе)$", "", n, flags=re.IGNORECASE)
    n = re.sub(r"^с\s+названием\s+", "", n, flags=re.IGNORECASE)
    return n.strip()


def pc_create_folder(name: str) -> str:
    n = _clean_name(name)
    if not n:
        return "не понял имя"
    path = os.path.join(os.path.expanduser("~"), "Desktop", n)
    if os.path.exists(path):
        return f"папка {n} уже есть"
    try:
        os.makedirs(path)
        return f"создал папку {n}"
    except Exception as e:
        return f"ошибка: {e}"


def pc_create_file(name: str, content: str = "") -> str:
    n = _clean_name(name)
    if not n:
        return "не понял имя"
    if not os.path.splitext(n)[1]:
        n += ".txt"
    path = os.path.join(os.path.expanduser("~"), "Desktop", n)
    if os.path.exists(path):
        return f"файл {n} уже есть"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"создал файл {n}"
    except Exception as e:
        return f"ошибка: {e}"


def pc_delete(name: str) -> str:
    n = _clean_name(name)
    if not n:
        return "не понял имя"

    home = os.path.expanduser("~")
    desktop = os.path.join(home, "Desktop")
    found = None

    candidates = [os.path.join(desktop, n)]
    for ext in [".txt", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".mp3", ".mp4", ".pdf", ".zip", ".xlsx"]:
        candidates.append(os.path.join(desktop, n + ext))

    for c in candidates:
        if os.path.exists(c):
            found = c
            break

    if not found:
        try:
            for entry in os.listdir(desktop):
                if os.path.splitext(entry)[0].lower() == n.lower():
                    found = os.path.join(desktop, entry)
                    break
        except Exception:
            pass

    if not found:
        return f"не нашёл {n}"

    try:
        if os.path.isdir(found):
            shutil.rmtree(found)
            return f"удалил папку {n}"
        else:
            os.remove(found)
            return f"удалил файл {n}"
    except Exception as e:
        return f"ошибка: {e}"


def pc_rename(old: str, new: str) -> str:
    o = _clean_name(old)
    n = _clean_name(new)
    if not o or not n:
        return "не понял"

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    old_path = None

    for c in [os.path.join(desktop, o), os.path.join(desktop, o + ".txt")]:
        if os.path.exists(c):
            old_path = c
            break

    if not old_path:
        try:
            for entry in os.listdir(desktop):
                if os.path.splitext(entry)[0].lower() == o.lower():
                    old_path = os.path.join(desktop, entry)
                    break
        except Exception:
            pass

    if not old_path:
        return f"не нашёл {o}"

    ext = os.path.splitext(old_path)[1]
    new_path = os.path.join(desktop, n + ext)

    if os.path.exists(new_path):
        return f"{n} уже существует"

    try:
        os.rename(old_path, new_path)
        return f"переименовал {o} в {n}"
    except Exception as e:
        return f"ошибка: {e}"


def pc_close(program: str) -> bool:
    proc_map = {
        "ютуб": ["chrome.exe"], "youtube": ["chrome.exe"],
        "браузер": ["chrome.exe"], "хром": ["chrome.exe"],
        "chrome": ["chrome.exe"],
        "блокнот": ["notepad.exe"],
        "калькулятор": ["calc.exe", "Calculator.exe", "CalculatorApp.exe"],
        "проводник": ["explorer.exe"],
        "консоль": ["cmd.exe"],
        "диспетчер": ["Taskmgr.exe"],
        "дискорд": ["Discord.exe"],
        "телеграм": ["Telegram.exe"],
        "стим": ["steam.exe"],
    }
    t = program.lower()
    for key, procs in proc_map.items():
        if key in t:
            for p in procs:
                subprocess.run(f"taskkill /F /IM {p}", shell=True, capture_output=True)
            return True
    return False


def open_url(url: str):
    chrome = find_chrome()
    if chrome:
        subprocess.Popen([chrome, "--new-window", url])
    else:
        webbrowser.open(url)


def take_screenshot() -> Image.Image:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        return Image.frombytes("RGB", raw.size, raw.rgb)


def read_screen_text() -> str:
    set_cat_state("thinking")
    img = take_screenshot()
    try:
        text = pytesseract.image_to_string(img, lang="rus+eng").strip()
    except Exception:
        text = ""
    set_cat_state("idle")
    return text


def handle_ocr(task: str) -> bool:
    t = task.lower()

    if "что на экране" in t or "что видишь" in t or "опиши экран" in t:
        text = read_screen_text()
        if not text:
            speak("Ничего не вижу")
            return True
        set_cat_state("thinking")
        prompt = f"Вот текст с экрана:\n\n{text[:1500]}\n\nКратко скажи что открыто. Как кот."
        try:
            resp = ollama.chat(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": CAT_PERSONA},
                    {"role": "user", "content": prompt},
                ],
                options=FAST_OPTS,
                keep_alive="30m",
            )
            answer = clean_output(resp["message"]["content"])
        except Exception as e:
            answer = f"Ошибка: {e}"
        speak(answer)
        return True

    if "прочитай экран" in t or "прочитай текст" in t:
        text = read_screen_text()
        if not text:
            speak("Текст не найден")
            return True
        speak("Прочитал")
        return True

    m = re.search(r"(?:найди|найти|ищи)\s+на\s+экране\s+(.+)", task, re.IGNORECASE)
    if m:
        needle = m.group(1).strip().lower()
        text = read_screen_text().lower()
        if needle in text:
            speak("Нашёл")
        else:
            speak("Не нашёл")
        return True

    return False


def wiki_search(query: str) -> str:
    try:
        r = requests.get(
            "https://ru.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search",
                    "srsearch": query, "format": "json", "srlimit": 1},
            timeout=4,
        )
        results = r.json().get("query", {}).get("search", [])
        if not results:
            return ""
        title = results[0]["title"]
        r2 = requests.get(
            f"https://ru.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}",
            timeout=4,
        )
        extract = r2.json().get("extract", "")
        if extract:
            return f"{title}: {extract}"
    except Exception:
        pass
    return ""


def _ddg_search(query, max_results):
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


def ddg_search(query: str, max_results: int = 3) -> str:
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_ddg_search, query, max_results)
            results = future.result(timeout=SEARCH_TIMEOUT)
    except (FTimeout, Exception):
        return ""
    if not results:
        return ""
    return "\n".join(f"- {r.get('title','')}: {r.get('body','')}" for r in results)


def web_search(query: str) -> str:
    q = re.sub(r"^(кто такой|кто такая|что такое)\s+", "", query, flags=re.IGNORECASE).strip()
    wiki = wiki_search(q)
    if wiki:
        return wiki
    return ddg_search(query)


def handle_browser(task: str) -> bool:
    t = task.lower()

    if "ютуб" in t or "youtube" in t:
        cleaned = re.sub(
            r"\b(напиши|найди|покажи|включи|поищи|открой|зайди|перейди|мне|на|в|ютуб|youtube|видео|ролик|ролики)\b",
            " ", t, flags=re.IGNORECASE
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) > 2:
            open_url(f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(cleaned)}")
            speak(f"Ищу {cleaned}")
        else:
            open_url("https://www.youtube.com")
            speak("Открываю ютуб")
        return True

    if re.match(r"^(найди|поищи|погугли|загугли|поиск|ищи)\b", t):
        engine = "google" if "гугл" in t or "google" in t else "yandex"
        cleaned = re.sub(
            r"\b(найди|поищи|погугли|загугли|поиск|ищи|"
            r"в|на|интернете|мне|пожалуйста|"
            r"гугл|google|яндекс|yandex|покажи|дай)\b",
            " ", task, flags=re.IGNORECASE
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) < 2:
            alt = re.sub(
                r"^(найди|поищи|погугли|загугли|поиск|ищи)\s+"
                r"(в\s+(гугл[еа]?|яндекс[еа]?|интернете?)\s+)?",
                "", task, flags=re.IGNORECASE
            ).strip()
            if len(alt) > 2:
                cleaned = alt
        if len(cleaned) < 2:
            speak("Что искать?")
            return True
        if engine == "google":
            open_url(f"https://www.google.com/search?q={urllib.parse.quote_plus(cleaned)}")
        else:
            open_url(f"https://yandex.ru/search/?text={urllib.parse.quote_plus(cleaned)}")
        speak(f"Ищу {cleaned}")
        return True

    return False


def handle_chat(question: str, use_search: bool = False):
    ctx = ""
    if use_search:
        ctx = web_search(question)
    user = f"Вопрос: {question}\n\nКонтекст:\n{ctx}\n\nОтветь как кот." if ctx else question

    full = ""
    set_cat_state("thinking")
    try:
        for chunk in ollama.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": CAT_PERSONA},
                {"role": "user", "content": user},
            ],
            keep_alive="30m",
            options=FAST_OPTS,
            stream=True,
        ):
            piece = chunk["message"]["content"]
            full += piece
    except Exception:
        set_cat_state("idle")
        speak("Не могу ответить")
        return
    full = clean_output(full)
    set_cat_state("idle")
    if len(full) < 200:
        speak(full)


def handle_mouse_keys(task: str) -> bool:
    t = task.lower().strip()
    set_cat_state("working")

    m = re.search(r"(?:двинь|передвинь|переведи|перемести)\s+мыш[ьи]\s+(?:в\s+)?(\d+)\s+(\d+)", t)
    if m:
        pyautogui.moveTo(int(m.group(1)), int(m.group(2)), duration=0.3)
        set_cat_state("idle")
        speak("Двинул")
        return True

    m = re.search(r"кликни\s+(?:в\s+)?(\d+)\s+(\d+)", t)
    if m:
        pyautogui.click(int(m.group(1)), int(m.group(2)))
        set_cat_state("idle")
        speak("Кликнул")
        return True

    if re.match(r"^(кликни|щёлкни)$", t):
        pyautogui.click()
        set_cat_state("idle")
        speak("Кликнул")
        return True

    if "двойной клик" in t or "дважды кликни" in t:
        pyautogui.doubleClick()
        set_cat_state("idle")
        speak("Двойной клик")
        return True

    if "правый клик" in t or "правой кнопкой" in t:
        pyautogui.rightClick()
        set_cat_state("idle")
        speak("Правый клик")
        return True

    if "прокрути вверх" in t:
        pyautogui.scroll(500)
        set_cat_state("idle")
        speak("Прокрутил")
        return True
    if "прокрути вниз" in t:
        pyautogui.scroll(-500)
        set_cat_state("idle")
        speak("Прокрутил")
        return True

    if "где мышь" in t or "координаты мыши" in t:
        x, y = pyautogui.position()
        set_cat_state("idle")
        speak(f"Мышь в {x} {y}")
        return True

    hotkeys = {
        "скопируй": ["ctrl", "c"], "копируй": ["ctrl", "c"],
        "вставь": ["ctrl", "v"],
        "вырежи": ["ctrl", "x"],
        "отмени": ["ctrl", "z"],
        "выдели всё": ["ctrl", "a"], "выдели все": ["ctrl", "a"],
        "сохрани": ["ctrl", "s"],
        "переключи окно": ["alt", "tab"], "смени окно": ["alt", "tab"],
        "закрой окно": ["alt", "f4"], "закрой активное": ["alt", "f4"],
        "сверни все": ["win", "d"], "покажи рабочий стол": ["win", "d"],
        "открой пуск": ["win"], "меню пуск": ["win"],
        "выполнить": ["win", "r"],
        "новую вкладку": ["ctrl", "t"], "закрой вкладку": ["ctrl", "w"],
        "обнови": ["ctrl", "r"],
        "переключи раскладку": ["alt", "shift"],
    }

    for key_phrase, keys in hotkeys.items():
        if key_phrase in t:
            pyautogui.hotkey(*keys)
            set_cat_state("idle")
            speak("Нажал")
            return True

    m = re.search(r"нажми\s+(ctrl|alt|shift|win)\s*\+\s*(\w+)", t)
    if m:
        pyautogui.hotkey(m.group(1), m.group(2))
        set_cat_state("idle")
        speak("Нажал")
        return True

    set_cat_state("idle")
    return False


def handle_pc_simple(task: str) -> bool:
    t = task.lower()

    if handle_mouse_keys(task):
        return True

    m = re.match(
        r"^(?:открой|запусти|включи)\s+(.+?)\s+(?:и|потом|затем)\s+(?:напиши|напечатай|введи|вставь)\s+(.+)",
        task, re.IGNORECASE
    )
    if m:
        prog = m.group(1).strip()
        txt = m.group(2).strip().strip('"').strip("'")
        ok, title = pc_open(prog)
        if not ok:
            speak(f"Не нашёл {prog}")
            return True
        time.sleep(1.5)
        if title:
            w = wait_for_window(["cat_notes", "Блокнот", "Notepad"], timeout=5)
            if w:
                focus_window(w)
        time.sleep(0.5)
        type_text(txt)
        speak("Готово")
        return True

    m = re.match(
        r"^(?:удали|сотри|убрать|стереть)\s+(.+)$",
        task, re.IGNORECASE
    )
    if m:
        name = m.group(1).strip()
        name = re.sub(r"^(?:папку|файл|документ|док)\s+", "", name, flags=re.IGNORECASE)
        name = name.strip()
        result = pc_delete(name)
        speak(result)
        return True

    m = re.match(
        r"^(?:переименуй|переименовать)\s+(?:папку\s+|файл\s+)?(.+?)\s+(?:в|на)\s+(.+)$",
        task, re.IGNORECASE
    )
    if m:
        old = m.group(1).strip()
        new = m.group(2).strip()
        result = pc_rename(old, new)
        speak(result)
        return True

    m = re.match(
        r"^(?:создай|сделай)\s+папку\s+(.+)$",
        task, re.IGNORECASE
    )
    if m:
        name = m.group(1).strip()
        result = pc_create_folder(name)
        speak(result)
        return True

    m = re.match(
        r"^(?:создай|сделай)\s+(?:текстовый\s+)?(?:файл|документ|док)\s+(.+)$",
        task, re.IGNORECASE
    )
    if m:
        name = m.group(1).strip()
        result = pc_create_file(name)
        speak(result)
        return True

    m = re.match(r"^(?:открой|покажи|запусти)\s+папку\s+(.+)", task, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        name = re.sub(r"\s+на\s+(пк|рабочем столе|компьютере)\s*$", "", name, flags=re.IGNORECASE).strip()
        if pc_open_folder(name):
            speak(f"Открыл папку {name}")
        else:
            speak(f"Не нашёл папку {name}")
        return True

    m = re.match(r"^(?:закрой|выключи|заверши)\s+(.+)", task, re.IGNORECASE)
    if m:
        target = m.group(1).strip()
        if pc_close(target):
            speak(f"Закрыл {target}")
        else:
            speak(f"Не нашёл {target}")
        return True

    m = re.match(
        r"^(?:открой|запусти)\s+(калькулятор|calc)\s+и\s+(?:посчитай|вычисли|сосчитай|посчитать)\s+(.+)",
        task, re.IGNORECASE
    )
    if m:
        expr_raw = m.group(2).strip()
        expr = parse_math(expr_raw)
        ok, _ = pc_open("calc")
        if not ok:
            speak("Не смог открыть калькулятор")
            return True
        time.sleep(1.5)
        w = wait_for_window(["Калькулятор", "Calculator"], timeout=5)
        if w:
            focus_window(w)
        if expr:
            time.sleep(0.4)
            type_text(expr)
            time.sleep(0.3)
            pyautogui.press("enter")
            result = safe_eval(expr)
            if result is not None:
                speak(f"{expr_raw} — это {result}")
        return True

    m = re.match(r"^(?:посчитай|вычисли|сосчитай|сколько будет|сколько)\s+(.+)", task, re.IGNORECASE)
    if m:
        expr_raw = m.group(1).strip()
        expr = parse_math(expr_raw)
        if expr and re.search(r"[0-9]", expr) and re.search(r"[+\-*/]", expr):
            result = safe_eval(expr)
            if result is not None:
                speak(f"{expr_raw} — это {result}")
                return True
        return False

    m = re.match(
        r"^(?:напиши|напечатай|введи)\s+в\s+(блокнот|notepad|калькулятор|calc|консоль|cmd|проводник)\s+(.+)",
        task, re.IGNORECASE
    )
    if m:
        prog = m.group(1).strip()
        txt = m.group(2).strip().strip('"').strip("'")
        ok, title = pc_open(prog)
        if not ok:
            speak(f"Не нашёл {prog}")
            return True
        time.sleep(1.5)
        if title:
            w = wait_for_window(["cat_notes", "Блокнот", "Notepad"], timeout=5)
            if w:
                focus_window(w)
        time.sleep(0.4)
        type_text(txt)
        speak("Готово")
        return True

    m = re.match(r"^(?:открой|запусти|включи|поиграем в)\s+([а-яa-z0-9 _\-]+)$", task, re.IGNORECASE)
    if m:
        prog = m.group(1).strip()
        prog = re.sub(r"\s+на\s+(пк|компьютере)\s*$", "", prog, flags=re.IGNORECASE).strip()
        if prog.lower() in SPECIAL_FOLDERS:
            if pc_open_folder(prog):
                speak(f"Открыл {prog}")
            else:
                speak(f"Не нашёл {prog}")
            return True
        ok, _ = pc_open(prog)
        if ok:
            speak(f"Открываю {prog}")
        else:
            speak(f"Не нашёл {prog}")
        return True

    m = re.match(r"^(?:напиши|напечатай|введи)\s+(.+)", task, re.IGNORECASE)
    if m:
        type_text(m.group(1).strip().strip('"').strip("'"))
        return True

    return False


def detect_intent(text: str) -> str:
    t = text.lower().strip()
    if t in ("пока", "до свидания", "бай", "прощай", "увидимся"):
        return "bye"

    ocr_keys = ["что на экране", "что видишь", "опиши экран",
                "прочитай экран", "прочитай текст", "найди на экране"]
    if any(k in t for k in ocr_keys):
        return "ocr"
    if re.search(r"(?:найди|найти|ищи)\s+на\s+экране\s+", t):
        return "ocr"

    mouse_keys = ["двинь мыш", "передвинь мыш", "кликни", "щёлкни",
                  "правый клик", "двойной клик", "прокрути", "скролл",
                  "где мыш", "координаты мыш",
                  "скопируй", "копируй", "вставь", "вырежи", "отмени",
                  "выдели всё", "сохрани", "переключи окно", "смени окно",
                  "закрой окно", "сверни все", "покажи рабочий стол",
                  "открой пуск", "меню пуск", "выполнить",
                  "новую вкладку", "закрой вкладку", "обнови",
                  "переключи раскладку", "нажми "]
    if any(k in t for k in mouse_keys):
        return "pc"

    about_cat = ["ты кот", "ты человек", "кто ты", "как тебя зовут",
                 "твоё имя", "твое имя", "ты бот", "ты ии", "ты робот",
                 "ты живой", "ты настоящий", "привет", "здарова",
                 "как дела", "что ты умеешь", "что умеешь"]
    if any(k in t for k in about_cat):
        return "chat"

    if re.match(r"^(закрой|выключи|заверши)\b", t):
        return "pc"

    if re.match(r"^(посчитай|вычисли|сосчитай|сколько\s+будет|сколько)\s+", t):
        if re.search(r"\b(плюс|минус|умножить|разделить|делить)\b", t) or \
           re.search(r"\d+\s*[+\-*/]\s*\d+", t):
            return "pc"

    if re.search(r"\b(ютуб|youtube|гугл|google|яндекс|yandex)\b", t):
        return "browser"

    if re.match(r"^(найди|поищи|погугли|загугли|поиск|ищи)\b", t):
        return "browser"

    if re.match(r"^(удали|сотри|убрать|стереть)\b", t):
        return "pc"
    if re.match(r"^(переименуй|переименовать)\b", t):
        return "pc"
    if re.match(r"^(создай|сделай)\s+папку\b", t):
        return "pc"
    if re.match(r"^(создай|сделай)\s+(?:текстовый\s+)?(?:файл|документ|док)\b", t):
        return "pc"

    pc_starters = ["открой", "отрой", "окрой", "запусти", "включи",
                   "напиши", "напечатай", "введи", "создай", "сделай",
                   "покажи папку", "поиграем в", "поиграй в",
                   "посчитай", "вычисли", "сосчитай"]
    if any(t.startswith(k) or k in t for k in pc_starters):
        return "pc"

    search_keys = ["когда", "где", "какой", "что такое",
                   "почему", "новости", "погода", "курс", "цена",
                   "кто такой", "кто такая"]
    if any(k in t for k in search_keys):
        return "search"

    return "chat"


def process_command(text: str):
    global VOICE_ENABLED
    VOICE_ENABLED = get_voice_state()

    if not text:
        return
    text = normalize(text)

    if text.lower() in ("выход", "exit", "quit", "q", "пока",
                        "до свидания", "бай", "прощай", "увидимся"):
        speak("Пока, хозяин! Мяу!")
        _shutdown()
        return

    if text.lower() == "голос вкл":
        set_voice_state(True)
        VOICE_ENABLED = True
        return
    if text.lower() == "голос выкл":
        set_voice_state(False)
        VOICE_ENABLED = False
        return

    intent = detect_intent(text)

    try:
        if intent == "bye":
            speak("Пока, хозяин! Мяу!")
            _shutdown()
        elif intent == "ocr":
            handle_ocr(text)
        elif intent == "browser":
            if not handle_browser(text):
                handle_chat(text, use_search=True)
        elif intent == "pc":
            if not handle_pc_simple(text):
                set_cat_state("error")
                speak("Не понял")
                time.sleep(1)
                set_cat_state("idle")
        elif intent == "search":
            handle_chat(text, use_search=True)
        else:
            handle_chat(text, use_search=False)
    except Exception:
        set_cat_state("error")
        time.sleep(1)
        set_cat_state("idle")


def _shutdown():
    global OLLAMA_PROCESS
    try:
        subprocess.run("taskkill /F /IM BarsikCat.exe", shell=True, capture_output=True)
        if OLLAMA_PROCESS:
            try:
                OLLAMA_PROCESS.terminate()
            except Exception:
                pass
    except Exception:
        pass
    os._exit(0)


def command_watcher():
    while True:
        try:
            if os.path.exists(COMMAND_FILE):
                with open(COMMAND_FILE, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    try:
                        os.remove(COMMAND_FILE)
                    except Exception:
                        pass
                    process_command(text)
        except Exception:
            pass
        time.sleep(0.3)


def main():
    set_cat_state("idle")

    try:
        if getattr(sys, "frozen", False):
            cat_exe = os.path.join(BASE_DIR, "BarsikCat.exe")
            if os.path.exists(cat_exe):
                subprocess.Popen([cat_exe, str(os.getpid())])
        else:
            for name in ("cat_pet.pyw", "cat_pet.py"):
                cat_script = os.path.join(BASE_DIR, name)
                if os.path.exists(cat_script):
                    subprocess.Popen(["pythonw", cat_script, str(os.getpid())])
                    break
    except Exception:
        pass

    ct = threading.Thread(target=command_watcher, daemon=True)
    ct.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()