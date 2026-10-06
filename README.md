# Erinnerung – Aktivitäts-Tracker

React-App (Vite + TypeScript + Tailwind) zum Erfassen und Teilen von Aktivitäten, mit Ticketsystem und Admin-Bereich.

## Ohne Installation nutzen

`Erinnerung.html` herunterladen und per Doppelklick im Browser öffnen – fertig. Kein Node.js, kein Server nötig.

Neu erzeugen mit `npm run build:single`.

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
