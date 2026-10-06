// Baut Erinnerung.html und Jarvis.html als eigenständige Dateien ins Projektverzeichnis.
import { execSync } from "node:child_process"
import { copyFileSync } from "node:fs"

const targets = { main: ["index.html", "Erinnerung.html"], jarvis: ["app-jarvis.html", "Jarvis.html"] }

for (const [page, [built, out]] of Object.entries(targets)) {
  execSync("npx vite build --mode single", { stdio: "inherit", env: { ...process.env, PAGE: page } })
  copyFileSync(`dist-single/${page}/${built}`, out)
  console.log(`→ ${out}`)
}
