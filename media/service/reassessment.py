from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from media.domain.errors import NotFoundError
from media.repository.canonical import CanonicalRepository

PILOT_ID = "primary-legacy-v1"
LEDGER_REL_PATH = "media/pilots/legacy-reassessment-primary.json"
ALLOWED_COHORT_VIEWING = {"watched", "partial", "dropped", "forgotten"}
STRATUM_ORDER = ("special", "low", "medium_low", "central", "high", "unrated_viewed")
_FEEDBACK_STATE_KEYS = ("viewing", "rating", "reaction", "feedback")


def ledger_bytes(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def file_sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def ledger_digest_bytes(payload: bytes) -> str:
    return file_sha256(payload)


def feedback_state_digest(signal: Mapping[str, Any] | None) -> str:
    current = signal or {}
    scoped = {key: current[key] for key in _FEEDBACK_STATE_KEYS if key in current}
    return ledger_digest_bytes(ledger_bytes(scoped))


def frozen_stratum(signal: Mapping[str, Any]) -> str:
    viewing = signal.get("viewing") or {}
    status = viewing.get("status")
    if status in {"partial", "dropped", "forgotten"}:
        return "special"

    rating = signal.get("rating") or {}
    score = rating.get("score")
    if score is None:
        return "unrated_viewed"
    numeric = float(score)
    if numeric <= 6.5:
        return "low"
    if numeric <= 7.5:
        return "medium_low"
    if numeric <= 8.5:
        return "central"
    return "high"


def frozen_order_key(pilot_id: str, work_id: str) -> str:
    payload = f"{pilot_id}\0{work_id}".encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _primary_signal(document: Mapping[str, Any]) -> Mapping[str, Any]:
    viewer_signals = document.get("viewer_signals") or {}
    signal = viewer_signals.get("primary") or {}
    return signal if isinstance(signal, Mapping) else {}


def build_frozen_cohort(repo: CanonicalRepository, *, pilot_id: str) -> dict[str, Any]:
    entries: dict[str, dict[str, Any]] = {}
    buckets: dict[str, list[str]] = defaultdict(list)

    for record in repo.iter_works():
        signal = _primary_signal(record.data)
        viewing = signal.get("viewing") or {}
        status = viewing.get("status")
        if status not in ALLOWED_COHORT_VIEWING:
            continue
        stratum = frozen_stratum(signal)
        item = {
            "viewing_status": status,
            "stratum": stratum,
            "order_key": frozen_order_key(pilot_id, record.id),
            "pre_pilot_feedback_digest": feedback_state_digest(signal),
        }
        entries[record.id] = item
        buckets[stratum].append(record.id)

    for stratum in STRATUM_ORDER:
        buckets[stratum].sort(key=lambda work_id: (entries[work_id]["order_key"], work_id))

    queue: list[str] = []
    offset = 0
    while True:
        added = False
        for stratum in STRATUM_ORDER:
            ids = buckets[stratum]
            if offset < len(ids):
                queue.append(ids[offset])
                added = True
        if not added:
            break
        offset += 1

    for rank, work_id in enumerate(queue):
        entries[work_id]["order_rank"] = rank

    return {
        "work_ids": queue,
        "items": {work_id: entries[work_id] for work_id in sorted(entries)},
    }


def build_initial_ledger(
    repo: CanonicalRepository,
    *,
    pilot_id: str,
    base_revision: str,
    baseline_path: str,
    baseline_document: Mapping[str, Any],
) -> dict[str, Any]:
    baseline_schema_version = baseline_document.get("schema_version")
    baseline_digest = baseline_document.get("canonical_input_digest")
    if not isinstance(baseline_schema_version, int):
        raise ValueError("baseline document must contain integer schema_version")
    if not isinstance(baseline_digest, str) or not baseline_digest.startswith("sha256:"):
        raise ValueError("baseline document must contain canonical_input_digest")

    cohort = build_frozen_cohort(repo, pilot_id=pilot_id)
    frozen_cohort = {
        "cohort_revision": base_revision,
        "work_ids": cohort["work_ids"],
        "items": cohort["items"],
    }
    return {
        "schema_version": 1,
        "pilot_id": pilot_id,
        "pilot_status": "active",
        "target": "primary",
        "base_revision": base_revision,
        "baseline_path": baseline_path,
        "baseline_schema_version": baseline_schema_version,
        "baseline_canonical_input_digest": baseline_digest,
        "frozen_cohort": frozen_cohort,
        "items": {work_id: {"status": "pending"} for work_id in cohort["work_ids"]},
        "sessions": [],
        "scheduled_reanalysis": {"last_completed": None},
    }


def read_ledger(path: Path) -> dict[str, Any]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("reassessment ledger root must be an object")
    return document


def _open_reassessment_session(document: Mapping[str, Any]) -> Mapping[str, Any] | None:
    sessions = document.get("sessions") or []
    for session in sessions:
        if isinstance(session, Mapping) and session.get("status") == "open":
            return session
    return None


def _safe_reassessment_card(
    record: Any,
    *,
    lifecycle: Mapping[str, Any],
    order_rank: int | None,
) -> dict[str, Any]:
    identity = record.data.get("identity") or {}
    metadata = record.data.get("metadata") or {}
    external = metadata.get("external") or {}
    directors = [
        item.get("name")
        for item in external.get("directors") or []
        if isinstance(item, Mapping) and isinstance(item.get("name"), str)
    ]
    main_cast = [
        item.get("name")
        for item in external.get("main_cast") or []
        if isinstance(item, Mapping) and isinstance(item.get("name"), str)
    ]
    return {
        "work_id": record.id,
        "title": identity.get("title_ru") or identity.get("title_original") or record.id,
        "year": identity.get("year"),
        "synopsis_short": external.get("synopsis_short"),
        "directors": directors,
        "main_cast": main_cast[:3],
        "queue_status": lifecycle.get("status"),
        "order_rank": order_rank,
    }


def build_reassessment_context(
    repo: CanonicalRepository,
    document: Mapping[str, Any],
    *,
    limit: int = 5,
) -> dict[str, Any]:
    """Build the unanchored first-response read model for reassessment."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    frozen = document.get("frozen_cohort") or {}
    frozen_ids = frozen.get("work_ids") or []
    frozen_items = frozen.get("items") or {}
    lifecycle_items = document.get("items") or {}
    open_session = _open_reassessment_session(document)

    if open_session is not None:
        candidate_ids = [
            work_id
            for work_id in open_session.get("reserved_work_ids") or []
            if isinstance(work_id, str)
            and isinstance(lifecycle_items.get(work_id), Mapping)
            and lifecycle_items[work_id].get("status") == "in_progress"
        ]
        open_summary = {
            "session_id": open_session.get("session_id"),
            "reserved_work_ids": list(open_session.get("reserved_work_ids") or []),
        }
    else:
        pending_ids = [
            work_id
            for work_id in frozen_ids
            if isinstance(work_id, str)
            and isinstance(lifecycle_items.get(work_id), Mapping)
            and lifecycle_items[work_id].get("status") == "pending"
        ]
        if pending_ids:
            candidate_ids = pending_ids
        else:
            candidate_ids = [
                work_id
                for work_id in frozen_ids
                if isinstance(work_id, str)
                and isinstance(lifecycle_items.get(work_id), Mapping)
                and lifecycle_items[work_id].get("status") == "deferred"
            ]
        open_summary = None

    cards: list[dict[str, Any]] = []
    for work_id in candidate_ids[:limit]:
        record = repo.get_work(work_id)
        if record is None:
            continue
        frozen_item = frozen_items.get(work_id) if isinstance(frozen_items, Mapping) else {}
        order_rank = frozen_item.get("order_rank") if isinstance(frozen_item, Mapping) else None
        cards.append(
            _safe_reassessment_card(
                record,
                lifecycle=lifecycle_items.get(work_id) or {},
                order_rank=order_rank,
            )
        )

    return {
        "pilot_id": document.get("pilot_id"),
        "ledger_digest": ledger_digest_bytes(ledger_bytes(document)),
        "open_session": open_summary,
        "cards": cards,
    }


def build_reassessment_history(repo: CanonicalRepository, work_id: str) -> dict[str, Any]:
    """Return explicit second-phase historical viewer evidence for one canonical work."""
    record = repo.get_work(work_id)
    if record is None:
        raise NotFoundError(f"unknown reassessment work id: {work_id}")
    signal = _primary_signal(record.data)
    evidence = {
        key: deepcopy(signal[key])
        for key in ("viewing", "rating", "reaction", "feedback", "history")
        if key in signal
    }
    return {"work_id": work_id, "viewer_evidence": evidence}



def build_reassessment_modernization_context(
    repo: CanonicalRepository,
    document: Mapping[str, Any],
    *,
    include_blocked: bool = False,
    limit: int = 20,
) -> dict[str, Any]:
    """Return factual operational cards for reviewed works that still need modernization."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    vocabulary_path = repo.media_root / "vocabulary.yaml"
    if not vocabulary_path.exists():
        raise NotFoundError("media vocabulary is missing")
    vocabulary_digest = file_sha256(vocabulary_path.read_bytes())
    frozen = document.get("frozen_cohort") or {}
    frozen_items = frozen.get("items") or {}
    lifecycle = document.get("items") or {}

    candidates: list[tuple[str, int, str, Mapping[str, Any]]] = []
    for work_id, item in lifecycle.items():
        if not isinstance(work_id, str) or not isinstance(item, Mapping) or item.get("status") != "reviewed":
            continue
        modernization = item.get("modernization")
        if modernization is None:
            modernization_status = "due"
        elif isinstance(modernization, Mapping) and modernization.get("status") == "blocked":
            if not include_blocked:
                continue
            modernization_status = "blocked"
        else:
            continue
        reviewed_at = item.get("reviewed_at")
        reviewed_key = reviewed_at if isinstance(reviewed_at, str) else ""
        frozen_item = frozen_items.get(work_id) if isinstance(frozen_items, Mapping) else {}
        rank = frozen_item.get("order_rank") if isinstance(frozen_item, Mapping) else None
        rank_key = rank if isinstance(rank, int) else 10**9
        candidates.append((reviewed_key, rank_key, work_id, item))

    candidates.sort(key=lambda value: (value[0], value[1], value[2]))
    cards: list[dict[str, Any]] = []
    for _, rank_key, work_id, item in candidates[:limit]:
        record = repo.get_work(work_id)
        if record is None:
            continue
        identity = record.data.get("identity") or {}
        metadata = record.data.get("metadata") or {}
        external = metadata.get("external") or {}
        semantic = metadata.get("semantic") or {}
        external_ids = identity.get("external_ids") or {}
        provider_identity = {
            key: deepcopy(external_ids[key])
            for key in ("tmdb", "imdb")
            if key in external_ids
        }
        provider_provenance = external.get("provenance") or {}
        traits = semantic.get("traits") or []
        modernization = item.get("modernization")
        modernization_status = (
            modernization.get("status")
            if isinstance(modernization, Mapping)
            else "due"
        )
        blocker_code = (
            modernization.get("blocker_code")
            if isinstance(modernization, Mapping)
            else None
        )
        frozen_item = frozen_items.get(work_id) if isinstance(frozen_items, Mapping) else {}
        order_rank = frozen_item.get("order_rank") if isinstance(frozen_item, Mapping) else None
        cards.append(
            {
                "work_id": work_id,
                "title": identity.get("title_ru") or identity.get("title_original") or work_id,
                "year": identity.get("year"),
                "reviewed_at": item.get("reviewed_at"),
                "order_rank": order_rank,
                "provider_identity": provider_identity,
                "provider_fetched_at": provider_provenance.get("fetched_at"),
                "semantic_trait_count": len(traits) if isinstance(traits, list) else 0,
                "work_digest": file_sha256(record.path.read_bytes()),
                "vocabulary_digest": vocabulary_digest,
                "modernization_status": modernization_status,
                "blocker_code": blocker_code,
            }
        )

    return {
        "pilot_id": document.get("pilot_id"),
        "ledger_digest": ledger_digest_bytes(ledger_bytes(document)),
        "vocabulary_digest": vocabulary_digest,
        "cards": cards,
    }
