"""
JARVIS – sessions.py
Ein Jarvis-Gespräch pro Gerät. "desktop" ist das Programmfenster samt
Sprachsteuerung am PC; Handys bekommen eigene IDs.
"""

import threading

from brain import Jarvis

DESKTOP = "desktop"

_sessions: dict[str, Jarvis] = {}
_lock = threading.Lock()


def get(device_id: str) -> Jarvis:
    device_id = device_id or "default"
    with _lock:
        if device_id not in _sessions:
            _sessions[device_id] = Jarvis(device_id)
        return _sessions[device_id]


def count() -> int:
    return len(_sessions)
