"""
JARVIS – jarvis.py (Konsolen-Version)
Die Variante ohne Fenster, wie in v2. Starten mit:  python jarvis.py
Das eigentliche Programm mit Fenster ist jarvis_app.py bzw. Jarvis.exe.

Neu: Während Jarvis spricht, kannst du eine beliebige Taste drücken, um
die Ausgabe sofort abzubrechen (z.B. wenn die Antwort zu lang ist oder du
schon weißt, was als Nächstes kommt).
"""

import sys
import threading

import config
import stt
import tts
from brain import Jarvis

try:
    import msvcrt
    _HAS_MSVCRT = True
except ImportError:
    _HAS_MSVCRT = False  # Nicht-Windows: Unterbrechen per Taste nicht verfügbar


def speak_interruptible(text: str):
    """Spricht den Text, kann aber per Tastendruck sofort abgebrochen werden."""
    t = threading.Thread(target=tts.speak, args=(text,), daemon=True)
    t.start()

    if not _HAS_MSVCRT:
        t.join()
        return

    while t.is_alive():
        if msvcrt.kbhit():
            msvcrt.getch()
            tts.stop_speaking()
            break
        t.join(timeout=0.05)


def run_push_to_talk(jarvis: Jarvis):
    print("=" * 50)
    print(" JARVIS ist bereit.")
    print(" Enter drücken zum Sprechen, oder Text eintippen.")
    print(" Während Jarvis spricht: beliebige Taste = unterbrechen.")
    print(" 'exit' zum Beenden.")
    print("=" * 50)

    while True:
        cmd = input("\n[Enter] = sprechen, oder Text eingeben > ").strip()

        if cmd.lower() in ("exit", "quit", "beenden"):
            print("Jarvis wird beendet.")
            break

        if cmd == "":
            text = stt.listen()
            if not text:
                print("(nichts verstanden)")
                continue
        else:
            text = cmd

        result = jarvis.process(text)
        answer = result.get("text") if result.get("type") == "reply" else _handle_confirm_cli(jarvis, result)
        if answer:
            speak_interruptible(answer)


def _handle_confirm_cli(jarvis: Jarvis, result: dict) -> str:
    """Bestätigungs-Fluss für die Konsole (das Handy hat sein eigenes UI-Modal)."""
    while result.get("type") == "confirm":
        print(f"\n⚠ BESTÄTIGUNG NÖTIG [{result['tool_name']}]")
        print(result["description"])
        answer = input("Erlauben? (j/n) > ").strip().lower()
        approved = answer in ("j", "ja", "y", "yes")
        result = jarvis.resume(result["id"], approved)
    return result.get("text", "")


def run_continuous(jarvis: Jarvis):
    print("=" * 50)
    print(f" JARVIS hört dauerhaft zu. Wake-Word: '{config.WAKE_WORD}'")
    print(" Strg+C zum Beenden.")
    print("=" * 50)

    while True:
        try:
            text = stt.listen(timeout=None, phrase_time_limit=12)
        except KeyboardInterrupt:
            print("\nJarvis wird beendet.")
            break

        if not text:
            continue

        lowered = text.lower()
        if config.WAKE_WORD and config.WAKE_WORD.lower() not in lowered:
            continue

        if config.WAKE_WORD:
            lowered = lowered.replace(config.WAKE_WORD.lower(), "", 1).strip()
            command_text = lowered if lowered else text
        else:
            command_text = text

        result = jarvis.process(command_text)
        answer = result.get("text") if result.get("type") == "reply" else _handle_confirm_cli(jarvis, result)
        if answer:
            speak_interruptible(answer)


def main():
    if not config.api_key_configured():
        print("FEHLER: Kein API-Schlüssel. Starte einmal das Programm (jarvis_app.py) und trag ihn unter")
        print(f"Einstellungen ein – oder schreib ihn in {config.SETTINGS_FILE}.")
        sys.exit(1)

    jarvis = Jarvis("console")
    speak_interruptible("Jarvis ist online. Wie kann ich helfen?")

    if config.CONTINUOUS_LISTENING:
        run_continuous(jarvis)
    else:
        run_push_to_talk(jarvis)


if __name__ == "__main__":
    main()
