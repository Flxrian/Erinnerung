# Erinnerung & J.A.R.V.I.S.

React-App (Vite + TypeScript + Tailwind) zum Erfassen und Teilen von Aktivitäten, mit Ticketsystem und Admin-Bereich.

## Ohne Installation nutzen

- **`Erinnerung.html`** – Aktivitäts-Tracker
- **`Jarvis.html`** – persönlicher Sprachassistent

Herunterladen und per Doppelklick im Browser öffnen (am besten Chrome oder Edge). Kein Node.js, kein Server nötig.
Neu erzeugen mit `npm run build:single`.

## J.A.R.V.I.S.

- **Sprechen**: auf den leuchtenden Kreis oder das Mikrofon tippen – oder in den Einstellungen „Dauerhaft zuhören“ aktivieren und „Jarvis, …“ sagen
- **Antwortet per Sprache** (Stimme und Tempo einstellbar)
- **Dateien**: per Sprache anlegen, vorlesen, gezielt ändern („ersetze Brot durch Vollkornbrot“), ergänzen, umbenennen, löschen.
  Speicherort wahlweise ein echter Ordner auf dem PC (Chrome/Edge) oder der Browser-Speicher (mit Download)
- **Erinnerungen & Timer** mit Ton, Sprachansage und Desktop-Benachrichtigung
- **Websuche** für aktuelle Infos, **Webseiten öffnen**, **Langzeitgedächtnis** („merk dir, dass …“)

Für die volle Intelligenz braucht Jarvis einen Claude API-Schlüssel ([console.anthropic.com](https://console.anthropic.com/settings/keys)),
der in den Einstellungen eingetragen wird. Ohne Schlüssel versteht er einfache Befehle: Uhrzeit, Datum, „Timer 5 Minuten“,
„Erinnere mich in 10 Minuten an …“, „Notiere …“, „Öffne YouTube“.

Der Schlüssel liegt nur im Browser und wird direkt an die Claude API geschickt. Die App ist für den eigenen Rechner gedacht –
nicht mit eingetragenem Schlüssel öffentlich hosten.

## Starten (Entwicklung)

```bash
npm install
npm run dev      # Entwicklungsserver auf http://localhost:5173
npm run build    # Produktions-Build nach dist/
```

## Funktionen

- **Anmeldung / Registrierung** – Demo-Konten: `admin` / `admin123` und `user1` / `user123`
- **Aktivitäten** – manuelle Einträge mit Datum (anlegen/löschen), automatisches Geräteprotokoll alle 30 Sekunden (max. 50 Einträge pro Benutzer)
- **Sharing-Modus** – Protokolleinträge per Checkbox teilen; geteilte Aktivitäten sind für alle Benutzer sichtbar
- **Tickets** – Fehler melden; Benutzer sehen ihre eigenen Tickets, Admins alle und können den Status ändern
- **Admin** – Benutzer anlegen, löschen, Admin-Rechte vergeben/entziehen (der letzte Admin bleibt geschützt)

Alle Daten werden im `localStorage` des Browsers gespeichert und bleiben nach einem Neuladen erhalten.

> Hinweis: Es gibt kein Backend. Benutzer und Passwörter liegen unverschlüsselt im Browser – die App ist eine Demo, kein sicheres Login-System.
