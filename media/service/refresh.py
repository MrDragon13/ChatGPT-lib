from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping

import yaml

from media.domain.changeset import MutationPlan
from media.domain.commands import RefreshMetadataCommand, RefreshWorkMetadataCommand
from media.domain.errors import CommandValidationError, MetadataRefreshPreflightError, ProviderUnavailableError
from media.providers.base import CanonicalMetadata, MetadataProvider, ProviderCandidate
from media.repository.canonical import WorkRecord
from media.repository.yaml_repo import YamlRepository
from media.tools.common import file_sha256
from media.service.resolve import normalize_title, resolve_work


def _candidate_dict(candidate: ProviderCandidate) -> dict[str, Any]:
    return asdict(candidate)


def _blocker(work_id: str, reason: str, candidates: list[ProviderCandidate] | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"work_id": work_id, "reason": reason}
    if candidates is not None:
        value["candidates"] = [_candidate_dict(candidate) for candidate in candidates]
    return value


def _movie_candidates(
    record: WorkRecord,
    candidates: list[ProviderCandidate],
    *,
    expected_year: int | None = None,
) -> list[ProviderCandidate]:
    identity = record.data.get("identity") or {}
    title = normalize_title(str(identity.get("title_original") or ""))
    year = expected_year if expected_year is not None else identity.get("year")
    return [
        candidate
        for candidate in candidates
        if candidate.media_type == "movie"
        and title in {normalize_title(candidate.title), normalize_title(candidate.original_title)}
        and (year is None or candidate.year == year)
    ]


def _provider_media_type(record: WorkRecord) -> str | None:
    identity = record.data.get("identity") or {}
    fmt = identity.get("format")
    if fmt == "movie":
        return "movie"
    if fmt in {"series", "miniseries"}:
        return "tv"
    return None


def _work_candidates(
    record: WorkRecord,
    candidates: list[ProviderCandidate],
    *,
    expected_year: int | None = None,
) -> list[ProviderCandidate]:
    identity = record.data.get("identity") or {}
    expected_media_type = _provider_media_type(record)
    title = normalize_title(str(identity.get("title_original") or ""))
    year = expected_year if expected_year is not None else identity.get("year")
    return [
        candidate
        for candidate in candidates
        if candidate.media_type == expected_media_type
        and title in {normalize_title(candidate.title), normalize_title(candidate.original_title)}
        and (year is None or candidate.year == year)
    ]


def _canonical_tmdb(record: WorkRecord) -> Mapping[str, Any] | None:
    identity = record.data.get("identity") or {}
    external_ids = identity.get("external_ids") or {}
    value = external_ids.get("tmdb")
    return value if isinstance(value, Mapping) else None


def _resolve_candidate(
    record: WorkRecord,
    command: RefreshMetadataCommand | RefreshWorkMetadataCommand,
    provider: MetadataProvider,
    *,
    allow_tv: bool = False,
) -> tuple[ProviderCandidate | None, dict[str, Any] | None]:
    identity = record.data.get("identity") or {}
    external_ids = identity.get("external_ids") or {}
    canonical_tmdb = _canonical_tmdb(record)
    tmdb_overrides = getattr(command, "tmdb_overrides", {})
    year_overrides = getattr(command, "year_overrides", {})
    override = tmdb_overrides.get(record.id)
    expected_year = year_overrides.get(record.id, identity.get("year"))
    expected_media_type = _provider_media_type(record)
    allowed_media_types = {"movie", "tv"} if allow_tv else {"movie"}
    if expected_media_type not in allowed_media_types:
        return None, _blocker(record.id, "identity_conflict")

    if canonical_tmdb is not None:
        canonical_type = canonical_tmdb.get("media_type")
        canonical_id = canonical_tmdb.get("id")
        if override is not None and (override.media_type != canonical_type or override.id != canonical_id):
            return None, _blocker(record.id, "override_conflict")
        if (
            canonical_type not in allowed_media_types
            or canonical_type != expected_media_type
            or not isinstance(canonical_id, int)
        ):
            return None, _blocker(record.id, "identity_conflict")
        return ProviderCandidate(canonical_type, canonical_id, str(identity.get("title_ru") or ""), str(identity.get("title_original") or ""), expected_year), None

    if override is not None:
        return ProviderCandidate("movie", override.id, str(identity.get("title_ru") or ""), str(identity.get("title_original") or ""), expected_year), None

    imdb_id = external_ids.get("imdb")
    if isinstance(imdb_id, str) and imdb_id:
        candidates = [
            candidate
            for candidate in provider.find_by_imdb(imdb_id)
            if candidate.media_type == expected_media_type
        ]
        if not candidates:
            return None, _blocker(record.id, "not_found")
        if len(candidates) > 1:
            return None, _blocker(record.id, "ambiguous_identity", candidates)
        return candidates[0], None

    title = str(identity.get("title_original") or "")
    candidate_pool = provider.search_work(title, expected_year)
    candidates = (
        _work_candidates(record, candidate_pool, expected_year=expected_year)
        if allow_tv
        else _movie_candidates(record, candidate_pool, expected_year=expected_year)
    )
    if not candidates:
        return None, _blocker(record.id, "not_found")
    if len(candidates) > 1:
        return None, _blocker(record.id, "ambiguous_identity", candidates)
    return candidates[0], None


def _identity_compatible(
    record: WorkRecord,
    candidate: ProviderCandidate,
    metadata: CanonicalMetadata,
    *,
    allow_title_mismatch: bool = False,
    expected_year: int | None = None,
    allow_tv: bool = False,
) -> bool:
    canonical = record.data.get("identity") or {}
    provider_identity = metadata.identity
    canonical_format = canonical.get("format")
    provider_format = provider_identity.get("format")
    expected_media_type = _provider_media_type(record)
    if candidate.media_type != expected_media_type:
        return False
    if candidate.media_type == "movie":
        if canonical_format != "movie" or provider_format != "movie":
            return False
    elif candidate.media_type == "tv":
        if not allow_tv or canonical_format not in {"series", "miniseries"} or provider_format not in {"series", "miniseries"}:
            return False
    else:
        return False

    canonical_year = canonical.get("year")
    provider_year = provider_identity.get("year")
    if expected_year is not None:
        if provider_year != expected_year:
            return False
    elif canonical_year is not None and provider_year is not None and canonical_year != provider_year:
        return False

    canonical_title = normalize_title(str(canonical.get("title_original") or ""))
    provider_titles = {
        normalize_title(str(provider_identity.get("title_original") or "")),
        normalize_title(str(provider_identity.get("title_ru") or "")),
    }
    if not allow_title_mismatch and canonical_title and canonical_title not in provider_titles:
        return False

    provider_ids = provider_identity.get("external_ids") or {}
    provider_tmdb = provider_ids.get("tmdb") or {}
    if provider_tmdb.get("media_type") != candidate.media_type or provider_tmdb.get("id") != candidate.provider_id:
        return False

    canonical_tmdb = _canonical_tmdb(record)
    if canonical_tmdb is not None and (
        canonical_tmdb.get("media_type") != provider_tmdb.get("media_type")
        or canonical_tmdb.get("id") != provider_tmdb.get("id")
    ):
        return False

    canonical_ids = canonical.get("external_ids") or {}
    canonical_imdb = canonical_ids.get("imdb")
    provider_imdb = provider_ids.get("imdb")
    if canonical_imdb and provider_imdb and canonical_imdb != provider_imdb:
        return False
    return True


def _merge_external(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> dict[str, Any]:
    merged = deepcopy(dict(existing))
    for key, value in incoming.items():
        if key == "external_metrics":
            metrics = deepcopy(dict(existing.get("external_metrics") or {}))
            if isinstance(value, Mapping) and value.get("tmdb") is not None:
                metrics["tmdb"] = deepcopy(value["tmdb"])
            if metrics:
                merged["external_metrics"] = metrics
            continue
        if value is None:
            continue
        merged[key] = deepcopy(value)
    return merged


def _refreshed_document(
    record: WorkRecord,
    metadata: CanonicalMetadata,
    *,
    day: str,
    year_override: int | None = None,
) -> dict[str, Any]:
    original = deepcopy(dict(record.data))
    document = deepcopy(original)

    identity = document.setdefault("identity", {})
    provider_identity = metadata.identity
    if year_override is not None:
        identity["year"] = year_override
    if provider_identity.get("release_date") is not None:
        identity["release_date"] = provider_identity["release_date"]
    external_ids = deepcopy(dict(identity.get("external_ids") or {}))
    provider_ids = provider_identity.get("external_ids") or {}
    if provider_ids.get("tmdb") is not None:
        external_ids["tmdb"] = deepcopy(provider_ids["tmdb"])
    if provider_ids.get("imdb"):
        external_ids["imdb"] = provider_ids["imdb"]
    if external_ids:
        identity["external_ids"] = external_ids

    metadata_doc = document.setdefault("metadata", {})
    metadata_doc["external"] = _merge_external(metadata_doc.get("external") or {}, metadata.external)

    if document != original:
        provenance = document.setdefault("provenance", {})
        provenance["updated_at"] = day
    return document


def _changed_metadata_domains(before: Mapping[str, Any], after: Mapping[str, Any]) -> tuple[str, ...]:
    domains: list[str] = []
    if before.get("identity") != after.get("identity"):
        domains.append("work.identity")
    if before.get("metadata") != after.get("metadata"):
        domains.append("work.metadata")
    return tuple(domains)


def plan_refresh_metadata(
    repo: YamlRepository,
    command: RefreshMetadataCommand,
    provider: MetadataProvider | None,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    if provider is None:
        raise ProviderUnavailableError("metadata provider is required for refresh_metadata")

    targets = sorted(
        (record for record in repo.iter_works() if (record.data.get("identity") or {}).get("format") == "movie"),
        key=lambda record: record.id,
    )
    blockers: list[Mapping[str, Any]] = []
    resolved: list[tuple[WorkRecord, CanonicalMetadata, int | None]] = []
    unmapped_genres: set[int] = set()

    for record in targets:
        candidate, blocker = _resolve_candidate(record, command, provider)
        if blocker is not None:
            blockers.append(blocker)
            continue
        assert candidate is not None
        metadata = provider.fetch_work(candidate.media_type, candidate.provider_id)
        override_is_resolution = record.id in command.tmdb_overrides and _canonical_tmdb(record) is None
        year_override = command.year_overrides.get(record.id)
        if not _identity_compatible(
            record,
            candidate,
            metadata,
            allow_title_mismatch=override_is_resolution,
            expected_year=year_override,
        ):
            blockers.append(_blocker(record.id, "identity_conflict"))
            continue
        resolved.append((record, metadata, year_override))
        unmapped_genres.update(metadata.unmapped_genre_ids)

    if blockers:
        raise MetadataRefreshPreflightError(tuple(blockers))

    value = now or datetime.now(timezone.utc)
    day = value.date().isoformat()
    documents: dict[str, Mapping[str, Any]] = {}
    changed_entities: list[str] = []
    for record, metadata, year_override in resolved:
        document = _refreshed_document(record, metadata, day=day, year_override=year_override)
        if document == record.data:
            continue
        path = f"media/data/works/{record.id}.yaml"
        documents[path] = document
        changed_entities.append(record.id)

    details = {
        "targeted_count": len(targets),
        "changed_count": len(changed_entities),
        "no_change_count": len(targets) - len(changed_entities),
        "changed_work_ids": list(changed_entities),
        "unmapped_genre_ids": sorted(unmapped_genres),
    }
    changed_domains = sorted({
        domain
        for record, metadata, year_override in resolved
        for domain in _changed_metadata_domains(
            record.data,
            _refreshed_document(record, metadata, day=day, year_override=year_override),
        )
    })
    return MutationPlan(
        command.operation_id,
        "refresh_metadata",
        tuple(changed_entities),
        documents,
        tuple(changed_domains),
        details,
    )



def _yaml_digest(document: Mapping[str, Any]) -> str:
    payload = yaml.safe_dump(dict(document), sort_keys=False, allow_unicode=True).encode("utf-8")
    return file_sha256(payload)


def plan_refresh_work_metadata(
    repo: YamlRepository,
    command: RefreshWorkMetadataCommand,
    provider: MetadataProvider | None,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    record = resolve_work(repo, command.work_ref)
    actual_digest = file_sha256(record.path.read_bytes())
    if actual_digest != command.expected_work_digest:
        raise CommandValidationError(
            f"work digest mismatch for {record.id}: expected {command.expected_work_digest}, current {actual_digest}"
        )
    if provider is None:
        raise ProviderUnavailableError("metadata provider is required for refresh_work_metadata")
    if (record.data.get("identity") or {}).get("format") not in {"movie", "series", "miniseries"}:
        raise MetadataRefreshPreflightError((_blocker(record.id, "identity_conflict"),))

    candidate, blocker = _resolve_candidate(record, command, provider, allow_tv=True)
    if blocker is not None:
        raise MetadataRefreshPreflightError((blocker,))
    assert candidate is not None
    metadata = provider.fetch_work(candidate.media_type, candidate.provider_id)
    if not _identity_compatible(record, candidate, metadata, allow_tv=True):
        raise MetadataRefreshPreflightError((_blocker(record.id, "identity_conflict"),))

    value = now or datetime.now(timezone.utc)
    day = value.date().isoformat()
    document = _refreshed_document(record, metadata, day=day)
    changed = document != record.data
    path = f"media/data/works/{record.id}.yaml"
    final_digest = _yaml_digest(document) if changed else actual_digest
    details = {
        "work_id": record.id,
        "expected_work_digest": command.expected_work_digest,
        "work_digest": final_digest,
        "unmapped_genre_ids": sorted(metadata.unmapped_genre_ids),
    }
    return MutationPlan(
        command.operation_id,
        "refresh_work_metadata",
        (record.id,) if changed else (),
        {path: document} if changed else {},
        _changed_metadata_domains(record.data, document) if changed else (),
        details,
    )
