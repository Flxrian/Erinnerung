"""
JARVIS – tts.py (Desktop)
Text-zu-Sprache mit wählbaren Anbietern (config.TTS_PROVIDER):

  "edge"        – natürliche Microsoft-Stimmen (z.B. Conrad), gratis,
                   braucht Internet – Standard
  "local_clone" – läuft komplett lokal (eigene/geklonte Stimme), kein
                   Zeichen-Limit, Satz-für-Satz-Streaming (Zusatzpakete nötig)
  "google"      – Google Cloud WaveNet, 4 Mio. Zeichen/Monat gratis
  "elevenlabs"  – sehr natürlich, 10.000 Zeichen/Monat gratis
  "windows"     – eingebaute Windows-Stimme, offline (auch automatischer Fallback)

Neu in der Desktop-Version:
  - Anbieter "edge"
  - Windows-Stimme direkt über SAPI: unterbrechbar und threadsicher

Neu in v4:
  - Unterbrechbar: stop_speaking() bricht eine laufende Ausgabe sofort ab
  - Kontingent-Tracking für google/elevenlabs (lokal mitgezählt, monatlich
    zurückgesetzt, wird nach jeder Ausgabe kurz angezeigt)
"""

import os
import platform
import re
import json
import base64
import tempfile
import threading
import queue
import datetime

import config

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
GOOGLE_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

_stop_event = threading.Event()


def stop_speaking():
    """Bricht eine laufende Sprachausgabe sofort ab (z.B. auf Zuruf/Tastendruck)."""
    _stop_event.set()
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass


# ---------------------------------------------------------------------
# Kontingent-Tracking (nur Anzeige, keine harte Bremse – die APIs selbst
# melden ja bereits 429, wenn das Kontingent wirklich aufgebraucht ist)
# ---------------------------------------------------------------------

def _load_usage() -> dict:
    path = getattr(config, "USAGE_FILE", "jarvis_usage.json")
    month = datetime.date.today().strftime("%Y-%m")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    if data.get("month") != month:
        data = {"month": month}
    return data


def _save_usage(data: dict):
    path = getattr(config, "USAGE_FILE", "jarvis_usage.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _track_usage(provider: str, chars: int, free_quota: int):
    data = _load_usage()
    used = data.get(provider, 0) + chars
    data[provider] = used
    _save_usage(data)
    pct = (used / free_quota * 100) if free_quota else 0
    print(f"[TTS] {provider}: {used:,}/{free_quota:,} Zeichen diesen Monat ({pct:.1f}%)".replace(",", "."))


# ---------------------------------------------------------------------
# Audiowiedergabe
# ---------------------------------------------------------------------

def _play_audio_file(path: str):
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()

    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    try:
        while pygame.mixer.music.get_busy():
            if _stop_event.is_set():
                pygame.mixer.music.stop()
                break
            pygame.time.wait(80)
    finally:
        # Datei freigeben, damit sie gelöscht werden kann (Windows sperrt geladene Dateien)
        pygame.mixer.music.unload()


def _play_mp3_bytes(audio_bytes: bytes):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        _play_audio_file(path)
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


# ---------------------------------------------------------------------
# ElevenLabs
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Microsoft Edge Neural Voices (edge-tts)
# ---------------------------------------------------------------------

def _speak_edge(text: str) -> bool:
    try:
        import asyncio
        import edge_tts
    except ImportError:
        print("[TTS] Paket 'edge-tts' fehlt – Fallback.")
        return False

    rate_pct = max(-50, min(100, round((config.TTS_RATE - 180) / 180 * 100)))
    voice = getattr(config, "EDGE_TTS_VOICE", "") or "de-DE-ConradNeural"
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        path = f.name
    try:
        asyncio.run(edge_tts.Communicate(text, voice, rate=f"{rate_pct:+d}%").save(path))
        if _stop_event.is_set():
            return True
        _play_audio_file(path)
        return True
    except Exception as e:
        print(f"[TTS] Edge-Stimme nicht verfügbar ({e}) – Fallback.")
        return False
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def _elevenlabs_configured() -> bool:
    key = getattr(config, "ELEVENLABS_API_KEY", "")
    return bool(key) and key != "DEIN_ELEVENLABS_KEY_HIER"


def _speak_elevenlabs(text: str) -> bool:
    import requests

    voice_id = getattr(config, "ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
    url = ELEVENLABS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": getattr(config, "ELEVENLABS_STABILITY", 0.45),
            "similarity_boost": getattr(config, "ELEVENLABS_SIMILARITY", 0.8),
        },
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
    except Exception as e:
        print(f"[TTS] ElevenLabs nicht erreichbar ({e}) – Fallback.")
        return False

    if resp.status_code == 401:
        print("[TTS] ElevenLabs: ungültiger API-Key – Fallback.")
        return False
    if resp.status_code == 429:
        print("[TTS] ElevenLabs: Monatskontingent erschöpft – Fallback.")
        return False
    if resp.status_code != 200:
        print(f"[TTS] ElevenLabs-Fehler {resp.status_code} – Fallback.")
        return False

    _play_mp3_bytes(resp.content)
    _track_usage("elevenlabs", len(text), 10_000)
    return True


# ---------------------------------------------------------------------
# Google Cloud TTS
# ---------------------------------------------------------------------

def _google_configured() -> bool:
    key = getattr(config, "GOOGLE_TTS_API_KEY", "")
    return bool(key) and key != "DEIN_GOOGLE_API_KEY_HIER"


def _speak_google(text: str) -> bool:
    import requests

    url = f"{GOOGLE_URL}?key={config.GOOGLE_TTS_API_KEY}"
    payload = {
        "input": {"text": text},
        "voice": {
            "languageCode": getattr(config, "GOOGLE_TTS_LANGUAGE", "de-DE"),
            "name": getattr(config, "GOOGLE_TTS_VOICE", "de-DE-Wavenet-B"),
        },
        "audioConfig": {"audioEncoding": "MP3"},
    }

    try:
        resp = requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"[TTS] Google TTS nicht erreichbar ({e}) – Fallback.")
        return False

    if resp.status_code == 403:
        print("[TTS] Google TTS: Zugriff verweigert (API/Billing prüfen) – Fallback.")
        return False
    if resp.status_code == 429:
        print("[TTS] Google TTS: Kontingent erschöpft – Fallback.")
        return False
    if resp.status_code != 200:
        print(f"[TTS] Google-TTS-Fehler {resp.status_code}: {resp.text[:200]} – Fallback.")
        return False

    audio_b64 = resp.json().get("audioContent")
    if not audio_b64:
        print("[TTS] Google TTS lieferte keine Audiodaten – Fallback.")
        return False

    _play_mp3_bytes(base64.b64decode(audio_b64))
    _track_usage("google", len(text), 4_000_000)
    return True


# ---------------------------------------------------------------------
# Lokales Voice Cloning (XTTS-v2), Satz-Streaming, unbegrenzt
# ---------------------------------------------------------------------

_local_clone_model = None
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')


def _split_sentences(text: str) -> list:
    parts = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]
    return parts or [text.strip()]


def _get_local_clone_model():
    global _local_clone_model
    if _local_clone_model is None:
        from TTS.api import TTS
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[TTS] Lade lokales Voice-Clone-Modell ({device}) – beim ersten Mal 1-2 Minuten...")
        _local_clone_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return _local_clone_model


def _speak_local_clone(text: str) -> bool:
    ref_wav = getattr(config, "LOCAL_CLONE_REFERENCE_WAV", "")
    if not ref_wav or not os.path.exists(ref_wav):
        print(f"[TTS] Referenz-Audiodatei nicht gefunden: {ref_wav} – Fallback.")
        return False

    try:
        model = _get_local_clone_model()
    except Exception as e:
        print(f"[TTS] Konnte lokales Modell nicht laden ({e}) – Fallback.")
        return False

    sentences = _split_sentences(text)
    language = getattr(config, "LOCAL_CLONE_LANGUAGE", "de")

    audio_queue = queue.Queue(maxsize=2)
    STOP = object()
    had_error = {"value": False}

    def producer():
        for sentence in sentences:
            if _stop_event.is_set():
                break
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    out_path = f.name
                model.tts_to_file(text=sentence, speaker_wav=ref_wav, language=language, file_path=out_path)
                audio_queue.put(out_path)
            except Exception as e:
                print(f"[TTS] Fehler bei Satz-Generierung ('{sentence[:40]}...'): {e}")
                had_error["value"] = True
        audio_queue.put(STOP)

    worker = threading.Thread(target=producer, daemon=True)
    worker.start()

    played_any = False
    while True:
        item = audio_queue.get()
        if item is STOP:
            break
        if _stop_event.is_set():
            try:
                os.remove(item)
            except Exception:
                pass
            continue
        try:
            _play_audio_file(item)
            played_any = True
        finally:
            try:
                os.remove(item)
            except Exception:
                pass

    worker.join(timeout=1)

    if not played_any and had_error["value"]:
        return False
    return True


# ---------------------------------------------------------------------
# Windows-Fallback (immer verfügbar)
# ---------------------------------------------------------------------

def _speak_sapi(text: str) -> bool:
    """Windows-Stimme direkt über SAPI – unterbrechbar über stop_speaking()."""
    try:
        import comtypes
        import comtypes.client
    except ImportError:
        return False

    SVSF_ASYNC, SVSF_PURGE = 1, 2
    comtypes.CoInitialize()
    try:
        voice = comtypes.client.CreateObject("SAPI.SpVoice")
        hint = (config.TTS_VOICE_HINT or "").lower()
        tokens = voice.GetVoices()
        descriptions = [tokens.Item(i).GetDescription() for i in range(tokens.Count)]
        match = next((i for i, d in enumerate(descriptions) if hint and hint in d.lower()), None)
        if match is None:
            match = next((i for i, d in enumerate(descriptions) if "german" in d.lower() or "deutsch" in d.lower()), None)
        if match is not None:
            voice.Voice = tokens.Item(match)
        voice.Rate = max(-10, min(10, round((config.TTS_RATE - 180) / 15)))
        voice.Speak(text, SVSF_ASYNC)
        while not voice.WaitUntilDone(100):
            if _stop_event.is_set():
                voice.Speak("", SVSF_ASYNC | SVSF_PURGE)
                break
        return True
    except Exception as e:
        print(f"[TTS] Windows-Stimme fehlgeschlagen: {e}")
        return False
    finally:
        comtypes.CoUninitialize()


def _speak_fallback(text: str):
    if platform.system() == "Windows" and _speak_sapi(text):
        return
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", config.TTS_RATE)
    for voice in engine.getProperty("voices"):
        if config.TTS_VOICE_HINT.lower() in voice.name.lower():
            engine.setProperty("voice", voice.id)
            break
    engine.say(text)
    engine.runAndWait()


# ---------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------

def speak(text: str):
    print(f"JARVIS: {text}")
    if not text.strip():
        return

    _stop_event.clear()
    provider = getattr(config, "TTS_PROVIDER", "edge")

    if provider == "edge":
        if _speak_edge(text):
            return
    elif provider == "local_clone":
        if _speak_local_clone(text):
            return
    elif provider == "google" and _google_configured():
        if _speak_google(text):
            return
    elif provider == "elevenlabs" and _elevenlabs_configured():
        if _speak_elevenlabs(text):
            return

    if not _stop_event.is_set():
        try:
            _speak_fallback(text)
        except Exception as e:
            print(f"[TTS] Keine Sprachausgabe möglich: {e}")
