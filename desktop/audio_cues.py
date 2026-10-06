"""
JARVIS – audio_cues.py
Kurze Signaltöne, damit hörbar ist, wann Jarvis zuhört/aufhört zuzuhören –
ohne auf die Konsole schauen zu müssen. Nutzt winsound (in Windows
eingebaut, keine zusätzliche Abhängigkeit).
"""

import config

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False  # z.B. beim Testen auf Nicht-Windows-Systemen


def _beep(freq: int, duration_ms: int):
    if not getattr(config, "BEEP_ENABLED", True):
        return
    if not _HAS_WINSOUND:
        return
    try:
        winsound.Beep(freq, duration_ms)
    except Exception:
        pass  # Signalton ist nice-to-have, darf nie den Ablauf stören


def listen_start():
    _beep(880, 110)


def listen_end():
    _beep(440, 110)
