"""
JARVIS – autostart.py
Jarvis mit Windows starten (minimiert im Infobereich). Nutzt den
Registry-Schlüssel HKCU\\...\\Run – keine Adminrechte nötig.
"""

import os
import sys

import config

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE = "Jarvis"


def supported() -> bool:
    return config.IS_WINDOWS


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pythonw if os.path.exists(pythonw) else sys.executable
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_app.py")
    return f'"{exe}" "{script}" --minimized'


def is_enabled() -> bool:
    if not supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE)
            return bool(value)
    except OSError:
        return False


def set_enabled(enabled: bool):
    if not supported():
        raise RuntimeError("Autostart gibt es nur unter Windows.")
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _VALUE, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, _VALUE)
            except FileNotFoundError:
                pass
