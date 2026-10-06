from types import SimpleNamespace as NS

import anthropic
import httpx2 as httpx
import pytest

import brain
import config


def text(t):
    return NS(type="text", text=t)


def tool(id_, name, **inp):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def response(*blocks, stop=None):
    if stop is None:
        stop = "tool_use" if any(b.type == "tool_use" for b in blocks) else "end_turn"
    return NS(content=list(blocks), stop_reason=stop)


class FakeClient:
    """Liefert vorbereitete Antworten und merkt sich jede Anfrage."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = NS(create=self._create)
        self.beta = NS(messages=NS(create=self._create_beta))

    def _create(self, **kwargs):
        self.calls.append(("std", kwargs))
        return self._next(kwargs)

    def _create_beta(self, **kwargs):
        self.calls.append(("beta", kwargs))
        return self._next(kwargs)

    def _next(self, kwargs):
        # Schnappschuss der Nachrichten, da die Liste danach weiter wächst
        kwargs["messages"] = list(kwargs["messages"])
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def fake(monkeypatch):
    holder = {}

    def install(*responses):
        client = FakeClient(*responses)
        monkeypatch.setattr(brain, "_get_client", lambda: client)
        holder["client"] = client
        return client
    return install


def assert_valid_history(history):
    """Jeder tool_use muss im direkt folgenden user-Turn ein tool_result haben."""
    for i, msg in enumerate(history):
        if msg["role"] != "assistant" or isinstance(msg["content"], str):
            continue
        ids = {b.id for b in msg["content"] if getattr(b, "type", None) == "tool_use"}
        if not ids:
            continue
        nxt = history[i + 1]
        assert nxt["role"] == "user"
        got = {b["tool_use_id"] for b in nxt["content"] if isinstance(b, dict) and b.get("type") == "tool_result"}
        assert ids <= got, f"Unbeantwortete Tool-Aufrufe {ids - got}"


def test_simple_reply_is_persisted(fake):
    fake(response(text("Es ist schön hier.")))
    j = brain.Jarvis("t1")
    assert j.process("Hallo") == {"type": "reply", "text": "Es ist schön hier."}
    assert [e["role"] for e in j.transcript()] == ["user", "assistant"]
    # Verlauf übersteht einen Neustart
    assert brain.Jarvis("t1").history[0]["content"] == "Hallo"


def test_file_dictation_append_then_edit(fake, workspace):
    client = fake(
        response(text("Mach ich."), tool("a", "append_to_file", path="Einkauf.txt", text="Milch\nBrot")),
        response(text("Notiert.")),
        response(tool("b", "read_file", path="Einkauf.txt")),
        response(tool("c", "edit_file", path="Einkauf.txt", old_text="Brot", new_text="Vollkornbrot"),
                 tool("d", "append_to_file", path="Einkauf.txt", text="Butter")),
        response(text("Erledigt.")),
    )
    j = brain.Jarvis("t2")
    assert j.process("Schreib Milch und Brot auf die Einkaufsliste")["text"] == "Mach ich. Notiert."
    assert j.process("Ersetz Brot durch Vollkornbrot und füg Butter hinzu")["text"] == "Erledigt."
    assert (workspace / "Einkauf.txt").read_text(encoding="utf-8") == "Milch\nVollkornbrot\nButter\n"
    # Beide parallelen Tool-Ergebnisse in EINER user-Nachricht
    last_user = client.calls[-1][1]["messages"][-1]
    assert [b["tool_use_id"] for b in last_user["content"]] == ["c", "d"]
    assert_valid_history(j.history)
    # Backups wurden angelegt
    assert any((workspace / "_backups").iterdir())


def test_dangerous_tool_needs_confirmation(fake, workspace):
    fake(
        response(text("Ich lege die Datei an."), tool("w", "write_file", path="hallo.py", content="print('hi')\n")),
        response(text("Fertig.")),
    )
    j = brain.Jarvis("t3")
    result = j.process("Schreib ein Hallo-Welt-Programm")
    assert result["type"] == "confirm" and result["tool_name"] == "write_file"
    assert "hallo.py" in result["question"]
    assert not (workspace / "hallo.py").exists()
    assert j.resume(result["id"], True)["text"] == "Fertig."
    assert (workspace / "hallo.py").read_text() == "print('hi')\n"
    assert_valid_history(j.history)


def test_unanswered_confirmation_does_not_break_conversation(fake, workspace):
    client = fake(
        response(tool("x", "run_shell_command", command="dir"), tool("y", "list_dir")),
        response(text("Okay, dann eben nicht.")),
    )
    j = brain.Jarvis("t4")
    assert j.process("Zeig mir die Dateien per Shell")["type"] == "confirm"
    # Nutzer sagt etwas anderes statt zu bestätigen
    assert j.process("Vergiss es")["text"] == "Okay, dann eben nicht."
    user_msg = client.calls[-1][1]["messages"][-1]
    ids = [b.get("tool_use_id") for b in user_msg["content"] if b.get("type") == "tool_result"]
    assert ids == ["x", "y"]
    assert user_msg["content"][-1] == {"type": "text", "text": "Vergiss es"}
    assert j.pending is None
    assert_valid_history(j.history)


def test_refusal_is_not_added_to_history(fake):
    fake(response(text(""), stop="refusal"))
    j = brain.Jarvis("t5")
    assert j.process("…")["text"] == "Dabei kann ich leider nicht helfen."
    assert all(m["role"] == "user" for m in j.history)


def test_api_error_rolls_back(fake):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    fake(anthropic.AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None))
    j = brain.Jarvis("t6")
    result = j.process("Hallo")
    assert result["error"] and "API-Schlüssel" in result["text"]
    assert j.history == []


def test_fallback_models_use_server_side_fallback(fake, monkeypatch):
    monkeypatch.setattr(config, "MODEL", "claude-opus-5-5")
    client = fake(response(text("Hi")))
    brain.Jarvis("t7").process("Hallo")
    kind, kwargs = client.calls[0]
    assert kind == "beta" and kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]
    assert kwargs["output_config"] == {"effort": "medium"}


def test_coding_disabled_hides_file_tools(fake, monkeypatch):
    monkeypatch.setattr(config, "CODING_ENABLED", False)
    client = fake(response(text("Hi")))
    brain.Jarvis("t8").process("Hallo")
    names = {t["name"] for t in client.calls[0][1]["tools"]}
    assert "write_file" not in names and "open_app" in names


def test_missing_key_gives_friendly_message(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    result = brain.Jarvis("t9").process("Hallo")
    assert "API-Schlüssel" in result["text"]
