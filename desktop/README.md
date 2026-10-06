# J.A.R.V.I.S. für Windows

Persönlicher Sprachassistent als richtiges Windows-Programm: eigenes Fenster,
Symbol im Infobereich neben der Uhr, Tastenkürzel zum Zuhören, Steuerung des
PCs und Arbeiten mit Dateien per Sprache.

## Installieren

1. Auf GitHub unter **Releases → „Jarvis für Windows (neueste Version)“**
   die Datei **`Jarvis-Setup.exe`** herunterladen.
2. Doppelklicken. Falls Windows „Der Computer wurde durch Windows geschützt“
   zeigt (das Programm ist nicht digital signiert): **Weitere Informationen →
   Trotzdem ausführen**.
3. Installieren – keine Adminrechte und kein Python nötig.

Ohne Installation: `Jarvis-portable.zip` entpacken und `Jarvis.exe` starten.

## Erster Start

Jarvis öffnet sich und bittet um einen **Claude API-Schlüssel**
([console.anthropic.com](https://console.anthropic.com/settings/keys)).
Über das Zahnrad → Einstellungen eintragen → Speichern. Fertig.

## Bedienung

| Was | Wie |
|---|---|
| Sprechen | Auf den leuchtenden Kreis klicken, **Strg+Alt+J** drücken oder Rechtsklick aufs Symbol → „Jetzt zuhören“ |
| Ohne Klick | Einstellungen → „Dauerhaft zuhören“, dann „Jarvis, …“ sagen |
| Schreiben | Unten ins Textfeld |
| Unterbrechen | Während Jarvis spricht auf den Kreis klicken |
| Fenster schließen | Jarvis läuft im Infobereich weiter (Erinnerungen, Handy). Beenden: Rechtsklick aufs Symbol → Beenden |

Beispiele:

- „Öffne Spotify“ · „Stell die Lautstärke auf 30 Prozent“ · „Sperr den PC“
- „Erinnere mich in 20 Minuten an die Wäsche“
- „Schreib eine Einkaufsliste mit Milch, Brot und Eiern“ →
  „Ersetz Brot durch Vollkornbrot“ → „Füg Butter hinzu“ → „Lies mir die Liste vor“
- „Schreib mir ein Python-Skript, das …“ → „Führ es aus“

Dateien legt Jarvis nur im **Arbeitsordner** an (Standard: `Dokumente\Jarvis`).
Vor jeder Änderung landet ein Backup in `_backups`, Gelöschtes in `_trash`.
Überschreiben, Löschen, Verschieben und Shell-Befehle musst du bestätigen –
per Klick oder per „ja“/„nein“.

## Handy

Einstellungen → Handy → „Jarvis vom Handy im selben WLAN nutzen“, Passwort
festlegen, speichern. Die angezeigte Adresse (z.B. `https://192.168.1.20:5000`)
am Handy öffnen, Zertifikatswarnung einmal bestätigen, Passwort eingeben.
Tipp: „Zum Startbildschirm hinzufügen“. Nur aus dem eigenen WLAN erreichbar,
nach 5 falschen Passwörtern 5 Minuten gesperrt.

## Stimmen

| Einstellung | |
|---|---|
| Microsoft Neural (Standard) | natürlich, gratis, braucht Internet |
| Windows-Stimme | offline, auch automatischer Ersatz |
| ElevenLabs / Google | eigener API-Schlüssel nötig |
| Eigene Stimme (Voice Cloning) | nur beim Start aus dem Quellcode mit `requirements-extra.txt` |

## Wo liegt was?

- Programm: `%LOCALAPPDATA%\Programs\Jarvis`
- Einstellungen, Verlauf, Protokolle: `%APPDATA%\Jarvis` (bleibt beim Deinstallieren erhalten)
- Fehlersuche: `%APPDATA%\Jarvis\jarvis_app.log`

## Aus dem Quellcode starten

```
pip install -r requirements.txt
python jarvis_app.py
```

`python jarvis.py` startet die alte Konsolen-Variante, `python server.py` nur
den Handy-Server. Tests: `pip install -r requirements-dev.txt && pytest tests`.

## Selbst bauen

Passiert automatisch bei jedem Push über GitHub Actions
(`.github/workflows/jarvis-windows.yml`): Tests → `pyinstaller jarvis.spec` →
Selbsttest der `.exe` → Inno Setup (`installer.iss`) → Release `jarvis-latest`.

## Änderungen gegenüber v2

- Richtiges Programm mit Fenster, Infobereich-Symbol, Tastenkürzel, Installer und Autostart
- Einstellungen im Programm statt in `config.py` (gespeichert in `%APPDATA%\Jarvis\settings.json`, wirken sofort)
- Neue Datei-Werkzeuge `edit_file` und `append_to_file` für gezielte Änderungen per Sprache
- Bestätigen per Sprache („ja“/„nein“)
- Natürliche Microsoft-Stimme als Standard, Windows-Stimme unterbrechbar
- Eigener Verlauf pro Gerät (vorher teilten sich Handy und PC eine Datei)
- Eine nicht beantwortete Bestätigung blockiert das Gespräch nicht mehr
- Sicherheit: kein Shell-Aufruf mehr mit Text von der KI (`open_app`, Herunterfahren),
  Handy ist standardmäßig aus, HTTPS-Zertifikat wird automatisch erzeugt
