from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from media.domain.changeset import MutationPlan
from media.domain.commands import SetInferredPreferencesCommand
from media.domain.errors import CommandValidationError
from media.repository.yaml_repo import YamlRepository
from media.service.reanalysis_status import EvidenceCheckpoint, checkpoint_matches_current_evidence
from media.tools.common import iter_jsonl, load_yaml
from media.tools.schema_utils import validate_against_schema


def _at(now: datetime | None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _vocabulary_terms(repo: YamlRepository) -> set[str]:
    doc = load_yaml(repo.media_root / "vocabulary.yaml") or {}
    return set((doc.get("terms") or {}).keys())


def _explicit_preference_ids(repo: YamlRepository, target: str) -> set[str]:
    path = repo.media_root / "preferences" / "explicit" / f"{target}.yaml"
    doc = load_yaml(path) if path.exists() else {}
    return {item.get("id") for item in (doc or {}).get("preferences", []) if item.get("id")}


def _interaction_ids(repo: YamlRepository) -> set[str]:
    result: set[str] = set()
    directory = repo.media_root / "data" / "interactions"
    if directory.exists():
        for path in sorted(directory.glob("*.jsonl")):
            for _, event in iter_jsonl(path):
                if event.get("id"):
                    result.add(str(event["id"]))
    return result


def _taste_algorithm_version(repo: YamlRepository) -> str:
    path = repo.media_root / "config" / "intelligence.yaml"
    document = load_yaml(path) if path.exists() else {}
    value = (document or {}).get("taste_algorithm_version", "media-taste-v1")
    return str(value)


def _validate_analysis(
    repo: YamlRepository,
    target: str,
    analysis: Any,
) -> dict[str, Any] | None:
    if analysis is None:
        return None
    payload = copy.deepcopy(dict(analysis))
    expected_algorithm = _taste_algorithm_version(repo)
    if payload.get("algorithm_version") != expected_algorithm:
        raise CommandValidationError(
            f"taste algorithm mismatch: expected {expected_algorithm}, got {payload.get('algorithm_version')}"
        )
    raw_checkpoint = payload.get("evidence_checkpoint") or {}
    try:
        checkpoint = EvidenceCheckpoint(
            material_event_count=int(raw_checkpoint["material_event_count"]),
            material_event_prefix_digest=str(raw_checkpoint["material_event_prefix_digest"]),
        )
        evidence_digest = str(payload["evidence_digest"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CommandValidationError("invalid evidence checkpoint") from exc
    if not checkpoint_matches_current_evidence(
        repo.media_root,
        target,
        checkpoint,
        evidence_digest,
    ):
        raise CommandValidationError("evidence checkpoint does not match canonical explicit evidence")
    return payload


def _validate_hypotheses(repo: YamlRepository, target: str, hypotheses: tuple[Any, ...]) -> None:
    viewers, groups = repo.configured_targets()
    targets = viewers | set(groups)
    if target not in targets:
        raise CommandValidationError(f"unknown target: {target}")

    vocabulary = _vocabulary_terms(repo)
    work_ids = {record.id for record in repo.iter_works()}
    explicit_ids = _explicit_preference_ids(repo, target)
    interaction_ids = _interaction_ids(repo)
    hypothesis_ids = {str(item.get("id")) for item in hypotheses}

    for hypothesis in hypotheses:
        hypothesis_id = str(hypothesis.get("id"))
        for term in hypothesis.get("terms") or []:
            if term not in vocabulary:
                raise CommandValidationError(f"unknown vocabulary term: {term}")
        for evidence in hypothesis.get("evidence") or []:
            entity_id = str(evidence.get("entity_id"))
            kind = evidence.get("kind")
            source_target = evidence.get("source_target")
            if source_target is not None and source_target not in targets:
                raise CommandValidationError(f"unknown evidence source target: {source_target}")
            if entity_id == hypothesis_id or entity_id in hypothesis_ids:
                raise CommandValidationError("inferred preferences cannot be independent evidence for inferred preferences")
            if kind == "explicit_preference":
                if entity_id not in explicit_ids:
                    raise CommandValidationError(f"unknown explicit preference evidence: {entity_id}")
            elif kind == "recommendation_interaction":
                if entity_id not in interaction_ids:
                    raise CommandValidationError(f"unknown recommendation interaction evidence: {entity_id}")
            elif entity_id not in work_ids:
                raise CommandValidationError(f"unknown work evidence: {entity_id}")


def plan_set_inferred_preferences(
    repo: YamlRepository,
    command: SetInferredPreferencesCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    hypotheses = tuple(copy.deepcopy(dict(item)) for item in command.hypotheses)
    _validate_hypotheses(repo, command.target, hypotheses)
    analysis = _validate_analysis(repo, command.target, command.analysis)
    payload = {
        "schema_version": 1,
        "target": command.target,
        "hypotheses": list(hypotheses),
        "updated_at": _at(now),
    }
    if analysis is not None:
        payload["analysis"] = analysis
    errors = validate_against_schema(payload, "inferred-preferences.schema.json", repo.media_root / "schemas")
    if errors:
        raise CommandValidationError("; ".join(errors))
    rel = f"media/preferences/inferred/{command.target}.yaml"
    path = repo.media_root.parent / rel
    existing = load_yaml(path) if path.exists() else None
    changed = existing != payload
    return MutationPlan(
        command.operation_id,
        "set_inferred_preferences",
        (f"preferences:{command.target}",) if changed else (),
        {rel: payload} if changed else {},
        (f"preferences.inferred:{command.target}",) if changed else (),
        details={"target": command.target},
    )
