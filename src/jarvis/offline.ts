import { runTool, type ToolContext } from "./tools"

/**
 * Einfache Befehle, die ohne API-Schlüssel funktionieren.
 * Gibt null zurück, wenn der Befehl nicht erkannt wurde.
 */
export async function handleOffline(input: string, ctx: ToolContext): Promise<string | null> {
  const text = input.toLowerCase().trim()
  const now = new Date()

  if (/^(hallo|hi|hey|guten (morgen|tag|abend))\b/.test(text)) {
    const h = now.getHours()
    return `${h < 11 ? "Guten Morgen" : h < 18 ? "Guten Tag" : "Guten Abend"}. Was kann ich für Sie tun?`
  }
  if (/wie spät|uhrzeit|wieviel uhr|wie viel uhr/.test(text)) {
    return `Es ist ${now.getHours()} Uhr ${now.getMinutes() || ""}`.trim() + "."
  }
  if (/welcher tag|datum|welches datum|den wievielten/.test(text)) {
    return `Heute ist ${now.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}.`
  }

  const units: Record<string, number> = { sekunde: 1, sekunden: 1, minute: 60, minuten: 60, stunde: 3600, stunden: 3600 }
  const numberWords: Record<string, number> = { eine: 1, einer: 1, ein: 1, zwei: 2, drei: 3, vier: 4, fünf: 5, zehn: 10, zwanzig: 20, dreißig: 30, halbe: 0.5 }
  const amount = (s: string) => (numberWords[s] ?? Number(s.replace(",", ".")))

  const timer = text.match(/timer (?:auf |für )?(\d+(?:[.,]\d+)?|\p{L}+) (sekunden?|minuten?|stunden?)/u)
  if (timer) {
    const seconds = Math.round(amount(timer[1]) * units[timer[2]])
    if (seconds > 0) return runTool("set_timer", { seconds, label: "Timer" }, ctx)
  }

  const remind = text.match(/erinner(?:e|ung)? mich in (\d+(?:[.,]\d+)?|\p{L}+) (sekunden?|minuten?|stunden?) (?:an |daran,? )?(.+)/u)
  if (remind) {
    const seconds = Math.round(amount(remind[1]) * units[remind[2]])
    const due = new Date(Date.now() + seconds * 1000)
    if (seconds > 0) return runTool("set_reminder", { text: remind[3].replace(/[.!]$/, ""), due_iso: due.toISOString() }, ctx)
  }

  const open = text.match(/^(?:öffne|starte|zeig mir) (.+)$/)
  if (open) {
    const sites: Record<string, string> = {
      youtube: "https://www.youtube.com",
      google: "https://www.google.com",
      gmail: "https://mail.google.com",
      netflix: "https://www.netflix.com",
      spotify: "https://open.spotify.com",
      wikipedia: "https://de.wikipedia.org",
      maps: "https://maps.google.com",
      amazon: "https://www.amazon.de",
      wetter: "https://www.google.com/search?q=wetter",
    }
    const key = Object.keys(sites).find((k) => open[1].includes(k))
    if (key) return runTool("open_website", { url: sites[key] }, ctx)
  }

  const note = text.match(/^(?:notiere?|notier dir|schreib(?:e)? auf)[:,]? (.+)$/)
  if (note) return runTool("append_to_file", { name: "Notizen.txt", text: input.trim().replace(/^\S+(?: dir| auf)?[:,]?\s*/i, "") }, ctx)

  return null
}
