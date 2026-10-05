from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

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
