import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { viteSingleFile } from "vite-plugin-singlefile"
import path from "node:path"

const pages = {
  main: path.resolve(import.meta.dirname, "index.html"),
  jarvis: path.resolve(import.meta.dirname, "app-jarvis.html"),
}

// `--mode single` erzeugt pro Seite eine einzige HTML-Datei, die per Doppelklick ohne Server läuft.
// Welche Seite, bestimmt die Umgebungsvariable PAGE (main oder jarvis).
export default defineConfig(({ mode }) => {
  const single = mode === "single"
  const page = (process.env.PAGE ?? "main") as keyof typeof pages
  return {
    base: "./",
    plugins: [react(), tailwindcss(), ...(single ? [viteSingleFile()] : [])],
    resolve: {
      alias: { "@": path.resolve(import.meta.dirname, "src") },
    },
    build: single
      ? { outDir: `dist-single/${page}`, rollupOptions: { input: pages[page] } }
      : { rollupOptions: { input: pages } },
  }
})
