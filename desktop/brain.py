"""
JARVIS – brain.py (Desktop)
Verbindet Claude (Tool-Use) mit den PC-/Datei-Tools.

Gegenüber v2:
  - Einstellungen wirken sofort (API-Key, Modell, Coding an/aus)
  - eigener Gesprächsverlauf pro Gerät (vorher teilten sich alle Geräte
    eine Datei)
  - neue Datei-Tools edit_file und append_to_file für gezielte Änderungen
    per Sprache
  - eine unbeantwortete Bestätigung blockiert das Gespräch nicht mehr
  - Ablehnungen (refusal) und abgeschnittene Antworten werden sauber behandelt
"""

import json
import re
import threading

import anthropic

import commands
import commands_dev
import config

MODELS = {
    "claude-opus-5-5": "Claude Opus 5.5 – am klügsten",
    "claude-sonnet-5-5": "Claude Sonnet 5.5 – schnell und günstig",
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude-haiku-4-5": "Claude Haiku 4.5 – am schnellsten",
}

# Modelle, bei denen eine Ablehnung serverseitig automatisch an ein anderes
# Modell weitergereicht werden kann (statt einfach abzubrechen)
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
_NO_EFFORT_MODELS = {"claude-haiku-4-5"}

MAX_TOKENS = 16000
MAX_TOOL_ROUNDS = 12
MAX_HISTORY_MESSAGES = 60

BASE_PROMPT = """Du bist JARVIS, ein persönlicher KI-Assistent, der auf dem PC \
des Nutzers läuft – ähnlich wie Jarvis aus Iron Man. Du bist knapp, hilfreich, \
leicht trocken-humorvoll und sprichst IMMER auf Deutsch. Antworten sollen kurz \
und für Sprachausgabe geeignet sein (keine Emojis, keine Markdown-Formatierung, \
keine langen Listen – maximal 1-3 Sätze), außer der Nutzer verlangt explizit mehr Detail.

Wenn der Nutzer eine PC-Aktion verlangt (App öffnen, Lautstärke, Sperren, \
Herunterfahren, Screenshot, Ordner/Website öffnen, Websuche, Zeit/Datum, \
Erinnerung setzen), rufe das passende Tool auf statt nur darüber zu reden. \
Gib niemals vor, eine Aktion ausgeführt zu haben, die du nicht wirklich über \
ein Tool aufgerufen hast."""

CODING_PROMPT = """

Du kannst außerdem mit Dateien arbeiten und programmieren: Dateien lesen, \
anlegen, gezielt bearbeiten, ergänzen, verschieben, löschen, Ordner anlegen \
und Shell-Befehle ausführen – aber NUR innerhalb des Workspace-Ordners des \
Nutzers. Pfade sind immer relativ zu diesem Ordner.

Der Nutzer diktiert Inhalte und Änderungen oft per Sprache. Spracherkennung \
macht Fehler: korrigiere offensichtliche Erkennungsfehler, Groß-/Kleinschreibung \
und Satzzeichen, wenn du diktierten Text speicherst. Wenn er von "der Liste" \
oder "meinen Notizen" spricht, sieh mit list_dir nach, welche Datei gemeint ist. \
Für Änderungen an bestehenden Dateien liest du sie zuerst mit read_file und \
änderst dann gezielt mit edit_file oder append_to_file, statt sie mit \
write_file komplett neu zu schreiben. write_file, delete_file, move_file und \
run_shell_command muss der Nutzer bestätigen – kündige kurz an, was du vorhast. \
Schreibe sauberen, funktionierenden Code."""

TOOLS = [
    {"name": "open_app", "description": "Öffnet ein Programm auf dem PC anhand seines Namens.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "close_app", "description": "Beendet ein laufendes Programm anhand seines Namens.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "open_folder", "description": "Öffnet einen bekannten Ordner im Explorer (z.B. downloads, desktop, dokumente).",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "open_website", "description": "Öffnet eine Webseite im Standardbrowser.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "web_search", "description": "Sucht einen Begriff im Web und öffnet die Ergebnisse im Browser.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "set_volume", "description": "Setzt die Systemlautstärke auf einen exakten Prozentwert (0-100).",
     "input_schema": {"type": "object", "properties": {"percent": {"type": "integer"}}, "required": ["percent"]}},
    {"name": "volume_up", "description": "Erhöht die Systemlautstärke etwas.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "volume_down", "description": "Verringert die Systemlautstärke etwas.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "volume_mute", "description": "Schaltet den Ton stumm/an.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lock_pc", "description": "Sperrt den PC sofort.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "shutdown_pc", "description": "Fährt den PC nach einer Verzögerung herunter.",
     "input_schema": {"type": "object", "properties": {"delay_seconds": {"type": "integer"}}}},
    {"name": "restart_pc", "description": "Startet den PC nach einer Verzögerung neu.",
     "input_schema": {"type": "object", "properties": {"delay_seconds": {"type": "integer"}}}},
    {"name": "cancel_shutdown", "description": "Bricht ein laufendes Herunterfahren/Neustart ab.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "take_screenshot", "description": "Erstellt einen Screenshot und speichert ihn auf dem Desktop.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_time", "description": "Gibt die aktuelle Uhrzeit zurück.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_date", "description": "Gibt das aktuelle Datum zurück.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "set_reminder", "description": "Erinnert den Nutzer nach einer bestimmten Anzahl Minuten per Sprachausgabe an etwas.",
     "input_schema": {"type": "object", "properties": {
         "minutes": {"type": "number", "description": "In wie vielen Minuten erinnert werden soll"},
         "message": {"type": "string", "description": "Woran erinnert werden soll"},
     }, "required": ["minutes", "message"]}},
]

DEV_TOOLS = [
    {"name": "list_dir", "description": "Listet Dateien und Unterordner im Workspace-Ordner auf.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    {"name": "read_file", "description": "Liest den Inhalt einer Datei im Workspace-Ordner.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Legt eine Datei im Workspace-Ordner an oder überschreibt sie komplett. Erfordert Bestätigung. Für Änderungen an bestehenden Dateien edit_file oder append_to_file nutzen.",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Ersetzt in einer Datei eine exakt vorkommende Textstelle (old_text) durch neuen Text (new_text) – z.B. eine Zeile ändern, einen Eintrag streichen, ein Wort korrigieren. old_text muss genau einmal vorkommen; vorher mit read_file lesen. Zum Löschen einer Stelle new_text leer lassen. Legt automatisch ein Backup an.",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
         "required": ["path", "old_text", "new_text"]}},
    {"name": "append_to_file", "description": "Hängt Text in einer neuen Zeile ans Ende einer Datei an und legt sie an, falls sie fehlt. Ideal für Listen, Notizen, Tagebuch.",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string"}, "text": {"type": "string"}}, "required": ["path", "text"]}},
    {"name": "delete_file", "description": "Verschiebt eine Datei im Workspace-Ordner in den Papierkorb. Erfordert Bestätigung.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "create_folder", "description": "Legt einen neuen Ordner im Workspace-Ordner an.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "move_file", "description": "Verschiebt/benennt eine Datei innerhalb des Workspace-Ordners um. Erfordert Bestätigung.",
     "input_schema": {"type": "object", "properties": {
         "source": {"type": "string"}, "destination": {"type": "string"}}, "required": ["source", "destination"]}},
    {"name": "run_shell_command", "description": "Führt einen Shell-Befehl im Workspace-Ordner aus. Erfordert Bestätigung.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
]

DANGEROUS_TOOLS = {"write_file", "delete_file", "run_shell_command", "move_file"}

_FUNC_MAP = {name: getattr(commands, name) for name in [
    "open_app", "close_app", "open_folder", "open_website", "web_search",
    "set_volume", "volume_up", "volume_down", "volume_mute", "lock_pc",
    "shutdown_pc", "restart_pc", "cancel_shutdown", "take_screenshot",
    "get_time", "get_date", "set_reminder",
]}
_DEV_FUNC_MAP = {name: getattr(commands_dev, name) for name in [
    "list_dir", "read_file", "write_file", "edit_file", "append_to_file", "delete_file",
    "create_folder", "move_file", "run_shell_command",
]}


def _system_prompt() -> str:
    prompt = BASE_PROMPT
    if config.CODING_ENABLED:
        prompt += CODING_PROMPT
    if config.USER_NAME:
        prompt += f"\n\nDer Nutzer heißt {config.USER_NAME}. Sprich ihn gelegentlich mit Namen an."
    return prompt


def _tools() -> list:
    return TOOLS + DEV_TOOLS if config.CODING_ENABLED else TOOLS


def _describe_action(tool_name: str, tool_input: dict) -> str:
    if tool_name == "write_file":
        content = tool_input.get("content", "") or ""
        more = "..." if len(content) > 300 else ""
        return f"Datei schreiben: {tool_input.get('path')}\n\n---\n{content[:300]}{more}"
    if tool_name == "delete_file":
        return f"Datei in den Papierkorb verschieben: {tool_input.get('path')}"
    if tool_name == "move_file":
        return f"Verschieben: {tool_input.get('source')} -> {tool_input.get('destination')}"
    if tool_name == "run_shell_command":
        return f"Shell-Befehl ausführen:\n{tool_input.get('command')}"
    return f"{tool_name}: {tool_input}"


def spoken_confirmation(tool_name: str, tool_input: dict) -> str:
    """Kurze Frage zum Vorlesen, wenn per Sprache bestätigt werden soll."""
    if tool_name == "write_file":
        return f"Soll ich die Datei {tool_input.get('path')} speichern?"
    if tool_name == "delete_file":
        return f"Soll ich {tool_input.get('path')} in den Papierkorb verschieben?"
    if tool_name == "move_file":
        return f"Soll ich {tool_input.get('source')} nach {tool_input.get('destination')} verschieben?"
    if tool_name == "run_shell_command":
        return "Soll ich den angezeigten Befehl ausführen?"
    return "Soll ich das ausführen?"


class JarvisError(Exception):
    """str(e) ist bereits die freundliche, sprechbare Fehlermeldung."""


_client = None
_client_key = None
_client_lock = threading.Lock()


def _get_client() -> anthropic.Anthropic:
    global _client, _client_key
    with _client_lock:
        if not config.api_key_configured():
            raise JarvisError("Mir fehlt noch der API-Schlüssel. Bitte trag ihn in den Einstellungen ein.")
        if _client is None or _client_key != config.ANTHROPIC_API_KEY:
            _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            _client_key = config.ANTHROPIC_API_KEY
        return _client


def _safe_id(device_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", device_id or "default")[:64] or "default"


class Jarvis:
    def __init__(self, device_id: str = "default"):
        self.device_id = _safe_id(device_id)
        self.history: list = []
        self._pending = None
        self._plain_log: list = []
        self.lock = threading.RLock()
        self._load_persisted_history()

    # -- Persistenz -------------------------------------------------

    def _history_path(self):
        config.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        return config.HISTORY_DIR / f"{self.device_id}.json"

    def _context_from_log(self) -> list:
        """Die letzten Einträge der Mitschrift als Gesprächskontext."""
        context = [{"role": e["role"], "content": e["content"]} for e in self._plain_log[-16:]
                   if e.get("role") in ("user", "assistant") and e.get("content")]
        while context and context[0]["role"] != "user":
            context.pop(0)
        return context

    def _load_persisted_history(self):
        path = self._history_path()
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._plain_log = json.load(f)
            self.history = self._context_from_log()
        except Exception as e:
            print(f"[Jarvis] Konnte Gesprächsverlauf nicht laden: {e}")
            self._plain_log = []

    def _persist(self, role: str, text: str):
        if not text:
            return
        self._plain_log.append({"role": role, "content": text})
        self._plain_log = self._plain_log[-config.HISTORY_MAX_TURNS:]
        try:
            with open(self._history_path(), "w", encoding="utf-8") as f:
                json.dump(self._plain_log, f, ensure_ascii=False)
        except Exception as e:
            print(f"[Jarvis] Konnte Gesprächsverlauf nicht speichern: {e}")

    def transcript(self) -> list:
        return list(self._plain_log)

    def reset(self):
        with self.lock:
            self.history = []
            self._pending = None
            self._plain_log = []
            try:
                self._history_path().unlink(missing_ok=True)
            except Exception:
                pass

    # -- API --------------------------------------------------------

    def _call_api(self):
        model = config.MODEL
        kwargs = dict(
            model=model,
            max_tokens=MAX_TOKENS,
            system=_system_prompt(),
            tools=_tools(),
            messages=self.history,
        )
        if model not in _NO_EFFORT_MODELS:
            kwargs["output_config"] = {"effort": "medium"}
        try:
            client = _get_client()
            if model in _FALLBACK_MODELS:
                return client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
            return client.messages.create(**kwargs)
        except JarvisError:
            raise
        except anthropic.APIConnectionError:
            raise JarvisError("Ich habe gerade keine Verbindung zur KI. Prüf bitte deine Internetverbindung.")
        except anthropic.AuthenticationError:
            raise JarvisError("Mein API-Schlüssel scheint ungültig zu sein. Bitte in den Einstellungen prüfen.")
        except anthropic.PermissionDeniedError:
            raise JarvisError("Der API-Schlüssel hat keinen Zugriff auf dieses Modell. Wähl in den Einstellungen ein anderes.")
        except anthropic.NotFoundError:
            raise JarvisError("Das eingestellte Modell gibt es nicht. Bitte in den Einstellungen ein anderes wählen.")
        except anthropic.RateLimitError:
            raise JarvisError("Ich bin gerade an meinem Nutzungslimit. Versuch es in ein, zwei Minuten nochmal.")
        except anthropic.BadRequestError as e:
            if re.search(r"credit|balance|billing", str(e), re.I):
                raise JarvisError("Das API-Guthaben ist aufgebraucht. Bitte unter console.anthropic.com aufladen.")
            print(f"[Jarvis] Ungültige Anfrage: {e}")
            raise JarvisError("Die KI hat die Anfrage abgelehnt. Sag 'neues Gespräch', falls das wieder passiert.")
        except anthropic.APIStatusError as e:
            raise JarvisError(f"Die KI meldet gerade einen Fehler, Code {e.status_code}. Versuch es gleich nochmal.")

    def _execute_tool(self, name: str, tool_input: dict) -> str:
        func = _FUNC_MAP.get(name) or (_DEV_FUNC_MAP.get(name) if config.CODING_ENABLED else None)
        if not func:
            return f"Unbekanntes Tool: {name}"
        try:
            return str(func(**(tool_input or {})))
        except TypeError as e:
            return f"Falsche Parameter für {name}: {e}"
        except Exception as e:
            return f"Fehler bei Ausführung von {name}: {e}"

    def _confirm_request(self, block, remaining, results) -> dict:
        self._pending = {
            "tool_use_id": block.id, "tool_name": block.name, "tool_input": block.input,
            "remaining_blocks": remaining, "collected_results": results,
        }
        return {"type": "confirm", "id": block.id, "tool_name": block.name,
                "description": _describe_action(block.name, block.input),
                "question": spoken_confirmation(block.name, block.input)}

    def _run_blocks(self, blocks, results) -> dict | None:
        """Führt Tool-Aufrufe aus. Gibt eine Bestätigungsanfrage zurück, falls nötig."""
        for i, block in enumerate(blocks):
            if block.name in DANGEROUS_TOOLS:
                return self._confirm_request(block, blocks[i + 1:], results)
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": self._execute_tool(block.name, block.input)})
        return None

    def _loop(self, response) -> dict:
        spoken: list[str] = []  # Text aus allen Runden, z.B. "Mach ich." vor einem Tool-Aufruf
        for _ in range(MAX_TOOL_ROUNDS):
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            if text:
                spoken.append(text)
            text = " ".join(spoken)

            if response.stop_reason == "refusal":
                # Abgelehnte Antwort nicht in den Verlauf übernehmen.
                return {"type": "reply", "text": "Dabei kann ich leider nicht helfen."}

            tool_blocks = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason == "max_tokens" and tool_blocks:
                # Abgeschnittener Tool-Aufruf: nicht ausführen und nicht speichern.
                return {"type": "reply", "text": "Die Antwort wurde zu lang und ist abgebrochen. Formulier die Aufgabe bitte kleiner."}

            self.history.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use" or not tool_blocks:
                self._persist("assistant", text)
                return {"type": "reply", "text": text or "Erledigt."}

            results: list = []
            confirm = self._run_blocks(tool_blocks, results)
            if confirm:
                if text:
                    confirm["text"] = text
                return confirm
            spoken = [text] if text else []
            self.history.append({"role": "user", "content": results})
            response = self._call_api()

        return {"type": "reply", "text": "Das waren zu viele Schritte auf einmal. Ich habe aufgehört, sicherheitshalber."}

    def _abandon_pending(self) -> list:
        """Offene Bestätigung verwerfen: alle ausstehenden Tool-Aufrufe als nicht ausgeführt melden."""
        if not self._pending:
            return []
        p = self._pending
        self._pending = None
        skipped = "Nicht ausgeführt – der Nutzer hat nicht bestätigt und etwas anderes gesagt."
        results = p["collected_results"] + [{"type": "tool_result", "tool_use_id": p["tool_use_id"], "content": skipped}]
        results += [{"type": "tool_result", "tool_use_id": b.id, "content": skipped} for b in p["remaining_blocks"]]
        return results

    def _trim_history(self):
        if len(self.history) > MAX_HISTORY_MESSAGES:
            # Neu aufsetzen aus der Text-Mitschrift – schlanker Kontext, nichts Halbfertiges.
            self.history = self._context_from_log()

    # -- öffentliche API --------------------------------------------

    @property
    def pending(self) -> dict | None:
        return self._pending

    def process(self, user_text: str) -> dict:
        with self.lock:
            leftover = self._abandon_pending()
            if not leftover:
                self._trim_history()
            content = leftover + [{"type": "text", "text": user_text}] if leftover else user_text
            start = len(self.history)
            self.history.append({"role": "user", "content": content})
            self._persist("user", user_text)
            try:
                return self._loop(self._call_api())
            except JarvisError as e:
                self._rollback(start, leftover)
                return {"type": "reply", "text": str(e), "error": True}
            except Exception as e:
                print(f"[Jarvis] Unerwarteter Fehler in process(): {e!r}")
                self._rollback(start, leftover)
                return {"type": "reply", "text": "Da ist intern etwas schiefgelaufen. Versuch es bitte nochmal.", "error": True}

    def _rollback(self, start: int, leftover: list):
        """Nach einem Fehler den Verlauf in einen gültigen Zustand bringen."""
        del self.history[start:]
        if leftover:
            # Die verworfenen Tool-Ergebnisse müssen trotzdem beantwortet bleiben.
            self.history.append({"role": "user", "content": leftover})
            self.history.append({"role": "assistant", "content": "Verstanden, abgebrochen."})

    def resume(self, confirm_id: str, approved: bool) -> dict:
        with self.lock:
            if not self._pending or self._pending["tool_use_id"] != confirm_id:
                return {"type": "reply", "text": "Diese Bestätigung ist nicht mehr aktuell."}

            p = self._pending
            self._pending = None
            result = (self._execute_tool(p["tool_name"], p["tool_input"]) if approved
                      else "Vom Nutzer abgelehnt. Aktion wurde NICHT ausgeführt.")
            results = p["collected_results"] + [{"type": "tool_result", "tool_use_id": p["tool_use_id"], "content": result}]

            try:
                confirm = self._run_blocks(p["remaining_blocks"], results)
                if confirm:
                    return confirm
                self.history.append({"role": "user", "content": results})
                return self._loop(self._call_api())
            except JarvisError as e:
                return {"type": "reply", "text": str(e), "error": True}
            except Exception as e:
                print(f"[Jarvis] Unerwarteter Fehler in resume(): {e!r}")
                return {"type": "reply", "text": "Da ist intern etwas schiefgelaufen. Versuch es bitte nochmal.", "error": True}
