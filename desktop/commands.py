"""
JARVIS – commands.py (Desktop)
PC-Steuerungsfunktionen.

Gegenüber v2:
  - Programme/Ordner kommen live aus den Einstellungen
  - kein Shell-Aufruf mehr mit Text von der KI (open_app, shutdown_pc)
  - Websuche maskiert Sonderzeichen korrekt, nur http(s)-Adressen
  - Erinnerungen erscheinen zusätzlich im Programmfenster
"""

import os
import shlex
import shutil
import subprocess
import ctypes
import threading
import urllib.parse
import webbrowser
import datetime
import platform

import config
import events

IS_WINDOWS = platform.system() == "Windows"


def _expand(path: str) -> str:
    return os.path.expandvars(path)


# ---------------------------------------------------------------------
# Programme öffnen / schließen
# ---------------------------------------------------------------------

def _launch(target: str):
    """Startet einen Eintrag aus KNOWN_APPS: Pfad mit optionalen Argumenten, ohne Shell."""
    target = _expand(target).strip()
    if os.path.exists(target) or shutil.which(target):
        exe, args = target, []
    else:
        # "C:\Pfad mit Leerzeichen\app.exe --flag": längsten existierenden Pfad-Anfang suchen
        parts = target.split(" ")
        for i in range(len(parts), 0, -1):
            candidate = " ".join(parts[:i])
            if os.path.exists(candidate) or shutil.which(candidate):
                exe, args = candidate, shlex.split(" ".join(parts[i:]), posix=not IS_WINDOWS)
                break
        else:
            raise FileNotFoundError(target)
    subprocess.Popen([exe, *args], close_fds=True)


def open_app(name: str) -> str:
    name = name.lower().strip()
    target = config.KNOWN_APPS.get(name)

    if not target:
        # Unbekannt: nur als einzelnes Programm im Suchpfad starten (z.B. "winword"), nie über die Shell.
        exe = shutil.which(name) or shutil.which(name + ".exe")
        if exe and " " not in name and not any(c in name for c in "&|;<>^%"):
            subprocess.Popen([exe], close_fds=True)
            return f"{name.capitalize()} wird geöffnet."
        return f"Ich kenne '{name}' nicht. Trag es in den Einstellungen unter Programme ein."

    try:
        _launch(target)
        return f"{name.capitalize()} wird geöffnet."
    except FileNotFoundError:
        return f"{name.capitalize()} ist nicht installiert oder der Pfad in den Einstellungen stimmt nicht."
    except Exception as e:
        return f"Konnte {name} nicht öffnen: {e}"


def close_app(name: str) -> str:
    try:
        import psutil
    except ImportError:
        return "Dafür wird das Paket 'psutil' benötigt (pip install psutil)."

    name = name.lower().strip()
    killed = []
    for proc in psutil.process_iter(["name"]):
        pname = (proc.info.get("name") or "").lower()
        if name in pname:
            try:
                proc.terminate()
                killed.append(pname)
            except Exception:
                pass

    if killed:
        return f"Beendet: {', '.join(set(killed))}."
    return f"Kein laufender Prozess mit '{name}' gefunden."


# ---------------------------------------------------------------------
# Ordner & Web
# ---------------------------------------------------------------------

def open_folder(name: str) -> str:
    name = name.lower().strip()
    path = config.KNOWN_FOLDERS.get(name)
    if not path and name in ("workspace", "arbeitsordner", "jarvis"):
        path = config.WORKSPACE_DIR
        os.makedirs(path, exist_ok=True)
    if not path:
        return f"Ich kenne den Ordner '{name}' nicht. Trag ihn in den Einstellungen unter Ordner ein."
    path = _expand(path)
    try:
        os.startfile(path) if IS_WINDOWS else subprocess.Popen(["xdg-open", path])
        return f"Ordner {name} wird geöffnet."
    except Exception as e:
        return f"Konnte den Ordner nicht öffnen: {e}"


def open_website(url: str) -> str:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        if "://" in url:
            return "Ich öffne nur Webseiten mit http oder https."
        url = "https://" + url
    webbrowser.open(url)
    return f"Öffne {url} im Browser."


def web_search(query: str) -> str:
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    webbrowser.open(url)
    return f"Ich suche im Web nach '{query}'."


# ---------------------------------------------------------------------
# Lautstärke (präzise über pycaw, mit Fallback)
# ---------------------------------------------------------------------

def _pycaw_volume():
    """Gibt das pycaw-Lautstärke-Interface zurück, oder None falls pycaw
    fehlt oder nicht unter Windows läuft."""
    if not IS_WINDOWS:
        return None
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


# Windows-Mediensteuerungscodes für WM_APPCOMMAND (Fallback ohne pycaw)
APPCOMMAND_VOLUME_MUTE = 0x80000
APPCOMMAND_VOLUME_UP = 0xA0000
APPCOMMAND_VOLUME_DOWN = 0x90000


def _fallback_volume_key(command):
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ctypes.windll.user32.SendMessageW(hwnd, 0x319, 0, command)


def set_volume(percent: int) -> str:
    """Setzt die Lautstärke auf einen exakten Prozentwert (0-100)."""
    percent = max(0, min(100, int(percent)))
    vol = _pycaw_volume()
    if vol is not None:
        vol.SetMasterVolumeLevelScalar(percent / 100, None)
        return f"Lautstärke auf {percent}% gesetzt."
    return "Exakte Lautstärke braucht das Paket 'pycaw' (pip install pycaw comtypes). Nutze stattdessen lauter/leiser."


def volume_up(steps: int = 3) -> str:
    vol = _pycaw_volume()
    if vol is not None:
        current = vol.GetMasterVolumeLevelScalar()
        vol.SetMasterVolumeLevelScalar(min(1.0, current + steps * 0.05), None)
        return "Lautstärke erhöht."
    if not IS_WINDOWS:
        return "Lautstärkesteuerung funktioniert nur unter Windows."
    for _ in range(steps):
        _fallback_volume_key(APPCOMMAND_VOLUME_UP)
    return "Lautstärke erhöht."


def volume_down(steps: int = 3) -> str:
    vol = _pycaw_volume()
    if vol is not None:
        current = vol.GetMasterVolumeLevelScalar()
        vol.SetMasterVolumeLevelScalar(max(0.0, current - steps * 0.05), None)
        return "Lautstärke verringert."
    if not IS_WINDOWS:
        return "Lautstärkesteuerung funktioniert nur unter Windows."
    for _ in range(steps):
        _fallback_volume_key(APPCOMMAND_VOLUME_DOWN)
    return "Lautstärke verringert."


def volume_mute() -> str:
    vol = _pycaw_volume()
    if vol is not None:
        muted = vol.GetMute()
        vol.SetMute(0 if muted else 1, None)
        return "Stummschaltung aufgehoben." if muted else "Stummgeschaltet."
    if not IS_WINDOWS:
        return "Lautstärkesteuerung funktioniert nur unter Windows."
    _fallback_volume_key(APPCOMMAND_VOLUME_MUTE)
    return "Stummgeschaltet."


# ---------------------------------------------------------------------
# System: Sperren, Herunterfahren, Screenshot
# ---------------------------------------------------------------------

def lock_pc() -> str:
    if not IS_WINDOWS:
        return "Sperren wird nur unter Windows unterstützt."
    ctypes.windll.user32.LockWorkStation()
    return "PC wird gesperrt."


def _delay(value) -> int:
    return max(10, min(int(value), 86_400))


def shutdown_pc(delay_seconds: int = 60) -> str:
    if not IS_WINDOWS:
        return "Herunterfahren wird nur unter Windows unterstützt."
    delay = _delay(delay_seconds)
    subprocess.run(["shutdown", "/s", "/t", str(delay)], check=False)
    return f"PC fährt in {delay} Sekunden herunter. Sag 'Abbrechen', um das zu stoppen."


def restart_pc(delay_seconds: int = 60) -> str:
    if not IS_WINDOWS:
        return "Neustart wird nur unter Windows unterstützt."
    delay = _delay(delay_seconds)
    subprocess.run(["shutdown", "/r", "/t", str(delay)], check=False)
    return f"PC startet in {delay} Sekunden neu. Sag 'Abbrechen', um das zu stoppen."


def cancel_shutdown() -> str:
    if not IS_WINDOWS:
        return "Nicht unter Windows verfügbar."
    subprocess.run(["shutdown", "/a"], check=False)
    return "Herunterfahren/Neustart wurde abgebrochen."


def take_screenshot() -> str:
    try:
        import pyautogui
    except ImportError:
        return "Dafür wird das Paket 'pyautogui' benötigt (pip install pyautogui)."

    folder = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(folder, exist_ok=True)
    filename = f"jarvis_screenshot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
    path = os.path.join(folder, filename)
    pyautogui.screenshot().save(path)
    return f"Screenshot gespeichert unter {path}."


def get_time() -> str:
    return f"Es ist {datetime.datetime.now():%H:%M} Uhr."


def get_date() -> str:
    return f"Heute ist der {datetime.datetime.now():%d.%m.%Y}."


# ---------------------------------------------------------------------
# Erinnerungen / Timer
# ---------------------------------------------------------------------

_active_timers = []


def set_reminder(minutes: float, message: str) -> str:
    """Erinnert nach X Minuten per Sprachausgabe an eine Nachricht."""
    import voice  # lokal importiert, um Zirkel-Importe zu vermeiden

    minutes = float(minutes)
    if minutes <= 0 or minutes > 7 * 24 * 60:
        return "Erinnerungen gehen von ein paar Sekunden bis zu einer Woche im Voraus."

    def fire():
        events.publish("reminder", f"Erinnerung: {message}")
        voice.say(f"Erinnerung: {message}")

    seconds = max(1, minutes * 60)
    timer = threading.Timer(seconds, fire)
    timer.daemon = True
    timer.start()
    _active_timers.append(timer)

    if minutes < 1:
        when = f"{int(minutes * 60)} Sekunden"
    elif minutes == int(minutes):
        when = f"{int(minutes)} Minuten"
    else:
        when = f"{minutes:.1f} Minuten"
    return f"Alles klar, ich erinnere dich in {when} an: {message}"
