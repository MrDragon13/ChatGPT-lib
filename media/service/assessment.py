from __future__ import annotations

from pathlib import Path
from typing import Any

from media.domain.commands import AssessCandidateRequest, TasteContextRequest
from media.domain.errors import CommandValidationError, NotFoundError
from media.domain.types import WorkRef
from media.repository.yaml_repo import YamlRepository, WorkRecord
from media.service.resolve import resolve_target_kind, resolve_work
from media.service.similarity import similarities_for_endpoint, work_ref_identity
from media.service.taste_context import build_taste_context


def _canonical_candidate(record: WorkRecord) -> tuple[dict[str, Any], dict[str, Any]]:
    data = record.data
    identity = data.get("identity") or {}
    semantic = ((data.get("metadata") or {}).get("semantic") or {})
    endpoint = {"kind": "canonical", "work_id": record.id}
    view = {
        "kind": "canonical",
        "id": record.id,
        "title_original": identity.get("title_original"),
        "title_ru": identity.get("title_ru"),
        "year": identity.get("year"),
        "semantic_fingerprint": [dict(item) for item in (semantic.get("traits") or []) if isinstance(item, dict)],
    }
    return endpoint, view


def _external_candidate(repo: YamlRepository, ref: WorkRef) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if ref.tmdb_media_type is not None and ref.tmdb_id is not None or ref.imdb_id is not None:
        _, endpoint = work_ref_identity(repo, ref)
        view = dict(endpoint)
        view["semantic_fingerprint"] = None
        return endpoint, view
    if ref.title:
        return None, {
            "kind": "external",
            "provider": None,
            "title": ref.title,
            "year": ref.year,
            "semantic_fingerprint": None,
        }
    raise CommandValidationError("candidate reference has no resolvable identity")


def _candidate_view(repo: YamlRepository, ref: WorkRef) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        record = resolve_work(repo, ref)
    except NotFoundError:
        return _external_candidate(repo, ref)
    return _canonical_candidate(record)


def build_candidate_assessment_context(media_root: Path, request: AssessCandidateRequest) -> dict[str, Any]:
    media_root = Path(media_root)
    repo = YamlRepository(media_root)
    resolve_target_kind(repo, request.target)
    endpoint, candidate = _candidate_view(repo, request.candidate)
    similarities = similarities_for_endpoint(media_root, request.target, endpoint) if endpoint is not None else []
    taste_context = build_taste_context(
        media_root,
        TasteContextRequest(
            schema_version=1,
            target=request.target,
            recent_limit=10,
            representative_limit=10,
        ),
    )
    return {
        "schema_version": 1,
        "target": request.target,
        "request": {"text": request.text},
        "candidate": candidate,
        "taste_context": taste_context,
        "similarities": similarities,
    }
