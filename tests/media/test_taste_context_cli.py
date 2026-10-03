from __future__ import annotations

import json
from pathlib import Path

from media.cli import main
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo


def test_taste_context_cli_emits_json_without_writes(tmp_path, monkeypatch, capsys):
    root = copy_fixture_repo(tmp_path)
    rebuild_generated(root / "media")
    request = root / "taste.json"
    request.write_text(json.dumps({
        "schema_version":1,
        "operation":"taste_context",
        "target":"primary",
        "recent_limit":2,
        "representative_limit":2,
    }), encoding="utf-8")
    before = {str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
    monkeypatch.chdir(root)
    assert main(["taste-context","--request",str(request),"--format","json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["target"] == "primary"
    assert "profile" in result
    after = {str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert after == before
