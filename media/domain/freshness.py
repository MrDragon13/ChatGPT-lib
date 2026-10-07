from __future__ import annotations

from typing import Any, Mapping


STATIC_METADATA_KEYS = (
    "genres",
    "runtime_min",
    "original_language",
    "countries",
    "production_status",
    "synopsis_short",
    "directors",
    "writers",
    "main_cast",
    "certifications",
    "content_warnings",
)


def _has_stable_identity(identity: Mapping[str, Any]) -> bool:
    external_ids = identity.get("external_ids") or {}
    if not isinstance(external_ids, Mapping):
        return False
    tmdb = external_ids.get("tmdb")
    imdb = external_ids.get("imdb")
    return bool(tmdb) or bool(imdb)


def evaluate_metadata_freshness(document: Mapping[str, Any]) -> Mapping[str, str]:
    identity = document.get("identity") or {}
    metadata = document.get("metadata") or {}
    external = metadata.get("external") or {}
    overrides = metadata.get("overrides") or {}

    identity_current = bool(
        isinstance(identity, Mapping)
        and identity.get("format")
        and identity.get("title_original")
        and identity.get("title_ru")
        and _has_stable_identity(identity)
    )

    static_current = any(
        key in external or key in overrides
        for key in STATIC_METADATA_KEYS
    )
    dynamic_metrics = external.get("external_metrics") if isinstance(external, Mapping) else None
    dynamic_current = isinstance(dynamic_metrics, Mapping) and bool(dynamic_metrics)

    return {
        "identity": "current" if identity_current else "missing",
        "static": "current" if static_current else "missing",
        "dynamic": "current" if dynamic_current else "missing",
    }
