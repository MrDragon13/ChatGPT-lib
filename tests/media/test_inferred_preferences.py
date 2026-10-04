from datetime import datetime, timezone

import pytest

from media.commands.schema import parse_command
from media.domain.errors import CommandValidationError
from media.service.transaction import execute_command
from media.tools.build_profiles import build_profile
from media.tools.common import dump_yaml, load_yaml
from tests.media.fixture_repo import copy_fixture_repo

UUID1 = "123e4567-e89b-42d3-a456-426614174020"
UUID2 = "123e4567-e89b-42d3-a456-426614174021"


def command(operation_id=UUID1, target="primary", hypotheses=None):
    return parse_command({
        "schema_version": 1,
        "operation_id": operation_id,
        "operation": "set_inferred_preferences",
        "target": target,
        "hypotheses": hypotheses if hypotheses is not None else [{
            "id": "intrigue-problem-solving",
            "statement": "Высокие оценки повторяются у фильмов с интригой и решением задач.",
            "affinity": 0.8,
            "confidence": "medium",
            "terms": ["story.intrigue", "story.problem_solving"],
            "evidence": [
                {"entity_id": "arrival-2016", "kind": "rating_correlation"},
            ],
        }],
    })


def test_inferred_command_requires_numeric_affinity():
    data = {
        "schema_version": 1,
        "operation_id": UUID1,
        "operation": "set_inferred_preferences",
        "target": "primary",
        "hypotheses": [{
            "id": "intrigue",
            "statement": "Нравится интрига",
            "confidence": "medium",
            "terms": ["story.intrigue"],
            "evidence": [{"entity_id": "arrival-2016", "kind": "rating_correlation"}],
        }],
    }
    with pytest.raises(CommandValidationError):
        parse_command(data)


def test_set_inferred_preferences_writes_canonical_file_and_exposes_explanation_only_profile(tmp_path):
    root = copy_fixture_repo(tmp_path)
    before = build_profile(root / "media", "primary")
    result = execute_command(root, command(), now=datetime(2026,10,3,tzinfo=timezone.utc))
    path = root / "media/preferences/inferred/primary.yaml"
    doc = load_yaml(path)
    assert doc["target"] == "primary"
    assert doc["hypotheses"][0]["affinity"] == 0.8
    assert doc["updated_at"] == "2026-10-03T00:00:00Z"
    profile = build_profile(root / "media", "primary")
    assert profile["inferred_preferences"][0]["id"] == "intrigue-problem-solving"
    assert profile["affinities"] == before["affinities"]
    assert result.status == "applied"


def test_set_inferred_preferences_replaces_stale_hypotheses(tmp_path):
    root = copy_fixture_repo(tmp_path)
    execute_command(root, command(), now=datetime(2026,10,3,tzinfo=timezone.utc))
    execute_command(root, command(operation_id=UUID2, hypotheses=[]), now=datetime(2026,10,4,tzinfo=timezone.utc))
    doc = load_yaml(root / "media/preferences/inferred/primary.yaml")
    assert doc["hypotheses"] == []
    profile = build_profile(root / "media", "primary")
    assert profile["inferred_preferences"] == []


def test_set_inferred_preferences_rejects_unknown_target(tmp_path):
    root = copy_fixture_repo(tmp_path)
    with pytest.raises(CommandValidationError):
        execute_command(root, command(target="stranger"))


def test_set_inferred_preferences_rejects_unknown_term(tmp_path):
    root = copy_fixture_repo(tmp_path)
    bad = [{
        "id":"unknown-term",
        "statement":"test",
        "affinity":0.5,
        "confidence":"low",
        "terms":["story.not-real"],
        "evidence":[{"entity_id":"arrival-2016","kind":"rating_correlation"}],
    }]
    with pytest.raises(CommandValidationError):
        execute_command(root, command(hypotheses=bad))


def test_set_inferred_preferences_rejects_unknown_work_evidence(tmp_path):
    root = copy_fixture_repo(tmp_path)
    bad = [{
        "id":"unknown-work",
        "statement":"test",
        "affinity":0.5,
        "confidence":"low",
        "terms":["story.intrigue"],
        "evidence":[{"entity_id":"not-a-work","kind":"rating_correlation"}],
    }]
    with pytest.raises(CommandValidationError):
        execute_command(root, command(hypotheses=bad))


def test_inferred_hypothesis_cannot_use_an_inferred_preference_as_evidence(tmp_path):
    root = copy_fixture_repo(tmp_path)
    inferred_dir = root / "media/preferences/inferred"
    inferred_dir.mkdir(parents=True, exist_ok=True)
    dump_yaml(inferred_dir / "primary.yaml", {
        "schema_version":1,
        "target":"primary",
        "updated_at":"2026-10-02T00:00:00Z",
        "hypotheses":[{
            "id":"old-hypothesis",
            "statement":"old",
            "affinity":0.5,
            "confidence":"low",
            "terms":["story.intrigue"],
            "evidence":[{"entity_id":"arrival-2016","kind":"rating_correlation"}],
        }],
    })
    bad = [{
        "id":"new-hypothesis",
        "statement":"new",
        "affinity":0.5,
        "confidence":"medium",
        "terms":["story.intrigue"],
        "evidence":[{"entity_id":"old-hypothesis","kind":"rating_correlation"}],
    }]
    with pytest.raises(CommandValidationError):
        execute_command(root, command(hypotheses=bad))


def test_inferred_preference_evidence_can_reference_explicit_preference_id(tmp_path):
    root = copy_fixture_repo(tmp_path)
    explicit = root / "media/preferences/explicit/primary.yaml"
    dump_yaml(explicit, {
        "schema_version":4,
        "target":"primary",
        "preferences":[{
            "id":"likes-intrigue",
            "statement":"Люблю интригу",
            "term":"story.intrigue",
            "affinity":1.0,
            "source":"explicit",
            "confidence":"exact",
        }],
        "rules":[],
        "constraints":[],
    })
    hypotheses = [{
        "id":"confirmed-intrigue",
        "statement":"Явная любовь к интриге подтверждает устойчивую закономерность.",
        "affinity":1.0,
        "confidence":"high",
        "terms":["story.intrigue"],
        "evidence":[{"entity_id":"likes-intrigue","kind":"explicit_preference"}],
    }]
    result = execute_command(root, command(hypotheses=hypotheses), now=datetime(2026,10,3,tzinfo=timezone.utc))
    assert result.status == "applied"