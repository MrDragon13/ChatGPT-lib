from __future__ import annotations

import hashlib
import json
from pathlib import Path

from media.repository.canonical import WorkRecord
from media.service.reassessment import (
    ALLOWED_COHORT_VIEWING,
    PILOT_ID,
    build_frozen_cohort,
    build_initial_ledger,
    feedback_state_digest,
    file_sha256,
    frozen_order_key,
    frozen_stratum,
    ledger_bytes,
    ledger_digest_bytes,
)


class FakeRepo:
    def __init__(self, works):
        self._works = list(works)

    def iter_works(self):
        yield from self._works


def work(work_id: str, status: str, score=None, *, source="explicit", extra=None) -> WorkRecord:
    signal = {"viewing": {"status": status}}
    if score is not None:
        signal["rating"] = {"score": score, "source": source, "confidence": "exact" if source == "explicit" else "medium"}
    if extra:
        signal.update(extra)
    document = {
        "id": work_id,
        "identity": {"title_original": work_id, "year": 2000},
        "viewer_signals": {"primary": signal},
    }
    return WorkRecord(Path(f"/repo/media/data/works/{work_id}.yaml"), document)


def test_digest_helpers_are_deterministic_and_scope_feedback_state():
    first = {"z": 1, "nested": {"b": 2, "a": 1}}
    second = {"nested": {"a": 1, "b": 2}, "z": 1}
    payload = ledger_bytes(first)
    assert payload == ledger_bytes(second)
    assert payload.endswith(b"\n")
    assert ledger_digest_bytes(payload) == "sha256:" + hashlib.sha256(payload).hexdigest()
    assert ledger_digest_bytes(ledger_bytes({**first, "z": 2})) != ledger_digest_bytes(payload)

    signal_a = {
        "feedback": {"signals": [], "summary": "ok"},
        "rating": {"confidence": "exact", "source": "explicit", "score": 8.0},
        "viewing": {"status": "watched"},
        "history": [{"ignored": True}],
    }
    signal_b = {
        "history": [{"different": True}],
        "viewing": {"status": "watched"},
        "rating": {"score": 8.0, "source": "explicit", "confidence": "exact"},
        "feedback": {"summary": "ok", "signals": []},
        "unrelated": "ignored",
    }
    assert feedback_state_digest(signal_a) == feedback_state_digest(signal_b)
    signal_b["feedback"] = {"summary": "changed", "signals": []}
    assert feedback_state_digest(signal_a) != feedback_state_digest(signal_b)

    raw = b"schema_version: 4\nid: example\n"
    assert file_sha256(raw) == "sha256:" + hashlib.sha256(raw).hexdigest()


def test_cohort_membership_uses_viewing_status_not_legacy_summary():
    assert ALLOWED_COHORT_VIEWING == {"watched", "partial", "dropped", "forgotten"}
    records = [
        work("watched", "watched", 8.0),
        work("partial", "partial", 7.0),
        work("dropped", "dropped", 4.0),
        work("forgotten", "forgotten", None),
        work("unwatched-with-text", "unwatched", None, extra={"feedback": {"summary": "Не смотрел.", "signals": []}}),
    ]
    cohort = build_frozen_cohort(FakeRepo(records), pilot_id=PILOT_ID)
    assert set(cohort["work_ids"]) == {"watched", "partial", "dropped", "forgotten"}
    assert "unwatched-with-text" not in cohort["items"]


def test_frozen_strata_follow_approved_rating_boundaries_and_special_precedence():
    assert frozen_stratum(work("x", "dropped", 9.5).data["viewer_signals"]["primary"]) == "special"
    assert frozen_stratum(work("x", "partial", None).data["viewer_signals"]["primary"]) == "special"
    assert frozen_stratum(work("x", "forgotten", 5.0).data["viewer_signals"]["primary"]) == "special"
    assert frozen_stratum(work("x", "watched", 6.5).data["viewer_signals"]["primary"]) == "low"
    assert frozen_stratum(work("x", "watched", 7.0).data["viewer_signals"]["primary"]) == "medium_low"
    assert frozen_stratum(work("x", "watched", 7.5).data["viewer_signals"]["primary"]) == "medium_low"
    assert frozen_stratum(work("x", "watched", 8.0).data["viewer_signals"]["primary"]) == "central"
    assert frozen_stratum(work("x", "watched", 8.5).data["viewer_signals"]["primary"]) == "central"
    assert frozen_stratum(work("x", "watched", 9.0).data["viewer_signals"]["primary"]) == "high"
    assert frozen_stratum(work("x", "watched", None).data["viewer_signals"]["primary"]) == "unrated_viewed"


def test_order_key_and_stratified_round_robin_are_deterministic():
    records = [
        work("special-a", "partial", 8.0),
        work("special-b", "dropped", 3.0),
        work("low-a", "watched", 6.0),
        work("low-b", "watched", 5.0),
        work("medium-a", "watched", 7.5),
        work("central-a", "watched", 8.5),
        work("high-a", "watched", 9.5),
        work("unrated-a", "watched", None),
    ]
    cohort = build_frozen_cohort(FakeRepo(records), pilot_id=PILOT_ID)
    reversed_cohort = build_frozen_cohort(FakeRepo(reversed(records)), pilot_id=PILOT_ID)
    assert cohort == reversed_cohort

    expected_key = "sha256:" + hashlib.sha256(f"{PILOT_ID}\0central-a".encode()).hexdigest()
    assert frozen_order_key(PILOT_ID, "central-a") == expected_key
    assert cohort["items"]["central-a"]["order_key"] == expected_key

    first_round = cohort["work_ids"][:6]
    assert {cohort["items"][work_id]["stratum"] for work_id in first_round} == {
        "special", "low", "medium_low", "central", "high", "unrated_viewed"
    }
    assert sorted(item["order_rank"] for item in cohort["items"].values()) == list(range(len(records)))

    for stratum in {item["stratum"] for item in cohort["items"].values()}:
        ids = [work_id for work_id in cohort["work_ids"] if cohort["items"][work_id]["stratum"] == stratum]
        assert ids == sorted(ids, key=lambda work_id: (cohort["items"][work_id]["order_key"], work_id))


def test_frozen_cohort_stores_only_reference_metadata_needed_for_pilot():
    record = work(
        "movie-a",
        "watched",
        8.0,
        source="inferred",
        extra={"feedback": {"summary": "legacy", "signals": []}, "reaction": {"value": "liked", "source": "inferred", "confidence": "medium"}},
    )
    signal = record.data["viewer_signals"]["primary"]
    cohort = build_frozen_cohort(FakeRepo([record]), pilot_id=PILOT_ID)
    item = cohort["items"]["movie-a"]
    assert item == {
        "viewing_status": "watched",
        "stratum": "central",
        "order_key": frozen_order_key(PILOT_ID, "movie-a"),
        "order_rank": 0,
        "pre_pilot_feedback_digest": feedback_state_digest(signal),
    }
    assert "rating" not in item
    assert "feedback" not in item


def test_initial_ledger_is_pending_and_preserves_baseline_provenance():
    repo = FakeRepo([work("low", "watched", 6.0), work("high", "watched", 9.0)])
    ledger = build_initial_ledger(
        repo,
        pilot_id=PILOT_ID,
        base_revision="35afaca898eae6937066f230906b41af0e1f6690",
        baseline_path="media/baselines/intelligence-stage-a.json",
        baseline_document={"schema_version": 2, "canonical_input_digest": "sha256:" + "9" * 64},
    )
    assert ledger["schema_version"] == 1
    assert ledger["pilot_id"] == PILOT_ID
    assert ledger["pilot_status"] == "active"
    assert ledger["target"] == "primary"
    assert ledger["base_revision"] == "35afaca898eae6937066f230906b41af0e1f6690"
    assert ledger["baseline_path"] == "media/baselines/intelligence-stage-a.json"
    assert ledger["baseline_schema_version"] == 2
    assert ledger["baseline_canonical_input_digest"] == "sha256:" + "9" * 64
    assert ledger["frozen_cohort"]["cohort_revision"] == ledger["base_revision"]
    assert set(ledger["items"]) == {"low", "high"}
    assert all(item == {"status": "pending"} for item in ledger["items"].values())
    assert ledger["sessions"] == []
    assert ledger["scheduled_reanalysis"] == {"last_completed": None}


def test_ledger_bytes_are_valid_utf8_json_with_trailing_newline():
    document = {"schema_version": 1, "pilot_id": PILOT_ID, "note": "кино"}
    payload = ledger_bytes(document)
    assert json.loads(payload.decode("utf-8")) == document
    assert payload.decode("utf-8").endswith("\n")
