import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./jarvis.css"
import Jarvis from "./Jarvis"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Jarvis />
  </StrictMode>,
)
