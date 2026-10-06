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

import json
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


_GOOGLE_ENDPOINT = "http://www.google.com/speech-api/v2/recognize"
_GOOGLE_KEY = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"  # öffentlicher Standard-Schlüssel von SpeechRecognition
# Byte-Reihenfolge der PCM-Samples (geprüft im Windows-Build, siehe tools/probe_google_stt.py)
L16_BIG_ENDIAN = False


def _parse_google(response_text: str) -> str | None:
    for line in response_text.split("\n"):
        if not line.strip():
            continue
        result = json.loads(line).get("result") or []
        if result and result[0].get("alternative"):
            return result[0]["alternative"][0].get("transcript") or None
    return None


def _recognize_google_pcm(audio) -> str | None:
    """Schickt das Audio als rohes PCM (audio/l16) statt als FLAC.
    So wird kein mitgeliefertes flac-Programm gestartet – das blockiert
    Windows' Smart App Control, weil es nicht signiert ist."""
    import requests
    rate = 16000
    pcm = audio.get_raw_data(convert_rate=rate, convert_width=2)
    if L16_BIG_ENDIAN:
        pcm = _swap16(pcm)
    resp = requests.post(
        _GOOGLE_ENDPOINT,
        params={"client": "chromium", "lang": config.STT_LANGUAGE, "key": _GOOGLE_KEY, "pFilter": 0},
        headers={"Content-Type": f"audio/l16; rate={rate}"},
        data=pcm,
        timeout=15,
    )
    resp.raise_for_status()
    return _parse_google(resp.text)


def _swap16(data: bytes) -> bytes:
    import array
    samples = array.array("h")
    samples.frombytes(data[: len(data) // 2 * 2])
    samples.byteswap()
    return samples.tobytes()


def _recognize_google(audio) -> str | None:
    try:
        text = _recognize_google_pcm(audio)
    except Exception as e:
        print(f"[STT] Google-Erkennung (PCM) fehlgeschlagen ({e}) – versuche FLAC.")
        try:
            text = _recognizer.recognize_google(audio, language=config.STT_LANGUAGE)
        except sr.UnknownValueError:
            return None
        except Exception as e2:
            print(f"[STT] Google-Spracherkennung nicht erreichbar: {e2}")
            return None
    if text:
        print(f"Du: {text}")
    return text


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
