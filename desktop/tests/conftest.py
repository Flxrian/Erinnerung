import os
import sys
import tempfile
from pathlib import Path

# Eigener Datenordner pro Testlauf – nie die echten Einstellungen anfassen.
_tmp = tempfile.mkdtemp(prefix="jarvis-test-")
os.environ["JARVIS_DATA_DIR"] = _tmp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

import config  # noqa: E402


@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    monkeypatch.setattr(config, "WORKSPACE_DIR", str(ws))
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(config, "CODING_ENABLED", True)
    monkeypatch.setattr(config, "MODEL", "claude-sonnet-4-6")
    monkeypatch.setattr(config, "HISTORY_DIR", tmp_path / "history")
    return ws
