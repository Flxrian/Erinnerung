"""
JARVIS – server.py (Desktop)
Webserver für das Programmfenster und (optional) das Handy im WLAN.

  - Programmfenster: nur über 127.0.0.1, mit einem bei jedem Start neu
    erzeugten Schlüssel – kein Passwort nötig.
  - Handy: über das WLAN, mit Passwort (APP_TOKEN), HTTPS und Sperre nach
    zu vielen Fehlversuchen. Nur aktiv, wenn in den Einstellungen erlaubt.

Kann weiterhin allein gestartet werden:  python server.py
"""

import hmac
import ipaddress
import os
import secrets
import socket
import threading
import time
from collections import defaultdict
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.serving import make_server

import config
import events
import sessions

LOCAL_TOKEN = secrets.token_urlsafe(24)

app = Flask(__name__, static_folder=str(config.STATIC_DIR), static_url_path="")
app.json.ensure_ascii = False

# Werden vom Desktop-Programm gesetzt: Fenster nach vorne holen / beenden
on_show_window = None
on_quit = None

# ---------------------------------------------------------------------
# Sicherheit
# ---------------------------------------------------------------------

_failed_attempts: dict[str, list] = defaultdict(list)


def _is_loopback() -> bool:
    if request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP"):
        return False
    try:
        return ipaddress.ip_address(request.remote_addr or "").is_loopback
    except ValueError:
        return False


def _is_private() -> bool:
    if request.headers.get("X-Forwarded-For") or request.headers.get("X-Real-IP"):
        return False
    try:
        addr = ipaddress.ip_address(request.remote_addr or "")
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback


def _phone_token_configured() -> bool:
    return bool(config.PHONE_ACCESS and config.APP_TOKEN and config.APP_TOKEN != "dein-geheimes-passwort-hier")


def _is_locked_out(ip: str) -> bool:
    now = time.time()
    _failed_attempts[ip] = [t for t in _failed_attempts[ip] if now - t < config.LOGIN_LOCKOUT_SECONDS]
    return len(_failed_attempts[ip]) >= config.MAX_FAILED_LOGIN_ATTEMPTS


def _is_desktop() -> bool:
    """Anfrage kommt vom Programmfenster auf diesem PC."""
    sent = request.headers.get("X-Jarvis-Token", "")
    return _is_loopback() and hmac.compare_digest(sent, LOCAL_TOKEN)


def require_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _is_desktop():
            return f(*args, **kwargs)

        ip = request.remote_addr or "unknown"
        if _is_locked_out(ip):
            return jsonify({"error": f"Zu viele Fehlversuche. Bitte warte {config.LOGIN_LOCKOUT_SECONDS // 60} Minuten."}), 429
        if not _phone_token_configured():
            return jsonify({"error": "Handy-Zugriff ist am PC nicht eingeschaltet (Einstellungen → Handy)."}), 403

        sent = request.headers.get("X-Jarvis-Token", "")
        if not hmac.compare_digest(sent, config.APP_TOKEN):
            _failed_attempts[ip].append(time.time())
            return jsonify({"error": "Falsches Passwort."}), 401
        return f(*args, **kwargs)
    return wrapper


def desktop_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _is_desktop():
            return jsonify({"error": "Nur im Programm auf dem PC verfügbar."}), 403
        return f(*args, **kwargs)
    return wrapper


@app.before_request
def _restrict_to_lan():
    if config.RESTRICT_TO_LAN and not _is_private():
        return jsonify({"error": "Zugriff verweigert: Jarvis ist nur aus dem eigenen WLAN erreichbar."}), 403


@app.after_request
def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


def _device_id() -> str:
    if _is_desktop():
        return sessions.DESKTOP
    device = request.headers.get("X-Device-Id", "default")
    # Handys dürfen nicht in das Desktop-Gespräch schreiben
    return "phone-" + device if device == sessions.DESKTOP else device


# ---------------------------------------------------------------------
# Routen: Gespräch (Fenster und Handy)
# ---------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "app": "jarvis",
        "version": config.VERSION,
        "auth_required": not _is_loopback(),
        "phone_access": _phone_token_configured(),
        "api_key": config.api_key_configured(),
    })


@app.route("/api/login", methods=["POST"])
@require_token
def login():
    return jsonify({"ok": True, "desktop": _is_desktop()})


@app.route("/api/history")
@require_token
def history():
    return jsonify({"messages": sessions.get(_device_id()).transcript()[-60:]})


def _speak_if_desktop(result: dict):
    data = request.get_json(silent=True, force=True) or {}
    if _is_desktop() and data.get("speak") and result.get("type") == "reply":
        import voice
        voice.say_async(result.get("text", ""))


@app.route("/api/chat", methods=["POST"])
@require_token
def chat():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("message") or "").strip()
    if not text:
        return jsonify({"error": "Kein Text übermittelt."}), 400
    if len(text) > 20_000:
        return jsonify({"error": "Nachricht ist zu lang."}), 400

    desktop = _is_desktop()
    if desktop:
        import voice
        voice.stop_speaking()
        events.publish("status", state="thinking")
    try:
        result = sessions.get(_device_id()).process(text)
    finally:
        if desktop:
            events.publish("status", state="idle")
    _speak_if_desktop(result)
    return jsonify(result)


@app.route("/api/confirm", methods=["POST"])
@require_token
def confirm():
    data = request.get_json(force=True, silent=True) or {}
    confirm_id = data.get("id", "")
    if not confirm_id:
        return jsonify({"error": "Keine Bestätigungs-ID übermittelt."}), 400

    desktop = _is_desktop()
    if desktop:
        events.publish("confirm_done", confirm_id=confirm_id)
        events.publish("status", state="thinking")
    try:
        result = sessions.get(_device_id()).resume(confirm_id, bool(data.get("approved")))
    finally:
        if desktop:
            events.publish("status", state="idle")
    _speak_if_desktop(result)
    return jsonify(result)


@app.route("/api/reset", methods=["POST"])
@require_token
def reset():
    sessions.get(_device_id()).reset()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------
# Routen: nur Programmfenster
# ---------------------------------------------------------------------

@app.route("/api/events")
@desktop_only
def get_events():
    after = int(request.args.get("after", 0))
    wait = min(float(request.args.get("wait", 0)), 25)
    return jsonify({"events": events.since(after, wait), "latest": events.latest_id()})


@app.route("/api/voice/activate", methods=["POST"])
@desktop_only
def voice_activate():
    import voice
    voice.activate()
    return jsonify({"ok": True})


@app.route("/api/voice/stop", methods=["POST"])
@desktop_only
def voice_stop():
    import voice
    voice.stop_speaking()
    return jsonify({"ok": True})


@app.route("/api/voice/test", methods=["POST"])
@desktop_only
def voice_test():
    import voice
    name = f", {config.USER_NAME}" if config.USER_NAME else ""
    voice.say_async(f"Guten Tag{name}. Ich bin Jarvis, Ihr persönlicher Assistent. So klinge ich mit den aktuellen Einstellungen.")
    return jsonify({"ok": True})


@app.route("/api/meta")
@desktop_only
def meta():
    import autostart
    import brain
    return jsonify({
        "version": config.VERSION,
        "models": brain.MODELS,
        "data_dir": str(config.DATA_DIR),
        "lan_url": lan_url(),
        "lan_running": _lan_server is not None,
        "autostart": autostart.is_enabled(),
        "autostart_supported": autostart.supported(),
        "continuous": __import__("voice").is_listening_continuously(),
    })


@app.route("/api/settings", methods=["GET", "POST"])
@desktop_only
def settings():
    if request.method == "GET":
        return jsonify(config.public())

    data = request.get_json(force=True, silent=True) or {}
    try:
        config.save(data)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Ungültige Einstellung: {e}"}), 400
    apply_runtime_settings()
    return jsonify({"ok": True, "settings": config.public(), "lan_url": lan_url(), "lan_running": _lan_server is not None})


@app.route("/api/autostart", methods=["POST"])
@desktop_only
def set_autostart():
    import autostart
    enabled = bool((request.get_json(force=True, silent=True) or {}).get("enabled"))
    try:
        autostart.set_enabled(enabled)
    except Exception as e:
        return jsonify({"error": f"Autostart konnte nicht geändert werden: {e}"}), 500
    return jsonify({"ok": True, "autostart": autostart.is_enabled()})


@app.route("/api/open_folder", methods=["POST"])
@desktop_only
def open_folder():
    which = (request.get_json(force=True, silent=True) or {}).get("which")
    path = {"workspace": config.WORKSPACE_DIR, "data": str(config.DATA_DIR)}.get(which)
    if not path:
        return jsonify({"error": "Unbekannter Ordner."}), 400
    os.makedirs(path, exist_ok=True)
    if config.IS_WINDOWS:
        os.startfile(path)
    return jsonify({"ok": True, "path": path})


def _local_control() -> bool:
    # Eigener Header erzwingt bei Browsern einen CORS-Preflight – fremde Webseiten
    # können diese Routen daher nicht auslösen, nur Programme auf diesem PC.
    return _is_loopback() and request.headers.get("X-Jarvis-Local") == "1"


@app.route("/api/show", methods=["POST"])
def show():
    # Zweiter Programmstart meldet sich hier: Fenster nach vorne holen.
    if not _local_control():
        return jsonify({"error": "Nur lokal."}), 403
    if on_show_window:
        on_show_window()
    return jsonify({"ok": True})


@app.route("/api/quit", methods=["POST"])
def quit_app():
    # Für den Deinstaller/Updater: Jarvis sauber beenden.
    if not _local_control():
        return jsonify({"error": "Nur lokal."}), 403
    if on_quit:
        threading.Timer(0.3, on_quit).start()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------
# Server starten/stoppen
# ---------------------------------------------------------------------

class _ServerThread(threading.Thread):
    def __init__(self, host: str, port: int, ssl_context=None):
        super().__init__(daemon=True, name=f"jarvis-http-{port}")
        self.server = make_server(host, port, app, threaded=True, ssl_context=ssl_context)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


_local_server: _ServerThread | None = None
_lan_server: _ServerThread | None = None
_lan_scheme = "http"


def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def lan_url() -> str:
    return f"{_lan_scheme}://{get_lan_ip()}:{config.PORT}" if _lan_server else ""


def local_url() -> str:
    return f"http://127.0.0.1:{config.LOCAL_PORT}/#token={LOCAL_TOKEN}"


def start_local():
    """Startet den Server für das Programmfenster. Wirft OSError, wenn der Port belegt ist."""
    global _local_server
    _local_server = _ServerThread("127.0.0.1", config.LOCAL_PORT)
    _local_server.start()


def apply_phone_settings():
    """Startet/stoppt den WLAN-Server passend zu den Einstellungen."""
    global _lan_server, _lan_scheme
    if _lan_server:
        _lan_server.shutdown()
        _lan_server = None
    if not _phone_token_configured():
        return

    ssl_ctx = None
    if config.HTTPS_ENABLED:
        import certs
        try:
            ssl_ctx = certs.ensure()
        except Exception as e:
            print(f"[Server] HTTPS-Zertifikat konnte nicht erzeugt werden ({e}) – nutze HTTP.")
    try:
        _lan_server = _ServerThread("0.0.0.0", config.PORT, ssl_ctx)
    except OSError as e:
        events.publish("info", f"Handy-Zugriff: Port {config.PORT} ist belegt ({e}).")
        return
    _lan_scheme = "https" if ssl_ctx else "http"
    _lan_server.start()
    print(f"[Server] Handy-Zugriff: {lan_url()}")


def apply_runtime_settings():
    import voice
    apply_phone_settings()
    voice.apply_settings()
    if on_settings_changed:
        on_settings_changed()


# Wird vom Desktop-Programm gesetzt (z.B. Hotkey neu registrieren)
on_settings_changed = None


if __name__ == "__main__":
    # Reiner Server-Modus ohne Fenster (wie in v2)
    if not _phone_token_configured():
        print("Handy-Zugriff ist aus. Starte das Programm und schalte ihn unter Einstellungen → Handy ein,")
        print(f"oder trage PHONE_ACCESS und APP_TOKEN in {config.SETTINGS_FILE} ein.")
        raise SystemExit(1)
    apply_phone_settings()
    print("=" * 55)
    print(" JARVIS Server läuft.")
    print(f" Im WLAN öffnen:  {lan_url()}")
    print(" Zum Beenden: Strg+C")
    print("=" * 55)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
