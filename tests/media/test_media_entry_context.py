from __future__ import annotations

from media.commands.schema import parse_command
from media.domain.digests import compute_viewer_digest
from media.service.media_entry_context import build_media_entry_context
from media.tools.common import dump_yaml, load_yaml
from tests.media.fixture_repo import copy_fixture_repo


def request(work_ref=None, target="primary"):
    return parse_command({
        "schema_version": 1,
        "operation": "media_entry_context",
        "work_ref": work_ref or {"id": "arrival-2016"},
        "target": target,
    })


def test_existing_media_entry_context_is_compact_and_target_scoped(tmp_path):
    root = copy_fixture_repo(tmp_path)
    work = load_yaml(root / "media/data/works/arrival-2016.yaml")

    result = build_media_entry_context(root / "media", request())

    assert result["schema_version"] == 1
    assert result["exists"] is True
    assert result["target"] == "primary"
    assert set(result) == {
        "schema_version",
        "exists",
        "target",
        "identity",
        "viewer",
        "metadata_freshness",
        "facts",
        "semantic",
        "interest",
    }
    assert result["identity"]["id"] == "arrival-2016"
    assert result["identity"]["title_original"] == "Arrival"
    assert result["viewer"]["digest"] == compute_viewer_digest(work, "primary")
    assert result["viewer"]["state"]["viewing"] == work["viewer_signals"]["primary"]["viewing"]
    assert "history" not in result["viewer"]["state"]
    assert "partner" not in result["viewer"]
    assert "profile" not in result
    assert "main_cast" not in result["facts"]
    assert set(result["facts"]) <= {"runtime_min", "genres", "original_language"}
    assert result["metadata_freshness"] == {
        "identity": "current",
        "static": "current",
        "dynamic": "missing",
    }
    assert set(result["semantic"]) == {
        "status",
        "key",
        "algorithm_version",
        "vocabulary_digest",
        "traits",
    }


def test_media_entry_context_keeps_structured_feedback_but_omits_history(tmp_path):
    root = copy_fixture_repo(tmp_path)
    path = root / "media/data/works/arrival-2016.yaml"
    work = load_yaml(path)
    signal = work["viewer_signals"]["primary"]
    signal["feedback"] = {
        "summary": "Сильная интрига.",
        "signals": [{
            "term": "story.intrigue",
            "sentiment": "positive",
            "strength": 3,
            "source": "explicit",
            "confidence": "high",
        }],
    }
    signal["history"] = [{
        "at": "2026-10-07T12:00:00Z",
        "event_id": "123e4567-e89b-42d3-a456-426614174777",
        "material_evidence": True,
        "previous": {},
        "current": {"feedback": signal["feedback"]},
    }]
    dump_yaml(path, work)

    result = build_media_entry_context(root / "media", request())

    state = result["viewer"]["state"]
    assert "history" not in state
    assert state["feedback"]["summary"] == "Сильная интрига."
    assert state["feedback"]["signals"][0]["term"] == "story.intrigue"


def test_missing_stable_work_returns_only_submitted_identity_without_fabricating_provider_facts(tmp_path):
    root = copy_fixture_repo(tmp_path)
    result = build_media_entry_context(
        root / "media",
        request({
            "tmdb_media_type": "movie",
            "tmdb_id": 987654321,
            "title": "Unknown Stable Film",
            "year": 2026,
        }),
    )

    assert result == {
        "schema_version": 1,
        "exists": False,
        "target": "primary",
        "requested_identity": {
            "tmdb_media_type": "movie",
            "tmdb_id": 987654321,
            "title": "Unknown Stable Film",
            "year": 2026,
        },
    }


def test_media_entry_context_validates_target_even_for_missing_work(tmp_path):
    root = copy_fixture_repo(tmp_path)
    from media.domain.errors import UnknownTargetError
    import pytest

    with pytest.raises(UnknownTargetError):
        build_media_entry_context(
            root / "media",
            request({"tmdb_media_type": "movie", "tmdb_id": 987654321}, target="ghost"),
        )
