import pytest

from media.domain.errors import PathPolicyError
from media.service.path_policy import verify_changed_paths


def test_edit_feedback_allows_only_work_generated_and_receipt_paths():
    verify_changed_paths("edit_viewing_feedback", [
        "media/data/works/arrival-2016.yaml",
        "media/generated/index.jsonl",
        "media/generated/profiles/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174001.json",
    ])
    with pytest.raises(PathPolicyError):
        verify_changed_paths("edit_viewing_feedback", ["media/preferences/inferred/primary.yaml"])


def test_existing_feedback_operation_cannot_modify_future_intelligence_paths():
    for path in (
        "media/preferences/inferred/primary.yaml",
        "media/data/interactions/2026-10.jsonl",
    ):
        with pytest.raises(PathPolicyError):
            verify_changed_paths("record_viewing_feedback", [path])


def test_similarity_operations_allow_only_relation_and_receipt_paths():
    allowed = [
        "media/data/relations/similarity/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174040.json",
    ]
    verify_changed_paths("set_work_similarity", allowed)
    verify_changed_paths("remove_work_similarity", allowed)

    for operation in ("set_work_similarity", "remove_work_similarity"):
        for forbidden in (
            "media/data/works/arrival-2016.yaml",
            "media/generated/index.jsonl",
            "media/preferences/inferred/primary.yaml",
        ):
            with pytest.raises(PathPolicyError):
                verify_changed_paths(operation, [forbidden])


def test_work_creation_paths_allow_similarity_reconciliation_but_regular_edits_do_not():
    relation_path = "media/data/relations/similarity/primary.yaml"
    verify_changed_paths("add_work", [relation_path])
    verify_changed_paths("record_viewing_feedback", [relation_path])

    for operation in ("edit_viewing_feedback", "set_interest", "set_semantic_fingerprint"):
        with pytest.raises(PathPolicyError):
            verify_changed_paths(operation, [relation_path])
