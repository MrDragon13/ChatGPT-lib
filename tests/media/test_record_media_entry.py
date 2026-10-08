from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

import media.service.transaction as transaction
from media.commands.schema import parse_command
from media.domain.digests import (
    compute_semantic_input_digest,
    compute_viewer_digest,
    compute_vocabulary_digest,
)
from media.domain.errors import CommandValidationError
from media.providers.base import CanonicalMetadata
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_work
from media.tools.common import load_yaml
from tests.media.fixture_repo import copy_fixture_repo


OP1 = "123e4567-e89b-42d3-a456-426614174301"
OP2 = "123e4567-e89b-42d3-a456-426614174302"
OP3 = "123e4567-e89b-42d3-a456-426614174303"
EVENT = "123e4567-e89b-42d3-a456-426614174399"
NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


class RaisingProvider:
    def fetch_work(self, *args, **kwargs):
        raise AssertionError("provider must not be called for an existing work")

    def search_work(self, *args, **kwargs):
        raise AssertionError("provider search must not be called")


class FakeProvider:
    def __init__(self, metadata: CanonicalMetadata):
        self.metadata = metadata
        self.calls = []

    def fetch_work(self, media_type, provider_id):
        self.calls.append(("fetch", media_type, provider_id))
        return self.metadata

    def search_work(self, *args, **kwargs):
        raise AssertionError("record_media_entry new-work path must use stable provider identity")


def _existing_command(root: Path, *, operation_id=OP1, event_id=EVENT, rating=9.0, digest=None, create=False):
    work = load_yaml(root / "media/data/works/arrival-2016.yaml")
    expected = digest or compute_viewer_digest(work, "primary")
    data = {
        "schema_version": 1,
        "operation_id": operation_id,
        "idempotency_key": event_id,
        "operation": "record_media_entry",
        "work_ref": {"id": "arrival-2016"},
        "create_if_missing": create,
        "target_updates": [{
            "target": "primary",
            "rating": {"score": rating, "source": "explicit", "confidence": "exact"},
            "reaction": {"value": "liked", "source": "explicit", "confidence": "high"},
            "feedback": {
                "summary": "Сильная интрига.",
                "signals": [{
                    "term": "story.intrigue",
                    "sentiment": "positive",
                    "strength": 3,
                    "source": "explicit",
                    "confidence": "high",
                }],
            },
        }],
        "preconditions": {"expected_viewer_digests": {"primary": expected}},
    }
    return data


def _provider_metadata(provider_id=987654):
    return CanonicalMetadata(
        identity={
            "format": "movie",
            "title_original": "New Film",
            "title_ru": "Новый фильм",
            "year": 2024,
            "release_date": "2024-05-10",
            "external_ids": {
                "tmdb": {"media_type": "movie", "id": provider_id},
                "imdb": "tt9876543",
            },
        },
        external={
            "genres": ["genre.drama"],
            "runtime_min": 121,
            "original_language": "en",
            "synopsis_short": "A carefully verified new film.",
            "external_metrics": {
                "tmdb": {"score": 7.2, "votes": 100, "observed_at": "2026-10-07"}
            },
            "provenance": {
                "provider": "tmdb",
                "provider_id": provider_id,
                "fetched_at": "2026-10-07T00:00:00Z",
            },
        },
    )


def _new_command(root: Path, metadata: CanonicalMetadata, *, operation_id=OP1, event_id=EVENT, trait="story.intrigue"):
    provider_id = metadata.identity["external_ids"]["tmdb"]["id"]
    return {
        "schema_version": 1,
        "operation_id": operation_id,
        "idempotency_key": event_id,
        "operation": "record_media_entry",
        "work_ref": {"tmdb_media_type": "movie", "tmdb_id": provider_id, "title": "New Film", "year": 2024},
        "create_if_missing": True,
        "target_updates": [{
            "target": "primary",
            "viewing": {"status": "watched"},
            "rating": {"score": 8.5, "source": "explicit", "confidence": "exact"},
        }],
        "creation_context": {
            "provider_identity": {"media_type": "movie", "id": provider_id},
        },
        "semantic_snapshot": {
            "traits": [{"term": trait, "source": "llm_inferred", "confidence": "high"}],
        },
        "preconditions": {"expected_viewer_digests": {}},
    }

def _snapshot(root: Path):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_existing_work_fast_path_never_calls_provider_and_preserves_work_knowledge(tmp_path, monkeypatch):
    root = copy_fixture_repo(tmp_path)
    before = load_yaml(root / "media/data/works/arrival-2016.yaml")
    calls = {"index": 0, "profiles": []}
    real_index = transaction.write_index
    real_profile = transaction.build_profile

    def counted_index(*args, **kwargs):
        calls["index"] += 1
        return real_index(*args, **kwargs)

    def counted_profile(media_root, target):
        calls["profiles"].append(target)
        return real_profile(media_root, target)

    monkeypatch.setattr(transaction, "write_index", counted_index)
    monkeypatch.setattr(transaction, "build_profile", counted_profile)

    result = transaction.execute_command(
        root,
        parse_command(_existing_command(root)),
        provider=RaisingProvider(),
        now=NOW,
    )
    after = load_yaml(root / "media/data/works/arrival-2016.yaml")

    assert result.status == "applied"
    assert after["metadata"] == before["metadata"]
    history = after["viewer_signals"]["primary"]["history"]
    assert len(history) == 1
    assert history[-1]["event_id"] == EVENT
    assert history[-1]["material_evidence"] is True
    assert calls["index"] == 1
    assert calls["profiles"].count("primary") == 1
    assert calls["profiles"].count("couple") == 1
    assert "partner" not in calls["profiles"]


def test_existing_work_stale_digest_fails_before_provider_or_mutation(tmp_path):
    root = copy_fixture_repo(tmp_path)
    before = _snapshot(root)
    command = _existing_command(root, digest="sha256:" + "0" * 64)

    with pytest.raises(CommandValidationError, match="viewer digest mismatch"):
        transaction.execute_command(root, parse_command(command), provider=RaisingProvider(), now=NOW)

    assert _snapshot(root) == before


def test_idempotency_key_deduplicates_retry_and_rejects_changed_payload(tmp_path):
    root = copy_fixture_repo(tmp_path)
    first = transaction.execute_command(root, parse_command(_existing_command(root, operation_id=OP1)), now=NOW)
    after_first = _snapshot(root)

    retry = _existing_command(root, operation_id=OP2)
    retry["preconditions"]["expected_viewer_digests"]["primary"] = compute_viewer_digest(
        load_yaml(root / "media/data/works/arrival-2016.yaml"), "primary"
    )
    second = transaction.execute_command(root, parse_command(retry), now=NOW)
    assert first.status == "applied"
    assert second.status == "already_applied"
    assert _snapshot(root) == after_first

    changed = _existing_command(root, operation_id=OP3, rating=8.0)
    changed["preconditions"]["expected_viewer_digests"]["primary"] = retry["preconditions"]["expected_viewer_digests"]["primary"]
    with pytest.raises(CommandValidationError, match="idempotency"):
        transaction.execute_command(root, parse_command(changed), now=NOW)


def test_new_work_is_created_with_one_provider_fetch_semantics_and_feedback_atomically(tmp_path):
    root = copy_fixture_repo(tmp_path)
    metadata = _provider_metadata()
    provider = FakeProvider(metadata)

    result = transaction.execute_command(
        root,
        parse_command(_new_command(root, metadata)),
        provider=provider,
        now=NOW,
    )

    repo = YamlRepository(root / "media")
    work = resolve_work(repo, parse_command(_new_command(root, metadata)).work_ref).data
    assert result.status == "applied"
    assert provider.calls == [("fetch", "movie", 987654)]
    assert work["metadata"]["semantic"]["traits"][0]["term"] == "story.intrigue"
    assert work["metadata"]["semantic"]["algorithm_version"] == "media-semantic-v1"
    assert work["viewer_signals"]["primary"]["rating"]["score"] == 8.5
    assert work["viewer_signals"]["primary"]["history"][-1]["event_id"] == EVENT


def test_invalid_new_work_semantics_or_provider_identity_leaves_tree_unchanged(tmp_path):
    root = copy_fixture_repo(tmp_path)
    metadata = _provider_metadata()
    before = _snapshot(root)
    invalid_trait = _new_command(root, metadata, trait="reaction.pacing_dragging")

    with pytest.raises(CommandValidationError):
        transaction.execute_command(root, parse_command(invalid_trait), provider=FakeProvider(metadata), now=NOW)
    assert _snapshot(root) == before

    mismatch = _new_command(root, metadata, operation_id=OP2, event_id=OP2)
    bad_metadata = _provider_metadata(provider_id=123456)
    with pytest.raises(CommandValidationError, match="provider identity"):
        transaction.execute_command(root, parse_command(mismatch), provider=FakeProvider(bad_metadata), now=NOW)
    assert _snapshot(root) == before


def test_create_if_missing_existing_work_reconciles_without_provider_or_overwriting_knowledge(tmp_path):
    root = copy_fixture_repo(tmp_path)
    before = load_yaml(root / "media/data/works/arrival-2016.yaml")
    current_digest = compute_viewer_digest(before, "primary")
    data = _existing_command(root, create=True, digest=current_digest)
    tmdb = before["identity"]["external_ids"]["tmdb"]
    data["work_ref"] = {"tmdb_media_type": tmdb["media_type"], "tmdb_id": tmdb["id"]}
    data["creation_context"] = {
        "provider_identity": {"media_type": tmdb["media_type"], "id": tmdb["id"]},
    }
    data["semantic_snapshot"] = {
        "traits": [{"term": "pacing.slow", "source": "llm_inferred", "confidence": "low"}],
    }

    transaction.execute_command(root, parse_command(data), provider=RaisingProvider(), now=NOW)
    after = load_yaml(root / "media/data/works/arrival-2016.yaml")
    assert after["metadata"] == before["metadata"]

    conflict = deepcopy(data)
    conflict["operation_id"] = OP2
    conflict["idempotency_key"] = OP2
    conflict["preconditions"]["expected_viewer_digests"]["primary"] = "sha256:" + "0" * 64
    with pytest.raises(CommandValidationError, match="viewer digest mismatch"):
        transaction.execute_command(root, parse_command(conflict), provider=RaisingProvider(), now=NOW)


def test_create_if_missing_existing_work_rejects_contradictory_provider_identity(tmp_path):
    root = copy_fixture_repo(tmp_path)
    before = load_yaml(root / "media/data/works/arrival-2016.yaml")
    data = _existing_command(root, create=True)
    tmdb = before["identity"]["external_ids"]["tmdb"]
    data["work_ref"] = {"tmdb_media_type": tmdb["media_type"], "tmdb_id": tmdb["id"]}
    data["creation_context"] = {
        "provider_identity": {"media_type": tmdb["media_type"], "id": 1},
    }
    data["semantic_snapshot"] = {"traits": []}

    with pytest.raises(CommandValidationError, match="provider identity"):
        transaction.execute_command(root, parse_command(data), provider=RaisingProvider(), now=NOW)




def test_new_work_trusts_provider_for_identity_metadata_and_semantic_bookkeeping(tmp_path):
    root = copy_fixture_repo(tmp_path)
    metadata = _provider_metadata()
    provider = FakeProvider(metadata)
    command = _new_command(root, metadata)
    command["creation_context"] = {"provider_identity": {"media_type": "movie", "id": 987654}}
    command["semantic_snapshot"] = {
        "traits": [{"term": "story.intrigue", "source": "llm_inferred", "confidence": "high"}],
    }

    result = transaction.execute_command(root, parse_command(command), provider=provider, now=NOW)
    work = resolve_work(YamlRepository(root / "media"), parse_command(command).work_ref).data
    vocabulary_digest = compute_vocabulary_digest(root / "media")
    expected_semantic_digest = compute_semantic_input_digest(work, vocabulary_digest, "media-semantic-v1")

    assert result.status == "applied"
    assert provider.calls == [("fetch", "movie", 987654)]
    assert work["identity"]["title_ru"] == "Новый фильм"
    assert work["metadata"]["external"]["runtime_min"] == 121
    assert work["metadata"]["semantic"]["vocabulary_digest"] == vocabulary_digest
    assert work["metadata"]["semantic"]["input_digest"] == expected_semantic_digest
