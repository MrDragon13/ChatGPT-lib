from __future__ import annotations

from dataclasses import dataclass

from media.domain.errors import AmbiguousIdentityError, NotFoundError, UnknownTargetError
from media.domain.types import WorkRef
from media.repository.canonical import CanonicalRepository, WorkRecord


@dataclass(frozen=True)
class ResolutionCandidate:
    id: str
    title: str
    year: int | None


def normalize_title(value: str) -> str:
    return " ".join(value.casefold().split())


def _candidate(record: WorkRecord) -> ResolutionCandidate:
    identity = record.data.get("identity") or {}
    return ResolutionCandidate(record.id, str(identity.get("title_original") or identity.get("title_ru") or record.id), identity.get("year"))


def resolve_target_kind(repo: CanonicalRepository, target: str) -> str:
    viewers, groups = repo.configured_targets()
    if target in viewers:
        return "viewer"
    if target in groups:
        return "group"
    raise UnknownTargetError(f"unknown target: {target}")


def resolve_work(repo: CanonicalRepository, ref: WorkRef) -> WorkRecord:
    if ref.id is not None:
        record = repo.get_work(ref.id)
        if record is None:
            raise NotFoundError(f"unknown work id: {ref.id}")
        return record
    records = list(repo.iter_works())
    if ref.tmdb_media_type is not None and ref.tmdb_id is not None:
        matches = []
        for record in records:
            external = ((record.data.get("identity") or {}).get("external_ids") or {})
            tmdb = external.get("tmdb") or {}
            if tmdb.get("media_type") == ref.tmdb_media_type and tmdb.get("id") == ref.tmdb_id:
                matches.append(record)
        return _one_or_error(matches, ref)
    if ref.imdb_id is not None:
        matches = [record for record in records if (((record.data.get("identity") or {}).get("external_ids") or {}).get("imdb") == ref.imdb_id)]
        return _one_or_error(matches, ref)
    if ref.title is not None:
        needle = normalize_title(ref.title)
        matches = []
        for record in records:
            identity = record.data.get("identity") or {}
            titles = [identity.get("title_original"), identity.get("title_ru"), *((identity.get("alternate_titles") or []))]
            if needle not in {normalize_title(str(title)) for title in titles if title}:
                continue
            if ref.year is not None and identity.get("year") != ref.year:
                continue
            matches.append(record)
        return _one_or_error(matches, ref)
    raise NotFoundError("work reference has no resolvable identity")


def _one_or_error(matches: list[WorkRecord], ref: WorkRef) -> WorkRecord:
    if not matches:
        raise NotFoundError(f"work not found: {ref}")
    if len(matches) > 1:
        candidates = tuple(sorted((_candidate(record) for record in matches), key=lambda c: (c.year or 0, c.id)))
        raise AmbiguousIdentityError(candidates)
    return matches[0]
