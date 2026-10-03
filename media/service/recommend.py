from __future__ import annotations

from pathlib import Path
from typing import Any

from media.domain.commands import RecommendContextRequest
from media.domain.errors import UnknownTargetError
from media.repository.index_repo import IndexRepository
from media.repository.yaml_repo import YamlRepository
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


def build_recommend_context(media_root: Path, request: RecommendContextRequest) -> dict[str, Any]:
    media_root = Path(media_root)
    repo = YamlRepository(media_root)
    viewers, groups = repo.configured_targets()
    if request.target not in viewers and request.target not in groups:
        raise UnknownTargetError(f"unknown target: {request.target}")
    members = groups.get(request.target, [])
    affinities = (_profile(media_root, request.target).get("affinities") or {})
    similarity_evidence = _similarities_by_canonical_work(media_root, request.target)
    candidates: list[tuple[int, int, str, dict[str, Any]]] = []
    for row in IndexRepository(media_root / "generated" / "index.jsonl").rows():
        runtime = row.get("runtime_min")
        if request.runtime_max is not None and runtime is not None and runtime > request.runtime_max:
            continue
        interest = (row.get("interest") or {}).get(request.target) or {}
        if not request.include_not_interested and interest.get("state") == "not_interested":
            continue
        viewer = row.get("viewer") or {}
        if request.only_unwatched:
            if request.target in viewers:
                if (viewer.get(request.target) or {}).get("viewing") == "watched":
                    continue
            elif members and all((viewer.get(member) or {}).get("viewing") == "watched" for member in members):
                continue
        strengths = []
        concerns = []
        matched = 0
        for trait in row.get("traits") or []:
            affinity = affinities.get(trait)
            if not affinity:
                continue
            matched += 1
            score = affinity.get("score", 0)
            if score > 0: strengths.append(trait)
            elif score < 0: concerns.append(trait)
        evidence = {
            "strengths": sorted(strengths),
            "concerns": sorted(concerns),
            "similarities": list(similarity_evidence.get(row["id"], [])),
        }
        if request.target in viewers:
            evidence["viewing"] = {request.target: (viewer.get(request.target) or {}).get("viewing")}
        else:
            evidence["viewing"] = {member: (viewer.get(member) or {}).get("viewing") for member in members}
        public = {"id": row["id"], "title_original": row.get("title_original"), "title_ru": row.get("title_ru"), "year": row.get("year"), "runtime_min": runtime, "genres": row.get("genres") or [], "traits": row.get("traits") or [], "interest": interest, "evidence": evidence}
        priority = int(interest.get("priority") or 0)
        candidates.append((-matched, -priority, row["id"], public))
    candidates.sort(key=lambda item: item[:3])
    return {"target": request.target, "request": {"text": request.text, "only_unwatched": request.only_unwatched, "runtime_max": request.runtime_max, "include_not_interested": request.include_not_interested}, "candidates": [item[3] for item in candidates[: request.limit]]}
