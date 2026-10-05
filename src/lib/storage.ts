import { useEffect, useState } from "react"

const PREFIX = "erinnerung:"

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? fallback : (JSON.parse(raw) as T)
  } catch {
    return fallback
  }
}

/** useState, dessen Wert in localStorage gespeichert wird und Reloads überlebt. */
export function usePersistentState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => read(key, initial))

  useEffect(() => {
    try {
      localStorage.setItem(PREFIX + key, JSON.stringify(value))
    } catch {
      // Speicher nicht verfügbar (z. B. privater Modus) – Daten bleiben nur im Speicher.
    }
  }, [key, value])

  return [value, setValue] as const
}

export const newId = () => crypto.randomUUID()
