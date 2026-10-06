# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Bauplan für Jarvis.exe – bauen mit:  pyinstaller --noconfirm jarvis.spec
from PyInstaller.utils.hooks import collect_data_files

datas = [("static", "static")]
datas += collect_data_files("speech_recognition")  # enthält den FLAC-Encoder für die Google-Erkennung
datas += collect_data_files("webview")

hiddenimports = [
    "pystray._win32",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
    "comtypes.client",
    "pycaw.pycaw",
    "edge_tts",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr",
]

a = Analysis(
    ["jarvis_app.py"],
    pathex=["."],
    datas=datas,
    hiddenimports=hiddenimports,
    # Große optionale Pakete (Voice Cloning, lokales Whisper) bleiben draußen
    excludes=["torch", "TTS", "faster_whisper", "ctranslate2", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Jarvis",
    console=False,
    icon="assets/jarvis.ico",
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="Jarvis", upx=False)
