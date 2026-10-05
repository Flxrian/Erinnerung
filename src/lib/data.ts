import type { User } from "./types"

export const defaultUsers: User[] = [
  { id: "1", username: "admin", password: "admin123", isAdmin: true },
  { id: "2", username: "user1", password: "user123", isAdmin: false },
]

export const deviceActivities = [
  "Geöffneter Webbrowser",
  "E-Mail überprüft",
  "Dokument-Editor geöffnet",
  "Videoanruf gestartet",
  "Musik-Player geöffnet",
  "Dateimanager zugegriffen",
  "Kalender-App geöffnet",
  "Coding IDE gestartet",
  "Messaging-App geöffnet",
  "Systemeinstellungen aufgerufen",
]

export const ACTIVITY_LOG_INTERVAL_MS = 30_000
export const ACTIVITY_LOG_LIMIT = 50
