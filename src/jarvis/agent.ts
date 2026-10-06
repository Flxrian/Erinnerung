import Anthropic from "@anthropic-ai/sdk"
import { clientTools, fileTools, runTool, webSearchTool, type ToolContext } from "./tools"

export type History = Anthropic.Beta.BetaMessageParam[]

const MODEL = "claude-opus-5-5"
const MAX_TOOL_ROUNDS = 8

const SYSTEM_PROMPT = `Du bist J.A.R.V.I.S., ein persönlicher KI-Assistent im Stil des Assistenten aus Iron Man: höflich, souverän, kompetent und mit einem trockenen, feinen Humor.

Deine Antworten werden meist laut vorgelesen. Deshalb:
- Antworte auf Deutsch, kurz und natürlich gesprochen – in der Regel ein bis drei Sätze.
- Keine Markdown-Formatierung, keine Aufzählungszeichen, keine Tabellen, keine Emojis, keine URLs vorlesen.
- Zahlen, Uhrzeiten und Daten so schreiben, wie man sie ausspricht (z. B. "halb sieben", "18 Uhr 30").
- Wenn der Benutzer ausdrücklich Details möchte, darfst du ausführlicher werden.

Du hast Werkzeuge für Erinnerungen, Timer, das Öffnen von Webseiten, eine Websuche für aktuelle Informationen, ein Langzeitgedächtnis und eine Dateiablage. Nutze sie selbstständig, wenn es passt, und bestätige danach knapp, was du getan hast. Wenn der Benutzer etwas Persönliches erzählt, das später nützlich ist (Name, Vorlieben, Termine, Gewohnheiten), speichere es mit remember_fact.

Dateien: Der Benutzer diktiert dir Inhalte und Änderungen per Sprache. Spracherkennung macht Fehler – korrigiere offensichtliche Erkennungsfehler, Groß- und Kleinschreibung und Satzzeichen, wenn du diktierten Text speicherst. Wenn er sagt "schreib", "notier" oder "speicher", lege eine Datei an oder ergänze eine passende bestehende. Wenn er von "der Liste" oder "meinen Notizen" spricht, schau mit list_files nach, welche Datei gemeint ist. Vor jeder Änderung an einer bestehenden Datei liest du sie mit read_file und änderst sie dann gezielt mit edit_file oder append_to_file, statt sie komplett neu zu schreiben. Lies beim Vorlesen von Dateien den Inhalt natürlich vor, ohne Formatierungszeichen. Lösche Dateien nur, wenn der Benutzer es ausdrücklich sagt.

Jede Benutzernachricht beginnt mit der aktuellen lokalen Zeit in eckigen Klammern. Nutze sie für Zeitberechnungen und erwähne sie nicht, außer man fragt danach.`

export interface TurnCallbacks {
  onText: (delta: string) => void
  onToolUse: (name: string) => void
}

export class JarvisError extends Error {}

function memoryBlock(memory: string[], userName: string): string {
  const lines = [
    userName ? `Der Benutzer heißt ${userName}. Sprich ihn oder sie gelegentlich mit Namen an.` : "",
    memory.length ? `Was du über den Benutzer weißt:\n${memory.map((m) => `- ${m}`).join("\n")}` : "",
  ].filter(Boolean)
  return lines.length ? lines.join("\n\n") : "Du weißt noch nichts Persönliches über den Benutzer."
}

function nowStamp() {
  const now = new Date()
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
  const offsetMin = -now.getTimezoneOffset()
  const sign = offsetMin >= 0 ? "+" : "-"
  const pad = (n: number) => String(Math.floor(Math.abs(n))).padStart(2, "0")
  const offset = `${sign}${pad(offsetMin / 60)}:${pad(offsetMin % 60)}`
  return `[${now.toLocaleString("de-DE", { dateStyle: "full", timeStyle: "short" })} · ${tz} · UTC${offset}]`
}

/**
 * Führt einen Gesprächszug aus: schickt die Nachricht, streamt die Antwort und
 * erledigt Werkzeugaufrufe, bis Jarvis fertig ist. Die History wird nur angehängt
 * (nie umgeschrieben), damit Denkblöcke gültig bleiben.
 */
export async function runTurn(opts: {
  apiKey: string
  history: History
  userText: string
  memory: string[]
  userName: string
  ctx: ToolContext
  callbacks: TurnCallbacks
  signal?: AbortSignal
}): Promise<{ history: History; text: string }> {
  const client = new Anthropic({ apiKey: opts.apiKey, dangerouslyAllowBrowser: true })
  const history: History = [...opts.history, { role: "user", content: `${nowStamp()} ${opts.userText}` }]
  let text = ""

  try {
    for (let round = 0; round < MAX_TOOL_ROUNDS; round++) {
      const stream = client.beta.messages.stream(
        {
          model: MODEL,
          max_tokens: 64000,
          betas: ["server-side-fallback-2026-07-01"],
          fallbacks: "default",
          output_config: { effort: "low" },
          system: [
            { type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } },
            { type: "text", text: memoryBlock(opts.memory, opts.userName) },
          ],
          tools: [...clientTools, ...fileTools, webSearchTool],
          messages: history,
        },
        { signal: opts.signal },
      )
      stream.on("text", (delta) => {
        text += delta
        opts.callbacks.onText(delta)
      })
      const message = await stream.finalMessage()

      if (message.stop_reason === "refusal") {
        // Abgelehnte Antwort verwerfen und den Zug zurücknehmen.
        const msg = " Dabei kann ich leider nicht helfen."
        opts.callbacks.onText(msg)
        return { history: opts.history, text: text + msg }
      }

      history.push({ role: "assistant", content: message.content })

      if (message.stop_reason === "pause_turn") continue
      if (message.stop_reason !== "tool_use") break

      const results: Anthropic.Beta.BetaToolResultBlockParam[] = []
      for (const block of message.content) {
        if (block.type !== "tool_use") continue
        opts.callbacks.onToolUse(block.name)
        try {
          results.push({ type: "tool_result", tool_use_id: block.id, content: await runTool(block.name, block.input, opts.ctx) })
        } catch (err) {
          results.push({
            type: "tool_result",
            tool_use_id: block.id,
            content: err instanceof Error ? err.message : String(err),
            is_error: true,
          })
        }
      }
      history.push({ role: "user", content: results })
      // Ein Leerzeichen trennt Text vor und nach dem Werkzeugaufruf.
      if (text && !/\s$/.test(text)) {
        text += " "
        opts.callbacks.onText(" ")
      }
    }
  } catch (err) {
    // Bei Fehlern bleibt die alte History gültig – der halbe Zug wird verworfen.
    if (err instanceof Anthropic.APIUserAbortError) throw err
    if (err instanceof Anthropic.AuthenticationError) throw new JarvisError("Der API-Schlüssel ist ungültig. Bitte in den Einstellungen prüfen.")
    if (err instanceof Anthropic.PermissionDeniedError) throw new JarvisError("Der API-Schlüssel hat keine Berechtigung für dieses Modell.")
    if (err instanceof Anthropic.RateLimitError) throw new JarvisError("Zu viele Anfragen gerade. Bitte gleich noch einmal versuchen.")
    if (err instanceof Anthropic.APIConnectionError) throw new JarvisError("Keine Verbindung zum Server. Bist du online?")
    if (err instanceof Anthropic.BadRequestError && /credit|balance|billing/i.test(err.message))
      throw new JarvisError("Das API-Guthaben ist aufgebraucht. Bitte unter console.anthropic.com aufladen.")
    if (err instanceof Anthropic.APIError) throw new JarvisError(`Fehler vom Server (${err.status ?? "?"}). Bitte später erneut versuchen.`)
    throw err
  }

  return { history, text }
}
