from __future__ import annotations

from pathlib import Path
from typing import Any

from media.domain.commands import RecommendContextRequest
from media.domain.errors import UnknownTargetError
from media.repository.yaml_repo import YamlRepository
from media.service.reanalysis_status import build_reanalysis_context
from media.service.recommendation_pool import eligible_local_candidates
from media.service.semantic_evidence import classify_candidate_traits
from media.service.similarity import similarity_context
from media.tools.common import load_yaml


def _profile(media_root: Path, target: str) -> dict[str, Any]:
    path = media_root / "generated" / "profiles" / f"{target}.yaml"
    if not path.exists():
        return {"target": target, "affinities": {}}
    doc = load_yaml(path) or {}
    return doc if isinstance(doc, dict) else {"target": target, "affinities": {}}


def _similarities_by_canonical_work(media_root: Path, target: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for relation in similarity_context(media_root, target):
        left = relation["left"]
        right = relation["right"]
        shared = {
            "terms": list(relation.get("terms") or []),
            "note": relation.get("note"),
            "updated_at": relation.get("updated_at"),
            "provenance": dict(relation.get("provenance") or {}),
        }
        if left.get("kind") == "canonical":
            result.setdefault(left["work_id"], []).append({"other": dict(right), **shared})
        if right.get("kind") == "canonical":
            result.setdefault(right["work_id"], []).append({"other": dict(left), **shared})
    return result


def _ranking_key(classification: dict[str, Any], priority: int, candidate_id: str) -> tuple[int, int, int, int, str]:
    if classification["ranking_basis"] == "trait_overlap":
        return (
            0,
            -int(classification["net_directional_count"]),
            int(classification["concerns_count"]),
            -priority,
            candidate_id,
        )
    return (1, 0, 0, -priority, candidate_id)


def _coverage(rows: list[dict[str, Any]], returned: list[dict[str, Any]]) -> dict[str, int]:
    pool_with_fingerprint = sum(1 for item in rows if item["fingerprint_trait_count"] > 0)
    pool_with_personalized_basis = sum(1 for item in rows if item["ranking_basis"] == "trait_overlap")
    returned_with_fingerprint = sum(1 for item in returned if item["fingerprint_trait_count"] > 0)
    returned_with_personalized_basis = sum(1 for item in returned if item["ranking_basis"] == "trait_overlap")
    return {
        "pool_total": len(rows),
        "pool_with_fingerprint": pool_with_fingerprint,
        "pool_with_personalized_basis": pool_with_personalized_basis,
        "pool_fallback": len(rows) - pool_with_personalized_basis,
        "returned_total": len(returned),
        "returned_with_fingerprint": returned_with_fingerprint,
        "returned_with_personalized_basis": returned_with_personalized_basis,
        "returned_fallback": len(returned) - returned_with_personalized_basis,
    }


def _limitations(coverage: dict[str, int]) -> list[str]:
    result: list[str] = []
    if coverage["pool_total"] > 0 and coverage["pool_with_fingerprint"] < coverage["pool_total"]:
        result.append("partial_semantic_coverage")
    if coverage["returned_fallback"] > 0:
        result.append("fallback_candidates_present")
    if coverage["pool_total"] > 0 and coverage["pool_with_personalized_basis"] == 0:
        result.append("no_personalized_candidates")
    return result


def build_recommend_context(media_root: Path, request: RecommendContextRequest) -> dict[str, Any]:
    media_root = Path(media_root)
    repo = YamlRepository(media_root)
    viewers, groups = repo.configured_targets()
    if request.target not in viewers and request.target not in groups:
        raise UnknownTargetError(f"unknown target: {request.target}")
    members = groups.get(request.target, [])
    affinities = (_profile(media_root, request.target).get("affinities") or {})
    similarity_evidence = _similarities_by_canonical_work(media_root, request.target)
    ranked: list[tuple[tuple[int, int, int, int, str], dict[str, Any], dict[str, Any]]] = []
    rows = eligible_local_candidates(
        media_root,
        target=request.target,
        only_unwatched=request.only_unwatched,
        include_not_interested=request.include_not_interested,
        runtime_max=request.runtime_max,
    )
    classified_pool: list[dict[str, Any]] = []
    for row in rows:
        runtime = row.get("runtime_min")
        interest = (row.get("interest") or {}).get(request.target) or {}
        viewer = row.get("viewer") or {}
        classification = classify_candidate_traits(row.get("traits") or [], affinities)
        pool_item = {
            "fingerprint_trait_count": classification["fingerprint_trait_count"],
            "ranking_basis": classification["ranking_basis"],
        }
        classified_pool.append(pool_item)
        evidence = {
            "strengths": sorted(classification["strengths"]),
            "concerns": sorted(classification["concerns"]),
            "evidence_details": classification["evidence_details"],
            "similarities": list(similarity_evidence.get(row["id"], [])),
        }
        if request.target in viewers:
            evidence["viewing"] = {request.target: (viewer.get(request.target) or {}).get("viewing")}
        else:
            evidence["viewing"] = {
                member: (viewer.get(member) or {}).get("viewing") for member in members
            }
        public = {
            "id": row["id"],
            "title_original": row.get("title_original"),
            "title_ru": row.get("title_ru"),
            "year": row.get("year"),
            "runtime_min": runtime,
            "genres": row.get("genres") or [],
            "traits": row.get("traits") or [],
            "interest": interest,
            "ranking_basis": classification["ranking_basis"],
            "fallback_reason": classification["fallback_reason"],
            "evidence": evidence,
        }
        priority = int(interest.get("priority") or 0)
        ranked.append((_ranking_key(classification, priority, row["id"]), public, pool_item))
    ranked.sort(key=lambda item: item[0])
    returned_ranked = ranked[: request.limit]
    returned_internal = [item[2] for item in returned_ranked]
    coverage = _coverage(classified_pool, returned_internal)
    reanalysis = build_reanalysis_context(media_root, request.target)
    limitations = _limitations(coverage)
    if coverage["pool_total"] == 0:
        limitations.append("empty_library")
    if reanalysis["due"]:
        limitations.append("taste_reanalysis_due")
    return {
        "target": request.target,
        "request": {
            "text": request.text,
            "only_unwatched": request.only_unwatched,
            "runtime_max": request.runtime_max,
            "include_not_interested": request.include_not_interested,
        },
        "coverage": coverage,
        "limitations": limitations,
        "reanalysis": reanalysis,
        "candidates": [item[1] for item in returned_ranked],
    }
