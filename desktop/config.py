"""
JARVIS – config.py (Desktop)
Alle Einstellungen. Die Werte stehen in settings.json im Datenordner
(Windows: %APPDATA%\\Jarvis) und werden im Programm unter "Einstellungen"
bearbeitet – config.py selbst muss niemand mehr anfassen.

Die anderen Module lesen Werte wie bisher über config.NAME. Änderungen über
save() wirken sofort, ohne Neustart.
"""

import json
import os
import platform
import sys
from pathlib import Path

APP_NAME = "Jarvis"
VERSION = "3.0.0"
IS_WINDOWS = platform.system() == "Windows"


def _data_dir() -> Path:
    override = os.environ.get("JARVIS_DATA_DIR")
    if override:
        base = Path(override)
    elif IS_WINDOWS:
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


# Programmordner (im fertigen .exe der entpackte Bundle-Ordner) und Datenordner
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = _data_dir()
SETTINGS_FILE = DATA_DIR / "settings.json"

_HOME = Path.home()

DEFAULTS = {
    # --- KI ---
    "ANTHROPIC_API_KEY": "",
    "MODEL": "claude-sonnet-4-6",
    "USER_NAME": "",

    # --- Sprache ---
    "WAKE_WORD": "jarvis",
    "CONTINUOUS_LISTENING": False,
    "STT_LANGUAGE": "de-DE",
    # "google" = kostenlos, braucht Internet | "whisper_local" = offline (nur mit Zusatzpaketen)
    "STT_PROVIDER": "google",
    "WHISPER_MODEL_SIZE": "base",
    "BEEP_ENABLED": True,
    "HOTKEY": "<ctrl>+<alt>+j",

    # "edge" = natürliche Microsoft-Stimmen (gratis, Internet) | "windows" = Systemstimme (offline)
    # "elevenlabs" | "google" | "local_clone" (nur mit Zusatzpaketen)
    "TTS_PROVIDER": "edge",
    "EDGE_TTS_VOICE": "de-DE-ConradNeural",
    "TTS_RATE": 180,
    "TTS_VOICE_HINT": "German",
    "ELEVENLABS_API_KEY": "",
    "ELEVENLABS_VOICE_ID": "pNInz6obpgDQGcFmaJgB",
    "ELEVENLABS_STABILITY": 0.45,
    "ELEVENLABS_SIMILARITY": 0.8,
    "GOOGLE_TTS_API_KEY": "",
    "GOOGLE_TTS_LANGUAGE": "de-DE",
    "GOOGLE_TTS_VOICE": "de-DE-Wavenet-B",
    "LOCAL_CLONE_REFERENCE_WAV": "",
    "LOCAL_CLONE_LANGUAGE": "de",

    # --- PC-Steuerung ---
    "KNOWN_FOLDERS": {
        "downloads": str(_HOME / "Downloads"),
        "desktop": str(_HOME / "Desktop"),
        "dokumente": str(_HOME / "Documents"),
        "bilder": str(_HOME / "Pictures"),
        "musik": str(_HOME / "Music"),
    },
    "KNOWN_APPS": {
        "notepad": "notepad.exe",
        "editor": "notepad.exe",
        "taschenrechner": "calc.exe",
        "rechner": "calc.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "terminal": "cmd.exe",
        "task-manager": "taskmgr.exe",
        "paint": "mspaint.exe",
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "discord": r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe",
        "spotify": r"%APPDATA%\Spotify\Spotify.exe",
        "steam": r"C:\Program Files (x86)\Steam\steam.exe",
    },

    # --- Dateien & Programmieren ---
    "CODING_ENABLED": True,
    "WORKSPACE_DIR": str(_HOME / "Documents" / "Jarvis"),
    "SHELL_TIMEOUT_SECONDS": 60,
    "TRASH_INSTEAD_OF_DELETE": True,
    "WRITE_FILE_BACKUP": True,

    # --- Handy-Zugriff (WLAN) ---
    "PHONE_ACCESS": False,
    "APP_TOKEN": "",
    "PORT": 5000,
    "RESTRICT_TO_LAN": True,
    "HTTPS_ENABLED": True,
    "MAX_FAILED_LOGIN_ATTEMPTS": 5,
    "LOGIN_LOCKOUT_SECONDS": 300,

    # --- Programm ---
    "START_MINIMIZED": False,
    "HISTORY_MAX_TURNS": 100,
}

# Werte, die nie an die Oberfläche zurückgeschickt werden (nur "gesetzt: ja/nein")
SECRET_KEYS = {"ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "GOOGLE_TTS_API_KEY", "APP_TOKEN"}

# Feste Pfade im Datenordner
HISTORY_DIR = DATA_DIR / "history"
ACTIONS_LOG_FILE = str(DATA_DIR / "jarvis_actions.log")
ACTIONS_LOG_MAX_BYTES = 2_000_000
ACTIONS_LOG_BACKUP_COUNT = 3
USAGE_FILE = str(DATA_DIR / "jarvis_usage.json")
SSL_CERT_FILE = str(DATA_DIR / "cert.pem")
SSL_KEY_FILE = str(DATA_DIR / "key.pem")
APP_LOG_FILE = DATA_DIR / "jarvis_app.log"

# Port des lokalen Programmfensters (nur 127.0.0.1)
LOCAL_PORT = int(os.environ.get("JARVIS_LOCAL_PORT", "47913"))


def _load() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"[Config] settings.json ist beschädigt ({e}) – nutze Standardwerte.")
        return {}


def _coerce(key: str, value):
    """Bringt einen Wert auf den Typ des Standardwerts (z.B. "30" -> 30)."""
    default = DEFAULTS[key]
    if isinstance(default, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "ja", "on", "yes")
        return bool(value)
    if isinstance(default, int):
        return int(value)
    if isinstance(default, float):
        return float(value)
    if isinstance(default, dict):
        if not isinstance(value, dict):
            raise ValueError(f"{key} muss eine Zuordnung sein.")
        return {str(k).strip().lower(): str(v).strip() for k, v in value.items() if str(k).strip()}
    return "" if value is None else str(value).strip()


def _apply(values: dict):
    g = globals()
    for key, default in DEFAULTS.items():
        g[key] = values.get(key, default)


_stored = _load()
_apply({k: v for k, v in _stored.items() if k in DEFAULTS})


def current() -> dict:
    return {key: globals()[key] for key in DEFAULTS}


def save(updates: dict) -> dict:
    """Übernimmt geänderte Einstellungen, speichert sie und gibt sie zurück.
    Unbekannte Schlüssel werden ignoriert; leere Geheimnisse bleiben unverändert."""
    values = current()
    for key, value in updates.items():
        if key not in DEFAULTS:
            continue
        if key in SECRET_KEYS and (value is None or value == ""):
            continue
        values[key] = _coerce(key, value)

    if values["PORT"] == LOCAL_PORT or not 1024 <= values["PORT"] <= 65535:
        raise ValueError("Ungültiger Port.")

    tmp = SETTINGS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(values, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SETTINGS_FILE)
    _apply(values)
    return values


def public() -> dict:
    """Einstellungen für die Oberfläche – Geheimnisse nur als 'gesetzt'."""
    out = {}
    for key, value in current().items():
        if key in SECRET_KEYS:
            out[key] = ""
            out[f"{key}__set"] = bool(value)
        else:
            out[key] = value
    return out


def api_key_configured() -> bool:
    key = globals().get("ANTHROPIC_API_KEY", "")
    return bool(key) and key != "DEIN_API_KEY_HIER"
