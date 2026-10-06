"""
JARVIS – stt.py
Spracherkennung über das Mikrofon. Zwei Anbieter wählbar über
config.STT_PROVIDER:

  "google"        – kostenlos, braucht Internet, inoffizielles/unklares
                     Limit (wie bisher)
  "whisper_local" – läuft komplett lokal (OpenAI Whisper via
                     faster-whisper), kein Internet nötig, kein Limit

Die eigentliche Audio-Aufnahme (inkl. automatischer Stille-Erkennung)
läuft in beiden Fällen über SpeechRecognition/Microphone – nur die
Erkennung selbst unterscheidet sich.
"""

import os
import tempfile

import speech_recognition as sr

import config
import audio_cues

_recognizer = sr.Recognizer()
_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        size = getattr(config, "WHISPER_MODEL_SIZE", "base")
        print(f"[STT] Lade lokales Whisper-Modell '{size}' – beim ersten Mal kann das etwas dauern...")
        _whisper_model = WhisperModel(size, device="auto", compute_type="auto")
    return _whisper_model


def _recognize_google(audio) -> str | None:
    try:
        text = _recognizer.recognize_google(audio, language=config.STT_LANGUAGE)
        print(f"Du: {text}")
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"[STT] Google-Spracherkennung nicht erreichbar: {e}")
        return None


def _recognize_whisper(audio) -> str | None:
    path = None
    try:
        model = _get_whisper_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio.get_wav_data())
            path = f.name

        lang = (config.STT_LANGUAGE or "de-DE").split("-")[0]
        segments, _info = model.transcribe(path, language=lang)
        text = " ".join(seg.text.strip() for seg in segments).strip()

        if text:
            print(f"Du: {text}")
            return text
        return None
    except Exception as e:
        print(f"[STT] Whisper-Fehler ({e}) – nutze Google als Fallback.")
        return _recognize_google(audio)
    finally:
        if path:
            try:
                os.remove(path)
            except Exception:
                pass


class MicrophoneError(Exception):
    pass


def listen(timeout: int | None = 6, phrase_time_limit: int = 12, cue: bool = True) -> str | None:
    """Hört auf dem Mikrofon und gibt den erkannten Text zurück (oder None).
    Wirft MicrophoneError, wenn kein Mikrofon verfügbar ist."""
    try:
        source = sr.Microphone()
        source.__enter__()
    except Exception as e:
        raise MicrophoneError(f"Kein Mikrofon gefunden ({e}).") from e
    try:
        _recognizer.adjust_for_ambient_noise(source, duration=0.4)
        print("... höre zu ...")
        if cue:
            audio_cues.listen_start()
        try:
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            if cue:
                audio_cues.listen_end()
            return None
    finally:
        source.__exit__(None, None, None)
    if cue:
        audio_cues.listen_end()

    provider = getattr(config, "STT_PROVIDER", "google")
    if provider == "whisper_local":
        return _recognize_whisper(audio)
    return _recognize_google(audio)
