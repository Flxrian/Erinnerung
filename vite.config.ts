import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { viteSingleFile } from "vite-plugin-singlefile"
import path from "node:path"

// `--mode single` erzeugt eine einzige HTML-Datei, die per Doppelklick ohne Server läuft.
export default defineConfig(({ mode }) => ({
  base: "./",
  plugins: [react(), tailwindcss(), ...(mode === "single" ? [viteSingleFile()] : [])],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "src") },
  },
  build: mode === "single" ? { outDir: "dist-single" } : {},
}))
