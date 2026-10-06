"""
JARVIS – voice.py
Sprachsteuerung am PC: Sprechen, Zuhören, Aktivierungswort ("Jarvis, ...")
und Bestätigen per "ja"/"nein". Alles, was hier passiert, landet zusätzlich
als Ereignis im Programmfenster.
"""

import re
import threading
import time

import config
import events
import sessions

_speak_lock = threading.Lock()
_mic_lock = threading.Lock()
_busy = threading.Event()          # ein Sprachbefehl wird gerade bearbeitet
_loop_thread: threading.Thread | None = None
_loop_stop = threading.Event()
_force_command_until = 0.0         # nach Hotkey/Klick: nächster Satz ohne Aktivierungswort

_YES = re.compile(r"\b(ja|jawohl|jo|klar|mach( das| es)?|ok(ay)?|genau|bitte|los|sicher|gerne|yes|bestätig\w*|erlaub\w*)\b", re.I)
_NO = re.compile(r"\b(nein|nö|nicht|stopp?|abbrechen|abbruch|lass( es| das)?|no|ablehn\w*)\b", re.I)


def _status(state: str):
    events.publish("status", state=state)


# ---------------------------------------------------------------------
# Sprechen
# ---------------------------------------------------------------------

def say(text: str):
    """Spricht den Text (blockierend, nacheinander statt durcheinander)."""
    import tts
    if not text or not text.strip():
        return
    with _speak_lock:
        _status("speaking")
        try:
            tts.speak(text)
        except Exception as e:
            print(f"[Voice] Sprachausgabe fehlgeschlagen: {e}")
        finally:
            _status("idle")


def say_async(text: str):
    threading.Thread(target=say, args=(text,), daemon=True).start()


def stop_speaking():
    import tts
    tts.stop_speaking()


# ---------------------------------------------------------------------
# Zuhören
# ---------------------------------------------------------------------

def _listen(timeout: float | None, phrase_time_limit: int = 15, cue: bool = True) -> str | None:
    import stt
    with _mic_lock:
        return stt.listen(timeout=timeout, phrase_time_limit=phrase_time_limit, cue=cue)


def _wake_pattern() -> re.Pattern | None:
    word = (config.WAKE_WORD or "").strip().lower()
    if not word:
        return None
    variants = {re.escape(word)}
    if word == "jarvis":
        variants |= {"jarvis", "jervis", "javis", "dschawis", "tschawis", "service"}
    return re.compile(r"\b(" + "|".join(sorted(variants)) + r")\b[,.!?]?\s*", re.I)


def _handle_result(jarvis, result: dict, spoken: bool):
    """Zeigt/spricht eine Antwort und führt Bestätigungen per Sprache durch."""
    while result.get("type") == "confirm":
        if result.get("text"):
            events.publish("jarvis", result["text"])
        events.publish("confirm", result["description"], confirm_id=result["id"], tool_name=result["tool_name"])
        if not spoken:
            return
        say(result["question"] + " Ja oder nein?")
        _status("listening")
        try:
            answer = _listen(timeout=8, phrase_time_limit=5) or ""
        except Exception:
            answer = ""
        _status("thinking")
        if jarvis.pending is None or jarvis.pending["tool_use_id"] != result["id"]:
            return  # wurde inzwischen im Fenster entschieden
        if _NO.search(answer):
            approved = False
        elif _YES.search(answer):
            approved = True
        else:
            events.publish("info", "Keine klare Antwort – bitte im Fenster bestätigen oder ablehnen.")
            say("Ich habe dich nicht verstanden. Bitte bestätige im Fenster.")
            return
        events.publish("user", answer)
        events.publish("confirm_done", confirm_id=result["id"])
        result = jarvis.resume(result["id"], approved)

    text = result.get("text", "")
    if text:
        events.publish("jarvis", text, error=bool(result.get("error")))
        if spoken:
            say(text)


def handle_command(text: str):
    """Ein per Sprache erkannter Befehl."""
    jarvis = sessions.get(sessions.DESKTOP)
    events.publish("user", text, source="voice")
    _status("thinking")
    try:
        result = jarvis.process(text)
        _handle_result(jarvis, result, spoken=True)
    finally:
        _status("idle")


def _listen_once_and_handle():
    if _busy.is_set():
        return
    _busy.set()
    try:
        stop_speaking()
        _status("listening")
        try:
            text = _listen(timeout=6)
        except Exception as e:
            events.publish("info", f"Mikrofon nicht verfügbar: {e}")
            return
        if not text:
            events.publish("info", "Nichts verstanden.")
            return
        handle_command(text)
    finally:
        _busy.clear()
        _status("idle")


def activate():
    """Mikrofon-Knopf / Hotkey: jetzt zuhören."""
    global _force_command_until
    if _loop_thread and _loop_thread.is_alive():
        stop_speaking()
        _force_command_until = time.time() + 10
        _status("listening")
        return
    threading.Thread(target=_listen_once_and_handle, daemon=True).start()


# ---------------------------------------------------------------------
# Dauerhaftes Zuhören mit Aktivierungswort
# ---------------------------------------------------------------------

def _continuous_loop():
    global _force_command_until
    print("[Voice] Dauerhaftes Zuhören aktiv.")
    failures = 0
    while not _loop_stop.is_set():
        try:
            text = _listen(timeout=5, phrase_time_limit=12, cue=False)
            failures = 0
        except Exception as e:
            failures += 1
            if failures == 1:
                events.publish("info", f"Dauerhaftes Zuhören: Mikrofon nicht verfügbar ({e}).")
            _loop_stop.wait(min(30, 2 ** failures))
            continue
        if not text or _loop_stop.is_set():
            continue

        forced = time.time() < _force_command_until
        pattern = _wake_pattern()
        match = pattern.search(text) if pattern else None
        if match:
            command = text[match.end():].strip()
            if not command:
                _force_command_until = time.time() + 8
                say("Ja?")
                _status("listening")
                continue
        elif forced or pattern is None:
            command = text
        else:
            continue

        _force_command_until = 0
        _busy.set()
        try:
            handle_command(command)
        finally:
            _busy.clear()
    print("[Voice] Dauerhaftes Zuhören beendet.")


def apply_settings():
    """Startet/stoppt das dauerhafte Zuhören passend zur Einstellung."""
    global _loop_thread
    running = _loop_thread is not None and _loop_thread.is_alive()
    if config.CONTINUOUS_LISTENING and not running:
        _loop_stop.clear()
        _loop_thread = threading.Thread(target=_continuous_loop, name="jarvis-wakeword", daemon=True)
        _loop_thread.start()
    elif not config.CONTINUOUS_LISTENING and running:
        _loop_stop.set()


def is_listening_continuously() -> bool:
    return _loop_thread is not None and _loop_thread.is_alive() and not _loop_stop.is_set()
