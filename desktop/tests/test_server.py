import pytest

import config
import server
import sessions


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "PHONE_ACCESS", False)
    monkeypatch.setattr(config, "APP_TOKEN", "")
    server._failed_attempts.clear()
    return server.app.test_client()


def desktop_headers():
    return {"X-Jarvis-Token": server.LOCAL_TOKEN}


def test_health_is_public(client):
    data = client.get("/api/health").get_json()
    assert data["app"] == "jarvis" and data["auth_required"] is False


def test_desktop_token_works_only_from_loopback(client, monkeypatch):
    monkeypatch.setattr(sessions.get(sessions.DESKTOP), "process", lambda t: {"type": "reply", "text": "ok"})
    r = client.post("/api/chat", json={"message": "hi"}, headers=desktop_headers())
    assert r.get_json() == {"type": "reply", "text": "ok"}
    r = client.post("/api/chat", json={"message": "hi"}, headers=desktop_headers(),
                    environ_base={"REMOTE_ADDR": "192.168.1.20"})
    assert r.status_code == 403  # Handy-Zugriff aus


def test_phone_needs_password_and_locks_out(client, monkeypatch):
    monkeypatch.setattr(config, "PHONE_ACCESS", True)
    monkeypatch.setattr(config, "APP_TOKEN", "richtig-geheim")
    phone = {"REMOTE_ADDR": "192.168.1.30"}
    ok = client.post("/api/login", headers={"X-Jarvis-Token": "richtig-geheim"}, environ_base=phone)
    assert ok.get_json() == {"ok": True, "desktop": False}
    for _ in range(config.MAX_FAILED_LOGIN_ATTEMPTS):
        assert client.post("/api/login", headers={"X-Jarvis-Token": "falsch"}, environ_base=phone).status_code == 401
    assert client.post("/api/login", headers={"X-Jarvis-Token": "richtig-geheim"}, environ_base=phone).status_code == 429


def test_internet_requests_are_blocked(client):
    r = client.get("/api/health", environ_base={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403


def test_phone_cannot_use_desktop_session(client, monkeypatch):
    monkeypatch.setattr(config, "PHONE_ACCESS", True)
    monkeypatch.setattr(config, "APP_TOKEN", "richtig-geheim")
    seen = []
    monkeypatch.setattr(sessions, "get", lambda d: seen.append(d) or type("J", (), {"transcript": lambda self: []})())
    client.get("/api/history", headers={"X-Jarvis-Token": "richtig-geheim", "X-Device-Id": "desktop"},
               environ_base={"REMOTE_ADDR": "192.168.1.30"})
    assert seen == ["phone-desktop"]


def test_settings_are_desktop_only_and_hide_secrets(client, monkeypatch):
    assert client.get("/api/settings").status_code == 403
    r = client.post("/api/settings", headers=desktop_headers(),
                    json={"ANTHROPIC_API_KEY": "sk-ant-neu", "USER_NAME": "Tony", "TTS_RATE": "200",
                          "BEEP_ENABLED": False, "UNBEKANNT": 1})
    data = r.get_json()["settings"]
    assert data["ANTHROPIC_API_KEY"] == "" and data["ANTHROPIC_API_KEY__set"] is True
    assert data["USER_NAME"] == "Tony" and data["TTS_RATE"] == 200 and data["BEEP_ENABLED"] is False
    assert config.ANTHROPIC_API_KEY == "sk-ant-neu"
    # Leeres Geheimnis = behalten
    client.post("/api/settings", headers=desktop_headers(), json={"ANTHROPIC_API_KEY": ""})
    assert config.ANTHROPIC_API_KEY == "sk-ant-neu"
    assert "UNBEKANNT" not in config.SETTINGS_FILE.read_text()


def test_events_keep_numeric_ids():
    import events
    with pytest.raises(ValueError):
        events.publish("confirm_done", id="toolu_1")
    e = events.publish("confirm_done", confirm_id="toolu_1")
    assert isinstance(e["id"], int) and events.since(e["id"] - 1)[-1]["confirm_id"] == "toolu_1"
