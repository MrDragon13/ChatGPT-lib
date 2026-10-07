from __future__ import annotations

from copy import deepcopy

from media.service.reanalysis_status import (
    EvidenceCheckpoint,
    build_reanalysis_context,
    get_reanalysis_status,
    snapshot_evidence,
)
from media.tools.common import dump_yaml, load_yaml
from tests.media.fixture_repo import copy_fixture_repo


def _work_path(root, work_id="arrival-2016"):
    return root / f"media/data/works/{work_id}.yaml"


def _append_material_event(root, *, work_id="arrival-2016", target="primary", event_no=1, rating=None):
    path = _work_path(root, work_id)
    work = load_yaml(path)
    signals = work.setdefault("viewer_signals", {})
    signal = signals.setdefault(target, {})
    previous = {}
    current = {}
    if rating is not None:
        if "rating" in signal:
            previous["rating"] = deepcopy(signal["rating"])
        incoming = {"score": rating, "source": "explicit", "confidence": "exact"}
        signal["rating"] = incoming
        current["rating"] = deepcopy(incoming)
    else:
        if "viewing" in signal:
            previous["viewing"] = deepcopy(signal["viewing"])
        incoming = {"status": "watched"}
        signal["viewing"] = incoming
        current["viewing"] = deepcopy(incoming)
    signal.setdefault("history", []).append({
        "at": f"2026-10-07T12:{event_no:02d}:00Z",
        "event_id": f"123e4567-e89b-42d3-a456-42661417{event_no:04d}",
        "material_evidence": True,
        "previous": previous,
        "current": current,
    })
    dump_yaml(path, work)


def _append_summary_only_event(root, *, event_no=20):
    path = _work_path(root)
    work = load_yaml(path)
    signal = work.setdefault("viewer_signals", {}).setdefault("primary", {})
    feedback = signal.setdefault("feedback", {"summary": "до", "signals": []})
    previous = {"feedback": deepcopy(feedback)}
    feedback["summary"] = "после"
    signal.setdefault("history", []).append({
        "at": f"2026-10-07T13:{event_no - 20:02d}:00Z",
        "event_id": f"123e4567-e89b-42d3-a456-42661418{event_no:04d}",
        "material_evidence": False,
        "previous": previous,
        "current": {"feedback": deepcopy(feedback)},
    })
    dump_yaml(path, work)


def _write_analysis(root, snapshot, *, target="primary", prefix_digest=None):
    checkpoint = snapshot.checkpoint
    dump_yaml(root / f"media/preferences/inferred/{target}.yaml", {
        "schema_version": 1,
        "target": target,
        "hypotheses": [],
        "updated_at": "2026-10-07T14:00:00Z",
        "analysis": {
            "evidence_checkpoint": {
                "material_event_count": checkpoint.material_event_count,
                "material_event_prefix_digest": prefix_digest or checkpoint.material_event_prefix_digest,
            },
            "evidence_digest": snapshot.evidence_digest,
            "algorithm_version": "media-taste-v1",
        },
    })


def test_threshold_uses_material_events_since_checkpoint(tmp_path):
    root = copy_fixture_repo(tmp_path)
    for index in range(1, 5):
        _append_material_event(root, event_no=index, rating=5.0 + index / 2)

    status = get_reanalysis_status(root / "media", "primary")
    assert status.outstanding_count == 4
    assert status.due is False
    assert status.checkpoint_valid is True

    _append_material_event(root, event_no=5, rating=8.0)
    status = get_reanalysis_status(root / "media", "primary")
    assert status.outstanding_count == 5
    assert status.due is True


def test_summary_only_event_does_not_advance_material_counter(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _append_material_event(root, event_no=1, rating=8.0)
    _append_summary_only_event(root)

    status = get_reanalysis_status(root / "media", "primary")
    assert status.outstanding_count == 1


def test_later_material_update_to_same_work_counts_once_per_event(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _append_material_event(root, event_no=1, rating=8.0)
    _append_material_event(root, event_no=2, rating=9.0)

    status = get_reanalysis_status(root / "media", "primary")
    assert status.outstanding_count == 2


def test_successful_checkpoint_resets_and_later_event_remains_outstanding(tmp_path):
    root = copy_fixture_repo(tmp_path)
    for index in range(1, 6):
        _append_material_event(root, event_no=index, rating=5.0 + index / 2)
    snapshot = snapshot_evidence(root / "media", "primary")
    _write_analysis(root, snapshot)

    status = get_reanalysis_status(root / "media", "primary")
    assert status.outstanding_count == 0
    assert status.due is False
    assert status.checkpoint_valid is True

    _append_material_event(root, event_no=6, rating=9.5)
    status = get_reanalysis_status(root / "media", "primary")
    assert status.outstanding_count == 1
    assert status.due is False
    assert status.checkpoint_valid is True


def test_invalid_prefix_digest_fails_safe_and_requires_reanalysis(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _append_material_event(root, event_no=1, rating=8.0)
    snapshot = snapshot_evidence(root / "media", "primary")
    _write_analysis(root, snapshot, prefix_digest="sha256:" + "0" * 64)

    status = get_reanalysis_status(root / "media", "primary")
    assert status.checkpoint_valid is False
    assert status.due is True


def test_destructive_material_change_without_history_invalidates_checkpoint(tmp_path):
    root = copy_fixture_repo(tmp_path)
    _append_material_event(root, event_no=1, rating=8.0)
    snapshot = snapshot_evidence(root / "media", "primary")
    _write_analysis(root, snapshot)

    path = _work_path(root)
    work = load_yaml(path)
    work["viewer_signals"]["primary"]["rating"]["score"] = 3.0
    dump_yaml(path, work)

    status = get_reanalysis_status(root / "media", "primary")
    assert status.checkpoint_valid is False
    assert status.due is True


def test_snapshot_checkpoint_is_stable_and_content_bound(tmp_path):
    root = copy_fixture_repo(tmp_path)
    first = snapshot_evidence(root / "media", "primary")
    second = snapshot_evidence(root / "media", "primary")
    assert first == second
    assert isinstance(first.checkpoint, EvidenceCheckpoint)
    assert first.checkpoint.material_event_count == 0

    _append_material_event(root, event_no=1, rating=8.0)
    changed = snapshot_evidence(root / "media", "primary")
    assert changed.checkpoint.material_event_count == 1
    assert changed.checkpoint.material_event_prefix_digest != first.checkpoint.material_event_prefix_digest
    assert changed.evidence_digest != first.evidence_digest


def test_couple_reanalysis_context_uses_member_counters_without_third_counter(tmp_path):
    root = copy_fixture_repo(tmp_path)
    for index in range(5):
        _append_material_event(root, target="primary", event_no=index + 1, rating=7.0 + index / 2)

    context = build_reanalysis_context(root / "media", "couple")

    assert context["target"] == "couple"
    assert context["due"] is True
    assert set(context["members"]) == {"primary", "partner"}
    assert context["members"]["primary"]["due"] is True
    assert context["members"]["partner"]["due"] is False
    assert "outstanding_count" not in context
