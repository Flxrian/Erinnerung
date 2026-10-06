"""
JARVIS – events.py
Kleine Ereignis-Warteschlange, über die das Programmfenster erfährt, was im
Hintergrund passiert (Sprachbefehle, Erinnerungen, Status "hört zu/spricht").
Das Fenster fragt sie regelmäßig über /api/events ab.
"""

import itertools
import threading
import time

_lock = threading.Condition()
_counter = itertools.count(1)
_events: list[dict] = []
_MAX = 300


def publish(kind: str, text: str = "", **extra) -> dict:
    if "id" in extra:
        raise ValueError("'id' ist für die Ereignisnummer reserviert – nutze z.B. confirm_id.")
    event = {"id": next(_counter), "kind": kind, "text": text, "time": time.time(), **extra}
    with _lock:
        _events.append(event)
        del _events[:-_MAX]
        _lock.notify_all()
    return event


def since(after_id: int, wait: float = 0.0) -> list[dict]:
    """Ereignisse mit id > after_id. Wartet bis zu `wait` Sekunden auf neue."""
    deadline = time.time() + wait
    with _lock:
        while True:
            result = [e for e in _events if e["id"] > after_id]
            remaining = deadline - time.time()
            if result or remaining <= 0:
                return result
            _lock.wait(remaining)


def latest_id() -> int:
    with _lock:
        return _events[-1]["id"] if _events else 0
