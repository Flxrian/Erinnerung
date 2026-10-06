import type Anthropic from "@anthropic-ai/sdk"
import { formatDue, formatDuration, makeReminder, type Reminder } from "./store"
import { checkContent, checkName, type FileBackend } from "./files"

/** Zugriff der Werkzeuge auf den App-Zustand. */
export interface ToolContext {
  getReminders: () => Reminder[]
  setReminders: (update: (prev: Reminder[]) => Reminder[]) => void
  getMemory: () => string[]
  setMemory: (update: (prev: string[]) => string[]) => void
  files: () => FileBackend
  onFilesChanged: () => void
}

type ToolDef = Anthropic.Beta.BetaTool

const def = (name: string, description: string, properties: Record<string, unknown>, required: string[]): ToolDef => ({
  name,
  description,
  input_schema: { type: "object", properties, required, additionalProperties: false },
  strict: true,
  eager_input_streaming: true,
})

export const clientTools: ToolDef[] = [
  def(
    "set_reminder",
    "Legt eine Erinnerung zu einem bestimmten Zeitpunkt an. Jarvis meldet sich dann per Sprache und Benachrichtigung. Berechne due_iso aus der aktuellen Zeit, die in jeder Nachricht mitgeschickt wird.",
    {
      text: { type: "string", description: "Woran erinnert werden soll, kurz formuliert" },
      due_iso: { type: "string", description: "Zeitpunkt als ISO-8601 mit Zeitzonen-Offset, z. B. 2026-10-06T18:30:00+02:00" },
    },
    ["text", "due_iso"],
  ),
  def(
    "set_timer",
    "Startet einen Countdown-Timer. Nutze dies für relative Zeiträume wie 'in 10 Minuten' ohne konkreten Termin.",
    {
      seconds: { type: "integer", description: "Dauer in Sekunden" },
      label: { type: "string", description: "Bezeichnung, z. B. 'Nudeln'" },
    },
    ["seconds", "label"],
  ),
  def("list_reminders", "Listet alle offenen Erinnerungen und Timer mit ihrer ID auf.", {}, []),
  def(
    "delete_reminder",
    "Löscht eine Erinnerung oder einen Timer anhand der ID aus list_reminders.",
    { id: { type: "string" } },
    ["id"],
  ),
  def(
    "open_website",
    "Öffnet eine Webseite in einem neuen Browser-Tab, z. B. YouTube, eine Google-Suche oder Google Maps.",
    { url: { type: "string", description: "Vollständige https-URL" } },
    ["url"],
  ),
  def(
    "remember_fact",
    "Speichert dauerhaft eine Information über den Benutzer (Vorlieben, Namen, wichtige Details), damit Jarvis sie in künftigen Gesprächen weiß.",
    { fact: { type: "string" } },
    ["fact"],
  ),
  def(
    "forget_fact",
    "Löscht gespeicherte Informationen, die den Suchtext enthalten.",
    { contains: { type: "string" } },
    ["contains"],
  ),
]

export const fileTools: ToolDef[] = [
  def("list_files", "Listet alle gespeicherten Dateien mit Größe und Änderungsdatum auf.", {}, []),
  def(
    "read_file",
    "Liest den vollständigen Inhalt einer Datei. Vor jeder Änderung an einer bestehenden Datei zuerst lesen.",
    { name: { type: "string", description: "Dateiname inkl. Endung, z. B. einkaufsliste.txt" } },
    ["name"],
  ),
  def(
    "write_file",
    "Erstellt eine neue Datei oder überschreibt eine bestehende komplett. Für kleine Änderungen an bestehenden Dateien stattdessen edit_file oder append_to_file nutzen. Ohne Angabe des Benutzers wähle einen sinnvollen deutschen Dateinamen mit .txt oder .md.",
    {
      name: { type: "string", description: "Dateiname inkl. Endung (.txt, .md, .csv, .json, .html …)" },
      content: { type: "string", description: "Der vollständige neue Inhalt" },
    },
    ["name", "content"],
  ),
  def(
    "edit_file",
    "Ersetzt in einer Datei eine exakt vorkommende Textstelle durch neuen Text (z. B. Zeile ändern, Eintrag streichen, Wort korrigieren). old_text muss genau einmal vorkommen; nutze dafür vorher read_file. Zum Löschen einer Stelle new_text leer lassen.",
    {
      name: { type: "string" },
      old_text: { type: "string", description: "Exakter Text, der ersetzt werden soll, inkl. Zeilenumbrüche" },
      new_text: { type: "string", description: "Ersatztext" },
    },
    ["name", "old_text", "new_text"],
  ),
  def(
    "append_to_file",
    "Hängt Text an das Ende einer Datei an (legt sie an, falls sie fehlt). Ideal für Listen, Tagebuch, Notizen.",
    {
      name: { type: "string" },
      text: { type: "string", description: "Anzuhängender Text; beginnt automatisch in einer neuen Zeile" },
    },
    ["name", "text"],
  ),
  def(
    "rename_file",
    "Benennt eine Datei um.",
    { name: { type: "string" }, new_name: { type: "string" } },
    ["name", "new_name"],
  ),
  def("delete_file", "Löscht eine Datei endgültig. Nur auf ausdrücklichen Wunsch des Benutzers.", { name: { type: "string" } }, ["name"]),
]

export const webSearchTool: Anthropic.Beta.BetaWebSearchTool20260209 = {
  type: "web_search_20260209",
  name: "web_search",
  max_uses: 3,
  user_location: { type: "approximate", country: "DE", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone },
}

const str = (v: unknown, field: string) => {
  if (typeof v !== "string" || !v.trim()) throw new Error(`Feld '${field}' fehlt oder ist kein Text.`)
  return v.trim()
}

/** Führt ein Werkzeug aus und liefert den Text für das tool_result. Wirft bei ungültiger Eingabe. */
export async function runTool(name: string, input: unknown, ctx: ToolContext): Promise<string> {
  const args = (input && typeof input === "object" ? input : {}) as Record<string, unknown>

  switch (name) {
    case "set_reminder": {
      const text = str(args.text, "text")
      const due = new Date(str(args.due_iso, "due_iso"))
      if (isNaN(due.getTime())) throw new Error("due_iso ist kein gültiges Datum.")
      if (due.getTime() < Date.now() - 60_000) throw new Error("Der Zeitpunkt liegt in der Vergangenheit.")
      const r = makeReminder(text, due, "reminder")
      ctx.setReminders((prev) => [...prev, r])
      return `Erinnerung ${r.id} gespeichert für ${formatDue(r.due)}.`
    }
    case "set_timer": {
      const seconds = Number(args.seconds)
      if (!Number.isFinite(seconds) || seconds <= 0 || seconds > 7 * 86400) throw new Error("seconds muss zwischen 1 und 604800 liegen.")
      const label = typeof args.label === "string" && args.label.trim() ? args.label.trim() : "Timer"
      const r = makeReminder(label, new Date(Date.now() + seconds * 1000), "timer")
      ctx.setReminders((prev) => [...prev, r])
      return `Timer ${r.id} „${label}“ läuft: ${formatDuration(seconds)}`
    }
    case "list_reminders": {
      const open = ctx.getReminders().filter((r) => !r.notified)
      if (open.length === 0) return "Keine offenen Erinnerungen oder Timer."
      return open.map((r) => `${r.id}: ${r.kind === "timer" ? "Timer" : "Erinnerung"} „${r.text}“ – ${formatDue(r.due)}`).join("\n")
    }
    case "delete_reminder": {
      const id = str(args.id, "id")
      if (!ctx.getReminders().some((r) => r.id === id)) throw new Error(`Keine Erinnerung mit ID ${id}.`)
      ctx.setReminders((prev) => prev.filter((r) => r.id !== id))
      return `Erinnerung ${id} gelöscht.`
    }
    case "open_website": {
      const url = new URL(str(args.url, "url"))
      if (url.protocol !== "https:" && url.protocol !== "http:") throw new Error("Nur http(s)-Adressen sind erlaubt.")
      const win = window.open(url.href, "_blank", "noopener")
      return win === null
        ? `Der Browser hat das Öffnen von ${url.href} blockiert (Pop-up-Blocker). Bitte dem Benutzer sagen, er soll Pop-ups für diese Seite erlauben.`
        : `${url.href} wurde geöffnet.`
    }
    case "remember_fact": {
      const fact = str(args.fact, "fact")
      ctx.setMemory((prev) => (prev.includes(fact) ? prev : [...prev, fact]))
      return "Gespeichert."
    }
    case "forget_fact": {
      const needle = str(args.contains, "contains").toLowerCase()
      const before = ctx.getMemory().length
      const after = ctx.getMemory().filter((f) => !f.toLowerCase().includes(needle))
      ctx.setMemory(() => after)
      return `${before - after.length} Einträge gelöscht.`
    }
    case "list_files": {
      const files = await ctx.files().list()
      if (files.length === 0) return `Keine Dateien im ${ctx.files().label}.`
      return files
        .sort((a, b) => b.modified - a.modified)
        .map((f) => `${f.name} (${f.size} Zeichen, geändert ${new Date(f.modified).toLocaleString("de-DE")})`)
        .join("\n")
    }
    case "read_file": {
      const content = await ctx.files().read(checkName(args.name))
      return content === "" ? "(Die Datei ist leer.)" : content
    }
    case "write_file": {
      const fileName = checkName(args.name)
      const existed = (await ctx.files().list()).some((f) => f.name === fileName)
      await ctx.files().write(fileName, checkContent(args.content))
      ctx.onFilesChanged()
      return `${fileName} ${existed ? "überschrieben" : "erstellt"} (${ctx.files().label}).`
    }
    case "edit_file": {
      const fileName = checkName(args.name)
      const oldText = typeof args.old_text === "string" ? args.old_text : ""
      const newText = typeof args.new_text === "string" ? args.new_text : ""
      if (!oldText) throw new Error("old_text darf nicht leer sein.")
      const content = await ctx.files().read(fileName)
      const count = content.split(oldText).length - 1
      if (count === 0) throw new Error("old_text kommt in der Datei nicht vor. Lies die Datei mit read_file und versuche es mit dem exakten Text erneut.")
      if (count > 1) throw new Error(`old_text kommt ${count}-mal vor. Wähle eine längere, eindeutige Textstelle.`)
      await ctx.files().write(fileName, checkContent(content.replace(oldText, () => newText)))
      ctx.onFilesChanged()
      return `${fileName} geändert.`
    }
    case "append_to_file": {
      const fileName = checkName(args.name)
      const text = str(args.text, "text")
      let content = ""
      try {
        content = await ctx.files().read(fileName)
      } catch {
        // Datei existiert noch nicht – wird neu angelegt.
      }
      const sep = content === "" || content.endsWith("\n") ? "" : "\n"
      await ctx.files().write(fileName, checkContent(content + sep + text + "\n"))
      ctx.onFilesChanged()
      return `Text an ${fileName} angehängt.`
    }
    case "rename_file": {
      const from = checkName(args.name)
      const to = checkName(args.new_name)
      if ((await ctx.files().list()).some((f) => f.name === to)) throw new Error(`${to} existiert bereits.`)
      const content = await ctx.files().read(from)
      await ctx.files().write(to, content)
      await ctx.files().remove(from)
      ctx.onFilesChanged()
      return `${from} heißt jetzt ${to}.`
    }
    case "delete_file": {
      const fileName = checkName(args.name)
      await ctx.files().remove(fileName)
      ctx.onFilesChanged()
      return `${fileName} gelöscht.`
    }
    default:
      throw new Error(`Unbekanntes Werkzeug: ${name}`)
  }
}
