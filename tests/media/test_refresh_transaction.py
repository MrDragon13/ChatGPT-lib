from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from media.cli import main
from media.domain.commands import RefreshMetadataCommand, RefreshWorkMetadataCommand
from media.domain.errors import PathPolicyError
from media.providers.base import CanonicalMetadata, ProviderCandidate
from media.service.path_policy import verify_changed_paths
from media.service.transaction import execute_command, preview_command
from media.tools.common import load_yaml
from media.tools.rebuild import rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo

UUID1 = "123e4567-e89b-42d3-a456-426614174301"
UUID2 = "123e4567-e89b-42d3-a456-426614174302"
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _arrival_only_repo(tmp_path):
    root = copy_fixture_repo(tmp_path)
    works = root / "media" / "data" / "works"
    for path in works.glob("*.yaml"):
        if path.name != "arrival-2016.yaml":
            path.unlink()
    rebuild_generated(root / "media")
    return root


class ArrivalProvider:
    def search_work(self, title, year=None):
        return [ProviderCandidate("movie", 329865, "Прибытие", "Arrival", 2016)]

    def find_by_imdb(self, imdb_id):
        return [ProviderCandidate("movie", 329865, "Прибытие", "Arrival", 2016)]

    def fetch_work(self, media_type, provider_id):
        return CanonicalMetadata(
            identity={
                "format": "movie",
                "title_original": "Arrival",
                "title_ru": "Прибытие",
                "year": 2016,
                "release_date": "2016-11-10",
                "external_ids": {
                    "tmdb": {"media_type": "movie", "id": 329865},
                    "imdb": "tt2543164",
                },
            },
            external={
                "runtime_min": 116,
                "genres": ["genre.science_fiction", "genre.drama"],
                "original_language": "en",
                "countries": ["US"],
                "production_status": "completed",
                "synopsis_short": "Лингвист пытается понять язык инопланетян.",
                "directors": [{"name": "Denis Villeneuve", "external_ids": {"tmdb": 137427}}],
                "writers": [],
                "main_cast": [],
                "external_metrics": {
                    "tmdb": {"score": 7.6, "votes": 18000, "observed_at": "2026-10-01"}
                },
                "provenance": {
                    "provider": "tmdb",
                    "provider_id": 329865,
                    "fetched_at": "2026-10-01T12:00:00Z",
                },
            },
            unmapped_genre_ids=(10749,),
        )


def _command(operation_id=UUID1):
    return RefreshMetadataCommand(1, operation_id, "all_movies", {})


def test_refresh_execute_persists_details_and_replay_is_idempotent(tmp_path):
    root = _arrival_only_repo(tmp_path)
    provider = ArrivalProvider()
    before_signals = load_yaml(root / "media/data/works/arrival-2016.yaml")["viewer_signals"]

    preview = preview_command(root, _command(), provider=provider, now=NOW)
    assert preview.status == "planned"
    assert preview.details["targeted_count"] == 1
    assert preview.details["changed_count"] == 1

    first = execute_command(root, _command(), provider=provider, now=NOW)
    assert first.status == "applied"
    assert first.details["unmapped_genre_ids"] == [10749]
    assert first.changed_entities == ("arrival-2016",)
    receipt = root / ".media/operations" / f"{UUID1}.json"
    receipt_json = json.loads(receipt.read_text(encoding="utf-8"))
    assert receipt_json["details"]["changed_count"] == 1
    assert load_yaml(root / "media/data/works/arrival-2016.yaml")["viewer_signals"] == before_signals

    replay = execute_command(root, _command(), provider=provider, now=datetime(2026, 10, 2, tzinfo=timezone.utc))
    assert replay.status == "already_applied"
    assert replay.details == first.details


def test_refresh_no_change_still_writes_replayable_receipt(tmp_path):
    root = _arrival_only_repo(tmp_path)
    provider = ArrivalProvider()
    execute_command(root, _command(UUID1), provider=provider, now=NOW)

    no_change = execute_command(root, _command(UUID2), provider=provider, now=NOW)
    assert no_change.status == "no_change"
    assert no_change.details["changed_count"] == 0
    assert no_change.details["no_change_count"] == 1
    assert (root / ".media/operations" / f"{UUID2}.json").exists()
    replay = execute_command(root, _command(UUID2), provider=provider, now=NOW)
    assert replay.status == "already_applied"
    assert replay.details["changed_count"] == 0


def test_refresh_path_policy_allows_only_normal_bulk_outputs():
    verify_changed_paths(
        "refresh_metadata",
        [
            "media/data/works/arrival-2016.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/primary.yaml",
            f".media/operations/{UUID1}.json",
        ],
    )
    with pytest.raises(PathPolicyError):
        verify_changed_paths("refresh_metadata", ["media/vocabulary.yaml"])
    with pytest.raises(PathPolicyError):
        verify_changed_paths("refresh_metadata", ["media/service/refresh.py"])


def test_cli_refresh_preflight_returns_structured_needs_input(tmp_path, monkeypatch, capsys):
    root = _arrival_only_repo(tmp_path)
    arrival = load_yaml(root / "media/data/works/arrival-2016.yaml")
    arrival["identity"].pop("external_ids", None)
    from media.tools.common import dump_yaml
    dump_yaml(root / "media/data/works/arrival-2016.yaml", arrival)
    rebuild_generated(root / "media")

    request = root / "refresh.json"
    request.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "operation_id": UUID1,
                "operation": "refresh_metadata",
                "scope": "all_movies",
            }
        ),
        encoding="utf-8",
    )

    class MissingProvider:
        def __init__(self, token):
            pass
        def search_work(self, title, year=None):
            return []
        def find_by_imdb(self, imdb_id):
            return []
        def fetch_work(self, media_type, provider_id):
            raise AssertionError("fetch should not run")

    monkeypatch.chdir(root)
    monkeypatch.setenv("TMDB_READ_TOKEN", "token")
    monkeypatch.setattr("media.cli.TMDBProvider", MissingProvider)

    assert main(["apply-command", str(request), "--format", "json"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "needs_input"
    assert result["reason"] == "metadata_refresh_preflight"
    assert result["blockers"] == [{"work_id": "arrival-2016", "reason": "not_found"}]


def test_refresh_work_metadata_preview_is_bound_to_current_work_digest(tmp_path):
    import hashlib
    from media.domain.types import WorkRef

    root = _arrival_only_repo(tmp_path)
    provider = ArrivalProvider()
    path = root / "media/data/works/arrival-2016.yaml"
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    command = RefreshWorkMetadataCommand(1, UUID2, WorkRef(id="arrival-2016"), digest)

    preview = preview_command(root, command, provider=provider, now=NOW)
    assert preview.status == "planned"
    assert preview.changed_entities == ("arrival-2016",)
    assert preview.details["work_id"] == "arrival-2016"
    assert preview.details["expected_work_digest"] == digest
