import json
from pathlib import Path

import pytest

from media.domain.errors import ProviderUnavailableError
from media.providers.base import ProviderCandidate
from media.providers.tmdb import TMDBProvider

FIXTURES = Path(__file__).parents[1] / "fixtures" / "tmdb"


def fake_request(url, headers):
    if "/search/multi" in url:
        return json.loads((FIXTURES / "search_arrival.json").read_text(encoding="utf-8"))
    if "/movie/329865" in url:
        return json.loads((FIXTURES / "movie_arrival.json").read_text(encoding="utf-8"))
    raise AssertionError(url)


def test_tmdb_normalizes_arrival_identity_and_provenance():
    provider = TMDBProvider("token", request_json=fake_request)
    candidates = provider.search_work("Arrival", 2016)
    assert [(c.media_type, c.provider_id) for c in candidates] == [("movie", 329865)]
    metadata = provider.fetch_work("movie", 329865)
    assert metadata.identity["title_original"] == "Arrival"
    assert metadata.identity["title_ru"] == "Прибытие"
    assert metadata.identity["year"] == 2016
    assert metadata.identity["external_ids"]["tmdb"] == {"media_type": "movie", "id": 329865}
    assert metadata.identity["external_ids"]["imdb"] == "tt2543164"
    assert metadata.external["runtime_min"] == 116
    assert metadata.external["provenance"]["provider"] == "tmdb"
    assert metadata.external["directors"][0]["name"] == "Denis Villeneuve"


def test_search_filters_out_person_results():
    assert all(
        candidate.media_type in {"movie", "tv"}
        for candidate in TMDBProvider("token", request_json=fake_request).search_work("Arrival")
    )


def test_provider_wraps_transport_failure():
    def broken(url, headers):
        raise OSError("offline")

    with pytest.raises(ProviderUnavailableError):
        TMDBProvider("token", request_json=broken).search_work("Arrival")


def test_find_by_imdb_returns_only_movie_candidates():
    seen_urls: list[str] = []

    def request_json(url, headers):
        seen_urls.append(url)
        return {
            "movie_results": [
                {
                    "id": 329865,
                    "title": "Прибытие",
                    "original_title": "Arrival",
                    "release_date": "2016-11-10",
                }
            ],
            "tv_results": [
                {
                    "id": 123,
                    "name": "Arrival",
                    "original_name": "Arrival",
                    "first_air_date": "2016-01-01",
                }
            ],
        }

    provider = TMDBProvider("token", request_json=request_json)
    assert provider.find_by_imdb("tt2543164") == [
        ProviderCandidate("movie", 329865, "Прибытие", "Arrival", 2016)
    ]
    assert "/find/tt2543164" in seen_urls[0]
    assert "external_source=imdb_id" in seen_urls[0]


def test_fetch_work_reports_unmapped_genre_ids_without_emitting_unknown_terms():
    def request_json(url, headers):
        return {
            "id": 329865,
            "title": "Прибытие",
            "original_title": "Arrival",
            "release_date": "2016-11-10",
            "runtime": 116,
            "original_language": "en",
            "production_countries": [{"iso_3166_1": "US"}],
            "status": "Released",
            "overview": "Overview",
            "genres": [{"id": 878}, {"id": 10749}, {"id": 18}],
            "vote_average": 7.6,
            "vote_count": 18000,
            "external_ids": {"imdb_id": "tt2543164"},
            "credits": {"crew": [], "cast": []},
        }

    metadata = TMDBProvider("token", request_json=request_json).fetch_work("movie", 329865)
    assert metadata.external["genres"] == ["genre.science_fiction", "genre.drama"]
    assert metadata.unmapped_genre_ids == (10749,)
