from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping

from media.domain.changeset import MutationPlan
from media.domain.commands import RecordMediaEntryCommand
from media.domain.digests import (
    compute_semantic_input_digest,
    compute_viewer_digest,
    compute_vocabulary_digest,
)
from media.domain.errors import CommandValidationError, NotFoundError, ProviderUnavailableError
from media.providers.base import MetadataProvider, ProviderCandidate
from media.repository.yaml_repo import YamlRepository
from media.service.enrich import make_work_id
from media.service.mutate import apply_feedback_updates
from media.service.resolve import resolve_work
from media.tools.common import load_yaml


def _date(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


def _semantic_algorithm_version(repo: YamlRepository) -> str:
    config = load_yaml(repo.media_root / "config" / "intelligence.yaml") or {}
    value = config.get("semantic_algorithm_version")
    if not isinstance(value, str) or not value:
        raise CommandValidationError("semantic_algorithm_version is missing from trusted config")
    return value


def _validate_viewer_preconditions(
    document: Mapping[str, Any],
    command: RecordMediaEntryCommand,
) -> None:
    expected = command.preconditions.expected_viewer_digests
    for update in command.target_updates:
        wanted = expected.get(update.target)
        if wanted is None:
            raise CommandValidationError(f"expected viewer digest is required for target: {update.target}")
        actual = compute_viewer_digest(document, update.target)
        if actual != wanted:
            raise CommandValidationError(
                f"viewer digest mismatch for {update.target}: expected {wanted}, got {actual}"
            )


def _validate_traits(repo: YamlRepository, traits: tuple[Mapping[str, Any], ...]) -> list[dict[str, Any]]:
    vocabulary = load_yaml(repo.media_root / "vocabulary.yaml") or {}
    terms = vocabulary.get("terms") or {}
    result: list[dict[str, Any]] = []
    for item in traits:
        trait = copy.deepcopy(dict(item))
        meta = terms.get(trait.get("term"))
        if meta is None:
            raise CommandValidationError(f"unknown vocabulary term: {trait.get('term')}")
        if meta.get("kind") == "reaction":
            raise CommandValidationError(f"reaction term cannot be a film trait: {trait.get('term')}")
        result.append(trait)
    return result


def _assert_provider_identity(command: RecordMediaEntryCommand, provider_identity: Mapping[str, Any]) -> None:
    creation = command.creation_context
    if creation is None:
        raise CommandValidationError("creation_context is required for new work")
    expected = creation.provider_identity
    tmdb = ((provider_identity.get("external_ids") or {}).get("tmdb") or {})
    if tmdb.get("media_type") != expected.media_type or tmdb.get("id") != expected.id:
        raise CommandValidationError("provider identity mismatch")
    if command.work_ref.tmdb_media_type is not None and command.work_ref.tmdb_id is not None:
        if command.work_ref.tmdb_media_type != expected.media_type or command.work_ref.tmdb_id != expected.id:
            raise CommandValidationError("provider identity contradicts work_ref")


def plan_record_media_entry(
    repo: YamlRepository,
    command: RecordMediaEntryCommand,
    provider: MetadataProvider | None,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    try:
        record = resolve_work(repo, command.work_ref)
    except NotFoundError:
        record = None

    if record is not None:
        if command.create_if_missing and command.creation_context is not None:
            _assert_provider_identity(command, record.data.get("identity") or {})
        _validate_viewer_preconditions(record.data, command)
        document, changed, targets = apply_feedback_updates(
            repo,
            record.data,
            command.target_updates,
            now=now,
            event_id=command.idempotency_key,
        )
        path = str(record.path.relative_to(repo.media_root.parent)).replace("\\", "/")
        return MutationPlan(
            command.operation_id,
            "record_media_entry",
            (record.id,) if changed else (),
            {path: document} if changed else {},
            tuple(sorted(f"viewer:{target}" for target in targets)) if changed else (),
            details={"work_id": record.id, "created": False},
        )

    if not command.create_if_missing:
        raise NotFoundError(f"work not found: {command.work_ref}")
    if command.creation_context is None or command.semantic_snapshot is None:
        raise CommandValidationError("creation_context and semantic_snapshot are required for new work")
    if provider is None:
        raise ProviderUnavailableError("metadata provider is required to create an unknown work")

    provider_identity = command.creation_context.provider_identity
    metadata = provider.fetch_work(provider_identity.media_type, provider_identity.id)
    _assert_provider_identity(command, metadata.identity)

    candidate = ProviderCandidate(
        provider_identity.media_type,
        provider_identity.id,
        str(metadata.identity.get("title_original") or command.work_ref.title or ""),
        str(metadata.identity.get("title_original") or command.work_ref.title or ""),
        metadata.identity.get("year"),
    )
    work_id = make_work_id(repo, metadata, candidate)
    document: dict[str, Any] = {
        "schema_version": 4,
        "id": work_id,
        "entity_type": "work",
        "identity": copy.deepcopy(dict(metadata.identity)),
        "metadata": {"external": copy.deepcopy(dict(metadata.external))} if metadata.external else {},
        "provenance": {"created_at": _date(now), "updated_at": _date(now)},
    }

    snapshot = command.semantic_snapshot
    vocabulary_digest = compute_vocabulary_digest(repo.media_root)
    algorithm_version = _semantic_algorithm_version(repo)
    semantic_digest = compute_semantic_input_digest(document, vocabulary_digest, algorithm_version)
    traits = _validate_traits(repo, snapshot.traits)
    document.setdefault("metadata", {})["semantic"] = {
        "traits": traits,
        "input_digest": semantic_digest,
        "vocabulary_digest": vocabulary_digest,
        "algorithm_version": algorithm_version,
    }

    document, changed, targets = apply_feedback_updates(
        repo,
        document,
        command.target_updates,
        now=now,
        event_id=command.idempotency_key,
    )
    if not changed:
        raise CommandValidationError("new work media entry must contain a material canonical update")

    domains = {"work.created", "work.identity", "work.metadata", "work.semantics"}
    domains.update(f"viewer:{target}" for target in targets)
    path = f"media/data/works/{work_id}.yaml"
    return MutationPlan(
        command.operation_id,
        "record_media_entry",
        (work_id,),
        {path: document},
        tuple(sorted(domains)),
        details={"work_id": work_id, "created": True},
    )
