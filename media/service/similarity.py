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


def _work_external_aliases(work_document: dict[str, Any]) -> set[str]:
    identity = work_document.get("identity") or {}
    external = identity.get("external_ids") or {}
    aliases: set[str] = set()
    tmdb = external.get("tmdb") or {}
    if isinstance(tmdb, dict) and tmdb.get("media_type") in {"movie", "tv"} and isinstance(tmdb.get("id"), int):
        aliases.add(f"external:tmdb:{tmdb['media_type']}:{tmdb['id']}")
    imdb = external.get("imdb")
    if isinstance(imdb, str) and imdb:
        aliases.add(f"external:imdb:{imdb}")
    return aliases


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _assertion_signature(relation: dict[str, Any]) -> tuple[tuple[str, ...], Any]:
    return tuple(relation.get("terms") or ()), relation.get("note")


def _choose_collision_winner(
    current: tuple[dict[str, Any], str, bool],
    candidate: tuple[dict[str, Any], str, bool],
) -> tuple[dict[str, Any], str, bool]:
    current_relation, current_identity, current_fully_canonical = current
    candidate_relation, candidate_identity, candidate_fully_canonical = candidate
    current_time = _parse_timestamp(current_relation.get("updated_at"))
    candidate_time = _parse_timestamp(candidate_relation.get("updated_at"))
    if candidate_time > current_time:
        return candidate
    if candidate_time < current_time:
        return current
    if candidate_fully_canonical != current_fully_canonical:
        return candidate if candidate_fully_canonical else current
    if candidate_identity < current_identity:
        return candidate
    return current


def reconcile_similarity_for_new_work(
    repo: YamlRepository,
    work_id: str,
    work_document: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    aliases = _work_external_aliases(work_document)
    if not aliases:
        return {}
    canonical = {"kind": "canonical", "work_id": work_id}
    relation_dir = repo.media_root / "data" / "relations" / "similarity"
    if not relation_dir.exists():
        return {}
    updated_documents: dict[str, dict[str, Any]] = {}
    for path in sorted(relation_dir.glob("*.yaml")):
        original = load_yaml(path) or {}
        if not isinstance(original, dict):
            continue
        winners: dict[tuple[str, str], tuple[dict[str, Any], str, bool]] = {}
        changed = False
        for raw_relation in original.get("relations") or []:
            if not isinstance(raw_relation, dict):
                continue
            relation = dict(raw_relation)
            raw_left = dict(relation.get("left") or {})
            raw_right = dict(relation.get("right") or {})
            try:
                original_left_key = endpoint_key(raw_left)
                original_right_key = endpoint_key(raw_right)
            except CommandValidationError:
                pair_identity = ""
            else:
                pair_identity = "|".join(sorted((original_left_key, original_right_key)))
            fully_canonical = raw_left.get("kind") == "canonical" and raw_right.get("kind") == "canonical"
            left = canonical if endpoint_key(raw_left) in aliases else raw_left
            right = canonical if endpoint_key(raw_right) in aliases else raw_right
            left_key = endpoint_key(left)
            right_key = endpoint_key(right)
            if left_key == right_key:
                changed = True
                continue
            if left_key > right_key:
                left, right = right, left
                left_key, right_key = right_key, left_key
            if left != raw_left or right != raw_right:
                changed = True
            relation["left"] = left
            relation["right"] = right
            pair = (left_key, right_key)
            candidate = (relation, pair_identity, fully_canonical)
            current = winners.get(pair)
            if current is None:
                winners[pair] = candidate
                continue
            changed = True
            winner = _choose_collision_winner(current, candidate)
            if _assertion_signature(current[0]) == _assertion_signature(candidate[0]):
                winner = _choose_collision_winner(current, candidate)
            winners[pair] = winner
        relations = [item[0] for _, item in sorted(winners.items(), key=lambda row: row[0])]
        output = {
            "schema_version": original.get("schema_version", 1),
            "target": original.get("target", path.stem),
            "relations": relations,
        }
        if changed or output != original:
            rel = f"media/data/relations/similarity/{path.name}"
            updated_documents[rel] = output
    return updated_documents


def similarity_context(media_root: Path, target: str) -> list[dict[str, Any]]:
    repo = YamlRepository(Path(media_root))
    resolve_target_kind(repo, target)
    doc = load_similarity_document(repo, target)
    result: list[dict[str, Any]] = []
    for relation in doc["relations"]:
        left = relation.get("left")
        right = relation.get("right")
        if not isinstance(left, dict) or not isinstance(right, dict):
            continue
        result.append({
            "left": dict(left),
            "right": dict(right),
            "terms": list(relation.get("terms") or []),
            "note": relation.get("note"),
            "updated_at": relation.get("updated_at"),
            "provenance": dict(relation.get("provenance") or {}),
        })
    return result


def similarities_for_endpoint(media_root: Path, target: str, endpoint: dict[str, Any]) -> list[dict[str, Any]]:
    wanted = endpoint_key(endpoint)
    result: list[dict[str, Any]] = []
    for relation in similarity_context(media_root, target):
        left_key = endpoint_key(relation["left"])
        right_key = endpoint_key(relation["right"])
        if left_key == wanted:
            other = relation["right"]
        elif right_key == wanted:
            other = relation["left"]
        else:
            continue
        result.append({
            "other": dict(other),
            "terms": list(relation.get("terms") or []),
            "note": relation.get("note"),
            "updated_at": relation.get("updated_at"),
            "provenance": dict(relation.get("provenance") or {}),
        })
    return result
