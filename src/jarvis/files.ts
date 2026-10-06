/**
 * Dateiablage für Jarvis. Zwei Varianten:
 * - "folder": ein echter Ordner auf dem PC (File System Access API, Chrome/Edge)
 * - "browser": Dateien im localStorage des Browsers (überall verfügbar, Download möglich)
 */

export interface FileInfo {
  name: string
  size: number
  modified: number
}

export interface FileBackend {
  kind: "folder" | "browser"
  label: string
  list(): Promise<FileInfo[]>
  read(name: string): Promise<string>
  write(name: string, content: string): Promise<void>
  remove(name: string): Promise<void>
}

const MAX_FILE_CHARS = 200_000

export function checkName(raw: unknown): string {
  if (typeof raw !== "string") throw new Error("Dateiname fehlt.")
  const name = raw.trim()
  if (!name || name.length > 120) throw new Error("Dateiname ist leer oder zu lang.")
  if (/[\\/:*?"<>|]/.test(name) || name.startsWith(".")) throw new Error(`Ungültiger Dateiname: ${name}`)
  if (!/\.[a-z0-9]{1,8}$/i.test(name)) throw new Error("Der Dateiname braucht eine Endung, z. B. .txt oder .md.")
  return name
}

export function checkContent(content: unknown): string {
  if (typeof content !== "string") throw new Error("Inhalt fehlt.")
  if (content.length > MAX_FILE_CHARS) throw new Error("Datei ist zu groß (max. 200.000 Zeichen).")
  return content
}

// ---------- Browser-Speicher ----------

const LS_KEY = "jarvis:files"
type Stored = Record<string, { content: string; modified: number }>

function load(): Stored {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) ?? "{}") as Stored
  } catch {
    return {}
  }
}

function save(files: Stored) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(files))
  } catch {
    throw new Error("Der Browser-Speicher ist voll. Bitte Dateien löschen oder einen Ordner auf dem PC wählen.")
  }
}

export const browserBackend: FileBackend = {
  kind: "browser",
  label: "Browser-Speicher",
  async list() {
    return Object.entries(load()).map(([name, f]) => ({ name, size: f.content.length, modified: f.modified }))
  },
  async read(name) {
    const f = load()[name]
    if (!f) throw new Error(`Datei „${name}“ gibt es nicht.`)
    return f.content
  },
  async write(name, content) {
    const files = load()
    files[name] = { content, modified: Date.now() }
    save(files)
  },
  async remove(name) {
    const files = load()
    if (!(name in files)) throw new Error(`Datei „${name}“ gibt es nicht.`)
    delete files[name]
    save(files)
  },
}

// ---------- Echter Ordner (File System Access API) ----------

type PermissionMode = { mode: "readwrite" }
interface DirHandle extends FileSystemDirectoryHandle {
  queryPermission(d: PermissionMode): Promise<PermissionState>
  requestPermission(d: PermissionMode): Promise<PermissionState>
}

declare global {
  interface Window {
    showDirectoryPicker?: (opts?: { id?: string; mode?: "read" | "readwrite" }) => Promise<FileSystemDirectoryHandle>
  }
}

export const folderSupported = () => typeof window.showDirectoryPicker === "function"

function folderBackend(dir: DirHandle): FileBackend {
  const notFound = (name: string) => new Error(`Datei „${name}“ gibt es nicht.`)
  return {
    kind: "folder",
    label: `Ordner „${dir.name}“`,
    async list() {
      const out: FileInfo[] = []
      for await (const entry of dir.values()) {
        if (entry.kind !== "file" || entry.name.startsWith(".")) continue
        const file = await entry.getFile()
        out.push({ name: entry.name, size: file.size, modified: file.lastModified })
      }
      return out
    },
    async read(name) {
      try {
        return await (await (await dir.getFileHandle(name)).getFile()).text()
      } catch {
        throw notFound(name)
      }
    },
    async write(name, content) {
      const handle = await dir.getFileHandle(name, { create: true })
      const writable = await handle.createWritable()
      await writable.write(content)
      await writable.close()
    },
    async remove(name) {
      try {
        await dir.removeEntry(name)
      } catch {
        throw notFound(name)
      }
    },
  }
}

// Ordner-Handle in IndexedDB merken, damit der Ordner nach Neustart wieder verbunden werden kann.
const DB = "jarvis"
const STORE = "handles"

function idb<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest): Promise<T> {
  return new Promise((resolve, reject) => {
    const open = indexedDB.open(DB, 1)
    open.onupgradeneeded = () => open.result.createObjectStore(STORE)
    open.onerror = () => reject(open.error)
    open.onsuccess = () => {
      const req = fn(open.result.transaction(STORE, mode).objectStore(STORE))
      req.onsuccess = () => resolve(req.result as T)
      req.onerror = () => reject(req.error)
    }
  })
}

export async function pickFolder(): Promise<FileBackend> {
  const dir = (await window.showDirectoryPicker!({ id: "jarvis", mode: "readwrite" })) as unknown as DirHandle
  await idb("readwrite", (s) => s.put(dir, "dir")).catch(() => undefined)
  return folderBackend(dir)
}

/** Gespeicherten Ordner laden. needsPermission = Nutzer muss einmal klicken, um ihn freizugeben. */
export async function restoreFolder(): Promise<{ dir: DirHandle; ready: boolean } | null> {
  try {
    const dir = await idb<DirHandle | undefined>("readonly", (s) => s.get("dir"))
    if (!dir) return null
    return { dir, ready: (await dir.queryPermission({ mode: "readwrite" })) === "granted" }
  } catch {
    return null
  }
}

export async function reconnectFolder(dir: DirHandle): Promise<FileBackend | null> {
  return (await dir.requestPermission({ mode: "readwrite" })) === "granted" ? folderBackend(dir) : null
}

export function backendFor(dir: DirHandle) {
  return folderBackend(dir)
}

export async function forgetFolder() {
  await idb("readwrite", (s) => s.delete("dir")).catch(() => undefined)
}

export function downloadText(name: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }))
  const a = document.createElement("a")
  a.href = url
  a.download = name
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
