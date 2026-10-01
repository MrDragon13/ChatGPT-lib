from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from media.domain.commands import RecommendContextRequest
from media.repository.index_repo import IndexRepository
from media.repository.yaml_repo import YamlRepository
from media.service.recommend import build_recommend_context
from media.tools.common import load_yaml
from media.tools.schema_utils import validate_against_schema


WEB_MANIFEST_SCHEMA_VERSION = 1


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


def _work_view(data: dict[str, Any], index_row: dict[str, Any]) -> dict[str, Any]:
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
    default_target = "couple" if "couple" in groups else (sorted_viewers[0] if sorted_viewers else None)

    index_rows = {
        row["id"]: row
        for row in IndexRepository(media_root / "generated" / "index.jsonl").rows()
    }

    works = [
        _work_view(record.data, index_rows.get(record.id, {}))
        for record in sorted(repo.iter_works(), key=lambda item: item.id)
    ]

    recommendations: dict[str, dict[str, Any]] = {}
    for target in targets:
        request = RecommendContextRequest(
            schema_version=1,
            target=target,
            text=None,
            only_unwatched=True,
            runtime_max=None,
            include_not_interested=False,
            limit=24,
        )
        recommendations[target] = build_recommend_context(media_root, request)

    manifest: dict[str, Any] = {
        "schema_version": WEB_MANIFEST_SCHEMA_VERSION,
        "default_target": default_target,
        "targets": {"viewers": sorted_viewers, "groups": sorted_groups},
        "vocabulary": _web_vocabulary(media_root),
        "profiles": {target: _load_profile(media_root, target) for target in targets},
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
