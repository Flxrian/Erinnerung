import { useEffect, useState } from "react"
import { DownloadIcon, FolderOpenIcon, PencilIcon, SaveIcon, Trash2Icon, XIcon } from "lucide-react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { downloadText, folderSupported, type FileBackend, type FileInfo } from "./files"
import { germanVoices } from "./speech"
import { formatDue, type Reminder, type Settings } from "./store"

const panel = "border-cyan-900 bg-[#06111c] text-cyan-100 max-h-[85vh] overflow-y-auto"
const btn =
  "inline-flex items-center gap-1.5 rounded-md border border-cyan-800 px-3 py-1.5 text-sm hover:bg-cyan-950 disabled:opacity-40"
const field = "w-full rounded-md border border-cyan-900 bg-[#020910] px-3 py-2 text-sm text-cyan-50 outline-none focus:border-cyan-500"

export function SettingsPanel(props: {
  open: boolean
  onOpenChange: (open: boolean) => void
  settings: Settings
  onChange: (s: Settings) => void
  memory: string[]
  onDeleteMemory: (index: number) => void
  onResetConversation: () => void
}) {
  const { settings: s, onChange } = props
  const [voices, setVoices] = useState(germanVoices)
  useEffect(() => {
    const update = () => setVoices(germanVoices())
    speechSynthesis.addEventListener("voiceschanged", update)
    return () => speechSynthesis.removeEventListener("voiceschanged", update)
  }, [])

  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className={panel}>
        <DialogHeader>
          <DialogTitle>Einstellungen</DialogTitle>
          <DialogDescription className="text-cyan-300/70">Alles wird nur in diesem Browser gespeichert.</DialogDescription>
        </DialogHeader>
        <div className="space-y-5 text-sm">
          <label className="block space-y-1.5">
            <span className="font-medium">Claude API-Schlüssel</span>
            <input
              type="password"
              className={field}
              placeholder="sk-ant-…"
              value={s.apiKey}
              onChange={(e) => onChange({ ...s, apiKey: e.target.value.trim() })}
            />
            <span className="block text-xs text-cyan-300/70">
              Ohne Schlüssel versteht Jarvis nur einfache Befehle (Uhrzeit, Timer, Notizen, Webseiten öffnen). Einen Schlüssel
              bekommst du unter{" "}
              <a className="underline" href="https://console.anthropic.com/settings/keys" target="_blank" rel="noreferrer">
                console.anthropic.com
              </a>
              . Die Nutzung kostet pro Anfrage ein paar Cent.
            </span>
          </label>
          <label className="block space-y-1.5">
            <span className="font-medium">Dein Name</span>
            <input className={field} value={s.userName} onChange={(e) => onChange({ ...s, userName: e.target.value })} />
          </label>
          <label className="block space-y-1.5">
            <span className="font-medium">Stimme</span>
            <select className={field} value={s.voiceURI} onChange={(e) => onChange({ ...s, voiceURI: e.target.value })}>
              <option value="">Automatisch</option>
              {voices.map((v) => (
                <option key={v.voiceURI} value={v.voiceURI}>
                  {v.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1.5">
            <span className="font-medium">Sprechtempo: {s.rate.toFixed(2)}</span>
            <input
              type="range"
              min={0.7}
              max={1.5}
              step={0.05}
              value={s.rate}
              className="w-full accent-cyan-400"
              onChange={(e) => onChange({ ...s, rate: Number(e.target.value) })}
            />
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" className="accent-cyan-400" checked={s.speak} onChange={(e) => onChange({ ...s, speak: e.target.checked })} />
            Antworten vorlesen
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className="accent-cyan-400"
              checked={s.wakeWord}
              onChange={(e) => onChange({ ...s, wakeWord: e.target.checked })}
            />
            Dauerhaft zuhören – auf „Jarvis …“ reagieren
          </label>

          <div className="space-y-2">
            <span className="font-medium">Was Jarvis sich gemerkt hat</span>
            {props.memory.length === 0 ? (
              <p className="text-xs text-cyan-300/70">Noch nichts. Sag z. B. „Jarvis, merk dir, dass ich Kaffee schwarz trinke.“</p>
            ) : (
              <ul className="space-y-1">
                {props.memory.map((m, i) => (
                  <li key={i} className="flex items-start justify-between gap-2 rounded bg-cyan-950/40 px-2 py-1">
                    <span>{m}</span>
                    <button aria-label="Vergessen" onClick={() => props.onDeleteMemory(i)}>
                      <XIcon className="h-4 w-4 text-cyan-400" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button className={btn} onClick={props.onResetConversation}>
            Gespräch neu beginnen
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function RemindersPanel(props: {
  open: boolean
  onOpenChange: (open: boolean) => void
  reminders: Reminder[]
  onDelete: (id: string) => void
}) {
  const open = props.reminders.filter((r) => !r.notified).sort((a, b) => a.due.localeCompare(b.due))
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className={panel}>
        <DialogHeader>
          <DialogTitle>Erinnerungen & Timer</DialogTitle>
          <DialogDescription className="text-cyan-300/70">
            Jarvis meldet sich, solange dieses Fenster geöffnet ist.
          </DialogDescription>
        </DialogHeader>
        {open.length === 0 ? (
          <p className="text-sm text-cyan-300/70">Nichts geplant. Sag z. B. „Erinnere mich morgen um 9 an den Zahnarzt.“</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {open.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-2 rounded bg-cyan-950/40 px-3 py-2">
                <span>
                  <span className="font-semibold">{r.kind === "timer" ? "⏱ " : "🔔 "}{r.text}</span>
                  <span className="block text-xs text-cyan-300/70">{formatDue(r.due)}</span>
                </span>
                <button aria-label="Löschen" onClick={() => props.onDelete(r.id)}>
                  <Trash2Icon className="h-4 w-4 text-cyan-400" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  )
}

export function FilesPanel(props: {
  open: boolean
  onOpenChange: (open: boolean) => void
  backend: FileBackend
  version: number
  canReconnect: boolean
  onPickFolder: () => void
  onReconnect: () => void
  onUseBrowser: () => void
  onChanged: () => void
}) {
  const { backend } = props
  const [files, setFiles] = useState<FileInfo[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState("")
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!props.open) return
    backend
      .list()
      .then((f) => setFiles(f.sort((a, b) => b.modified - a.modified)))
      .catch((e: Error) => setError(e.message))
  }, [backend, props.open, props.version])

  useEffect(() => {
    if (!selected) return
    backend
      .read(selected)
      .then((c) => {
        setContent(c)
        setError("")
      })
      .catch((e: Error) => setError(e.message))
  }, [backend, selected, props.version])

  const close = () => {
    setSelected(null)
    setEditing(false)
  }

  return (
    <Dialog
      open={props.open}
      onOpenChange={(o) => {
        if (!o) close()
        props.onOpenChange(o)
      }}
    >
      <DialogContent className={`${panel} max-w-2xl`}>
        <DialogHeader>
          <DialogTitle>Dateien</DialogTitle>
          <DialogDescription className="text-cyan-300/70">Speicherort: {backend.label}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap gap-2">
          {folderSupported() && (
            <button className={btn} onClick={props.onPickFolder}>
              <FolderOpenIcon className="h-4 w-4" /> Ordner auf dem PC wählen
            </button>
          )}
          {props.canReconnect && (
            <button className={btn} onClick={props.onReconnect}>
              <FolderOpenIcon className="h-4 w-4" /> Gespeicherten Ordner verbinden
            </button>
          )}
          {backend.kind === "folder" && (
            <button className={btn} onClick={props.onUseBrowser}>
              Browser-Speicher nutzen
            </button>
          )}
        </div>
        {!folderSupported() && (
          <p className="text-xs text-cyan-300/70">
            Echte Ordner auf dem PC gehen nur in Chrome oder Edge. Hier werden Dateien im Browser gespeichert – du kannst sie
            jederzeit herunterladen.
          </p>
        )}
        {error && <p className="text-sm text-red-400">{error}</p>}

        {selected ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold">{selected}</span>
              <span className="flex gap-2">
                {editing ? (
                  <button
                    className={btn}
                    onClick={async () => {
                      try {
                        await backend.write(selected, content)
                        setEditing(false)
                        props.onChanged()
                      } catch (e) {
                        setError((e as Error).message)
                      }
                    }}
                  >
                    <SaveIcon className="h-4 w-4" /> Speichern
                  </button>
                ) : (
                  <button className={btn} onClick={() => setEditing(true)}>
                    <PencilIcon className="h-4 w-4" /> Bearbeiten
                  </button>
                )}
                <button className={btn} onClick={() => downloadText(selected, content)}>
                  <DownloadIcon className="h-4 w-4" /> Download
                </button>
                <button className={btn} onClick={close}>
                  Zurück
                </button>
              </span>
            </div>
            {editing ? (
              <textarea className={`${field} min-h-72 font-mono`} value={content} onChange={(e) => setContent(e.target.value)} />
            ) : (
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-[#020910] p-3 text-sm">{content || "(leer)"}</pre>
            )}
          </div>
        ) : files.length === 0 ? (
          <p className="text-sm text-cyan-300/70">
            Noch keine Dateien. Sag z. B. „Jarvis, schreib eine Einkaufsliste mit Milch, Brot und Eiern.“
          </p>
        ) : (
          <ul className="space-y-1 text-sm">
            {files.map((f) => (
              <li key={f.name} className="flex items-center justify-between gap-2 rounded bg-cyan-950/40 px-3 py-2">
                <button className="flex-1 text-left hover:underline" onClick={() => setSelected(f.name)}>
                  {f.name}
                  <span className="block text-xs text-cyan-300/70">{new Date(f.modified).toLocaleString("de-DE")}</span>
                </button>
                <button
                  aria-label={`${f.name} löschen`}
                  onClick={async () => {
                    if (!confirm(`„${f.name}“ wirklich löschen?`)) return
                    await backend.remove(f.name).catch((e: Error) => setError(e.message))
                    props.onChanged()
                  }}
                >
                  <Trash2Icon className="h-4 w-4 text-cyan-400" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  )
}
