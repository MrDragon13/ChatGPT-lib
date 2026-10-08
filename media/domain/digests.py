from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml


STATIC_METADATA_KEYS = (
    "genres",
    "runtime_min",
    "original_language",
    "countries",
    "production_status",
    "certifications",
    "content_warnings",
)

IDENTITY_SEMANTIC_KEYS = (
    "format",
    "medium",
    "title_original",
    "title_ru",
    "alternate_titles",
    "year",
    "release_date",
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value)).hexdigest()


def _viewer_signal(document: Mapping[str, Any], target: str) -> Mapping[str, Any] | None:
    viewers = document.get("viewer_signals") or {}
    if isinstance(viewers, Mapping) and target in viewers:
        value = viewers.get(target)
        return value if isinstance(value, Mapping) else None
    groups = document.get("group_signals") or {}
    if isinstance(groups, Mapping):
        value = groups.get(target)
        return value if isinstance(value, Mapping) else None
    return None


def compute_viewer_digest(document: Mapping[str, Any], target: str) -> str:
    return _sha256(_viewer_signal(document, target))


def compute_vocabulary_digest(media_root: Path) -> str:
    path = Path(media_root) / "vocabulary.yaml"
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return _sha256(document)


def normalize_semantic_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().replace("ё", "е")
    normalized = (
        normalized
        .replace("—", "-")
        .replace("–", "-")
        .replace("−", "-")
        .replace("‐", "-")
        .replace("‑", "-")
        .replace("…", "...")
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"\s*-\s*", " - ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_semantic_metadata_value(key: str, value: Any) -> Any:
    if key == "synopsis_short" and isinstance(value, str):
        return normalize_semantic_text(value)
    if key in {"genres", "countries"} and isinstance(value, (list, tuple)):
        items = [deepcopy(item) for item in value]
        return sorted(items, key=_canonical_json)
    return deepcopy(value)


def semantic_input_projection(document: Mapping[str, Any]) -> Mapping[str, Any]:
    identity = document.get("identity") or {}
    projected_identity = {
        key: deepcopy(identity[key])
        for key in IDENTITY_SEMANTIC_KEYS
        if key in identity
    }

    metadata = document.get("metadata") or {}
    external = metadata.get("external") or {}
    overrides = metadata.get("overrides") or {}
    effective: dict[str, Any] = {}
    for key in STATIC_METADATA_KEYS:
        if key in external:
            effective[key] = _normalize_semantic_metadata_value(key, external[key])
        if key in overrides:
            effective[key] = _normalize_semantic_metadata_value(key, overrides[key])

    return {
        "identity": projected_identity,
        "metadata": effective,
    }


def compute_semantic_input_digest(
    document: Mapping[str, Any],
    vocabulary_digest: str,
    algorithm_version: str,
) -> str:
    return _sha256(
        {
            "semantic_input": semantic_input_projection(document),
            "vocabulary_digest": vocabulary_digest,
            "algorithm_version": algorithm_version,
        }
    )


def material_evidence_projection(
    signal: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if not signal:
        return {}

    result: dict[str, Any] = {}
    for key in ("viewing", "rating", "reaction"):
        value = signal.get(key)
        if value is not None:
            result[key] = deepcopy(value)

    feedback = signal.get("feedback") or {}
    signals = feedback.get("signals") or []
    if signals:
        normalized = [deepcopy(item) for item in signals if isinstance(item, Mapping)]
        normalized.sort(key=lambda item: _canonical_json(item))
        result["feedback_signals"] = normalized
    return result


def is_material_evidence_change(
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
) -> bool:
    return material_evidence_projection(before) != material_evidence_projection(after)
