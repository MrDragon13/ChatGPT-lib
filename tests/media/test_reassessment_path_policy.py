from __future__ import annotations

import pytest

from media.domain.errors import PathPolicyError
from media.service.path_policy import verify_changed_paths, verify_operation_specific_paths


LEDGER = "media/pilots/legacy-reassessment-primary.json"
RECEIPT = ".media/operations/123e4567-e89b-42d3-a456-426614174001.json"


def test_existing_operations_cannot_modify_reassessment_ledger():
    for operation in (
        "add_work",
        "record_viewing_feedback",
        "edit_viewing_feedback",
        "set_interest",
        "set_semantic_fingerprint",
        "set_inferred_preferences",
        "record_recommendation_interaction",
        "set_work_similarity",
        "remove_work_similarity",
    ):
        with pytest.raises(PathPolicyError):
            verify_changed_paths(operation, [LEDGER])


def test_reserve_and_close_allow_only_exact_ledger_and_receipt():
    for operation in ("reserve_reassessment_session", "close_reassessment_session"):
        verify_changed_paths(operation, [LEDGER, RECEIPT])
        for forbidden in (
            "media/pilots/other.json",
            "media/data/works/arrival-2016.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/primary.yaml",
            "media/preferences/inferred/primary.yaml",
        ):
            with pytest.raises(PathPolicyError):
                verify_changed_paths(operation, [forbidden])


def test_complete_allows_narrow_feedback_side_effect_paths_but_no_semantic_or_preference_paths():
    allowed = [
        LEDGER,
        "media/data/works/arrival-2016.yaml",
        "media/generated/index.jsonl",
        "media/generated/profiles/primary.yaml",
        RECEIPT,
    ]
    verify_changed_paths("complete_reassessment_item", allowed)
    verify_operation_specific_paths(
        "complete_reassessment_item",
        allowed,
        {"work_id": "arrival-2016"},
    )

    for forbidden in (
        "media/vocabulary.yaml",
        "media/preferences/inferred/primary.yaml",
        "media/data/relations/similarity/primary.yaml",
        "media/data/works/arrival-2016.yaml.bak",
    ):
        with pytest.raises(PathPolicyError):
            verify_changed_paths("complete_reassessment_item", [forbidden])


def test_complete_shape_guard_rejects_wrong_or_multiple_work_files_even_when_wildcard_matches():
    with pytest.raises(PathPolicyError, match="reserved work"):
        verify_operation_specific_paths(
            "complete_reassessment_item",
            [LEDGER, "media/data/works/batman-2022.yaml", RECEIPT],
            {"work_id": "arrival-2016"},
        )

    with pytest.raises(PathPolicyError, match="at most one"):
        verify_operation_specific_paths(
            "complete_reassessment_item",
            [
                LEDGER,
                "media/data/works/arrival-2016.yaml",
                "media/data/works/batman-2022.yaml",
                RECEIPT,
            ],
            {"work_id": "arrival-2016"},
        )


def test_complete_shape_guard_requires_planner_work_id_when_a_work_changes():
    with pytest.raises(PathPolicyError, match="work_id"):
        verify_operation_specific_paths(
            "complete_reassessment_item",
            [LEDGER, "media/data/works/arrival-2016.yaml", RECEIPT],
            {},
        )
