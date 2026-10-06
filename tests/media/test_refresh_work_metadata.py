from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from media.domain.commands import RefreshWorkMetadataCommand
from media.domain.errors import CommandValidationError, MetadataRefreshPreflightError
from media.domain.types import WorkRef
from media.providers.base import CanonicalMetadata, ProviderCandidate
from media.repository.yaml_repo import YamlRepository
from media.service.refresh import plan_refresh_work_metadata
from media.tools.common import dump_yaml

UUID = "123e4567-e89b-42d3-a456-426614174310"
NOW = datetime(2026, 10, 7, 0, 0, tzinfo=timezone.utc)


def _digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _work(work_id: str, title: str, year: int, *, tmdb_id=None, imdb_id=None):
    ids = {}
    if tmdb_id is not None:
        ids["tmdb"] = {"media_type": "movie", "id": tmdb_id}
    if imdb_id is not None:
        ids["imdb"] = imdb_id
    identity = {"format": "movie", "title_original": title, "title_ru": title, "year": year}
    if ids:
        identity["external_ids"] = ids
    return {
        "schema_version": 4,
        "id": work_id,
        "entity_type": "work",
        "identity": identity,
        "metadata": {
            "external": {"runtime_min": 90},
            "semantic": {"traits": [{"term": "tone.serious", "source": "llm_inferred", "confidence": "medium"}]},
        },
        "viewer_signals": {
            "primary": {
                "viewing": {"status": "watched"},
                "rating": {"score": 8, "source": "explicit", "confidence": "exact"},
            }
        },
        "provenance": {"created_at": "2026-01-01", "updated_at": "2026-01-01"},
    }


def _metadata(provider_id: int, title: str, year: int, *, imdb_id=None):
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
        external={
            "runtime_min": 123,
            "genres": ["genre.drama"],
            "provenance": {"provider": "tmdb", "provider_id": provider_id, "fetched_at": "2026-10-07T00:00:00Z"},
        },
    )


class FakeProvider:
    def __init__(self, *, fetched=None, imdb=None, searched=None):
        self.fetched = dict(fetched or {})
        self.imdb = dict(imdb or {})
        self.searched = dict(searched or {})
        self.calls = []

    def fetch_work(self, media_type, provider_id):
        self.calls.append(("fetch", media_type, provider_id))
        return self.fetched[provider_id]

    def find_by_imdb(self, imdb_id):
        self.calls.append(("imdb", imdb_id))
        return list(self.imdb.get(imdb_id, ()))

    def search_work(self, title, year=None):
        self.calls.append(("search", title, year))
        return list(self.searched.get((title, year), ()))


def _repo(tmp_path, *works):
    media = tmp_path / "media"
    for work in works:
        dump_yaml(media / "data" / "works" / f"{work['id']}.yaml", work)
    return YamlRepository(media)


def _command(record):
    return RefreshWorkMetadataCommand(1, UUID, WorkRef(id=record.id), _digest(record.path))


def test_refresh_work_metadata_changes_only_selected_work_and_preserves_non_metadata_layers(tmp_path):
    first = _work("movie-a-2020", "Movie A", 2020, tmdb_id=10, imdb_id="tt0000010")
    second = _work("movie-b-2021", "Movie B", 2021, tmdb_id=11)
    repo = _repo(tmp_path, first, second)
    record = repo.get_work("movie-a-2020")
    provider = FakeProvider(fetched={10: _metadata(10, "Movie A", 2020, imdb_id="tt0000010")})

    plan = plan_refresh_work_metadata(repo, _command(record), provider, now=NOW)
    assert plan.changed_entities == ("movie-a-2020",)
    assert set(plan.documents) == {"media/data/works/movie-a-2020.yaml"}
    updated = plan.documents["media/data/works/movie-a-2020.yaml"]
    assert updated["viewer_signals"] == first["viewer_signals"]
    assert updated["metadata"]["semantic"] == first["metadata"]["semantic"]
    assert updated["metadata"]["external"]["runtime_min"] == 123
    assert plan.details["work_id"] == "movie-a-2020"
    assert plan.details["expected_work_digest"] == _digest(record.path)
    assert plan.details["work_digest"].startswith("sha256:")


def test_refresh_work_metadata_accepts_unique_imdb_resolution(tmp_path):
    work = _work("movie-a-2020", "Movie A", 2020, imdb_id="tt0000010")
    repo = _repo(tmp_path, work)
    record = repo.get_work("movie-a-2020")
    provider = FakeProvider(
        fetched={10: _metadata(10, "Movie A", 2020, imdb_id="tt0000010")},
        imdb={"tt0000010": [ProviderCandidate("movie", 10, "Movie A", "Movie A", 2020)]},
    )
    plan = plan_refresh_work_metadata(repo, _command(record), provider, now=NOW)
    assert plan.changed_entities == ("movie-a-2020",)
    assert ("imdb", "tt0000010") in provider.calls


def test_refresh_work_metadata_rejects_stale_digest_before_provider_access(tmp_path):
    work = _work("movie-a-2020", "Movie A", 2020, tmdb_id=10)
    repo = _repo(tmp_path, work)
    provider = FakeProvider(fetched={10: _metadata(10, "Movie A", 2020)})
    command = RefreshWorkMetadataCommand(1, UUID, WorkRef(id="movie-a-2020"), "sha256:" + "0" * 64)
    with pytest.raises(CommandValidationError, match="digest mismatch"):
        plan_refresh_work_metadata(repo, command, provider, now=NOW)
    assert provider.calls == []


@pytest.mark.parametrize(
    ("provider", "reason"),
    [
        (FakeProvider(searched={("Movie A", 2020): []}), "not_found"),
        (
            FakeProvider(searched={("Movie A", 2020): [
                ProviderCandidate("movie", 10, "Movie A", "Movie A", 2020),
                ProviderCandidate("movie", 11, "Movie A", "Movie A", 2020),
            ]}),
            "ambiguous_identity",
        ),
    ],
)
def test_refresh_work_metadata_identity_blockers_fail_closed(tmp_path, provider, reason):
    repo = _repo(tmp_path, _work("movie-a-2020", "Movie A", 2020))
    record = repo.get_work("movie-a-2020")
    with pytest.raises(MetadataRefreshPreflightError) as caught:
        plan_refresh_work_metadata(repo, _command(record), provider, now=NOW)
    assert caught.value.blockers[0]["work_id"] == "movie-a-2020"
    assert caught.value.blockers[0]["reason"] == reason


def test_refresh_work_metadata_no_change_still_binds_current_digest(tmp_path):
    work = _work("movie-a-2020", "Movie A", 2020, tmdb_id=10)
    work["identity"]["release_date"] = "2020-02-03"
    work["metadata"]["external"] = {
        "runtime_min": 123,
        "genres": ["genre.drama"],
        "provenance": {"provider": "tmdb", "provider_id": 10, "fetched_at": "2026-10-07T00:00:00Z"},
    }
    repo = _repo(tmp_path, work)
    record = repo.get_work("movie-a-2020")
    provider = FakeProvider(fetched={10: _metadata(10, "Movie A", 2020)})

    plan = plan_refresh_work_metadata(repo, _command(record), provider, now=NOW)
    assert plan.documents == {}
    assert plan.changed_entities == ()
    assert plan.details["work_id"] == "movie-a-2020"
    assert plan.details["work_digest"] == _digest(record.path)
