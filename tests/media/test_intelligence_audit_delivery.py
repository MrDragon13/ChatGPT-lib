from __future__ import annotations

import json
from pathlib import Path

from media.tools import audit_intelligence
from tests.media.fixture_repo import copy_fixture_repo


def test_audit_cli_json_is_deterministic(tmp_path, capsys):
    root = copy_fixture_repo(tmp_path)

    assert audit_intelligence.main([str(root), "--format", "json"]) == 0
    first = capsys.readouterr().out
    assert audit_intelligence.main([str(root), "--format", "json"]) == 0
    second = capsys.readouterr().out

    assert first == second
    payload = json.loads(first)
    assert payload["schema_version"] == 2
    assert "generated_at" not in payload
    assert "source_revision" not in payload


def test_write_baseline_separates_deterministic_payload_and_provenance(tmp_path, capsys):
    root = copy_fixture_repo(tmp_path)
    output = root / "media/baselines/intelligence-stage-a.json"

    assert audit_intelligence.main(
        [
            str(root),
            "--write-baseline",
            str(output),
            "--source-revision",
            "abc123",
            "--generated-at",
            "2026-10-04T12:00:00Z",
        ]
    ) == 0
    capsys.readouterr()

    meta_path = output.with_suffix(".meta.json")
    assert output.exists()
    assert meta_path.exists()

    payload = json.loads(output.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "generated_at" not in payload
    assert "source_revision" not in payload
    assert meta == {
        "baseline": output.name,
        "canonical_input_digest": payload["canonical_input_digest"],
        "generated_at": "2026-10-04T12:00:00Z",
        "payload_schema_version": payload["schema_version"],
        "source_revision": "abc123",
    }


def test_baseline_writer_uses_exact_meta_suffix(tmp_path):
    root = copy_fixture_repo(tmp_path)
    output = root / "media/baselines/example.json"

    audit_intelligence.main(
        [
            str(root),
            "--write-baseline",
            str(output),
            "--source-revision",
            "deadbeef",
            "--generated-at",
            "2026-10-04T12:00:00Z",
        ]
    )

    assert output.with_suffix(".meta.json").exists()
    assert not Path(str(output) + ".meta.json").exists()


def test_living_docs_expose_post_reset_audit_contract():
    intelligence = Path("docs/architecture/intelligence.md").read_text(encoding="utf-8")
    layout = Path("docs/reference/repository-layout.md").read_text(encoding="utf-8")
    status = Path("docs/status/current.md").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/media-dev-check.yml").read_text(encoding="utf-8")

    assert "audit_intelligence" in intelligence
    assert "canonical_input_digest" in intelligence
    assert "Stage A baseline" in intelligence
    assert "синтет" in intelligence.lower()
    assert "Stage A" in layout and "baseline" in layout.lower() and "отсутств" in layout.lower()
    assert "synthetic/reference fixtures" in status or "синтет" in status.lower()
    assert not Path("media/baselines/intelligence-stage-a.json").exists()
    assert not Path("media/baselines/intelligence-stage-a.meta.json").exists()
    assert "python -m media.tools.audit_intelligence . --format json" in workflow
