from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_agent_contract_routes_legacy_reassessment_without_exposing_old_opinion_first():
    text = _text("media/AGENTS.md")
    assert "legacy reassessment" in text.lower()
    assert "reassessment-context" in text
    assert "reassessment-history" in text
    assert "reserve_reassessment_session" in text
    assert "complete_reassessment_item" in text
    assert "close_reassessment_session" in text
    assert "old rating" in text.lower() or "old opinion" in text.lower()
    assert "semantic" in text.lower()


def test_start_prompt_preserves_neutral_memory_jog_and_unanchored_first_answer():
    text = _text("media/START_PROMPT.md")
    assert "переоцен" in text.lower()
    assert "нейтраль" in text.lower()
    assert "стар" in text.lower()
    assert "перв" in text.lower()


def test_runbook_states_pilot_lifecycle_cadence_and_no_semantic_backfill():
    text = _text("docs/runbooks/media-legacy-reassessment.md")
    for phrase in (
        "5",
        "15",
        "pending",
        "deferred",
        "confirmed_unchanged",
        "expected_ledger_digest",
        "Stage A",
        "semantic",
        "reassessment-context",
        "reassessment-history",
    ):
        assert phrase.lower() in text.lower()


def test_architecture_and_reference_docs_name_pilot_boundaries_and_typed_operations():
    intelligence = _text("docs/architecture/intelligence.md")
    pipeline = _text("docs/architecture/write-pipeline.md")
    commands = _text("docs/reference/media-commands.md")
    for operation in (
        "reserve_reassessment_session",
        "complete_reassessment_item",
        "close_reassessment_session",
    ):
        assert operation in pipeline
        assert operation in commands
    assert "semantic" in intelligence.lower()
    assert "legacy reassessment" in intelligence.lower()
    assert "expected_ledger_digest" in pipeline


def test_status_says_foundation_is_implemented_but_pilot_not_yet_activated():
    text = _text("docs/status/current.md").lower()
    assert "reassessment" in text
    assert "foundation" in text
    assert "not activated" in text or "не актив" in text
    assert "35afaca898eae6937066f230906b41af0e1f6690" in text


def test_docs_define_expected_profile_drift_against_frozen_stage_a_baseline():
    combined = "\n".join(
        _text(path)
        for path in (
            "docs/architecture/intelligence.md",
            "docs/runbooks/media-legacy-reassessment.md",
            "docs/status/current.md",
        )
    ).lower()
    assert "profile" in combined
    assert "drift" in combined
    assert "stage a" in combined
    assert "baseline" in combined
