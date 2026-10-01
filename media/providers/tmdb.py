from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from media.domain.errors import ProviderUnavailableError
from media.providers.base import CanonicalMetadata, ProviderCandidate

RequestJson = Callable[[str, Mapping[str, str]], Mapping[str, Any]]

TMDB_GENRE_TERM_BY_ID = {
    878: "genre.science_fiction",
    18: "genre.drama",
    28: "genre.action",
    12: "genre.adventure",
    35: "genre.comedy",
    80: "genre.crime",
    9648: "genre.mystery",
    53: "genre.thriller",
}


def _year(value: str | None) -> int | None:
    if not value or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _default_request_json(url: str, headers: Mapping[str, str]) -> Mapping[str, Any]:
    request = Request(url, headers=dict(headers))
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("TMDB response must be an object")
    return payload


class TMDBProvider:
    def __init__(self, token: str, request_json: RequestJson | None = None):
        self.token = token
        self.request_json = request_json or _default_request_json
        self.base_url = "https://api.themoviedb.org/3"

    def _get(self, path: str, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        query = urlencode({k: v for k, v in (params or {}).items() if v is not None})
        url = f"{self.base_url}{path}" + (f"?{query}" if query else "")
        try:
            return self.request_json(url, {"Authorization": f"Bearer {self.token}", "Accept": "application/json"})
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(f"TMDB request failed: {exc}") from exc

    def search_work(self, title: str, year: int | None = None) -> list[ProviderCandidate]:
        payload = self._get("/search/multi", {"query": title, "language": "ru-RU", "include_adult": "false"})
        candidates: list[ProviderCandidate] = []
        for item in payload.get("results") or []:
            media_type = item.get("media_type")
            if media_type not in {"movie", "tv"}:
                continue
            localized = item.get("title") if media_type == "movie" else item.get("name")
            original = item.get("original_title") if media_type == "movie" else item.get("original_name")
            date_value = item.get("release_date") if media_type == "movie" else item.get("first_air_date")
            if not isinstance(item.get("id"), int):
                continue
            candidates.append(ProviderCandidate(media_type, item["id"], str(localized or original or ""), str(original or localized or ""), _year(date_value)))
        return candidates

    def fetch_work(self, media_type: str, provider_id: int) -> CanonicalMetadata:
        payload = self._get(f"/{media_type}/{provider_id}", {"language": "ru-RU", "append_to_response": "external_ids,credits,release_dates,content_ratings"})
        localized = payload.get("title") if media_type == "movie" else payload.get("name")
        original = payload.get("original_title") if media_type == "movie" else payload.get("original_name")
        date_value = payload.get("release_date") if media_type == "movie" else payload.get("first_air_date")
        year = _year(date_value)
        show_type = payload.get("type") if media_type == "tv" else None
        canonical_format = "movie" if media_type == "movie" else ("miniseries" if show_type == "Miniseries" else "series")
        external_ids = payload.get("external_ids") or {}
        identity: dict[str, Any] = {
            "format": canonical_format,
            "title_original": str(original or localized or f"TMDB {provider_id}"),
            "title_ru": str(localized or original or f"TMDB {provider_id}"),
            "year": year,
            "release_date": date_value or None,
            "external_ids": {"tmdb": {"media_type": media_type, "id": provider_id}, "imdb": external_ids.get("imdb_id") or None},
        }
        runtime = payload.get("runtime")
        if runtime is None and media_type == "tv":
            episode_runtime = payload.get("episode_run_time") or []
            runtime = episode_runtime[0] if episode_runtime else None
        crew = (payload.get("credits") or {}).get("crew") or []
        cast = (payload.get("credits") or {}).get("cast") or []
        directors = [self._person(person) for person in crew if person.get("job") == "Director"]
        writers = [self._person(person) for person in crew if person.get("job") in {"Writer", "Screenplay", "Teleplay"}]
        status_raw = str(payload.get("status") or "")
        status = "completed" if status_raw in {"Released", "Ended"} else "cancelled" if status_raw == "Canceled" else "ongoing" if status_raw in {"Returning Series", "In Production", "Planned"} else "unknown"
        external: dict[str, Any] = {
            "genres": [TMDB_GENRE_TERM_BY_ID[item["id"]] for item in payload.get("genres") or [] if item.get("id") in TMDB_GENRE_TERM_BY_ID],
            "runtime_min": runtime,
            "original_language": payload.get("original_language"),
            "countries": [str(item.get("iso_3166_1")) for item in payload.get("production_countries") or [] if item.get("iso_3166_1")],
            "production_status": status,
            "synopsis_short": payload.get("overview") or None,
            "directors": directors,
            "writers": writers,
            "main_cast": [self._person(person, character=True) for person in cast[:12]],
            "assets": {},
            "external_metrics": {"tmdb": {"score": payload.get("vote_average"), "votes": payload.get("vote_count"), "observed_at": datetime.now(timezone.utc).date().isoformat()}},
            "provenance": {"provider": "tmdb", "provider_id": provider_id, "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")},
        }
        if payload.get("poster_path"):
            external["assets"]["poster"] = {"provider": "tmdb", "path": payload["poster_path"]}
        if payload.get("backdrop_path"):
            external["assets"]["backdrop"] = {"provider": "tmdb", "path": payload["backdrop_path"]}
        if not external["assets"]:
            external.pop("assets")
        return CanonicalMetadata(identity=identity, external=external)

    @staticmethod
    def _person(person: Mapping[str, Any], character: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {"name": str(person.get("name") or "")}
        if character:
            result["character"] = person.get("character") or None
        if isinstance(person.get("id"), int):
            result["external_ids"] = {"tmdb": person["id"]}
        return result
