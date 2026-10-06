// Minimale Typen für die Web Speech API (in Chrome/Edge als webkitSpeechRecognition verfügbar).
interface RecognitionResult {
  isFinal: boolean
  0: { transcript: string }
}
interface RecognitionEvent {
  resultIndex: number
  results: { length: number; [i: number]: RecognitionResult }
}
export interface Recognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  start(): void
  stop(): void
  abort(): void
  onresult: ((e: RecognitionEvent) => void) | null
  onerror: ((e: { error: string }) => void) | null
  onend: (() => void) | null
}

type RecognitionCtor = new () => Recognition
const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor }
const RecognitionImpl = w.SpeechRecognition ?? w.webkitSpeechRecognition

export const recognitionSupported = Boolean(RecognitionImpl)

/**
 * Hört zu und meldet Zwischen- und Endergebnisse.
 * continuous = Dauerbetrieb (für das Aktivierungswort), sonst eine einzelne Äußerung.
 */
export function createListener(opts: {
  continuous: boolean
  onInterim: (text: string) => void
  onFinal: (text: string) => void
  onEnd: () => void
  onError: (error: string) => void
}) {
  if (!RecognitionImpl) return null
  const rec = new RecognitionImpl()
  rec.lang = "de-DE"
  rec.continuous = opts.continuous
  rec.interimResults = true
  rec.onresult = (e) => {
    let interim = ""
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i]
      if (r.isFinal) opts.onFinal(r[0].transcript.trim())
      else interim += r[0].transcript
    }
    opts.onInterim(interim.trim())
  }
  rec.onerror = (e) => opts.onError(e.error)
  rec.onend = () => opts.onEnd()
  return rec
}

// ---------- Sprachausgabe ----------

export function germanVoices() {
  return speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith("de"))
}

function pickVoice(voiceURI: string) {
  const voices = speechSynthesis.getVoices()
  return (
    voices.find((v) => v.voiceURI === voiceURI) ??
    germanVoices().find((v) => /male|männ|conrad|stefan|markus|killian|google deutsch/i.test(v.name)) ??
    germanVoices()[0] ??
    null
  )
}

/** Entfernt Formatierungszeichen und Links, die vorgelesen merkwürdig klingen. */
function speakable(text: string) {
  return text
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[*_#`>|]/g, "")
    .replace(/\s+/g, " ")
    .trim()
}

/**
 * Spricht gestreamten Text satzweise, sobald ein Satz vollständig ist,
 * damit Jarvis schon redet, während die Antwort noch entsteht.
 */
export class Speaker {
  private buffer = ""
  private pending = 0
  private idleResolvers: (() => void)[] = []
  enabled = true
  voiceURI = ""
  rate = 1.05
  onSpeakingChange: (speaking: boolean) => void = () => {}

  push(delta: string) {
    this.buffer += delta
    const match = this.buffer.match(/^([\s\S]*?[.!?…:])(\s+)([\s\S]*)$/)
    if (match && match[1].length > 20) {
      this.say(match[1])
      this.buffer = match[3]
    }
  }

  flush() {
    if (this.buffer.trim()) this.say(this.buffer)
    this.buffer = ""
  }

  say(text: string) {
    const clean = speakable(text)
    if (!this.enabled || !clean || typeof speechSynthesis === "undefined") return
    const u = new SpeechSynthesisUtterance(clean)
    u.lang = "de-DE"
    u.rate = this.rate
    u.pitch = 0.95
    const voice = pickVoice(this.voiceURI)
    if (voice) u.voice = voice
    this.pending++
    this.onSpeakingChange(true)
    const done = () => {
      this.pending = Math.max(0, this.pending - 1)
      if (this.pending === 0) {
        this.onSpeakingChange(false)
        this.idleResolvers.splice(0).forEach((r) => r())
      }
    }
    u.onend = done
    u.onerror = done
    speechSynthesis.speak(u)
  }

  stop() {
    this.buffer = ""
    this.pending = 0
    if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel()
    this.onSpeakingChange(false)
    this.idleResolvers.splice(0).forEach((r) => r())
  }

  get speaking() {
    return this.pending > 0
  }

  /** Wartet, bis alles ausgesprochen ist. */
  idle() {
    return this.pending === 0 ? Promise.resolve() : new Promise<void>((r) => this.idleResolvers.push(r))
  }
}
