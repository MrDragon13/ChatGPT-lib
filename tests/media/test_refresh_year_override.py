from __future__ import annotations

from datetime import datetime, timezone

import pytest

from media.domain.commands import ProviderWorkRef, RefreshMetadataCommand
from media.domain.errors import MetadataRefreshPreflightError
from media.providers.base import CanonicalMetadata, ProviderCandidate
from media.repository.yaml_repo import YamlRepository
from media.service.refresh import plan_refresh_metadata
from media.tools.common import dump_yaml


def _repo(tmp_path, *, year: int = 2019) -> YamlRepository:
    work = {
        "schema_version": 4,
        "id": "gentlemen-2019",
        "entity_type": "work",
        "identity": {
            "format": "movie",
            "title_original": "The Gentlemen",
            "title_ru": "Джентльмены",
            "year": year,
        },
        "viewer_signals": {
            "primary": {
                "viewing": {"status": "dropped"},
                "feedback": {"summary": "keep me", "signals": []},
            }
        },
        "provenance": {"created_at": "2026-01-01", "updated_at": "2026-01-01"},
    }
    media_root = tmp_path / "media"
    dump_yaml(media_root / "data" / "works" / "gentlemen-2019.yaml", work)
    return YamlRepository(media_root)


class Provider:
    def search_work(self, title, year=None):
        assert title == "The Gentlemen"
        assert year == 2020
        return [ProviderCandidate("movie", 522627, "Джентльмены", "The Gentlemen", 2020)]

    def find_by_imdb(self, imdb_id):
        raise AssertionError("IMDb lookup is not expected")

    def fetch_work(self, media_type, provider_id):
        assert (media_type, provider_id) == ("movie", 522627)
        return CanonicalMetadata(
            identity={
                "format": "movie",
                "title_original": "The Gentlemen",
                "title_ru": "Джентльмены",
                "year": 2020,
                "release_date": "2020-01-01",
                "external_ids": {
                    "tmdb": {"media_type": "movie", "id": 522627},
                    "imdb": "tt8367814",
                },
            },
            external={
                "runtime_min": 113,
                "provenance": {
                    "provider": "tmdb",
                    "provider_id": 522627,
                    "fetched_at": "2026-10-01T12:00:00Z",
                },
            },
        )


def test_year_override_is_used_for_lookup_and_atomically_corrects_canonical_year(tmp_path):
    repo = _repo(tmp_path)
    command = RefreshMetadataCommand(
        1,
        "123e4567-e89b-42d3-a456-426614174498",
        "all_movies",
        {},
        {"gentlemen-2019": 2020},
    )

    plan = plan_refresh_metadata(repo, command, Provider(), now=datetime(2026, 10, 1, tzinfo=timezone.utc))

    updated = plan.documents["media/data/works/gentlemen-2019.yaml"]
    assert updated["identity"]["year"] == 2020
    assert updated["identity"]["external_ids"]["tmdb"]["id"] == 522627
    assert updated["viewer_signals"]["primary"]["feedback"]["summary"] == "keep me"


def test_year_override_must_match_provider_identity(tmp_path):
    repo = _repo(tmp_path)
    command = RefreshMetadataCommand(
        1,
        "123e4567-e89b-42d3-a456-426614174497",
        "all_movies",
        {"gentlemen-2019": ProviderWorkRef("movie", 522627)},
        {"gentlemen-2019": 2021},
    )

    with pytest.raises(MetadataRefreshPreflightError) as exc:
        plan_refresh_metadata(repo, command, Provider(), now=datetime(2026, 10, 1, tzinfo=timezone.utc))

    assert exc.value.blockers[0]["work_id"] == "gentlemen-2019"
    assert exc.value.blockers[0]["reason"] == "identity_conflict"
