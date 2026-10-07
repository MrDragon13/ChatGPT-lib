from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_media_command_stages_pilot_state_and_dispatches_exact_head_with_replay_base():
    text = _text("media-command.yml")
    assert "media/pilots" in text
    assert "base_sha=$(git rev-parse origin/main)" in text
    assert "steps.replay.outputs.base_sha" in text
    assert '-f expected_sha="$HEAD_SHA" -f base_sha="$BASE_SHA"' in text


def test_media_command_applies_operation_specific_shape_guard_before_commit():
    text = _text("media-command.yml")
    assert "verify_operation_specific_paths" in text
    assert "operation_id" in text
    assert ".media/operations" in text


def test_media_check_accepts_base_sha_fetches_history_and_runs_transition_validator_for_changed_ledger():
    text = _text("media-check.yml")
    assert "base_sha:" in text
    assert "required: true" in text.split("base_sha:", 1)[1].split("permissions:", 1)[0]
    assert "fetch-depth: 0" in text
    assert "git fetch origin main" in text
    assert "git merge-base --is-ancestor" in text
    assert "media/pilots/legacy-reassessment-primary.json" in text
    assert "git diff --name-only" in text
    assert "git show" in text
    assert "expected_ledger_digest" in text
    assert "python -m media.tools.validate_reassessment_transition" in text
    assert "--operation-receipt" in text
    assert "contents: read" in text
    assert "contents: write" not in text


def test_media_check_fails_closed_if_operation_changes_ledger_without_base_ledger_or_unique_receipt():
    text = _text("media-check.yml")
    assert "Base reassessment ledger is missing" in text
    assert "Expected exactly one operation receipt" in text
    assert "Base ledger digest does not match operation receipt" in text


def test_privileged_auto_merge_revalidates_current_main_ledger_digest_for_all_pilot_operations():
    text = _text("media-auto-merge.yml")
    for operation in (
        "reserve_reassessment_session",
        "complete_reassessment_item",
        "close_reassessment_session",
    ):
        assert f'[ "$OP_KIND" = "{operation}" ]' in text
    assert 'case "$OP_KIND" in' not in text
    assert "legacy-reassessment-primary.json?ref=main" in text
    assert "expected_ledger_digest" in text
    assert "sha256sum" in text
    assert "stale reassessment ledger" in text.lower()


def test_privileged_auto_merge_revalidates_reserve_and_complete_work_raw_digests_and_changed_file_shape():
    text = _text("media-auto-merge.yml")
    assert "reserved_items" in text
    assert "pre_review_work_file_digest" in text
    assert "media/data/works/$WORK_ID.yaml?ref=main" in text
    assert "Stale reserved work during reassessment reservation" in text
    assert "complete_reassessment_item may change at most one work" in text
    assert "reserved work path" in text.lower()


def test_privileged_pilot_guards_use_shell_and_github_contents_not_pr_head_python():
    text = _text("media-auto-merge.yml")
    pilot_block = text.split("Pilot stale-state and work-file guards", 1)[1].split("echo \"eligible=true\"", 1)[0]
    assert "gh api" in pilot_block
    assert "jq" in pilot_block
    assert "python" not in pilot_block.lower()


def test_media_command_treats_single_work_refresh_as_provider_dependent():
    text = _text("media-command.yml")
    assert "operation == 'refresh_work_metadata'" in text


def test_media_check_accepts_only_dedicated_modernization_operation_for_modernization_ledger_transition():
    text = _text("media-check.yml")
    assert "record_reassessment_modernization" in text
    assert "Pilot ledger changed under non-reassessment operation" in text
