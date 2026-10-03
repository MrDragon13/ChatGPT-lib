from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from media.domain.changeset import MutationPlan
from media.domain.commands import RemoveWorkSimilarityCommand, SetWorkSimilarityCommand
from media.domain.errors import CommandValidationError, NotFoundError
from media.domain.types import WorkRef
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_target_kind, resolve_work
from media.tools.common import load_yaml


def endpoint_key(endpoint: dict[str, Any]) -> str:
    if endpoint.get("kind") == "canonical":
        return f"work:{endpoint['work_id']}"
    if endpoint.get("provider") == "tmdb":
        return f"external:tmdb:{endpoint['media_type']}:{endpoint['id']}"
    if endpoint.get("provider") == "imdb":
        return f"external:imdb:{endpoint['id']}"
    raise CommandValidationError("unsupported similarity endpoint")


def work_ref_identity(repo: YamlRepository, ref: WorkRef) -> tuple[str, dict[str, Any]]:
    if ref.id is not None:
        record = resolve_work(repo, ref)
        endpoint = {"kind": "canonical", "work_id": record.id}
        return endpoint_key(endpoint), endpoint

    if ref.tmdb_media_type is None and ref.tmdb_id is None and ref.imdb_id is None:
        raise CommandValidationError("persistent similarity work reference requires canonical id or stable provider identity")

    try:
        record = resolve_work(repo, ref)
    except NotFoundError:
        record = None
    if record is not None:
        endpoint = {"kind": "canonical", "work_id": record.id}
        return endpoint_key(endpoint), endpoint

    if not ref.title:
        raise CommandValidationError("external similarity endpoint requires a display title snapshot")
    if ref.tmdb_media_type is not None and ref.tmdb_id is not None:
        endpoint = {
            "kind": "external",
            "provider": "tmdb",
            "media_type": ref.tmdb_media_type,
            "id": ref.tmdb_id,
            "title": ref.title,
            "year": ref.year,
        }
        return endpoint_key(endpoint), endpoint
    if ref.imdb_id is not None:
        endpoint = {
            "kind": "external",
            "provider": "imdb",
            "id": ref.imdb_id,
            "title": ref.title,
            "year": ref.year,
        }
        return endpoint_key(endpoint), endpoint
    raise CommandValidationError("unsupported stable external similarity identity")


def normalize_similarity_pair(repo: YamlRepository, left: WorkRef, right: WorkRef) -> tuple[dict[str, Any], dict[str, Any]]:
    left_key, left_endpoint = work_ref_identity(repo, left)
    right_key, right_endpoint = work_ref_identity(repo, right)
    if left_key == right_key:
        raise CommandValidationError("work similarity cannot point to the same resolved work")
    if left_key <= right_key:
        return left_endpoint, right_endpoint
    return right_endpoint, left_endpoint


def _relation_path(repo: YamlRepository, target: str) -> tuple[Path, str]:
    absolute = repo.media_root / "data" / "relations" / "similarity" / f"{target}.yaml"
    relative = f"media/data/relations/similarity/{target}.yaml"
    return absolute, relative


def load_similarity_document(repo: YamlRepository, target: str) -> dict[str, Any]:
    path, _ = _relation_path(repo, target)
    if not path.exists():
        return {"schema_version": 1, "target": target, "relations": []}
    doc = load_yaml(path) or {}
    if not isinstance(doc, dict):
        raise CommandValidationError(f"invalid similarity document for target {target}")
    return {
        "schema_version": doc.get("schema_version", 1),
        "target": doc.get("target", target),
        "relations": [dict(item) for item in (doc.get("relations") or []) if isinstance(item, dict)],
    }


def _validate_terms(repo: YamlRepository, terms: tuple[str, ...]) -> None:
    vocabulary = load_yaml(repo.media_root / "vocabulary.yaml") or {}
    canonical = set((vocabulary.get("terms") or {}).keys()) if isinstance(vocabulary, dict) else set()
    unknown = sorted(set(terms) - canonical)
    if unknown:
        raise CommandValidationError(f"unknown vocabulary term(s): {', '.join(unknown)}")


def _pair_key(left: dict[str, Any], right: dict[str, Any]) -> tuple[str, str]:
    return endpoint_key(left), endpoint_key(right)


def _entity_id(target: str, left: dict[str, Any], right: dict[str, Any]) -> str:
    left_key, right_key = _pair_key(left, right)
    return f"similarity:{target}:{left_key}|{right_key}"


def plan_set_work_similarity(
    repo: YamlRepository,
    command: SetWorkSimilarityCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    resolve_target_kind(repo, command.target)
    _validate_terms(repo, command.terms)
    left, right = normalize_similarity_pair(repo, command.left, command.right)
    doc = load_similarity_document(repo, command.target)
    pair = _pair_key(left, right)
    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    replacement = {
        "type": "similar",
        "left": left,
        "right": right,
        "terms": list(command.terms),
        "note": command.note,
        "updated_at": timestamp,
        "provenance": {"source": "explicit"},
    }
    relations: list[dict[str, Any]] = []
    replaced = False
    for relation in doc["relations"]:
        try:
            relation_pair = _pair_key(relation["left"], relation["right"])
        except (KeyError, CommandValidationError):
            relations.append(relation)
            continue
        if relation_pair == pair:
            if not replaced:
                relations.append(replacement)
                replaced = True
        else:
            relations.append(relation)
    if not replaced:
        relations.append(replacement)
    relations.sort(key=lambda relation: _pair_key(relation["left"], relation["right"]))
    output = {"schema_version": 1, "target": command.target, "relations": relations}
    _, rel_path = _relation_path(repo, command.target)
    entity_id = _entity_id(command.target, left, right)
    return MutationPlan(command.operation_id, "set_work_similarity", (entity_id,), {rel_path: output}, False, ())


def plan_remove_work_similarity(
    repo: YamlRepository,
    command: RemoveWorkSimilarityCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    del now
    resolve_target_kind(repo, command.target)
    left, right = normalize_similarity_pair(repo, command.left, command.right)
    doc = load_similarity_document(repo, command.target)
    pair = _pair_key(left, right)
    kept: list[dict[str, Any]] = []
    removed = False
    for relation in doc["relations"]:
        try:
            relation_pair = _pair_key(relation["left"], relation["right"])
        except (KeyError, CommandValidationError):
            kept.append(relation)
            continue
        if relation_pair == pair:
            removed = True
        else:
            kept.append(relation)
    if not removed:
        return MutationPlan(command.operation_id, "remove_work_similarity", (), {}, False, ())
    output = {"schema_version": 1, "target": command.target, "relations": kept}
    _, rel_path = _relation_path(repo, command.target)
    entity_id = _entity_id(command.target, left, right)
    return MutationPlan(command.operation_id, "remove_work_similarity", (entity_id,), {rel_path: output}, False, ())
