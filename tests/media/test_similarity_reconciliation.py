from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from media.commands.schema import parse_command
from media.providers.base import CanonicalMetadata, ProviderCandidate
from media.service.transaction import execute_command
from media.tools.common import load_yaml
from tests.media.fixture_repo import copy_fixture_repo


NOW = datetime(2026, 10, 3, 20, 15, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 3, 21, 0, tzinfo=timezone.utc)


class NewFilmProvider:
    def search_work(self, title, year=None):
        return [ProviderCandidate("movie", 777, "Новый фильм", "New Film", 2025)]

    def fetch_work(self, media_type, provider_id):
        return CanonicalMetadata(
            identity={
                "format": "movie",
                "title_original": "New Film",
                "title_ru": "Новый фильм",
                "year": 2025,
                "external_ids": {
                    "tmdb": {"media_type": "movie", "id": 777},
                    "imdb": "tt7777777",
                },
            },
            external={
                "runtime_min": 101,
                "provenance": {
                    "provider": "tmdb",
                    "provider_id": 777,
                    "fetched_at": "2026-10-01T00:00:00Z",
                },
            },
        )


def _set(operation_id: str, left: dict, right: dict, *, note: str, terms=None):
    return parse_command({
        "schema_version": 1,
        "operation_id": operation_id,
        "operation": "set_work_similarity",
        "target": "primary",
        "left": left,
        "right": right,
        "terms": list(terms if terms is not None else ["story.intrigue"]),
        "note": note,
    })


def _add(operation_id="123e4567-e89b-42d3-a456-426614174099"):
    return parse_command({
        "schema_version": 1,
        "operation_id": operation_id,
        "operation": "add_work",
        "work_ref": {"title": "New Film", "year": 2025},
    })


def _relations(root: Path):
    doc = load_yaml(root / "media/data/relations/similarity/primary.yaml")
    return doc["relations"]


def _tmdb_ref():
    return {"tmdb_media_type": "movie", "tmdb_id": 777, "title": "New Film", "year": 2025}


def _imdb_ref():
    return {"imdb_id": "tt7777777", "title": "New Film", "year": 2025}


def test_add_work_reconciles_external_endpoint_to_canonical_work(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    execute_command(
        root,
        _set("123e4567-e89b-42d3-a456-426614174050", {"id": "arrival-2016"}, _tmdb_ref(), note="До добавления"),
        now=NOW,
    )

    execute_command(root, _add(), provider=NewFilmProvider(), now=LATER)

    relation = _relations(root)[0]
    endpoints = {endpoint.get("work_id") for endpoint in (relation["left"], relation["right"])}
    assert endpoints == {"arrival-2016", "new-film-2025"}
    assert all(endpoint["kind"] == "canonical" for endpoint in (relation["left"], relation["right"]))


def test_reconciliation_conflict_keeps_newer_explicit_assertion_without_merging(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    execute_command(
        root,
        _set("123e4567-e89b-42d3-a456-426614174051", {"id": "arrival-2016"}, _tmdb_ref(), note="Старая причина", terms=["story.intrigue"]),
        now=NOW,
    )
    execute_command(
        root,
        _set("123e4567-e89b-42d3-a456-426614174052", {"id": "arrival-2016"}, _imdb_ref(), note="Новая причина", terms=[]),
        now=LATER,
    )

    execute_command(root, _add(), provider=NewFilmProvider(), now=LATER)

    relations = _relations(root)
    assert len(relations) == 1
    assert relations[0]["note"] == "Новая причина"
    assert relations[0]["terms"] == []
    assert relations[0]["updated_at"] == LATER.isoformat()


def test_reconciliation_identical_collision_deduplicates_and_keeps_latest_timestamp(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    execute_command(
        root,
        _set("123e4567-e89b-42d3-a456-426614174053", {"id": "arrival-2016"}, _tmdb_ref(), note="Одинаково"),
        now=NOW,
    )
    execute_command(
        root,
        _set("123e4567-e89b-42d3-a456-426614174054", {"id": "arrival-2016"}, _imdb_ref(), note="Одинаково"),
        now=LATER,
    )

    execute_command(root, _add(), provider=NewFilmProvider(), now=LATER)

    relations = _relations(root)
    assert len(relations) == 1
    assert relations[0]["updated_at"] == LATER.isoformat()


def test_reconciliation_removes_relation_that_becomes_self_link(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    execute_command(
        root,
        _set("123e4567-e89b-42d3-a456-426614174055", _tmdb_ref(), _imdb_ref(), note="Два идентификатора одного фильма"),
        now=NOW,
    )

    execute_command(root, _add(), provider=NewFilmProvider(), now=LATER)

    assert _relations(root) == []


def test_equal_timestamp_collision_uses_stable_lexical_relation_identity_tiebreak(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    execute_command(
        root,
        _set("123e4567-e89b-42d3-a456-426614174056", {"id": "arrival-2016"}, _tmdb_ref(), note="TMDB"),
        now=NOW,
    )
    execute_command(
        root,
        _set("123e4567-e89b-42d3-a456-426614174057", {"id": "arrival-2016"}, _imdb_ref(), note="IMDb"),
        now=NOW,
    )

    execute_command(root, _add(), provider=NewFilmProvider(), now=LATER)

    relations = _relations(root)
    assert len(relations) == 1
    assert relations[0]["note"] == "IMDb"
