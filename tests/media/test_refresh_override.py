from __future__ import annotations

from datetime import datetime, timezone

from media.domain.commands import ProviderWorkRef, RefreshMetadataCommand
from media.providers.base import CanonicalMetadata
from media.repository.yaml_repo import YamlRepository
from media.service.refresh import plan_refresh_metadata
from media.tools.common import dump_yaml


def test_explicit_override_can_resolve_title_variant_without_weakening_identity_checks(tmp_path):
    work = {
        "schema_version": 4,
        "id": "variant-2020",
        "entity_type": "work",
        "identity": {
            "format": "movie",
            "title_original": "Canonical: Title",
            "title_ru": "Каноническое название",
            "year": 2020,
        },
        "provenance": {"created_at": "2026-01-01", "updated_at": "2026-01-01"},
    }
    media_root = tmp_path / "media"
    dump_yaml(media_root / "data" / "works" / "variant-2020.yaml", work)

    class Provider:
        def fetch_work(self, media_type, provider_id):
            assert (media_type, provider_id) == ("movie", 77)
            return CanonicalMetadata(
                identity={
                    "format": "movie",
                    "title_original": "Canonical Title",
                    "title_ru": "Каноническое название",
                    "year": 2020,
                    "release_date": "2020-01-02",
                    "external_ids": {
                        "tmdb": {"media_type": "movie", "id": 77},
                        "imdb": "tt0000077",
                    },
                },
                external={
                    "runtime_min": 100,
                    "provenance": {
                        "provider": "tmdb",
                        "provider_id": 77,
                        "fetched_at": "2026-10-01T12:00:00Z",
                    },
                },
            )

        def search_work(self, title, year=None):
            raise AssertionError("explicit override must bypass title search")

        def find_by_imdb(self, imdb_id):
            raise AssertionError("explicit override must bypass IMDb lookup")

    command = RefreshMetadataCommand(
        1,
        "123e4567-e89b-42d3-a456-426614174499",
        "all_movies",
        {"variant-2020": ProviderWorkRef("movie", 77)},
    )

    plan = plan_refresh_metadata(
        YamlRepository(media_root),
        command,
        Provider(),
        now=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )

    assert plan.changed_entities == ("variant-2020",)
    assert plan.documents["media/data/works/variant-2020.yaml"]["identity"]["external_ids"]["tmdb"]["id"] == 77
