from copy import deepcopy
from pathlib import Path

from media.tools.schema_utils import validate_against_schema

SCHEMAS = Path("media/schemas")


def base_work(fmt="movie"):
    return {
        "schema_version": 4,
        "id": "sample-2020",
        "entity_type": "work",
        "identity": {"format": fmt, "title_original": "Sample", "title_ru": "Пример", "year": 2020},
    }


def valid(doc, schema="work.schema.json"):
    errors = validate_against_schema(doc, schema, SCHEMAS)
    assert errors == [], errors


def invalid(doc, schema="work.schema.json"):
    assert validate_against_schema(doc, schema, SCHEMAS)


def test_movie_without_medium_or_external_ids_is_valid():
    valid(base_work())


def test_medium_if_present_is_closed_enum():
    doc = base_work(); doc["identity"]["medium"] = "animation"; valid(doc)
    doc["identity"]["medium"] = "puppets"; invalid(doc)


def test_partner_only_liked_signal_is_valid():
    doc = base_work(); doc["viewer_signals"] = {"partner": {"reaction": {"value": "liked", "source": "explicit", "confidence": "high"}}}; valid(doc)


def test_rating_and_reaction_are_independent_and_rating_has_half_step():
    doc = base_work(); doc["viewer_signals"] = {"primary": {"rating": {"score": 8.5, "source": "explicit", "confidence": "exact"}}}; valid(doc)
    doc["viewer_signals"]["primary"]["rating"]["score"] = 8.3; invalid(doc)


def test_tmdb_identity_is_composite_object():
    doc = base_work(); doc["identity"]["external_ids"] = {"tmdb": {"media_type": "movie", "id": 123}, "imdb": "tt1234567"}; valid(doc)
    doc["identity"]["external_ids"]["tmdb"] = 123; invalid(doc)


def test_seasonless_series_and_special_season_zero_are_valid():
    valid(base_work("series"))
    doc = base_work("series"); doc["seasons"] = [{"number": 0, "title": "Specials", "release_year": 2020, "episode_count": 2}]; valid(doc)


def test_movie_cannot_contain_seasons():
    doc = base_work("movie"); doc["seasons"] = [{"number": 1}]; invalid(doc)


def test_group_signal_reuses_rating_reaction_feedback_semantics():
    doc = base_work(); doc["group_signals"] = {"couple": {"reaction": {"value": "liked", "source": "explicit", "confidence": "high"}, "rating": {"score": 9.0, "source": "explicit", "confidence": "exact"}, "feedback": {"summary": "Хорошо вдвоём", "signals": []}, "suitability": {"strength": 3}}}; valid(doc)


def test_metadata_layers_people_assets_and_traits_are_structured():
    doc = base_work(); doc["metadata"] = {"external": {"runtime_min": 120, "directors": [{"name": "Director", "external_ids": {"tmdb": 12, "imdb": "nm0000012"}}], "assets": {"poster": {"provider": "tmdb", "path": "/poster.jpg"}}}, "overrides": {"runtime_min": 121}, "semantic": {"traits": [{"term": "story.intrigue", "source": "llm_inferred", "confidence": "medium"}]}}; valid(doc)
    broken = deepcopy(doc); broken["metadata"]["external"]["directors"] = ["Director"]; invalid(broken)


def test_manual_overrides_are_allowlisted_not_provider_shaped_escape_hatch():
    doc = base_work(); doc["metadata"] = {"external": {}, "overrides": {"synopsis_short": "Manual"}, "semantic": {}}; valid(doc)
    doc["metadata"]["overrides"]["random_provider_blob"] = {"x": 1}; invalid(doc)


def test_collection_supports_sparse_signals_without_propagating_members():
    doc = {"schema_version": 4, "id": "series-x", "entity_type": "collection", "name_ru": "Серия X", "name_original": "Series X", "member_ids": [], "viewer_signals": {"primary": {"rating": {"score": 8.5, "source": "inferred", "confidence": "medium"}}}}
    valid(doc, "collection.schema.json")
