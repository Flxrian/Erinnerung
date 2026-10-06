import commands
import commands_dev


def test_paths_outside_workspace_are_rejected(workspace):
    assert commands_dev.read_file("../geheim.txt").startswith("ABGELEHNT")
    assert commands_dev.append_to_file("../../x.txt", "hi").startswith("ABGELEHNT")


def test_edit_file_keeps_windows_line_endings(workspace):
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "liste.txt").write_bytes(b"Milch\r\nBrot\r\nEier\r\n")
    assert commands_dev.edit_file("liste.txt", "Brot\nEier", "Toast\nEier").startswith("Datei geändert")
    assert (workspace / "liste.txt").read_bytes() == b"Milch\r\nToast\r\nEier\r\n"


def test_edit_file_errors_are_helpful(workspace):
    commands_dev.append_to_file("a.txt", "eins\neins")
    assert "2-mal" in commands_dev.edit_file("a.txt", "eins", "zwei")
    assert "nicht vor" in commands_dev.edit_file("a.txt", "drei", "vier")
    assert "nicht gefunden" in commands_dev.edit_file("fehlt.txt", "x", "y")


def test_move_does_not_overwrite(workspace):
    commands_dev.append_to_file("a.txt", "A")
    commands_dev.append_to_file("b.txt", "B")
    assert "existiert bereits" in commands_dev.move_file("a.txt", "b.txt")


def test_delete_goes_to_trash(workspace):
    commands_dev.append_to_file("weg.txt", "x")
    assert "Papierkorb" in commands_dev.delete_file("weg.txt")
    assert not (workspace / "weg.txt").exists()
    assert len(list((workspace / "_trash").iterdir())) == 1


def test_blocked_shell_commands():
    assert commands_dev.run_shell_command("format C:").startswith("ABGELEHNT")
    assert commands_dev.run_shell_command("shutdown /s /t 0").startswith("ABGELEHNT")


def test_open_app_never_uses_shell(monkeypatch):
    calls = []
    monkeypatch.setattr(commands.subprocess, "Popen", lambda *a, **k: calls.append((a, k)))
    assert "kenne" in commands.open_app("calc & del C:\\x")
    assert calls == []


def test_web_search_escapes_query(monkeypatch):
    opened = []
    monkeypatch.setattr(commands.webbrowser, "open", opened.append)
    commands.web_search("C++ & Rust?")
    assert opened == ["https://www.google.com/search?q=C%2B%2B+%26+Rust%3F"]


def test_open_website_only_http(monkeypatch):
    opened = []
    monkeypatch.setattr(commands.webbrowser, "open", opened.append)
    assert "nur Webseiten" in commands.open_website("file:///C:/Windows")
    commands.open_website("youtube.com")
    assert opened == ["https://youtube.com"]
