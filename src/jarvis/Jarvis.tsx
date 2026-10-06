import { useCallback, useEffect, useRef, useState, type FormEvent } from "react"
import { BellIcon, FolderIcon, MicIcon, MicOffIcon, SendIcon, SettingsIcon, SquareIcon } from "lucide-react"
import { usePersistentState, newId } from "@/lib/storage"
import { JarvisError, runTurn, type History } from "./agent"
import {
  backendFor,
  browserBackend,
  forgetFolder,
  pickFolder,
  reconnectFolder,
  restoreFolder,
  type FileBackend,
} from "./files"
import { handleOffline } from "./offline"
import { FilesPanel, RemindersPanel, SettingsPanel } from "./Panels"
import { createListener, recognitionSupported, Speaker, type Recognition } from "./speech"
import { defaultSettings, type Reminder, type Settings } from "./store"
import type { ToolContext } from "./tools"

type Status = "idle" | "listening" | "thinking" | "speaking"
interface ChatMessage {
  id: string
  role: "user" | "jarvis" | "info"
  text: string
}

const MAX_HISTORY = 80
const WAKE = /\b(jarvis|jervis|dschawis|tschawis|javis)\b[,.!]?\s*/i

const toolLabels: Record<string, string> = {
  set_reminder: "Erinnerung wird gespeichert",
  set_timer: "Timer wird gestellt",
  list_reminders: "Erinnerungen werden geprüft",
  delete_reminder: "Erinnerung wird gelöscht",
  open_website: "Webseite wird geöffnet",
  remember_fact: "Wird gemerkt",
  forget_fact: "Wird vergessen",
  list_files: "Dateien werden durchsucht",
  read_file: "Datei wird gelesen",
  write_file: "Datei wird gespeichert",
  edit_file: "Datei wird bearbeitet",
  append_to_file: "Datei wird ergänzt",
  rename_file: "Datei wird umbenannt",
  delete_file: "Datei wird gelöscht",
}

function beep() {
  try {
    const ctx = new AudioContext()
    ;[0, 0.25, 0.5].forEach((t) => {
      const o = ctx.createOscillator()
      const g = ctx.createGain()
      o.frequency.value = 880
      g.gain.setValueAtTime(0.15, ctx.currentTime + t)
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.2)
      o.connect(g).connect(ctx.destination)
      o.start(ctx.currentTime + t)
      o.stop(ctx.currentTime + t + 0.2)
    })
  } catch {
    // Kein Audio verfügbar.
  }
}

export default function Jarvis() {
  const [settings, setSettings] = usePersistentState<Settings>("jarvis-settings", defaultSettings)
  const [reminders, setReminders] = usePersistentState<Reminder[]>("jarvis-reminders", [])
  const [memory, setMemory] = usePersistentState<string[]>("jarvis-memory", [])
  const [history, setHistory] = usePersistentState<History>("jarvis-history", [])
  const [chat, setChat] = usePersistentState<ChatMessage[]>("jarvis-chat", [])

  const [status, setStatus] = useState<Status>("idle")
  const [activity, setActivity] = useState("")
  const [interim, setInterim] = useState("")
  const [input, setInput] = useState("")
  const [panel, setPanel] = useState<"settings" | "reminders" | "files" | null>(null)
  const [backend, setBackend] = useState<FileBackend>(browserBackend)
  const [savedDir, setSavedDir] = useState<Awaited<ReturnType<typeof restoreFolder>>>(null)
  const [filesVersion, setFilesVersion] = useState(0)

  const speaker = useRef(new Speaker()).current
  const listener = useRef<Recognition | null>(null)
  const abort = useRef<AbortController | null>(null)
  const busy = useRef(false)
  const awaitingCommand = useRef(0)
  const chatEnd = useRef<HTMLDivElement>(null)

  // Aktuelle Werte für Werkzeuge und Callbacks, ohne sie neu erzeugen zu müssen.
  const latest = useRef({ reminders, memory, history, settings, backend })
  latest.current = { reminders, memory, history, settings, backend }

  useEffect(() => {
    speaker.enabled = settings.speak
    speaker.voiceURI = settings.voiceURI
    speaker.rate = settings.rate
    speaker.onSpeakingChange = (speaking) => setStatus((s) => (speaking ? "speaking" : s === "speaking" ? "idle" : s))
  }, [speaker, settings.speak, settings.voiceURI, settings.rate])

  useEffect(() => chatEnd.current?.scrollIntoView({ behavior: "smooth" }), [chat])

  // Gespeicherten PC-Ordner wiederherstellen.
  useEffect(() => {
    restoreFolder().then((saved) => {
      setSavedDir(saved)
      if (saved?.ready) setBackend(backendFor(saved.dir))
    })
  }, [])

  const addChat = useCallback(
    (role: ChatMessage["role"], text: string) => {
      const msg = { id: newId(), role, text }
      setChat((prev) => [...prev, msg].slice(-200))
      return msg.id
    },
    [setChat],
  )

  const toolCtx: ToolContext = {
    getReminders: () => latest.current.reminders,
    setReminders: (update) => {
      latest.current.reminders = update(latest.current.reminders)
      setReminders(latest.current.reminders)
    },
    getMemory: () => latest.current.memory,
    setMemory: (update) => {
      latest.current.memory = update(latest.current.memory)
      setMemory(latest.current.memory)
    },
    files: () => latest.current.backend,
    onFilesChanged: () => setFilesVersion((v) => v + 1),
  }

  // ---------- Fällige Erinnerungen ----------
  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now()
      const due = latest.current.reminders.filter((r) => !r.notified && new Date(r.due).getTime() <= now)
      if (due.length === 0) return
      for (const r of due) {
        const text = r.kind === "timer" ? `Ihr Timer „${r.text}“ ist abgelaufen.` : `Erinnerung: ${r.text}.`
        beep()
        addChat("info", `🔔 ${text}`)
        speaker.say(text)
        if ("Notification" in window && Notification.permission === "granted") new Notification("J.A.R.V.I.S.", { body: text })
      }
      const ids = new Set(due.map((r) => r.id))
      const dayAgo = now - 86_400_000
      toolCtx.setReminders((prev) =>
        prev
          .map((r) => (ids.has(r.id) ? { ...r, notified: true } : r))
          .filter((r) => !r.notified || new Date(r.due).getTime() > dayAgo),
      )
    }, 1000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [addChat, speaker])

  // ---------- Fragen an Jarvis ----------
  const ask = useCallback(
    async (raw: string) => {
      const text = raw.trim()
      if (!text || busy.current) return
      busy.current = true
      speaker.stop()
      setInterim("")
      addChat("user", text)
      setStatus("thinking")
      if ("Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(() => {})

      const { settings: s } = latest.current
      try {
        if (!s.apiKey) {
          const reply =
            (await handleOffline(text, toolCtx)) ??
            "Für diese Frage brauche ich einen Claude API-Schlüssel. Bitte trage ihn in den Einstellungen ein."
          addChat("jarvis", reply)
          speaker.say(reply)
          return
        }

        let replyId = ""
        let reply = ""
        abort.current = new AbortController()
        const result = await runTurn({
          apiKey: s.apiKey,
          history: latest.current.history,
          userText: text,
          memory: latest.current.memory,
          userName: s.userName,
          ctx: toolCtx,
          signal: abort.current.signal,
          callbacks: {
            onText: (delta) => {
              reply += delta
              if (!replyId) replyId = addChat("jarvis", reply)
              else setChat((prev) => prev.map((m) => (m.id === replyId ? { ...m, text: reply } : m)))
              speaker.push(delta)
            },
            onToolUse: (name) => setActivity(toolLabels[name] ?? "Arbeite …"),
          },
        })
        speaker.flush()
        if (!result.text.trim()) addChat("jarvis", "Erledigt.")
        if (result.history.length > MAX_HISTORY) {
          // Zu lang: neues Gespräch beginnen. Das Gedächtnis bleibt erhalten.
          setHistory([])
          addChat("info", "Neues Gespräch begonnen – Gemerktes bleibt erhalten.")
        } else {
          setHistory(result.history)
        }
      } catch (err) {
        if ((err as Error).name === "AbortError" || /abort/i.test((err as Error).message)) {
          addChat("info", "Abgebrochen.")
        } else {
          const msg = err instanceof JarvisError ? err.message : `Unerwarteter Fehler: ${(err as Error).message}`
          addChat("info", `⚠ ${msg}`)
          speaker.say(msg)
        }
      } finally {
        abort.current = null
        busy.current = false
        setActivity("")
        setStatus(speaker.speaking ? "speaking" : "idle")
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [addChat, setChat, setHistory, speaker],
  )

  // ---------- Spracheingabe ----------
  const stopListening = useCallback(() => {
    const l = listener.current
    listener.current = null
    l?.abort()
    setInterim("")
    setStatus((s) => (s === "listening" ? "idle" : s))
  }, [])

  const listenOnce = useCallback(() => {
    if (listener.current) return stopListening()
    speaker.stop()
    const rec = createListener({
      continuous: false,
      onInterim: setInterim,
      onFinal: (t) => {
        listener.current = null
        void ask(t)
      },
      onEnd: () => {
        if (listener.current === rec) listener.current = null
        setInterim("")
        setStatus((s) => (s === "listening" ? "idle" : s))
      },
      onError: (e) => {
        if (e === "not-allowed") addChat("info", "⚠ Mikrofon-Zugriff wurde verweigert. Bitte im Browser erlauben.")
      },
    })
    if (!rec) return
    listener.current = rec
    setStatus("listening")
    rec.start()
  }, [addChat, ask, speaker, stopListening])

  // Dauerhaftes Zuhören auf das Aktivierungswort.
  useEffect(() => {
    if (!settings.wakeWord || !recognitionSupported) return
    let stopped = false
    let rec: Recognition | null = null

    const start = async () => {
      if (stopped) return
      // Nicht zuhören, während Jarvis denkt oder spricht – sonst hört er sich selbst.
      while (!stopped && (busy.current || speaker.speaking)) {
        await new Promise((r) => setTimeout(r, 300))
        await speaker.idle()
      }
      if (stopped) return
      rec = createListener({
        continuous: true,
        onInterim: (t) => (WAKE.test(t) || awaitingCommand.current > Date.now() ? setInterim(t) : undefined),
        onFinal: (t) => {
          setInterim("")
          const match = t.match(WAKE)
          let command = ""
          if (match) command = t.slice((match.index ?? 0) + match[0].length).trim()
          else if (awaitingCommand.current > Date.now()) command = t
          else return
          if (!command) {
            awaitingCommand.current = Date.now() + 8000
            speaker.say("Ja?")
            return
          }
          awaitingCommand.current = 0
          rec?.abort()
          void ask(command)
        },
        onEnd: () => {
          rec = null
          setTimeout(start, 250)
        },
        onError: (e) => {
          if (e === "not-allowed") {
            stopped = true
            addChat("info", "⚠ Mikrofon-Zugriff wurde verweigert. Dauerhaftes Zuhören ist aus.")
            setSettings((s) => ({ ...s, wakeWord: false }))
          }
        },
      })
      try {
        rec?.start()
      } catch {
        setTimeout(start, 1000)
      }
    }
    void start()
    return () => {
      stopped = true
      rec?.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.wakeWord])

  const submit = (e: FormEvent) => {
    e.preventDefault()
    void ask(input)
    setInput("")
  }

  const stopAll = () => {
    abort.current?.abort()
    speaker.stop()
    stopListening()
  }

  const statusText =
    activity ||
    {
      idle: settings.wakeWord ? "Ich höre zu – sag „Jarvis …“" : "Bereit",
      listening: "Ich höre …",
      thinking: "Denke nach …",
      speaking: "Spreche …",
    }[status]

  const openReminders = reminders.filter((r) => !r.notified).length

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 pb-4">
      <header className="flex items-center justify-between py-4">
        <h1 className="font-mono text-lg tracking-[0.35em] text-cyan-300">J.A.R.V.I.S.</h1>
        <nav className="flex gap-1">
          <IconButton label="Dateien" onClick={() => setPanel("files")}>
            <FolderIcon className="h-5 w-5" />
          </IconButton>
          <IconButton label="Erinnerungen" onClick={() => setPanel("reminders")}>
            <BellIcon className="h-5 w-5" />
            {openReminders > 0 && (
              <span className="absolute -right-0.5 -top-0.5 rounded-full bg-cyan-400 px-1.5 text-[10px] font-bold text-black">
                {openReminders}
              </span>
            )}
          </IconButton>
          <IconButton label="Einstellungen" onClick={() => setPanel("settings")}>
            <SettingsIcon className="h-5 w-5" />
          </IconButton>
        </nav>
      </header>

      <Reactor status={status} onClick={recognitionSupported ? listenOnce : undefined} />
      <p className="mt-4 text-center font-mono text-sm uppercase tracking-widest text-cyan-400">{statusText}</p>
      <p className="min-h-6 text-center text-cyan-100/80 italic">{interim}</p>

      {!settings.apiKey && chat.length === 0 && (
        <div className="mx-auto mt-4 max-w-md rounded-lg border border-cyan-900 bg-cyan-950/30 p-4 text-sm text-cyan-200">
          Willkommen. Für volle Intelligenz trage in den{" "}
          <button className="underline" onClick={() => setPanel("settings")}>
            Einstellungen
          </button>{" "}
          deinen Claude API-Schlüssel ein. Einfache Befehle wie „Wie spät ist es?“, „Timer 5 Minuten“ oder „Notiere Milch kaufen“
          funktionieren auch ohne.
        </div>
      )}

      <main className="mt-4 flex-1 space-y-3 overflow-y-auto">
        {chat.map((m) => (
          <div
            key={m.id}
            className={
              m.role === "user"
                ? "ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-cyan-900/50 px-4 py-2"
                : m.role === "jarvis"
                  ? "mr-auto max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-bl-sm border border-cyan-800/60 bg-[#06111c] px-4 py-2"
                  : "text-center text-xs text-cyan-400/80"
            }
          >
            {m.text}
          </div>
        ))}
        <div ref={chatEnd} />
      </main>

      <form onSubmit={submit} className="sticky bottom-0 mt-4 flex gap-2 bg-[#03070d] pt-2">
        <input
          className="flex-1 rounded-full border border-cyan-800 bg-[#06111c] px-4 py-3 text-cyan-50 outline-none placeholder:text-cyan-700 focus:border-cyan-400"
          placeholder={recognitionSupported ? "Schreiben oder Mikrofon antippen …" : "Nachricht an Jarvis …"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        {status === "thinking" || status === "speaking" ? (
          <RoundButton label="Stopp" onClick={stopAll}>
            <SquareIcon className="h-5 w-5" />
          </RoundButton>
        ) : input.trim() ? (
          <RoundButton label="Senden" type="submit">
            <SendIcon className="h-5 w-5" />
          </RoundButton>
        ) : recognitionSupported ? (
          <RoundButton label={status === "listening" ? "Zuhören beenden" : "Sprechen"} onClick={listenOnce} active={status === "listening"}>
            {status === "listening" ? <MicOffIcon className="h-5 w-5" /> : <MicIcon className="h-5 w-5" />}
          </RoundButton>
        ) : null}
      </form>
      {!recognitionSupported && (
        <p className="mt-2 text-center text-xs text-cyan-600">Spracheingabe gibt es in Chrome und Edge.</p>
      )}

      <SettingsPanel
        open={panel === "settings"}
        onOpenChange={(o) => setPanel(o ? "settings" : null)}
        settings={settings}
        onChange={setSettings}
        memory={memory}
        onDeleteMemory={(i) => setMemory((prev) => prev.filter((_, j) => j !== i))}
        onResetConversation={() => {
          setHistory([])
          setChat([])
        }}
      />
      <RemindersPanel
        open={panel === "reminders"}
        onOpenChange={(o) => setPanel(o ? "reminders" : null)}
        reminders={reminders}
        onDelete={(id) => setReminders((prev) => prev.filter((r) => r.id !== id))}
      />
      <FilesPanel
        open={panel === "files"}
        onOpenChange={(o) => setPanel(o ? "files" : null)}
        backend={backend}
        version={filesVersion}
        canReconnect={Boolean(savedDir && backend.kind !== "folder")}
        onPickFolder={async () => {
          try {
            setBackend(await pickFolder())
            setSavedDir(await restoreFolder())
          } catch {
            // Auswahl abgebrochen.
          }
        }}
        onReconnect={async () => {
          if (!savedDir) return
          const b = await reconnectFolder(savedDir.dir)
          if (b) setBackend(b)
        }}
        onUseBrowser={async () => {
          await forgetFolder()
          setSavedDir(null)
          setBackend(browserBackend)
        }}
        onChanged={() => setFilesVersion((v) => v + 1)}
      />
    </div>
  )
}

function Reactor({ status, onClick }: { status: Status; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Sprechen"
      data-state={status}
      className="reactor relative mx-auto mt-6 grid h-52 w-52 place-items-center rounded-full focus:outline-none sm:h-60 sm:w-60"
    >
      <svg viewBox="0 0 200 200" className="reactor-ring absolute inset-0 h-full w-full">
        <circle cx="100" cy="100" r="94" fill="none" stroke="rgb(34 211 238 / 0.35)" strokeWidth="2" strokeDasharray="4 8" />
        <circle cx="100" cy="100" r="86" fill="none" stroke="rgb(34 211 238 / 0.7)" strokeWidth="3" strokeDasharray="60 30 10 30" />
      </svg>
      <svg viewBox="0 0 200 200" className="reactor-ring-rev absolute inset-0 h-full w-full">
        <circle cx="100" cy="100" r="72" fill="none" stroke="rgb(103 232 249 / 0.6)" strokeWidth="6" strokeDasharray="20 14" />
      </svg>
      <div
        className={`reactor-core h-24 w-24 rounded-full transition-colors duration-500 sm:h-28 sm:w-28 ${
          status === "listening"
            ? "bg-cyan-300 shadow-[0_0_60px_20px_rgba(34,211,238,0.6)]"
            : status === "thinking"
              ? "bg-sky-500 shadow-[0_0_50px_15px_rgba(14,165,233,0.5)]"
              : status === "speaking"
                ? "bg-cyan-200 shadow-[0_0_70px_25px_rgba(165,243,252,0.6)]"
                : "bg-cyan-600/80 shadow-[0_0_40px_10px_rgba(8,145,178,0.45)]"
        }`}
      />
    </button>
  )
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button aria-label={label} title={label} onClick={onClick} className="relative rounded-md p-2 text-cyan-300 hover:bg-cyan-950">
      {children}
    </button>
  )
}

function RoundButton(props: {
  label: string
  onClick?: () => void
  type?: "button" | "submit"
  active?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type={props.type ?? "button"}
      aria-label={props.label}
      title={props.label}
      onClick={props.onClick}
      className={`grid h-12 w-12 shrink-0 place-items-center rounded-full border border-cyan-500 ${
        props.active ? "bg-cyan-400 text-black" : "bg-cyan-950 text-cyan-200 hover:bg-cyan-900"
      }`}
    >
      {props.children}
    </button>
  )
}
