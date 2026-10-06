import { newId } from "@/lib/storage"

export interface Settings {
  apiKey: string
  userName: string
  voiceURI: string
  rate: number
  wakeWord: boolean
  speak: boolean
}

export interface Reminder {
  id: string
  text: string
  due: string // ISO-Zeitpunkt
  kind: "reminder" | "timer"
  notified: boolean
}

export const defaultSettings: Settings = {
  apiKey: "",
  userName: "",
  voiceURI: "",
  rate: 1.05,
  wakeWord: false,
  speak: true,
}

export function makeReminder(text: string, due: Date, kind: Reminder["kind"]): Reminder {
  return { id: newId().slice(0, 8), text, due: due.toISOString(), kind, notified: false }
}

export const formatDue = (iso: string) =>
  new Date(iso).toLocaleString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })

export function formatDuration(seconds: number) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.round(seconds % 60)
  return [h && `${h} Std.`, m && `${m} Min.`, s && `${s} Sek.`].filter(Boolean).join(" ") || "0 Sek."
}
