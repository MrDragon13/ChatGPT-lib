from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).parents[2]
WORKFLOWS=ROOT/".github"/"workflows"


def _text(name:str)->str:
    return (WORKFLOWS/name).read_text(encoding="utf-8")


def _policy()->dict:
    return json.loads((ROOT/"media/config/operation_path_policy.json").read_text(encoding="utf-8"))


def test_media_command_has_same_repo_branch_guard_before_secrets():
    text=_text("media-command.yml")
    assert "github.event.pull_request.head.repo.full_name == github.repository" in text
    assert "startsWith(github.head_ref, 'media/op-')" in text
    assert "TMDB_READ_TOKEN" in text
    assert "OPENAI" not in text.upper()
    assert "pull-requests: write" in text
    assert "actions: write" in text


def test_media_command_serializes_data_writes_without_cancelling_pending_runs():
    text=_text("media-command.yml")
    concurrency=text.split("concurrency:",1)[1].split("jobs:",1)[0]
    assert "group: media-data-pipeline" in concurrency
    assert "cancel-in-progress: false" in concurrency
    assert "queue: max" in concurrency


def test_media_command_requires_one_request_and_replays_on_fresh_main():
    text=_text("media-command.yml")
    assert "Resolve pending or already-applied request" in text
    assert "Expected exactly one pending request or a recognized data: apply media operation commit" in text
    assert "find .media/requests -maxdepth 1 -type f -name '*.json'" in text
    assert "Replay v6 operation on latest main" in text
    assert "git fetch origin main" in text
    assert "git reset --hard" in text
    assert "MAX_ATTEMPTS" in text
    assert "current_main" in text


def test_provider_secret_is_exposed_only_when_operation_needs_provider():
    text=_text("media-command.yml")
    assert "needs_provider" in text
    assert "create_if_missing" in text
    assert "operation == 'add_work'" in text
    assert "operation == 'refresh_metadata'" in text
    assert "operation == 'refresh_work_metadata'" in text
    assert "'record_media_entry'" in text
    assert "steps.operation.outputs.needs_provider == 'true'" in text


def test_all_auto_merge_operations_use_single_runner_and_manual_refresh_stays_manual():
    operations=_policy()["operations"]
    assert not any("reassessment" in name for name in operations)
    for name,entry in operations.items():
        if entry["auto_merge"]:
            assert entry["execution_class"]=="v6_single_runner", name
        else:
            assert name=="refresh_metadata"
            assert entry["execution_class"]=="manual_review"


def test_single_runner_has_targeted_authoritative_gate_and_exact_head_merge():
    text=_text("media-command.yml")
    fast=text.split("- name: Replay v6 operation on latest main",1)[1].split("- name: Replay branch on current main",1)[0]
    assert "python -m media.tools.validate ." in fast
    assert "python -m media.cli rebuild --check" in fast
    for operation in (
        "record_media_entry",
        "set_inferred_preferences",
        "add_work",
        "edit_viewing_feedback|set_interest",
        "set_semantic_fingerprint",
        "record_recommendation_interaction",
        "set_work_similarity|remove_work_similarity",
        "refresh_work_metadata",
    ):
        assert operation in fast
    assert "tests/media/test_command_contracts.py" in fast
    assert "tests/media/test_path_policy.py" in fast
    assert "python -m pytest -q" not in fast
    assert "media.cli doctor" not in fast
    assert "Merge checked v6 operation" in fast
    assert 'pulls/$PR_NUMBER/merge' in fast
    assert '{"sha": "$HEAD_SHA", "merge_method": "merge"}' in fast
    assert "git push origin HEAD:main" not in fast
    assert "gh pr merge --auto" not in fast


def test_single_runner_dispatches_pages_for_exact_merge_sha():
    text=_text("media-command.yml")
    fast=text.split("- name: Replay v6 operation on latest main",1)[1].split("- name: Replay branch on current main",1)[0]
    assert "media-pages.yml" in fast
    assert 'expected_sha="$MERGE_SHA"' in fast
    assert "publish_mode=media" in fast


def test_media_command_has_no_dependency_on_removed_legacy_workflows():
    text=_text("media-command.yml")
    assert "media-check.yml" not in text
    assert "media-auto-merge.yml" not in text
    assert not (WORKFLOWS/"media-check.yml").exists()
    assert not (WORKFLOWS/"media-auto-merge.yml").exists()


def test_manual_refresh_metadata_is_verified_and_left_for_review():
    text=_text("media-command.yml")
    assert "steps.operation.outputs.execution_class == 'manual_review'" in text
    assert "python -m pytest -q" in text
    assert "python -m media.tools.validate ." in text
    assert "python -m media.cli rebuild --check" in text
    assert "python -m media.cli doctor --format json" in text
    assert "Leave manual operation ready for review" in text
    assert "No automatic merge is attempted for this execution class." in text


def test_media_command_stages_canonical_and_derived_outputs_without_legacy_pilot():
    text=_text("media-command.yml")
    for path in (
        "media/data/works",
        "media/generated/index.jsonl",
        "media/generated/profiles",
        ".media/operations",
        "media/data/interactions",
        "media/preferences/inferred",
        "media/data/relations/similarity",
    ):
        assert path in text
    assert "media/pilots" not in text


def test_media_dev_check_triggers_when_trusted_path_policy_changes():
    text=_text("media-dev-check.yml")
    trigger_block=text.split("on:",1)[1].split("permissions:",1)[0]
    assert "media/config/operation_path_policy.json" in trigger_block


def test_maintenance_is_manual_and_read_only():
    text=_text("media-maintenance.yml")
    assert "workflow_dispatch:" in text
    assert "contents: read" in text
    assert "contents: write" not in text
    assert "doctor" in text
    assert "rebuild --check" in text


def test_broker_check_is_read_only_and_secret_free():
    text=_text("broker-check.yml")
    assert "contents: read" in text
    assert "contents: write" not in text
    assert "npm ci" in text
    assert "npm run test:run" in text
    assert "npm run typecheck" in text
    assert "CLOUDFLARE_API_TOKEN" not in text
    assert "GITHUB_APP_PRIVATE_KEY" not in text
    assert "GITHUB_APP_CLIENT_SECRET" not in text


def test_broker_deploy_is_manual_main_sha_gated_and_uses_only_cloudflare_deploy_secrets():
    text=_text("broker-deploy.yml")
    assert "workflow_dispatch:" in text
    assert "expected_sha" in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "git rev-parse HEAD" in text
    assert "npm ci" in text
    assert "npm run test:run" in text
    assert "npm run typecheck" in text
    assert "wrangler deploy" in text
    assert "secrets.CLOUDFLARE_API_TOKEN" in text
    assert "secrets.CLOUDFLARE_ACCOUNT_ID" in text
    assert "GITHUB_APP_PRIVATE_KEY" not in text
    assert "GITHUB_APP_CLIENT_SECRET" not in text


def test_pages_deploy_remains_independent_of_cloudflare_credentials():
    text=_text("media-pages.yml")
    assert "CLOUDFLARE_API_TOKEN" not in text
    assert "CLOUDFLARE_ACCOUNT_ID" not in text

def test_single_runner_replay_shell_is_syntax_valid():
    import subprocess
    import yaml

    workflow = yaml.safe_load(_text("media-command.yml"))
    steps = workflow["jobs"]["apply"]["steps"]
    replay = next(step for step in steps if step.get("name") == "Replay v6 operation on latest main")
    result = subprocess.run(
        ["bash", "-n"],
        input=replay["run"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr



def test_single_runner_waits_for_github_mergeability_after_force_push():
    text=_text("media-command.yml")
    fast=text.split("- name: Replay v6 operation on latest main",1)[1].split("- name: Replay branch on current main",1)[0]
    assert "Wait for GitHub PR mergeability" in fast
    assert "MAX_MERGE_READY_ATTEMPTS" in fast
    assert 'repos/$REPO/pulls/$PR_NUMBER' in fast
    assert ".head.sha" in fast
    assert ".base.sha" in fast
    assert ".mergeable" in fast
    assert "sleep 2" in fast


def test_single_runner_handles_merge_api_failure_without_set_e_short_circuit():
    text=_text("media-command.yml")
    fast=text.split("- name: Replay v6 operation on latest main",1)[1].split("- name: Replay branch on current main",1)[0]
    merge_call=fast.index('gh api --method PUT "repos/$REPO/pulls/$PR_NUMBER/merge"')
    before=fast[max(0,merge_call-400):merge_call]
    after=fast[merge_call:merge_call+1200]
    assert "set +e" in before
    assert "MERGE_STATUS=$?" in after
    assert "set -e" in after
    assert '"$MERGE_STATUS" -eq 0' in after
    assert ".merged == true" in after
    assert "Merge API was not ready" in after


def test_single_runner_tolerates_stale_pr_head_after_force_push():
    text = _text("media-command.yml")
    guard = text.split('if [ "$PR_HEAD_SHA" != "$HEAD_SHA" ]; then', 1)[1].split("fi", 1)[0]
    assert 'git ls-remote origin "refs/heads/$BRANCH"' in guard
    assert "continue" in guard
    assert "stale PR API head" in guard
    assert "exit 5" not in guard


def test_single_runner_can_recover_request_from_already_applied_branch():
    text = _text("media-command.yml")
    assert "Recover request from applied branch" in text
    assert "data: apply media operation" in text
    assert "git show" in text
    assert "already-applied branch" in text
