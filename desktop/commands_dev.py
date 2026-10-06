"""
JARVIS – commands_dev.py (Desktop)
Coding-Fähigkeiten, sandboxed auf config.WORKSPACE_DIR.

Neu in der Desktop-Version:
  - edit_file (gezieltes Ersetzen einer Textstelle) und append_to_file,
    beide mit automatischem Backup
  - Protokoll liegt im Datenordner (%APPDATA%\\Jarvis)

Neu in v2:
  - delete_file verschiebt in einen _trash-Unterordner statt endgültig zu
    löschen (config.TRASH_INSTEAD_OF_DELETE)
  - write_file legt vor dem Überschreiben automatisch ein Backup an
  - create_folder, move_file als weitere Tools
  - Protokoll rotiert jetzt (wächst nicht mehr unbegrenzt)

SICHERHEIT (unverändert, nicht entfernen/umgehen):
  1. Alle Datei-Operationen sind auf config.WORKSPACE_DIR eingesperrt.
  2. Shell-Befehle laufen IMMER mit cwd=WORKSPACE_DIR und Timeout.
  3. Blockliste verhindert zerstörerische Befehle, unabhängig von einer
     Nutzer-Bestätigung.
  4. Jede Aktion wird protokolliert.
  5. Die "darf das wirklich ausgeführt werden?"-Bestätigung passiert in
     brain.py/server.py, bevor diese Funktionen überhaupt aufgerufen werden.
"""

import os
import re
import shutil
import logging
import subprocess
import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

import config

_LOG_PATH = config.ACTIONS_LOG_FILE

_logger = logging.getLogger("jarvis_actions")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = RotatingFileHandler(
        _LOG_PATH,
        maxBytes=getattr(config, "ACTIONS_LOG_MAX_BYTES", 2_000_000),
        backupCount=getattr(config, "ACTIONS_LOG_BACKUP_COUNT", 3),
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    _logger.addHandler(_handler)


def _log(action: str, detail: str, result: str = ""):
    try:
        msg = f"{action} | {detail}"
        if result:
            msg += f" -> {result[:500].strip()}"
        _logger.info(msg)
    except Exception:
        pass


class UnsafePathError(Exception):
    pass


def _workspace() -> Path:
    workspace = Path(config.WORKSPACE_DIR).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _resolve_in_workspace(rel_path: str) -> Path:
    workspace = _workspace()
    candidate = (workspace / rel_path).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError:
        raise UnsafePathError(
            f"Pfad '{rel_path}' liegt außerhalb des erlaubten Workspace-Ordners ({workspace}). Abgelehnt."
        )
    return candidate


# ---------------------------------------------------------------------
# Datei-Operationen
# ---------------------------------------------------------------------

def read_file(path: str) -> str:
    try:
        full = _resolve_in_workspace(path)
    except UnsafePathError as e:
        return f"ABGELEHNT: {e}"

    if not full.exists():
        return f"Datei nicht gefunden: {path}"
    if full.is_dir():
        return f"'{path}' ist ein Ordner, keine Datei."

    try:
        content = full.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Fehler beim Lesen: {e}"

    _log("read_file", path)
    max_chars = 12000
    if len(content) > max_chars:
        return content[:max_chars] + f"\n\n[... gekürzt, Datei hat {len(content)} Zeichen ...]"
    return content


def _backup(full: Path) -> str:
    """Kopiert eine bestehende Datei nach _backups/ und gibt einen Hinweis zurück."""
    if not getattr(config, "WRITE_FILE_BACKUP", True) or not full.exists():
        return ""
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_dir = _workspace() / "_backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{full.name}.{ts}.bak"
        shutil.copy2(full, backup_path)
        return f" (Backup der alten Version: _backups/{backup_path.name})"
    except Exception as e:
        return f" (Backup fehlgeschlagen: {e})"


def write_file(path: str, content: str) -> str:
    try:
        full = _resolve_in_workspace(path)
    except UnsafePathError as e:
        return f"ABGELEHNT: {e}"
    if full.is_dir():
        return f"'{path}' ist ein Ordner."

    backup_note = _backup(full)

    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
    except Exception as e:
        _log("write_file FEHLER", path, str(e))
        return f"Fehler beim Schreiben: {e}"

    _log("write_file", f"{path} ({len(content)} Zeichen)")
    return f"Datei geschrieben: {path} ({len(content)} Zeichen).{backup_note}"


def edit_file(path: str, old_text: str, new_text: str = "") -> str:
    try:
        full = _resolve_in_workspace(path)
    except UnsafePathError as e:
        return f"ABGELEHNT: {e}"
    if not full.is_file():
        return f"Datei nicht gefunden: {path}"
    if not old_text:
        return "old_text darf nicht leer sein."

    try:
        # newline="" erhält Windows-Zeilenenden (\r\n) unverändert
        with open(full, "r", encoding="utf-8", newline="") as f:
            content = f.read()
    except UnicodeDecodeError:
        return f"{path} ist keine Textdatei und kann nicht bearbeitet werden."

    count = content.count(old_text)
    if count == 0:
        # Häufiger Fall: andere Zeilenenden (Windows \r\n) als im Suchtext
        normalized = content.replace("\r\n", "\n")
        if normalized.count(old_text.replace("\r\n", "\n")) == 1 and "\r\n" in content:
            new = normalized.replace(old_text.replace("\r\n", "\n"), new_text.replace("\r\n", "\n"), 1)
            content_out = new.replace("\n", "\r\n")
        else:
            return "Die Textstelle kommt in der Datei nicht vor. Lies die Datei mit read_file und nimm den exakten Text."
    elif count > 1:
        return f"Die Textstelle kommt {count}-mal vor. Nimm einen längeren, eindeutigen Ausschnitt."
    else:
        content_out = content.replace(old_text, new_text, 1)

    note = _backup(full)
    try:
        full.write_text(content_out, encoding="utf-8", newline="")
    except Exception as e:
        _log("edit_file FEHLER", path, str(e))
        return f"Fehler beim Schreiben: {e}"
    _log("edit_file", f"{path}: {old_text[:80]!r} -> {new_text[:80]!r}")
    return f"Datei geändert: {path}.{note}"


def append_to_file(path: str, text: str) -> str:
    try:
        full = _resolve_in_workspace(path)
    except UnsafePathError as e:
        return f"ABGELEHNT: {e}"
    if full.is_dir():
        return f"'{path}' ist ein Ordner."

    existing = ""
    if full.exists():
        try:
            existing = full.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"{path} ist keine Textdatei."
    sep = "" if not existing or existing.endswith("\n") else "\n"
    note = _backup(full)
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "a", encoding="utf-8") as f:
            f.write(sep + text.rstrip("\n") + "\n")
    except Exception as e:
        _log("append_to_file FEHLER", path, str(e))
        return f"Fehler beim Schreiben: {e}"
    _log("append_to_file", f"{path} (+{len(text)} Zeichen)")
    return f"{'Ergänzt' if existing else 'Angelegt'}: {path}.{note}"


def delete_file(path: str) -> str:
    try:
        full = _resolve_in_workspace(path)
    except UnsafePathError as e:
        return f"ABGELEHNT: {e}"

    if not full.exists():
        return f"Datei nicht gefunden: {path}"
    if full.is_dir():
        return f"'{path}' ist ein Ordner. Aus Sicherheitsgründen werden nur einzelne Dateien gelöscht, keine Ordner."

    if getattr(config, "TRASH_INSTEAD_OF_DELETE", True):
        try:
            trash_dir = _workspace() / "_trash"
            trash_dir.mkdir(exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            trash_path = trash_dir / f"{ts}_{full.name}"
            shutil.move(str(full), str(trash_path))
        except Exception as e:
            _log("delete_file FEHLER", path, str(e))
            return f"Fehler beim Löschen: {e}"
        _log("delete_file (in Papierkorb verschoben)", path)
        return f"Datei in den Papierkorb verschoben: {path} (wiederherstellbar aus _trash/{trash_path.name})."

    try:
        full.unlink()
    except Exception as e:
        _log("delete_file FEHLER", path, str(e))
        return f"Fehler beim Löschen: {e}"
    _log("delete_file (endgültig)", path)
    return f"Datei endgültig gelöscht: {path}."


def list_dir(path: str = ".") -> str:
    try:
        full = _resolve_in_workspace(path)
    except UnsafePathError as e:
        return f"ABGELEHNT: {e}"

    if not full.exists():
        return f"Ordner nicht gefunden: {path}"
    if not full.is_dir():
        return f"'{path}' ist eine Datei, kein Ordner."

    entries = []
    for item in sorted(full.iterdir()):
        if item.name in ("_trash", "_backups"):
            continue
        kind = "📁" if item.is_dir() else "📄"
        entries.append(f"{kind} {item.name}")

    _log("list_dir", path)
    return "\n".join(entries) if entries else "(leerer Ordner)"


def create_folder(path: str) -> str:
    try:
        full = _resolve_in_workspace(path)
    except UnsafePathError as e:
        return f"ABGELEHNT: {e}"

    try:
        full.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"Fehler beim Anlegen: {e}"

    _log("create_folder", path)
    return f"Ordner angelegt: {path}."


def move_file(source: str, destination: str) -> str:
    try:
        src = _resolve_in_workspace(source)
        dst = _resolve_in_workspace(destination)
    except UnsafePathError as e:
        return f"ABGELEHNT: {e}"

    if not src.exists():
        return f"Quelle nicht gefunden: {source}"
    if dst.exists():
        return f"Ziel existiert bereits: {destination}. Erst umbenennen oder löschen."

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    except Exception as e:
        _log("move_file FEHLER", f"{source} -> {destination}", str(e))
        return f"Fehler beim Verschieben: {e}"

    _log("move_file", f"{source} -> {destination}")
    return f"Verschoben: {source} -> {destination}."


# ---------------------------------------------------------------------
# Shell-Befehle (sandboxed, mit Blockliste und Timeout)
# ---------------------------------------------------------------------

_BLOCKED_PATTERNS = [
    r"\brm\s+-rf\s+/", r"\brmdir\s+/s", r"\bdel\s+/[sf].*\*",
    r"\bformat\s+[a-zA-Z]:", r"\bdiskpart\b",
    r"\bshutdown\b", r"\brestart-computer\b",
    r":\(\)\s*{\s*:\s*\|\s*:\s*&\s*}\s*;\s*:",
    r"\breg\s+delete\b", r"\bregedit\b",
    r"\bnet\s+user\b", r"\bnetsh\b",
    r"\btaskkill\s+/f\s+/im\s+explorer",
    r">\s*/dev/sd", r"\bmkfs\b",
    r"\bwget\b.*\|\s*sh\b", r"\bcurl\b.*\|\s*sh\b",
    r"\bInvoke-WebRequest\b.*\|\s*iex\b",
]
_BLOCKED_RE = re.compile("|".join(_BLOCKED_PATTERNS), re.IGNORECASE)


def is_command_blocked(command: str) -> str | None:
    if _BLOCKED_RE.search(command):
        return "Befehl enthält ein als gefährlich eingestuftes Muster (z.B. Formatieren, rekursives Löschen, Shutdown, Registry-Änderung, Fork Bomb)."
    if len(command) > 2000:
        return "Befehl ist unplausibel lang."
    return None


def run_shell_command(command: str) -> str:
    blocked_reason = is_command_blocked(command)
    if blocked_reason:
        _log("run_shell_command BLOCKIERT", command, blocked_reason)
        return f"ABGELEHNT (Sicherheitsregel): {blocked_reason}"

    workspace = _workspace()
    _log("run_shell_command", command)

    try:
        result = subprocess.run(
            command, shell=True, cwd=str(workspace),
            capture_output=True, text=True,
            timeout=config.SHELL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"Befehl abgebrochen: Timeout nach {config.SHELL_TIMEOUT_SECONDS} Sekunden."
    except Exception as e:
        return f"Fehler beim Ausführen: {e}"

    output = (result.stdout or "") + (result.stderr or "")
    max_chars = 6000
    if len(output) > max_chars:
        output = output[:max_chars] + "\n[... gekürzt ...]"

    _log("run_shell_command Ergebnis", command, output)
    status = "erfolgreich" if result.returncode == 0 else f"Exit-Code {result.returncode}"
    return f"[{status}]\n{output.strip() or '(keine Ausgabe)'}"
