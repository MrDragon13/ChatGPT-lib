from __future__ import annotations

from pathlib import Path
from typing import Any

from media.domain.commands import AssessCandidateRequest, TasteContextRequest
from media.domain.errors import CommandValidationError, NotFoundError
from media.domain.types import WorkRef
from media.repository.yaml_repo import YamlRepository, WorkRecord
from media.service.resolve import resolve_target_kind, resolve_work
from media.service.semantic_evidence import classify_candidate_traits
from media.service.similarity import similarities_for_endpoint, work_ref_identity
from media.service.taste_context import build_taste_context
from media.tools.build_profiles import build_profile


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


def _numeric_rating(signal: dict[str, Any] | None) -> bool:
    rating = (signal or {}).get("rating") or {}
    score = rating.get("score")
    return isinstance(score, (int, float)) and not isinstance(score, bool)


def _has_semantic_fingerprint(work: dict[str, Any]) -> bool:
    traits = (((work.get("metadata") or {}).get("semantic") or {}).get("traits") or [])
    return any(isinstance(item, dict) and isinstance(item.get("term"), str) and item.get("term") for item in traits)


def _supporting_work_ids(taste_context: dict[str, Any], canonical_work_ids: set[str]) -> set[str]:
    result: set[str] = set()
    for item in taste_context.get("recent_feedback") or []:
        work_id = item.get("id") if isinstance(item, dict) else None
        if work_id in canonical_work_ids:
            result.add(work_id)
    representative = taste_context.get("representative") or {}
    for bucket in ("high", "low"):
        for item in representative.get(bucket) or []:
            work_id = item.get("id") if isinstance(item, dict) else None
            if work_id in canonical_work_ids:
                result.add(work_id)
    return result


def _profile_rated_work_ids(
    works: dict[str, dict[str, Any]],
    *,
    target: str,
    members: list[str],
) -> set[str]:
    result: set[str] = set()
    for work_id, work in works.items():
        viewer_signals = work.get("viewer_signals") or {}
        if not members:
            if _numeric_rating(viewer_signals.get(target)):
                result.add(work_id)
            continue

        if any(_numeric_rating(viewer_signals.get(member)) for member in members):
            result.add(work_id)
            continue
        group_signals = work.get("group_signals") or {}
        if _numeric_rating(group_signals.get(target)):
            result.add(work_id)
    return result


def _candidate_trait_terms(candidate: dict[str, Any]) -> list[str]:
    fingerprint = candidate.get("semantic_fingerprint") or []
    return [
        item["term"]
        for item in fingerprint
        if isinstance(item, dict) and isinstance(item.get("term"), str) and item.get("term")
    ]


def _assessment_coverage(
    repo: YamlRepository,
    media_root: Path,
    *,
    target: str,
    candidate: dict[str, Any],
    taste_context: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    viewers, groups = repo.configured_targets()
    members = list(groups.get(target, [])) if target in groups else []
    works = {record.id: record.data for record in repo.iter_works()}
    canonical_work_ids = set(works)

    traits = _candidate_trait_terms(candidate)
    profile = build_profile(media_root, target)
    classification = classify_candidate_traits(traits, profile.get("affinities") or {})
    supporting_ids = _supporting_work_ids(taste_context, canonical_work_ids)
    rated_ids = _profile_rated_work_ids(works, target=target, members=members)

    supporting_with_fingerprint = sum(_has_semantic_fingerprint(works[work_id]) for work_id in supporting_ids)
    rated_with_fingerprint = sum(_has_semantic_fingerprint(works[work_id]) for work_id in rated_ids)
    candidate_has_fingerprint = bool(traits)
    candidate_directional_matches = int(classification["directional_match_count"])

    coverage = {
        "candidate_has_fingerprint": candidate_has_fingerprint,
        "candidate_directional_matches": candidate_directional_matches,
        "supporting_works_total": len(supporting_ids),
        "supporting_works_with_fingerprint": supporting_with_fingerprint,
        "profile_rated_works_total": len(rated_ids),
        "profile_rated_works_with_fingerprint": rated_with_fingerprint,
    }

    limitations: list[str] = []
    if not candidate_has_fingerprint:
        limitations.append("no_candidate_semantic_fingerprint")
    if candidate_directional_matches == 0:
        limitations.append("no_candidate_personalized_basis")
    supporting_partial = bool(supporting_ids) and supporting_with_fingerprint < len(supporting_ids)
    rated_partial = bool(rated_ids) and rated_with_fingerprint < len(rated_ids)
    if supporting_partial or rated_partial:
        limitations.append("partial_semantic_coverage")

    return coverage, limitations


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
    assessment_coverage, limitations = _assessment_coverage(
        repo,
        media_root,
        target=request.target,
        candidate=candidate,
        taste_context=taste_context,
    )
    return {
        "schema_version": 1,
        "target": request.target,
        "request": {"text": request.text},
        "candidate": candidate,
        "taste_context": taste_context,
        "similarities": similarities,
        "assessment_coverage": assessment_coverage,
        "limitations": limitations,
    }
