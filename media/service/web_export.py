from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from media.domain.commands import RecommendContextRequest, TasteContextRequest
from media.repository.index_repo import IndexRepository
from media.repository.yaml_repo import YamlRepository
from media.service.recommend import build_recommend_context
from media.service.similarity import similarity_context
from media.service.taste_context import build_taste_context
from media.tools.common import load_yaml
from media.tools.schema_utils import validate_against_schema


WEB_MANIFEST_SCHEMA_VERSION = 3


def _load_profile(media_root: Path, target: str) -> dict[str, Any]:
    path = media_root / "generated" / "profiles" / f"{target}.yaml"
    if not path.exists():
        return {"target": target, "affinities": {}}
    doc = load_yaml(path) or {}
    return dict(doc) if isinstance(doc, dict) else {"target": target, "affinities": {}}


def _web_vocabulary(media_root: Path) -> dict[str, dict[str, str]]:
    doc = load_yaml(media_root / "vocabulary.yaml") or {}
    terms = doc.get("terms") or {}
    result: dict[str, dict[str, str]] = {}
    for term_id in sorted(terms):
        meta = terms.get(term_id) or {}
        kind = meta.get("kind")
        label_ru = meta.get("label_ru")
        if isinstance(kind, str) and isinstance(label_ru, str):
            result[term_id] = {"kind": kind, "label_ru": label_ru}
    return result


def _manifest_v3_context(context: dict[str, Any]) -> dict[str, Any]:
    projected = dict(context)
    projected.pop("reanalysis", None)
    if "limitations" in projected:
        projected["limitations"] = [
            item for item in (projected.get("limitations") or [])
            if item != "taste_reanalysis_due"
        ]
    return projected


def _semantic_fingerprint(data: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = data.get("metadata") or {}
    semantic = metadata.get("semantic") or {}
    result: list[dict[str, Any]] = []
    for trait in semantic.get("traits") or []:
        if not isinstance(trait, dict):
            continue
        term = trait.get("term")
        source = trait.get("source")
        confidence = trait.get("confidence")
        if isinstance(term, str) and isinstance(source, str) and isinstance(confidence, str):
            result.append(dict(trait))
    return result


def _canonical_web_endpoint(work_id: str, work_data: dict[str, Any]) -> dict[str, Any]:
    identity = work_data.get("identity") or {}
    return {
        "kind": "canonical",
        "id": work_id,
        "title_original": identity.get("title_original"),
        "title_ru": identity.get("title_ru"),
        "year": identity.get("year"),
    }


def _web_similarity_other(endpoint: dict[str, Any], works: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if endpoint.get("kind") == "canonical":
        work_id = endpoint.get("work_id")
        if not isinstance(work_id, str) or work_id not in works:
            return None
        return _canonical_web_endpoint(work_id, works[work_id])
    if endpoint.get("kind") == "external":
        return dict(endpoint)
    return None


def _similarity_projection(
    media_root: Path,
    works: dict[str, dict[str, Any]],
    targets: list[str],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    projection = {
        work_id: {target: [] for target in targets}
        for work_id in works
    }
    for target in targets:
        for relation in similarity_context(media_root, target):
            left = relation["left"]
            right = relation["right"]
            shared = {
                "terms": list(relation.get("terms") or []),
                "note": relation.get("note"),
                "updated_at": relation.get("updated_at"),
                "provenance": dict(relation.get("provenance") or {}),
            }
            if left.get("kind") == "canonical" and isinstance(left.get("work_id"), str):
                left_id = left["work_id"]
                other = _web_similarity_other(right, works)
                if left_id in projection and other is not None:
                    projection[left_id][target].append({"other": other, **shared})
            if right.get("kind") == "canonical" and isinstance(right.get("work_id"), str):
                right_id = right["work_id"]
                other = _web_similarity_other(left, works)
                if right_id in projection and other is not None:
                    projection[right_id][target].append({"other": other, **shared})
    return projection


def _work_view(
    data: dict[str, Any],
    index_row: dict[str, Any],
    similarities: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    metadata = data.get("metadata") or {}
    provenance = data.get("provenance") or {}
    return {
        "id": data["id"],
        "identity": dict(data.get("identity") or {}),
        "metadata": {"external": dict(metadata.get("external") or {})},
        "viewer_signals": dict(data.get("viewer_signals") or {}),
        "group_signals": dict(data.get("group_signals") or {}),
        "interest": dict(index_row.get("interest") or {}),
        "traits": list(index_row.get("traits") or []),
        "semantic_fingerprint": _semantic_fingerprint(data),
        "similarities": {target: list(items) for target, items in similarities.items()},
        "collections": list(index_row.get("collections") or []),
        "provenance": {
            "created_at": provenance.get("created_at"),
            "updated_at": provenance.get("updated_at"),
        },
    }


def build_web_manifest(media_root: Path) -> dict[str, Any]:
    media_root = Path(media_root)
    repo = YamlRepository(media_root)
    viewers, groups = repo.configured_targets()
    sorted_viewers = sorted(viewers)
    sorted_groups = {group_id: list(groups[group_id]) for group_id in sorted(groups)}
    targets = sorted(viewers | set(groups))
    default_target = (
        "primary"
        if "primary" in viewers
        else (sorted_viewers[0] if sorted_viewers else ("couple" if "couple" in groups else None))
    )

    index_rows = {
        row["id"]: row
        for row in IndexRepository(media_root / "generated" / "index.jsonl").rows()
    }
    work_records = sorted(repo.iter_works(), key=lambda item: item.id)
    work_documents = {record.id: record.data for record in work_records}
    similarities = _similarity_projection(media_root, work_documents, targets)

    works = [
        _work_view(record.data, index_rows.get(record.id, {}), similarities[record.id])
        for record in work_records
    ]

    recommendations: dict[str, dict[str, Any]] = {}
    taste_contexts: dict[str, dict[str, Any]] = {}
    for target in targets:
        recommendation_request = RecommendContextRequest(
            schema_version=1,
            target=target,
            text=None,
            only_unwatched=True,
            runtime_max=None,
            include_not_interested=False,
            limit=24,
        )
        recommendations[target] = _manifest_v3_context(
            build_recommend_context(media_root, recommendation_request)
        )
        taste_request = TasteContextRequest(
            schema_version=1,
            target=target,
            recent_limit=12,
            representative_limit=8,
        )
        taste_contexts[target] = _manifest_v3_context(
            build_taste_context(media_root, taste_request)
        )

    manifest: dict[str, Any] = {
        "schema_version": WEB_MANIFEST_SCHEMA_VERSION,
        "default_target": default_target,
        "targets": {"viewers": sorted_viewers, "groups": sorted_groups},
        "vocabulary": _web_vocabulary(media_root),
        "profiles": {target: _load_profile(media_root, target) for target in targets},
        "taste_contexts": taste_contexts,
        "recommendations": recommendations,
        "works": works,
    }

    errors = validate_against_schema(manifest, "web-manifest.schema.json", media_root / "schemas")
    if errors:
        raise ValueError("invalid web manifest: " + "; ".join(errors))
    return manifest


def write_web_manifest(media_root: Path, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_web_manifest(media_root)
    payload = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output_path.write_text(payload, encoding="utf-8")
    return output_path
