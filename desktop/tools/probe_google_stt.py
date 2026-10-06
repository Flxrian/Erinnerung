"""Prüft im Windows-Build, in welcher Byte-Reihenfolge Googles Spracherkennung
rohes PCM (audio/l16) erwartet. Eingabe: eine 16-kHz-Mono-WAV-Datei mit Sprache."""
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests  # noqa: E402

import stt  # noqa: E402

with wave.open(sys.argv[1], "rb") as w:
    assert w.getframerate() == 16000 and w.getsampwidth() == 2 and w.getnchannels() == 1
    little = w.readframes(w.getnframes())

for name, data in (("little-endian", little), ("big-endian", stt._swap16(little))):
    try:
        r = requests.post(stt._GOOGLE_ENDPOINT,
                          params={"client": "chromium", "lang": "en-US", "key": stt._GOOGLE_KEY, "pFilter": 0},
                          headers={"Content-Type": "audio/l16; rate=16000"}, data=data, timeout=20)
        print(f"PROBE {name}: HTTP {r.status_code} -> {stt._parse_google(r.text)!r}")
    except Exception as e:
        print(f"PROBE {name}: Fehler {e}")
