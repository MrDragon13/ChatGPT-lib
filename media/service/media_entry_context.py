from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from media.domain.commands import MediaEntryContextRequest
from media.domain.digests import compute_viewer_digest
from media.domain.errors import NotFoundError
from media.domain.freshness import evaluate_metadata_freshness
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_target_kind, resolve_work
from media.tools.model import effective_metadata


def _requested_identity(request: MediaEntryContextRequest) -> dict[str, Any]:
    ref = request.work_ref
    values = {
        "id": ref.id,
        "title": ref.title,
        "year": ref.year,
        "tmdb_media_type": ref.tmdb_media_type,
        "tmdb_id": ref.tmdb_id,
        "imdb_id": ref.imdb_id,
    }
    return {key: value for key, value in values.items() if value is not None}


def _identity_view(document: dict[str, Any]) -> dict[str, Any]:
    identity = document.get("identity") or {}
    result = {
        "id": document.get("id"),
        "format": identity.get("format"),
        "medium": identity.get("medium"),
        "title_original": identity.get("title_original"),
        "title_ru": identity.get("title_ru"),
        "year": identity.get("year"),
        "release_date": identity.get("release_date"),
        "external_ids": copy.deepcopy(identity.get("external_ids") or {}),
    }
    return {key: value for key, value in result.items() if value is not None}


def _target_state(document: dict[str, Any], kind: str, target: str) -> dict[str, Any]:
    container_key = "viewer_signals" if kind == "viewer" else "group_signals"
    raw = ((document.get(container_key) or {}).get(target) or {})
    return {
        key: copy.deepcopy(raw[key])
        for key in ("viewing", "rating", "reaction", "feedback")
        if key in raw
    }


def _semantic_view(document: dict[str, Any]) -> dict[str, Any]:
    semantic = ((document.get("metadata") or {}).get("semantic") or {})
    traits = [
        copy.deepcopy(dict(item))
        for item in (semantic.get("traits") or [])
        if isinstance(item, dict)
    ]
    key = semantic.get("input_digest")
    status = "current" if key else ("legacy_unkeyed" if traits else "missing")
    return {
        "status": status,
        "key": key,
        "algorithm_version": semantic.get("algorithm_version"),
        "vocabulary_digest": semantic.get("vocabulary_digest"),
        "traits": traits,
    }


def build_media_entry_context(
    media_root: Path,
    request: MediaEntryContextRequest,
) -> dict[str, Any]:
    media_root = Path(media_root)
    repo = YamlRepository(media_root)
    target_kind = resolve_target_kind(repo, request.target)

    try:
        record = resolve_work(repo, request.work_ref)
    except NotFoundError:
        return {
            "schema_version": 1,
            "exists": False,
            "target": request.target,
            "requested_identity": _requested_identity(request),
        }

    document = dict(record.data)
    metadata = effective_metadata(document)
    interest = (((document.get("target_states") or {}).get(request.target) or {}).get("interest"))
    return {
        "schema_version": 1,
        "exists": True,
        "target": request.target,
        "identity": _identity_view(document),
        "viewer": {
            "state": _target_state(document, target_kind, request.target),
            "digest": compute_viewer_digest(document, request.target),
        },
        "metadata_freshness": dict(evaluate_metadata_freshness(document)),
        "facts": {
            key: copy.deepcopy(metadata[key])
            for key in ("runtime_min", "genres", "original_language")
            if key in metadata
        },
        "semantic": _semantic_view(document),
        "interest": copy.deepcopy(interest) if interest is not None else None,
    }
