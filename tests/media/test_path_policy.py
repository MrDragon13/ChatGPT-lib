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
