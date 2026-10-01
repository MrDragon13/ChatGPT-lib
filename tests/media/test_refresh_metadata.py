from __future__ import annotations

from datetime import datetime, timezone
import importlib

import pytest

from media.domain.commands import ProviderWorkRef, RefreshMetadataCommand
import media.domain.errors as domain_errors
from media.domain.errors import ProviderUnavailableError
from media.providers.base import CanonicalMetadata, ProviderCandidate
from media.repository.yaml_repo import YamlRepository
from media.tools.common import dump_yaml

UUID = "123e4567-e89b-42d3-a456-426614174200"
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _planner():
    return importlib.import_module("media.service.refresh").plan_refresh_metadata


def _repo(tmp_path, *works):
    media_root = tmp_path / "media"
    for work in works:
        dump_yaml(media_root / "data" / "works" / f"{work['id']}.yaml", work)
    return YamlRepository(media_root)


def _work(
    work_id: str,
    title: str,
    year: int,
    *,
    fmt: str = "movie",
    tmdb_id: int | None = None,
    imdb_id: str | None = None,
    external: dict | None = None,
):
    identity = {"format": fmt, "title_original": title, "title_ru": title, "year": year}
    ids = {}
    if tmdb_id is not None:
        ids["tmdb"] = {"media_type": "movie", "id": tmdb_id}
    if imdb_id is not None:
        ids["imdb"] = imdb_id
    if ids:
        identity["external_ids"] = ids
    return {
        "schema_version": 4,
        "id": work_id,
        "entity_type": "work",
        "identity": identity,
        "metadata": {
            "external": external or {},
            "overrides": {"runtime_min": 111},
            "semantic": {"traits": [{"term": "tone.serious", "source": "inferred", "confidence": "medium"}]},
        },
        "viewer_signals": {
            "primary": {
                "viewing": {"status": "watched"},
                "rating": {"score": 8, "source": "explicit", "confidence": "exact"},
            }
        },
        "canonical_relations": [{"target_id": "other", "type": "sequel", "source": "manual"}],
        "provenance": {"created_at": "2026-01-01", "updated_at": "2026-01-01"},
    }


def _metadata(
    provider_id: int,
    title: str,
    year: int,
    *,
    imdb_id: str | None = None,
    external: dict | None = None,
    unmapped: tuple[int, ...] = (),
):
    return CanonicalMetadata(
        identity={
            "format": "movie",
            "title_original": title,
            "title_ru": title,
            "year": year,
            "release_date": f"{year}-02-03",
            "external_ids": {
                "tmdb": {"media_type": "movie", "id": provider_id},
                "imdb": imdb_id,
            },
        },
        external=external
        or {
            "runtime_min": 123,
            "genres": ["genre.drama"],
            "external_metrics": {
                "tmdb": {"score": 7.5, "votes": 100, "observed_at": "2026-10-01"}
            },
            "provenance": {
                "provider": "tmdb",
                "provider_id": provider_id,
                "fetched_at": "2026-10-01T12:00:00Z",
            },
        },
        unmapped_genre_ids=unmapped,
    )


class FakeProvider:
    def __init__(self, *, fetched=None, searched=None, imdb=None, fail=False):
        self.fetched = dict(fetched or {})
        self.searched = dict(searched or {})
        self.imdb = dict(imdb or {})
        self.fail = fail
        self.calls = []

    def fetch_work(self, media_type, provider_id):
        self.calls.append(("fetch", media_type, provider_id))
        if self.fail:
            raise ProviderUnavailableError("offline")
        return self.fetched[provider_id]

    def search_work(self, title, year=None):
        self.calls.append(("search", title, year))
        if self.fail:
            raise ProviderUnavailableError("offline")
        return list(self.searched.get((title, year), ()))

    def find_by_imdb(self, imdb_id):
        self.calls.append(("imdb", imdb_id))
        if self.fail:
            raise ProviderUnavailableError("offline")
        return list(self.imdb.get(imdb_id, ()))


def _command(overrides=None):
    return RefreshMetadataCommand(1, UUID, "all_movies", overrides or {})


def test_direct_tmdb_refresh_preserves_user_owned_fields_and_non_tmdb_metrics(tmp_path):
    existing_external = {
        "runtime_min": 90,
        "external_metrics": {
            "imdb": {"score": 8.1, "votes": 1000, "observed_at": "2026-09-01"},
            "tmdb": {"score": 6.0, "votes": 10, "observed_at": "2026-09-01"},
        },
    }
    original = _work("movie-a-2020", "Movie A", 2020, tmdb_id=10, imdb_id="tt0000010", external=existing_external)
    repo = _repo(tmp_path, original)
    provider = FakeProvider(fetched={10: _metadata(10, "Movie A", 2020, imdb_id="tt0000010", unmapped=(10749,))})

    plan = _planner()(repo, _command(), provider, now=NOW)
    document = plan.documents["media/data/works/movie-a-2020.yaml"]

    assert provider.calls == [("fetch", "movie", 10)]
    assert document["identity"]["title_original"] == "Movie A"
    assert document["identity"]["year"] == 2020
    assert document["identity"]["release_date"] == "2020-02-03"
    assert document["viewer_signals"] == original["viewer_signals"]
    assert document["metadata"]["overrides"] == original["metadata"]["overrides"]
    assert document["metadata"]["semantic"] == original["metadata"]["semantic"]
    assert document["canonical_relations"] == original["canonical_relations"]
    assert document["metadata"]["external"]["external_metrics"]["imdb"] == existing_external["external_metrics"]["imdb"]
    assert document["metadata"]["external"]["external_metrics"]["tmdb"]["score"] == 7.5
    assert document["provenance"] == {"created_at": "2026-01-01", "updated_at": "2026-10-01"}
    assert plan.details["targeted_count"] == 1
    assert plan.details["changed_count"] == 1
    assert plan.details["unmapped_genre_ids"] == [10749]


def test_override_is_used_before_title_search_and_imdb_and_title_fallback_are_supported(tmp_path):
    override_work = _work("override-2020", "Override", 2020)
    imdb_work = _work("imdb-2021", "IMDb Work", 2021, imdb_id="tt0000021")
    title_work = _work("title-2022", "Title Work", 2022)
    series = _work("series-2023", "Series", 2023, fmt="series")
    repo = _repo(tmp_path, override_work, imdb_work, title_work, series)
    provider = FakeProvider(
        fetched={
            20: _metadata(20, "Override", 2020),
            21: _metadata(21, "IMDb Work", 2021, imdb_id="tt0000021"),
            22: _metadata(22, "Title Work", 2022),
        },
        imdb={"tt0000021": [ProviderCandidate("movie", 21, "IMDb Work", "IMDb Work", 2021)]},
        searched={
            ("Title Work", 2022): [ProviderCandidate("movie", 22, "Title Work", "Title Work", 2022)]
        },
    )
    command = _command({"override-2020": ProviderWorkRef("movie", 20)})

    plan = _planner()(repo, command, provider, now=NOW)

    assert set(plan.changed_entities) == {"override-2020", "imdb-2021", "title-2022"}
    assert ("search", "Override", 2020) not in provider.calls
    assert ("imdb", "tt0000021") in provider.calls
    assert ("search", "Title Work", 2022) in provider.calls
    assert all("series-2023.yaml" not in path for path in plan.documents)
    assert plan.details["targeted_count"] == 3


def test_preflight_aggregates_missing_and_ambiguous_identity_without_partial_plan(tmp_path):
    missing = _work("missing-2020", "Missing", 2020)
    ambiguous = _work("ambiguous-2021", "Ambiguous", 2021)
    repo = _repo(tmp_path, missing, ambiguous)
    provider = FakeProvider(
        searched={
            ("Missing", 2020): [],
            ("Ambiguous", 2021): [
                ProviderCandidate("movie", 31, "Ambiguous", "Ambiguous", 2021),
                ProviderCandidate("movie", 32, "Ambiguous", "Ambiguous", 2021),
            ],
        }
    )

    with pytest.raises(Exception) as caught:
        _planner()(repo, _command(), provider, now=NOW)

    error_type = getattr(domain_errors, "MetadataRefreshPreflightError")
    assert isinstance(caught.value, error_type)
    blockers = caught.value.blockers
    assert {(item["work_id"], item["reason"]) for item in blockers} == {
        ("missing-2020", "not_found"),
        ("ambiguous-2021", "ambiguous_identity"),
    }
    ambiguous_blocker = next(item for item in blockers if item["work_id"] == "ambiguous-2021")
    assert len(ambiguous_blocker["candidates"]) == 2


def test_override_conflict_and_provider_identity_conflict_fail_closed(tmp_path):
    rebound = _work("rebound-2020", "Rebound", 2020, tmdb_id=40)
    imdb_conflict = _work("conflict-2021", "Conflict", 2021, tmdb_id=41, imdb_id="tt-old0041")
    repo = _repo(tmp_path, rebound, imdb_conflict)
    provider = FakeProvider(fetched={41: _metadata(41, "Conflict", 2021, imdb_id="tt-new0041")})
    command = _command({"rebound-2020": ProviderWorkRef("movie", 99)})

    with pytest.raises(Exception) as caught:
        _planner()(repo, command, provider, now=NOW)

    error_type = getattr(domain_errors, "MetadataRefreshPreflightError")
    assert isinstance(caught.value, error_type)
    reasons = {(item["work_id"], item["reason"]) for item in caught.value.blockers}
    assert ("rebound-2020", "override_conflict") in reasons
    assert ("conflict-2021", "identity_conflict") in reasons


def test_provider_outage_propagates_without_partial_refresh(tmp_path):
    repo = _repo(tmp_path, _work("offline-2020", "Offline", 2020, tmdb_id=50))
    with pytest.raises(ProviderUnavailableError):
        _planner()(repo, _command(), FakeProvider(fail=True), now=NOW)


def test_absent_provider_fields_are_conservative_and_no_change_does_not_touch_updated_at(tmp_path):
    existing_external = {
        "runtime_min": 120,
        "genres": ["genre.drama"],
        "external_metrics": {"imdb": {"score": 8.0, "votes": 1, "observed_at": "2026-01-01"}},
        "provenance": {"provider": "tmdb", "provider_id": 60, "fetched_at": "2026-01-01T00:00:00Z"},
    }
    work = _work("steady-2020", "Steady", 2020, tmdb_id=60, external=existing_external)
    work["identity"]["release_date"] = "2020-02-03"
    provider_external = {
        "genres": ["genre.drama"],
        "external_metrics": {},
        "provenance": existing_external["provenance"],
    }
    provider = FakeProvider(fetched={60: _metadata(60, "Steady", 2020, external=provider_external)})
    repo = _repo(tmp_path, work)

    plan = _planner()(repo, _command(), provider, now=NOW)

    assert plan.documents == {}
    assert plan.changed_entities == ()
    assert plan.details["changed_count"] == 0
    assert plan.details["no_change_count"] == 1
