from __future__ import annotations

import json
from pathlib import Path

import yaml

from media.cli import main
from media.repository.yaml_repo import YamlRepository
from media.service.reassessment import PILOT_ID, build_initial_ledger, ledger_bytes
from media.tools.common import dump_yaml
from tests.media.fixture_repo import copy_fixture_repo


def _activate_fixture_ledger(root: Path) -> str:
    work_path = root / "media/data/works/watched-by-primary-only.yaml"
    work = yaml.safe_load(work_path.read_text(encoding="utf-8"))
    work.setdefault("viewer_signals", {}).setdefault("primary", {}).update(
        {
            "viewing": {"status": "watched"},
            "rating": {"score": 8.0, "source": "explicit", "confidence": "exact"},
            "feedback": {"summary": "Старый отзыв", "signals": []},
        }
    )
    work.setdefault("metadata", {}).setdefault("external", {}).update(
        {
            "synopsis_short": "Герой расследует исчезновение в небольшом городе.",
            "directors": [{"name": "Режиссёр Один"}],
            "main_cast": [{"name": "Актёр Один", "character": "Hero"}],
        }
    )
    dump_yaml(work_path, work)

    ledger = build_initial_ledger(
        YamlRepository(root / "media"),
        pilot_id=PILOT_ID,
        base_revision="35afaca898eae6937066f230906b41af0e1f6690",
        baseline_path="media/baselines/intelligence-stage-a.json",
        baseline_document={
            "schema_version": 2,
            "canonical_input_digest": "sha256:" + "9" * 64,
        },
    )
    ledger_path = root / "media/pilots/legacy-reassessment-primary.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_bytes(ledger_bytes(ledger))
    return "watched-by-primary-only"


def test_cli_reassessment_context_is_unanchored(tmp_path, monkeypatch, capsys):
    root = copy_fixture_repo(tmp_path)
    _activate_fixture_ledger(root)
    monkeypatch.chdir(root)

    assert main(["reassessment-context", "--limit", "1", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["cards"]
    card = payload["cards"][0]
    assert set(card) == {
        "work_id",
        "title",
        "year",
        "synopsis_short",
        "directors",
        "main_cast",
        "queue_status",
        "order_rank",
    }
    assert "rating" not in repr(card)
    assert "feedback" not in repr(card)
    assert "Старый отзыв" not in repr(card)


def test_cli_reassessment_history_is_explicit_second_phase(tmp_path, monkeypatch, capsys):
    root = copy_fixture_repo(tmp_path)
    work_id = _activate_fixture_ledger(root)
    monkeypatch.chdir(root)

    assert main(["reassessment-history", work_id, "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["work_id"] == work_id
    assert payload["viewer_evidence"]["rating"]["score"] == 8.0
    assert payload["viewer_evidence"]["feedback"]["summary"] == "Старый отзыв"
    assert "metadata" not in payload
    assert "semantic" not in repr(payload)
