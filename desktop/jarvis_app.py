"""
JARVIS – jarvis_app.py
Das Desktop-Programm: eigenes Fenster, Symbol im Infobereich (neben der
Uhr), Tastenkürzel zum Zuhören und Hintergrundbetrieb für Erinnerungen und
Handy-Zugriff.

Starten:  python jarvis_app.py            (oder Jarvis.exe)
Optionen: --minimized   nur im Infobereich starten (Autostart)
          --selftest    prüft, ob alles Nötige vorhanden ist, und beendet sich
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser

import config


# ---------------------------------------------------------------------
# Protokoll: Ausgaben landen in jarvis_app.log (das .exe hat keine Konsole)
# ---------------------------------------------------------------------

class _Tee:
    def __init__(self, *streams):
        self.streams = [s for s in streams if s is not None]

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass

    def flush(self):
        pass


def _setup_logging():
    try:
        if config.APP_LOG_FILE.exists() and config.APP_LOG_FILE.stat().st_size > 1_000_000:
            config.APP_LOG_FILE.replace(config.APP_LOG_FILE.with_suffix(".old.log"))
        log = open(config.APP_LOG_FILE, "a", encoding="utf-8", buffering=1)
    except Exception:
        return
    log.write(f"\n===== Jarvis {config.VERSION} gestartet {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
    sys.stdout = _Tee(sys.stdout, log)
    sys.stderr = _Tee(sys.stderr, log)


def _message_box(text: str, title: str = "Jarvis"):
    print(f"[{title}] {text}")
    if config.IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)
        except Exception:
            pass


# ---------------------------------------------------------------------
# Nur eine Instanz: läuft Jarvis schon, wird dessen Fenster geöffnet
# ---------------------------------------------------------------------

def _local(path: str, method: str = "GET", timeout: float = 1.5):
    req = urllib.request.Request(f"http://127.0.0.1:{config.LOCAL_PORT}{path}", method=method,
                                 data=b"{}" if method == "POST" else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _signal_running_instance() -> bool:
    try:
        if _local("/api/health").get("app") != "jarvis":
            return False
        _local("/api/show", "POST")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------
# Selbsttest (für den automatischen Build)
# ---------------------------------------------------------------------

REQUIRED_MODULES = ["flask", "anthropic", "werkzeug", "PIL", "pystray", "pynput", "speech_recognition",
                    "edge_tts", "pygame", "requests", "cryptography", "psutil", "pyautogui", "webview"]
WINDOWS_MODULES = ["comtypes", "pycaw.pycaw", "pyaudio"]


def _selftest() -> int:
    import importlib
    missing = []
    for name in REQUIRED_MODULES + (WINDOWS_MODULES if config.IS_WINDOWS else []):
        try:
            importlib.import_module(name)
        except Exception as e:
            missing.append(f"{name}: {e}")
    try:
        health = _local("/api/health", timeout=5)
        ok_server = health.get("app") == "jarvis"
    except Exception as e:
        ok_server = False
        missing.append(f"server: {e}")
    try:
        import brain  # noqa: F401  (prüft Tool-Definitionen und Importe)
    except Exception as e:
        missing.append(f"brain: {e}")

    print("SELFTEST", "OK" if not missing and ok_server else "FEHLER")
    for m in missing:
        print("  -", m)
    return 0 if not missing and ok_server else 1


# ---------------------------------------------------------------------
# Infobereich-Symbol und Tastenkürzel
# ---------------------------------------------------------------------

class App:
    def __init__(self):
        self.window = None
        self.tray = None
        self.hotkey = None
        self.quitting = False
        self.hint_shown = False

    # -- Fenster --------------------------------------------------------

    def show(self):
        if self.window is not None:
            try:
                self.window.show()
                self.window.restore()
                return
            except Exception as e:
                print(f"[App] Fenster konnte nicht angezeigt werden: {e}")
        self._open_browser_window()

    def _open_browser_window(self):
        """Ersatz, falls das eingebettete Fenster nicht verfügbar ist: Edge im App-Modus."""
        import server
        url = server.local_url()
        edge = shutil.which("msedge") or next((p for p in (
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ) if os.path.exists(p)), None)
        if edge:
            subprocess.Popen([edge, f"--app={url}", "--window-size=480,820"], close_fds=True)
        else:
            webbrowser.open(url)

    def quit(self):
        self.quitting = True
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass
        try:
            if self.window:
                self.window.destroy()
        except Exception:
            pass
        # Hintergrund-Threads (Server, Mikrofon) nicht abwarten
        threading.Timer(1.5, lambda: os._exit(0)).start()

    def _on_closing(self):
        if self.quitting:
            return True
        self.window.hide()
        if not self.hint_shown and self.tray is not None:
            self.hint_shown = True
            try:
                self.tray.notify("Jarvis läuft im Hintergrund weiter. Rechtsklick auf das Symbol zum Beenden.", "Jarvis")
            except Exception:
                pass
        return False

    # -- Infobereich ----------------------------------------------------

    def start_tray(self, detached: bool = True) -> bool:
        try:
            import pystray
            from PIL import Image
        except Exception as e:
            print(f"[App] Kein Infobereich-Symbol möglich: {e}")
            return False

        import voice
        image = Image.open(config.STATIC_DIR / "icon-192.png")
        menu = pystray.Menu(
            pystray.MenuItem("Jarvis öffnen", lambda: self.show(), default=True),
            pystray.MenuItem("Jetzt zuhören", lambda: voice.activate()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", lambda: self.quit()),
        )
        self.tray = pystray.Icon("Jarvis", image, "Jarvis", menu)
        if detached:
            self.tray.run_detached()
        else:
            self.tray.run()
        return True

    # -- Tastenkürzel ---------------------------------------------------

    def register_hotkey(self):
        if self.hotkey:
            try:
                self.hotkey.stop()
            except Exception:
                pass
            self.hotkey = None
        combo = (config.HOTKEY or "").strip()
        if not combo:
            return
        try:
            from pynput import keyboard
            import voice
            self.hotkey = keyboard.GlobalHotKeys({combo: voice.activate})
            self.hotkey.daemon = True
            self.hotkey.start()
            print(f"[App] Tastenkürzel {combo} aktiv.")
        except Exception as e:
            print(f"[App] Tastenkürzel '{combo}' nicht möglich: {e}")


def main():
    parser = argparse.ArgumentParser(description="Jarvis – persönlicher Sprachassistent")
    parser.add_argument("--minimized", action="store_true", help="nur im Infobereich starten")
    parser.add_argument("--selftest", action="store_true", help="Installation prüfen und beenden")
    args = parser.parse_args()

    _setup_logging()

    if not args.selftest and _signal_running_instance():
        return 0

    import server
    import voice

    try:
        server.start_local()
    except OSError as e:
        _message_box(f"Jarvis konnte nicht starten, Port {config.LOCAL_PORT} ist belegt.\n\n{e}")
        return 1

    if args.selftest:
        return _selftest()

    app = App()
    server.on_show_window = app.show
    server.on_settings_changed = app.register_hotkey
    server.apply_phone_settings()
    voice.apply_settings()
    app.register_hotkey()

    start_hidden = args.minimized or config.START_MINIMIZED

    try:
        import webview
    except Exception as e:
        print(f"[App] Eingebettetes Fenster nicht verfügbar ({e}) – nutze Browser-Fenster.")
        webview = None

    if webview is not None:
        try:
            app.window = webview.create_window(
                "Jarvis", server.local_url(), width=480, height=820, min_size=(380, 560),
                background_color="#03070d", hidden=start_hidden,
            )
            app.window.events.closing += app._on_closing
            tray_ok = app.start_tray(detached=True)
            if not tray_ok:
                # Ohne Infobereich-Symbol beendet Schließen das Programm.
                app.window.events.closing -= app._on_closing
            webview.start(private_mode=False, storage_path=str(config.DATA_DIR / "webview"))
            app.quit()
            return 0
        except Exception:
            print("[App] Fenster-Fehler:\n" + traceback.format_exc())
            app.window = None

    # Ersatzbetrieb: Browser-Fenster + Infobereich-Symbol im Hauptthread
    if not start_hidden:
        app.show()
    if app.tray is None and app.start_tray(detached=False):
        app.quit()
        return 0
    # Infobereich läuft bereits (oder gibt es nicht): Hintergrundbetrieb bis "Beenden"
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    sys.exit(main())
