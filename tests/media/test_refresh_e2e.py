from __future__ import annotations

from datetime import datetime, timezone

from media.commands.schema import parse_command
from media.providers.base import CanonicalMetadata, ProviderCandidate
from media.service.transaction import execute_command
from media.tools.common import dump_yaml, load_yaml
from media.tools.rebuild import check_generated, rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo

UUID = "123e4567-e89b-42d3-a456-426614174399"
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


class ThreeWayRefreshProvider:
    _records = {
        841: ("Dune", "Дюна", 1984, "tt0087182", 137),
        329865: ("Arrival", "Прибытие", 2016, "tt2543164", 116),
        900: ("The Secret", "Секрет", 2010, "tt0000900", 105),
    }

    def find_by_imdb(self, imdb_id):
        if imdb_id == "tt2543164":
            return [ProviderCandidate("movie", 329865, "Прибытие", "Arrival", 2016)]
        return []

    def search_work(self, title, year=None):
        if title == "The Secret" and year == 2010:
            return [ProviderCandidate("movie", 900, "Секрет", "The Secret", 2010)]
        return []

    def fetch_work(self, media_type, provider_id):
        original, ru, year, imdb, runtime = self._records[provider_id]
        return CanonicalMetadata(
            identity={
                "format": "movie",
                "title_original": original,
                "title_ru": ru,
                "year": year,
                "release_date": f"{year}-01-01",
                "external_ids": {
                    "tmdb": {"media_type": "movie", "id": provider_id},
                    "imdb": imdb,
                },
            },
            external={
                "runtime_min": runtime,
                "genres": ["genre.drama"],
                "original_language": "en",
                "countries": ["US"],
                "production_status": "completed",
                "synopsis_short": f"Synopsis for {original}",
                "directors": [],
                "writers": [],
                "main_cast": [],
                "external_metrics": {
                    "tmdb": {"score": 7.0, "votes": 100, "observed_at": "2026-10-01"}
                },
                "provenance": {
                    "provider": "tmdb",
                    "provider_id": provider_id,
                    "fetched_at": "2026-10-01T12:00:00Z",
                },
            },
        )


def test_e2e_bulk_refresh_covers_tmdb_imdb_and_title_paths_atomically(tmp_path):
    root = copy_fixture_repo(tmp_path)
    works = root / "media" / "data" / "works"
    keep = {"dune-1984.yaml", "arrival-2016.yaml", "hidden-name-2010.yaml"}
    for path in works.glob("*.yaml"):
        if path.name not in keep:
            path.unlink()

    arrival_path = works / "arrival-2016.yaml"
    arrival = load_yaml(arrival_path)
    arrival["identity"]["external_ids"].pop("tmdb")
    dump_yaml(arrival_path, arrival)

    before_signals = load_yaml(arrival_path)["viewer_signals"]
    before_interest = load_yaml(works / "dune-1984.yaml")["target_states"]
    rebuild_generated(root / "media")

    command = parse_command(
        {
            "schema_version": 1,
            "operation_id": UUID,
            "operation": "refresh_metadata",
            "scope": "all_movies",
        }
    )
    provider = ThreeWayRefreshProvider()

    first = execute_command(root, command, provider=provider, now=NOW)

    assert first.status == "applied"
    assert set(first.changed_entities) == {"dune-1984", "arrival-2016", "hidden-name-2010"}
    assert first.details["targeted_count"] == 3
    assert first.details["changed_count"] == 3
    assert check_generated(root / "media") == []

    dune = load_yaml(works / "dune-1984.yaml")
    arrival = load_yaml(arrival_path)
    secret = load_yaml(works / "hidden-name-2010.yaml")
    assert dune["target_states"] == before_interest
    assert arrival["viewer_signals"] == before_signals
    assert arrival["identity"]["external_ids"]["tmdb"]["id"] == 329865
    assert secret["identity"]["external_ids"]["tmdb"]["id"] == 900
    assert secret["metadata"]["external"]["runtime_min"] == 105

    receipt = root / ".media" / "operations" / f"{UUID}.json"
    assert receipt.exists()
    replay = execute_command(root, command, provider=provider, now=NOW)
    assert replay.status == "already_applied"
    assert replay.details == first.details
